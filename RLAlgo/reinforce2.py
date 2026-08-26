import torch
from parameter import *
import numpy as np
from toolkit.time import *

from network.harvester_attention_rev import HarvesterAttention


class REINFORCE2:
    def __init__(self, network_type = 0,state_dim=2333, hidden_dim=10, action_dim=10, learning_rate=LR, gamma=GAMMA, device=DEVICE):
        # self.policy_net = PolicyNet(state_dim, hidden_dim,action_dim).to(device)
        
        # self.policy_net = MatchingNet(state_dim, [64]).to(device)
        
        if network_type ==0:
            self.policy_net = HarvesterAttention(
                d_self_features=5,
                d_context_in=5,
                d_context_hidden=64,
                d_k=16,
                ).to(device)
        
        
        # Keep eager mode: the original compile result was not assigned.
        
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=learning_rate)  # 使用Adam优化器
        self.gamma = gamma  # 折扣因子
        self.device = device
        
    # 多个agent的REINFORCE，每个agent单独存储自己的transition，最后累积梯度，然后统一更新 
    def reset_multi_agent_transition(self,num_agents=NUM_TANKERS):
        self.transition = {'states': [[] for _ in range(num_agents)],
                           'actions': [[] for _ in range(num_agents)],
                           'rewards': [[] for _ in range(num_agents)],
                           'mask': [[] for _ in range(num_agents)],
                           }
        

    def take_action(self, state, force_greedy=True):  # 根据动作概率分布随机采样
        s1, s2 = state
        # s1: (N, Feat_Dim) -> (1, N, Feat_Dim)
        s1_tensor = torch.tensor(s1, dtype=torch.float).to(self.device)
        # s2: (Context_Dim,) -> (1, Context_Dim)
        s2_tensor = torch.tensor(s2, dtype=torch.float).to(self.device)
        
        # 单样本推理不需要 mask (或者 mask 全为 True)
        reposition_vec, attn_weights, probs, vec_length = self.policy_net(s1_tensor, s2_tensor)
        # probs 期望形状: (batch_size, action_dim)

        if force_greedy:
            actions = probs.argmax(dim=-1)          # (batch_size,)
        else:
            dist = torch.distributions.Categorical(probs)
            actions = dist.sample()                 # (batch_size,)

        return actions.tolist(),vec_length.reshape(-1).detach().cpu().numpy()
    
    # def take_action2(self, state,mask:np.ndarray,force_greedy=True):  # 根据动作概率分布随机采样
    #     s1, s2 = state
    #     s1 = np.expand_dims(s1, axis=0)  # 扩展为批量维度
    #     s2 = np.expand_dims(s2, axis=0)  # 扩展为批量维度
    #     s1 = torch.tensor(s1, dtype=torch.float).to(self.device)
    #     s2 = torch.tensor(s2, dtype=torch.float).to(self.device)
        
    #     mask = np.expand_dims(mask, axis=0)  # 扩展为批量维度
    #     mask = torch.from_numpy(mask).to(self.device)
    #     probs = self.policy_net(s1, s2, mask)
    #     # probs 期望形状: (batch_size, action_dim)

    #     if force_greedy:
    #         actions = probs.argmax(dim=-1)          # (batch_size,)
    #     else:
    #         dist = torch.distributions.Categorical(probs)
    #         actions = dist.sample()                 # (batch_size,)

    #     return actions.tolist()
    
    
    # def take_greedy_action(self,state):
    #     state = torch.tensor(state, dtype=torch.float).to(self.device)
    #     probs = self.policy_net(state)
        
    #     return action

    def update(self, transition_dict=None):
        from torch.nn.utils.rnn import pad_sequence
        
        transition_dict = self.transition
        self.optimizer.zero_grad()
        
        # 1. 收集所有数据
        all_s1 = [] # 变长序列列表
        all_s2 = [] # 定长向量列表
        all_actions = []
        all_returns = []
        
        for tid in range(NUM_TANKERS):
            reward_list = transition_dict['rewards'][tid]
            state_list = transition_dict['states'][tid]
            action_list = transition_dict['actions'][tid]
            
            if not state_list:
                continue

            # 预先计算折扣回报 G (从后往前)
            G = 0
            trajectory_returns = []
            for r in reversed(reward_list):
                G = self.gamma * G + r
                trajectory_returns.insert(0, G)
            
            # 分离 s1 和 s2，并将 s1 转为 Tensor 以便 padding
            for s in state_list:
                # s[0] 是变长序列 (N, Feat_Dim)
                all_s1.append(torch.tensor(s[0], dtype=torch.float))
                # s[1] 是定长向量 (Context_Dim,)
                all_s2.append(s[1])
            
            all_actions.extend(action_list)
            all_returns.extend(trajectory_returns)
            
        # 如果没有数据，直接返回
        if not all_s1:
            return

        # 2. 并行化处理 (Padding + Mask)
        # s1_padded(online_harvester_features): (Batch, Max_Len, Feat_Dim)
        s1_padded = pad_sequence(all_s1, batch_first=True).to(self.device)
        
        # 生成 Mask: (Batch, Max_Len)
        # True 表示有效数据，False 表示 Padding
        lengths = torch.tensor([len(s) for s in all_s1]).to(self.device)
        max_len = s1_padded.size(1)
        # arange: [0, 1, ..., max_len-1]
        # mask[i, j] = j < lengths[i]
        mask = torch.arange(max_len, device=self.device)[None, :] < lengths[:, None]
        
        # s2(idle_tankers_features): (Batch, Context_Dim)
        s2_tensor = torch.tensor(np.array(all_s2), dtype=torch.float).to(self.device)
        
        return_tensor = torch.tensor(all_returns, dtype=torch.float).view(-1, 1).to(self.device)
        action_tensor = torch.tensor(all_actions, dtype=torch.int64).view(-1, 1).to(self.device)
        
        # 3. 并行前向传播 (传入 mask)
        # 输入形状: [Batch, Max_Len, Feat_Dim] -> 输出形状: [Batch, Action_Dim]
        # s1_padded : online_harvester_features  /  s2_tensor : idle_tankers_features
        _, _, probs, _ = self.policy_net(s1_padded, s2_tensor, mask=mask)
        
        # 4. 计算 Loss
        # gather: 选出实际执行动作对应的概率
        selected_probs = probs.gather(1, action_tensor)
        
        # 防止 log(0)
        log_probs = torch.log(selected_probs + 1e-8)
        
        # Loss = - sum(G * log_prob)
        loss = -torch.sum(return_tensor * log_probs)
        
        # 5. 反向传播与更新 (只做一次)
        loss.backward()
        self.optimizer.step()
        
    def update_serial(self, transition_dict=None):
        transition_dict = self.transition
        self.optimizer.zero_grad()
        
        total_loss = 0
        count = 0
        
        for tid in range(NUM_TANKERS):
            reward_list = transition_dict['rewards'][tid]
            state_list = transition_dict['states'][tid]
            action_list = transition_dict['actions'][tid]
            
            if not state_list:
                continue

            # 计算折扣回报 G
            G = 0
            trajectory_returns = []
            for r in reversed(reward_list):
                G = self.gamma * G + r
                trajectory_returns.insert(0, G)
            
            # 逐个时间步计算 Loss
            for i in range(len(state_list)):
                s1, s2 = state_list[i]
                action = action_list[i]
                return_val = trajectory_returns[i]
                
                # 转换为 Tensor (单样本)
                # s1: (seq_len, feat_dim) -> (1, seq_len, feat_dim)
                # s2: (feat_dim,) -> (1, feat_dim)
                s1_tensor = torch.tensor(s1, dtype=torch.float).unsqueeze(0).to(self.device)
                s2_tensor = torch.tensor(s2, dtype=torch.float).unsqueeze(0).to(self.device)
                action_tensor = torch.tensor([action], dtype=torch.int64).to(self.device)
                return_tensor = torch.tensor([return_val], dtype=torch.float).to(self.device)
                
                # 前向传播
                _, _, probs, _ = self.policy_net(s1_tensor, s2_tensor)
                
                # 计算当前步的 Loss
                log_prob = torch.log(probs.gather(1, action_tensor.view(1, -1)))
                loss = - (log_prob * return_tensor)
                
                total_loss += loss
                count += 1
        
        if count == 0:
            return

        # 反向传播与更新
        # 可以除以 count 做 mean reduction，或者直接 sum
        (total_loss / count).backward() 
        self.optimizer.step()
        
        
    def save(self,dir,episode_num):
        import os
        path = os.path.join(dir,f'checkpoint_epoch{str(episode_num)}.pt')
        
        
        torch.save({
            'model_state_dict': self.policy_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        },path)   
    
    # 注意如果动作为重定位，记得写一个空的奖励
    def load(self,dir,episode_num):
        import os
        path = os.path.join(dir,f'checkpoint_epoch{str(episode_num)}.pt')
        
        checkpoint = torch.load(path,map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        print_with_time(f"Data loaded from {path}") # 从{path}加载模型
        
        
'''
        
t1-t2 正常计算奖励    y phit2-  phit1 

t2 发现控制权被打断了 进行计时 同时上一个时间步减去 y phit2

t2+k 恢复控制权 中间过去了k步，把这个加回到 y^k phi t2+k

'''
