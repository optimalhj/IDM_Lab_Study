from agent.reposition.base_agent import BaseRepositionAgent
import numpy as np
from parameter import *

# from RLAlgo.reinforce import REINFORCE
# from RLAlgo.marlreinforce import MARLREINFORCE

from RLAlgo.reinforce2 import REINFORCE2

from toolkit.log_analysis import find_latest_checkpoint

from toolkit.time import print_with_time

from environment import HarvesterTankerCorporationEnvironment
class ChihayaRepositionAgent(BaseRepositionAgent):
    
    def __init__(self, train_mode):
        super().__init__(train_mode)
        self.algo = REINFORCE2(network_type=0)
    
    def model_initialization(self, load_episode=-1):
        
        last_time_train_epoch = find_latest_checkpoint(MODEL_REPOSITION_SAVE_DIR)
        # 表示无上次训练文件
        if last_time_train_epoch==-1:
            begin_episode = 1
            print_with_time(f'没有在{MODEL_REPOSITION_SAVE_DIR}找到REPOSITION模型参数，从头开始训练Chihaya')
        else:
        # 有训练文件
        # 如果不为-1，表示指定加载某一轮次的模型
            if load_episode != -1:
                last_time_train_epoch = load_episode
            
            begin_episode = last_time_train_epoch + 1
            self.algo.load(MODEL_REPOSITION_SAVE_DIR,last_time_train_epoch)
            print_with_time(f'从{MODEL_REPOSITION_SAVE_DIR}加载REPOSITION模型Chihaya参数，最后训练轮次为{last_time_train_epoch}，本次从第{begin_episode}轮开始训练/测试')
            
            
        return begin_episode
    
    
    
        
    def before_every_episode(self):
        self.every_tanker_interval_count = np.zeros((NUM_TANKERS,),dtype=int)   
        self.algo.reset_multi_agent_transition()
        
        self.every_tanker_last_time_decision_step = np.full((NUM_TANKERS),-1,dtype=int)
        
    
    
    def before_reposition_move(self, env):
        for i in range(NUM_TANKERS):
            self.every_tanker_interval_count[i] +=1
    
    
    def return_online_harvester_features(self, env: HarvesterTankerCorporationEnvironment):
        
        current_pos = env.harvester_current_position.copy()
    
        how_long_since_last_fuel =env.i_step-env.harvester_last_fuel_step
        
        harvester_feature = np.column_stack([
            env.harvester_working_time_count/TOTAL_STEP,
            how_long_since_last_fuel/TOTAL_STEP,
            env.harvester_last_fuel_amount/FUEL_CAPACITY,
            env.harvester_request_status
        ])
        
        whether_halting = np.zeros((NUM_HARVESTERS),dtype=float)
        
        for hid in range(NUM_HARVESTERS):
            if env.harvester_remaining_fuel[hid]<=1e-3:
                whether_halting[hid]=1.0
                
        
        online_harvesters = np.array([hid for hid in range(NUM_HARVESTERS) if env.harvester_working_status[hid]==0])
        
        features = []
        idle_tankers = env.idle_tankers_list()
        for tid in idle_tankers:
            tanker_pos = env.tanker_current_position[tid]
            relative_pos = current_pos - tanker_pos  # (NUM_HARVESTERS, 2)
            
            feature = np.hstack((relative_pos,
                                harvester_feature, 
                                whether_halting.reshape(-1,1)))
            
            feature = feature[online_harvesters]
            features.append(feature)
        
        return np.array(features)
    
    def return_idle_tankers_features(self, env: HarvesterTankerCorporationEnvironment):
        
        current_pos = env.tanker_current_position.copy()
        
        target_pos = env.tanker_current_position.copy()
        
        whether_busy = np.zeros((NUM_TANKERS),dtype=float)
        for tid in range(NUM_TANKERS):
            if env.tanker_target_hid_list[tid]:
                first_hid = env.tanker_target_hid_list[tid][0]
                target_pos[tid] = env.harvester_current_position[first_hid]
                whether_busy[tid] = 1.0
        
        pos_features = np.hstack((current_pos,target_pos))        
        idle_tankers = env.idle_tankers_list()
        
        features = []
        for tid in idle_tankers:
            pos = env.tanker_current_position[tid]
            
            double_pos = np.hstack((pos,pos))
            
            relative_pos = pos_features - double_pos  # (NUM_TANKERS, 4)
            feature = np.hstack((relative_pos,
                                whether_busy.reshape(-1,1)))
            
            feature = np.delete(feature, tid, axis=0)  # 删除自身
            features.append(feature)
            
        return np.array(features)
            
    def take_reposition_action2(self, env:HarvesterTankerCorporationEnvironment,idle_tankers:list):
        
        
        online_harvester_features = self.return_online_harvester_features(env)
        
        idle_tankers_features = self.return_idle_tankers_features(env)
                
        
        actions,move_dists = self.algo.take_action((online_harvester_features,idle_tankers_features),force_greedy=(not REPOSITION_TRAIN_MODE))
        
        
        need_add_fuel_harvesters = env.get_need_add_fuel_harvesters()
        
        for idx,tid in enumerate(idle_tankers):
            
            if REPOSITION_TRAIN_MODE:
                interval = self.every_tanker_interval_count[tid]
                self.every_tanker_interval_count[tid] = 0
                
                potential_energy_before = env.get_sum_potential_energy_given_tid(tid)
                
                # 如果不是第一次记录该智能体的奖励，则把上一次的奖励补上
                if self.algo.transition['rewards'][tid] and not NO_USE_PBRS:
                    self.algo.transition['rewards'][tid][-1] += GAMMA**interval * potential_energy_before
                
                action= actions[idx]
                dist = move_dists[idx]
                
                
                self.algo.transition['states'][tid].append((online_harvester_features[idx],idle_tankers_features[idx]))
                self.algo.transition['actions'][tid].append(action)
                
                if NO_USE_PBRS:
                    r = 0.0
                else:
                    r = - potential_energy_before
                    
                self.algo.transition['rewards'][tid].append(r)  # 先占位，奖励在after_every_step中补上
            
            action= actions[idx]
            dist = move_dists[idx]
            
            if dist<10:
                this_tanker_move_direction = ACTION_STAY
            else:
                if action == 0:
                    this_tanker_move_direction = ACTION_RIGHT
                elif action == 1:
                    this_tanker_move_direction = ACTION_LEFT
                elif action == 2:
                    this_tanker_move_direction = ACTION_UP
                else:
                    this_tanker_move_direction = ACTION_DOWN
                
            
            this_move_fuel_consumption = env.handle_tanker_move(tid,this_tanker_move_direction)
            
            for hid in need_add_fuel_harvesters:
                whether_add_fuel, add_fuel_amount = env.try_refuel_given_tid_hid(tid,hid,env.i_step,must_be_target=False)
                if REPOSITION_TRAIN_MODE:
                    self.algo.transition['rewards'][tid][-1] += W_S*add_fuel_amount
            
            if REPOSITION_TRAIN_MODE:
            
                self.algo.transition['rewards'][tid][-1] += - this_move_fuel_consumption*W_C
        
    def take_reposition_action(self, env:HarvesterTankerCorporationEnvironment,idle_tankers:list):
        
        online_harvester_features = self.return_online_harvester_features(env)
        
        idle_tankers_features = self.return_idle_tankers_features(env)
                
        actions,move_dists = self.algo.take_action((online_harvester_features,idle_tankers_features),force_greedy=(not REPOSITION_TRAIN_MODE))
        
        
        need_add_fuel_harvesters = env.get_need_add_fuel_harvesters()
        
        for idx,tid in enumerate(idle_tankers):
            
            # 这个tid该时间步要决策
            self.every_tanker_last_time_decision_step[tid] = env.i_step
                
            
            # 提取动作
            action= actions[idx]
            dist = move_dists[idx]
            if REPOSITION_TRAIN_MODE:
                potential_energy_before = env.get_sum_potential_energy_given_tid(tid)
                self.algo.transition['states'][tid].append((online_harvester_features[idx],idle_tankers_features[idx]))
                
            
            if dist<10:
                this_tanker_move_direction = ACTION_STAY
                action = 4
            else:
                if action == 0:
                    this_tanker_move_direction = ACTION_RIGHT
                elif action == 1:
                    this_tanker_move_direction = ACTION_LEFT
                elif action == 2:
                    this_tanker_move_direction = ACTION_UP
                elif action == 3:
                    this_tanker_move_direction = ACTION_DOWN
                elif action ==4:
                    this_tanker_move_direction = ACTION_STAY
            
            if REPOSITION_TRAIN_MODE:
                self.algo.transition['actions'][tid].append(action)
                
            
            this_move_fuel_consumption = env.handle_tanker_move(tid,this_tanker_move_direction)
            
            potential_energy_after = env.get_sum_potential_energy_given_tid(tid)
            
            if REPOSITION_TRAIN_MODE:
                
                if NO_USE_PBRS:
                    r = 0.0
                else:
                    r = - potential_energy_before + potential_energy_after
                
                self.algo.transition['rewards'][tid].append(r)
            
            for hid in need_add_fuel_harvesters:
                whether_add_fuel, add_fuel_amount = env.try_refuel_given_tid_hid(tid,hid,env.i_step,must_be_target=False)
                if REPOSITION_TRAIN_MODE:
                    self.algo.transition['rewards'][tid][-1] += W_S*add_fuel_amount
            
            if REPOSITION_TRAIN_MODE:
            
                self.algo.transition['rewards'][tid][-1] += - this_move_fuel_consumption*W_C    
        
    
    # def after_every_step(self, env):
    def after_every_step(self, env:HarvesterTankerCorporationEnvironment):
        
        if REPOSITION_TRAIN_MODE:
            this_time_halting_harvesters = env.count_this_step_halting_harvesters()
            reward_every_tanker = W_WAITING*this_time_halting_harvesters / NUM_TANKERS
            
            for tid in range(NUM_TANKERS):
                # 该智能体上次决策时间步不是-1，表示该智能体至少决策过一次
                if self.every_tanker_last_time_decision_step[tid]!=-1:
                    interval = env.i_step - self.every_tanker_last_time_decision_step[tid]
                    self.algo.transition['rewards'][tid][-1] += -GAMMA**interval * reward_every_tanker
            
    
        
         
        
    def after_every_episode(self,env:HarvesterTankerCorporationEnvironment):
        
        if REPOSITION_TRAIN_MODE:
        
            print_with_time(f'cum reward = {sum([sum(self.algo.transition["rewards"][tid]) for tid in range(NUM_TANKERS)])}')
            
            if REPOSITION_TRAIN_MODE:
                # self.algo.update_serial()
                self.algo.update()
                
                if (env.i_episode) % SAVE_MODEL_FREQUENCY == 0:
                    self.algo.save(MODEL_REPOSITION_SAVE_DIR,env.i_episode)
                    print_with_time("Reposition Chihaya model saved")