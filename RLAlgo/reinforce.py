import torch
from parameter import *
import numpy as np
from toolkit.time import *

from network.high_match_net import MatchingModel

class REINFORCE:
    def __init__(self, method = 'EasyMatch', hidden_dim=10, action_dim=10, learning_rate=LR, gamma=GAMMA,
                 device=DEVICE):
        # self.policy_net = PolicyNet(state_dim, hidden_dim,action_dim).to(device)
        
        # self.policy_net = MatchingNet(state_dim, [64]).to(device)
        
        
        if method=='EasyMatch':
            self.policy_net = MatchingModel(
                tanker_dim=5,
                tractor_dim=7,
                extra_dim=4
            ).to(device)
        else:
            raise ValueError(f'Unknown method {method} for REINFORCE')
        
        
        
        # The original call discarded torch.compile's return value and causes
        # platform-specific compiler/encoding failures on Windows.
        
        
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(),
                                          lr=learning_rate)  # 使用Adam优化器
        self.gamma = gamma  # 折扣因子
        self.device = device
        
        
    def reset_transition(self):
        self.transition = {'states': [], 'actions': [], 'rewards': [], 'masks': []}
        
    def reset_multi_agent_transition(self,num_agents):
        self.transition = {'states': [[] for _ in range(num_agents)],
                           'actions': [[] for _ in range(num_agents)],
                           'rewards': [[] for _ in range(num_agents)],
                           'masks': [[] for _ in range(num_agents)]}
        

    def take_action(self, state, mask=None, force_greedy=(not DISPATCH_TRAIN_MODE)):  # 根据动作概率分布随机采样
        
        state_pack = (
            torch.tensor(state[0], dtype=torch.float).unsqueeze(0).to(self.device),
            torch.tensor(state[1], dtype=torch.float).unsqueeze(0).to(self.device),
            torch.tensor(state[2], dtype=torch.float).unsqueeze(0).to(self.device)
        )
        
        if mask is not None:
            mask = torch.tensor(mask, dtype=torch.bool).unsqueeze(0).to(self.device)
        probs = self.policy_net(state_pack, mask)
        
        if force_greedy:
            action = torch.argmax(probs)
        else:
            action_dist = torch.distributions.Categorical(probs)
            action = action_dist.sample()
        return action.item()
    
    
    # def take_greedy_action(self,state):
    #     state = torch.tensor(state, dtype=torch.float).to(self.device)
    #     probs = self.policy_net(state)
        
    #     return action

    def update(self, transition_dict=None):
        
        transition_dict = self.transition
        
        reward_list = transition_dict['rewards']
        state_list = transition_dict['states']
        action_list = transition_dict['actions']
        mask_list = transition_dict['masks']

        G = 0
        self.optimizer.zero_grad()
        for i in reversed(range(len(reward_list))):  # 从最后一步算起
            reward = reward_list[i]
            
            s = state_list[i]
            state_pack = (
                torch.tensor(s[0], dtype=torch.float).unsqueeze(0).to(self.device),
                torch.tensor(s[1], dtype=torch.float).unsqueeze(0).to(self.device),
                torch.tensor(s[2], dtype=torch.float).unsqueeze(0).to(self.device)
            )

            action = torch.tensor([action_list[i]]).view(-1, 1).to(self.device)
            
            mask = None
            if len(mask_list) > i:
                mask = torch.tensor(mask_list[i], dtype=torch.bool).unsqueeze(0).to(self.device)

            log_prob = torch.log(self.policy_net(state_pack, mask).gather(1, action))
            G = self.gamma * G + reward
            loss = -log_prob * G  # 每一步的损失函数
            loss.backward()  # 反向传播计算梯度
        self.optimizer.step()  # 梯度下降
        
        
    def save(self,dir,episode_num):
        import os
        path = os.path.join(dir,f'checkpoint_epoch{str(episode_num)}.pt')
        
        
        torch.save({
            'model_state_dict': self.policy_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        },path)   
    
    
    def load(self,dir,episode_num):
        import os
        path = os.path.join(dir,f'checkpoint_epoch{str(episode_num)}.pt')
        
        checkpoint = torch.load(path,map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        print_with_time(f"Model loaded from {path}") # 从{path}加载模型
        
        
'''
        
t1-t2 正常计算奖励    y phit2-  phit1 

t2 发现控制权被打断了 进行计时 同时上一个时间步减去 y phit2

t2+k 恢复控制权 中间过去了k步，把这个加回到 y^k phi t2+k

'''
