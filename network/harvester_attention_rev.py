import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from network.high_match_net import TransformerEncoder
from network.base_net import MLP

class HarvesterAttention(nn.Module):
    """
    农机-加油车自注意力重定位模型（输出4方向概率）
    核心逻辑：
    1. 输入：农机总特征（空间方位+自身特征） + 上下文不定长序列
    2. 空间特征→相对x/y坐标（V向量，直接取前两位）
    3. 上下文序列→TransformerEncoder→Pooling→与农机特征拼接
    4. 自注意力计算→重定位向量（x/y坐标）
    5. 计算向量的单位方向和长度
    6. 与4个固定方向做点积→加权长度→softmax→4方向概率
    """
    def __init__(self, d_self_features: int, d_context_in: int, d_context_hidden: int = 32, d_k: int = 16):
        super().__init__()
        self.d_x_dim = 2 + d_self_features  # x特征维度（2空间+自身特征）
        self.d_context_hidden = d_context_hidden
        self.d_model = self.d_x_dim + d_context_hidden  # Q/K输入总维度
        self.d_k = d_k
        self.d_v = 2  # V的维度：相对x/y坐标

        # 上下文处理模块
        self.context_encoder = TransformerEncoder(
            input_dim=d_context_in,
            d_model=d_context_hidden, nhead=2, num_layers=2)

        # Q/K映射线性层
        self.W_q = nn.Linear(self.d_model, d_k)
        self.W_k = nn.Linear(self.d_model, d_k)

        # 初始化权重
        nn.init.xavier_uniform_(self.W_q.weight)
        nn.init.xavier_uniform_(self.W_k.weight)
        nn.init.zeros_(self.W_q.bias)
        nn.init.zeros_(self.W_k.bias)

        # 定义4个固定方向向量（右、左、上、下），shape=(1, 2, 4)（适配batch和点积计算）
        self.fixed_directions = nn.Parameter(
            torch.tensor([[[1, -1, 0, 0],  # x轴方向：右(1,0)、左(-1,0)
                          [0, 0, 1, -1]]],  # y轴方向：上(0,1)、下(0,-1)
                        dtype=torch.float32),
            requires_grad=False  # 固定方向，不参与训练
        )
        
        self.stay_head = MLP(input_dim=1, hidden_dims=[128], output_dim=1)
        
        # 可学习的温度系数，控制Softmax的尖锐程度
        # self.temperature = nn.Parameter(torch.tensor(5.0)) 

    def forward(self, x: torch.Tensor, context: torch.Tensor, mask: torch.Tensor = None) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        前向传播
        Args:
            x: 农机特征 (batch_size, num_agri, 2 + d_self)
            context: 上下文序列 (batch_size, seq_len, d_context_in)
            mask: 掩码 (batch_size, num_agri), True表示有效, False表示padding
        Returns:
            reposition_vec: 重定位原始向量（x/y坐标），shape=(batch_size, 2)
            attn_weights: 注意力权重，shape=(batch_size, N, N)
            direction_probs: 4方向概率（右、左、上、下），shape=(batch_size, 4)
            vec_length: 重定位向量的长度（距离），shape=(batch_size, 1)
        """
        batch_size, num_agri, d_x_dim = x.shape

        # 1. 处理上下文数据
        # Transformer编码
        ctx_encoded = self.context_encoder(context)
        # Pooling (平均池化) -> (B, C_hidden)
        ctx_pooled = ctx_encoded.mean(dim=1)
        
        # 拼接上下文特征到x
        # (B, C_hidden) -> (B, N, C_hidden)
        ctx_expanded = ctx_pooled.unsqueeze(1).expand(-1, num_agri, -1)
        # (B, N, d_x) + (B, N, C_hidden) -> (B, N, d_model)
        x_combined = torch.cat([x, ctx_expanded], dim=-1)

        # 2. 获取V向量 (直接取前两位: relative_x, relative_y)
        V = x[:, :, :2]

        # 3. 计算Q/K/注意力权重 (使用拼接后的特征)
        Q = self.W_q(x_combined)
        K = self.W_k(x_combined)
        attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        
        if mask is not None:
            # mask: (B, N). True为有效数据.
            # 扩展维度以匹配attn_scores (B, N, N)
            # 我们屏蔽掉无效的Key (最后一维)
            mask_expanded = mask.unsqueeze(1) # (B, 1, N)
            attn_scores = attn_scores.masked_fill(~mask_expanded, float('-inf'))
        
        attn_weights = F.softmax(attn_scores, dim=-1)
        
        if mask is not None:
            attn_weights = torch.nan_to_num(attn_weights, nan=0.0)

        # 4. 聚合 (使用 Mean Pooling 防止数值爆炸)
        weighted_v = torch.matmul(attn_weights, V)
        
        if mask is not None:
            # 对Query维度(dim=1)进行Masked Mean
            mask_float = mask.unsqueeze(-1).float() # (B, N, 1)
            weighted_v = weighted_v * mask_float
            sum_v = weighted_v.sum(dim=1)
            count = mask_float.sum(dim=1).clamp(min=1e-9)
            reposition_vec = sum_v / count
        else:
            reposition_vec = weighted_v.mean(dim=1) 

        # ------------------------------ 新增：4方向概率计算 ------------------------------
        # 5. 计算重定位向量的长度（L2范数），加epsilon避免除0
        vec_length = torch.norm(reposition_vec, p=2, dim=-1, keepdim=True)  # (batch_size, 1)
        
        stay_score = self.stay_head(vec_length)  # (batch_size, 1)
        

        # 6. 与4个固定方向做点积（批量计算，shape广播：(B,2) × (1,2,4) → (B,4)）
        # 点积公式：a·b = a_x*b_x + a_y*b_y
        # 直接使用reposition_vec，包含了长度信息
        dot_products = torch.matmul(reposition_vec.unsqueeze(1), self.fixed_directions).squeeze(1)  # (batch_size, 4)
        # 对应关系：dot_products[:,0]→右，[:,1]→左，[:,2]→上，[:,3]→下

        weighted_scores = torch.cat([dot_products, stay_score], dim=-1)  # (batch_size, 5)

        # 8. softmax归一化，得到5方向概率
        direction_probs = F.softmax(weighted_scores, dim=-1)  # (batch_size, 5)
        # --------------------------------------------------------------------------------

        return reposition_vec, attn_weights, direction_probs, vec_length


# ------------------------------ 测试示例 ------------------------------
if __name__ == "__main__":
    # 配置参数
    batch_size = 2
    num_agri = 5
    d_self = 2  # 自身特征维度（工作时长、上次加油时间）
    d_context_in = 10 # 上下文特征维度
    d_k = 16

    # 构造测试数据
    # x: 前2位为相对坐标(x,y)，后面为自身特征
    spatial_features = torch.randn(batch_size, num_agri, 2) * 100 # relative x, y
    self_features = torch.rand(batch_size, num_agri, d_self) * torch.tensor([10, 24])
    x = torch.cat([spatial_features, self_features], dim=-1)
    
    # context数据
    context = torch.randn(batch_size, 8, d_context_in) # seq_len=8

    # mask数据
    mask = torch.tensor([[True, True, True, False, False],
                         [True, True, False, False, False]])

    # 初始化模型
    model = HarvesterAttention(d_self_features=d_self, d_context_in=d_context_in, d_k=d_k)

    # 前向传播
    reposition_vec, attn_weights, direction_probs, vec_length = model(x, context, mask=mask)

    # 输出结果
    print("="*70)
    print(f"重定位原始向量（x/y坐标）：")
    print(reposition_vec.round(2))
    print("="*70)
    print(f"向量长度（距离）：")
    print(vec_length.round(2))
    print("="*70)
    print(f"4方向概率（右、左、上、下）：")
    print(direction_probs.round(3))
    print(f"概率和验证（应接近1.0）：{direction_probs.sum(dim=1).round(3)}")
    print("="*70)
    print("第一个batch的注意力权重：")
    print(attn_weights[0].round(3))
    print("="*70)

    # 验证逻辑正确性（以第一个batch为例）
    print("逻辑验证（第一个batch）：")
    vec = reposition_vec[0].numpy()
    length = vec_length[0].item()
    unit_vec = vec / (length + 1e-8)
    directions = [(1,0), (-1,0), (0,1), (0,-1)]  # 右、左、上、下
    dot_scores = [unit_vec[0]*d[0] + unit_vec[1]*d[1] for d in directions]
    weighted_scores = [s * length for s in dot_scores]
    probs = F.softmax(torch.tensor(weighted_scores), dim=0).numpy()
    print(f"原始向量：{vec.round(2)}，长度：{length:.2f}")
    print(f"单位向量：{unit_vec.round(2)}")
    print(f"点积分数：{[round(s,2) for s in dot_scores]}")
    print(f"加权分数：{[round(s,2) for s in weighted_scores]}")
    print(f"计算概率：{probs.round(3)}（与模型输出一致）")
    print("="*70)