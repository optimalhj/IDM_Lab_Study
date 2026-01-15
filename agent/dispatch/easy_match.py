
from environment import HarvesterTankerCorporationEnvironment
from agent.dispatch.base_agent import BaseDispatchAgent
from RLAlgo.reinforce import *
from RLAlgo.dqn import *
import numpy as np

from toolkit.time import print_with_time
from toolkit.log_analysis import find_latest_checkpoint

class EasyMatchAgent(BaseDispatchAgent):
    """简单匹配智能体"""


    def __init__(self, train_mode: bool = True,algo_name='reinforce'):
        
        super().__init__(train_mode)
        
        
        self.algo_name = algo_name
        
        if self.algo_name=='reinforce':
            self.algo = REINFORCE(method='EasyMatch')
        else:
            raise ValueError(f'Unknown algo_name {self.algo_name} for EasyMatchAgent')
            
        
        # 模仿训练
        self.all_transition = {'states': [], 'actions': [],'masks': []}
            
            
    def model_initialization(self, load_episode=-1,read_path=MODEL_DISPATCH_SAVE_DIR):
        
        last_time_train_epoch = find_latest_checkpoint(read_path)
        # 表示无上次训练文件
        if last_time_train_epoch==-1:
            begin_episode = 1
            print_with_time(f'没有在{read_path}找到DISPATCH模型参数，从头开始训练EasyMatch')
        else:
        # 有训练文件
        # 如果不为-1，表示指定加载某一轮次的模型
            if load_episode != -1:
                last_time_train_epoch = load_episode
            
            begin_episode = last_time_train_epoch + 1
            self.algo.load(read_path,last_time_train_epoch)
            print_with_time(f'从{read_path}加载DISPATCH模型EasyMatch参数，最后训练轮次为{last_time_train_epoch}，本次从第{begin_episode}轮开始训练/测试')
            
            
        return begin_episode
        
    
    
    def return_all_tanker_features(self, env: HarvesterTankerCorporationEnvironment):
        
        current_pos = env.tanker_current_position.copy()
        
        target_pos = env.tanker_current_position.copy()
        
        whether_busy = np.zeros((NUM_TANKERS),dtype=float)
        
        
        for tid in range(NUM_TANKERS):
            if env.tanker_target_hid_list[tid]:
                first_hid = env.tanker_target_hid_list[tid][0]
                target_pos[tid] = env.harvester_current_position[first_hid]
                whether_busy[tid] = 1.0
                
        current_pos = current_pos/COL_NUMS
        target_pos = target_pos/COL_NUMS
        
        features = np.hstack((current_pos, target_pos, whether_busy.reshape(-1,1)))
        
        return features
                
                
                
    def return_all_harvester_features(self, env: HarvesterTankerCorporationEnvironment):
        
        current_pos = env.harvester_current_position.copy()
        current_pos = current_pos/COL_NUMS
        
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
                
                
        features = np.hstack((current_pos,
                              harvester_feature, 
                              whether_halting.reshape(-1,1)))
        
        return features
        
    def matching_feature(self,env: HarvesterTankerCorporationEnvironment, tid:int, hid:int):
        
        current_cost = env.current_tasks_path_length(tid)
        
        
        extra_cost = env.extra_task_cost(tid,hid)
        total_cost = current_cost + extra_cost
        
        whether_idle = 1 if not env.tanker_target_hid_list[tid] else 0
        
        time = env.i_step/TOTAL_STEP
        
        return np.array([whether_idle,total_cost,extra_cost,time])
     
    def before_every_episode(self):
        
        
        self.algo.reset_transition()
        
        self.last_time_action_step = -1
        '''以下为了把后续的奖励写回对应的位置'''
        # 如果该时间步作出了一个动作，那么添加一条记录，之后溯源该时间步，并累加奖励
        self.step_reward_dict = {} # 某个时间步对应的奖励总和
        
        # 加油车被指定为服务目标的时间步。在任务进行过程中，通过该记录追溯在哪个时间步，进而追溯奖励
        # 当服务完成后，删除该记录del
        
        self.harvester_targeted_step = {} #农机是在哪一个时间步被指定为服务目标的
    
    
    def after_every_step(self, env):
            
        halting_but_not_targeted_harvesters = env.halting_but_not_targeted_harvesters_list()
        
        halting_reward = len(halting_but_not_targeted_harvesters)*W_WAITING
        
        # !!!!!不确定这样加是否合理，先这样看看
        if self.step_reward_dict:
            assert self.last_time_action_step != -1
            self.step_reward_dict[self.last_time_action_step] -= halting_reward
    
    
    
    def after_every_episode(self,env: HarvesterTankerCorporationEnvironment):
        
        if DISPATCH_TRAIN_MODE:
        
            self.algo.transition['rewards'] = [self.step_reward_dict[key] for key in sorted(self.step_reward_dict.keys())]

        
            
            print_with_time(f"Easy Match cum reward = {sum(self.algo.transition['rewards'])}")
            
            
            if self.algo_name=='reinforce':
                self.algo.update()

            
            if (env.i_episode) %  SAVE_MODEL_FREQUENCY== 0:

                self.algo.save(MODEL_DISPATCH_SAVE_DIR,env.i_episode)
                print_with_time("Dispatch Easymatch model saved")
        
        
        
    
    def after_dispatch_move(self, env: HarvesterTankerCorporationEnvironment,target_hid,current_tid,whether_add_fuel,add_amount,this_move_fuel_consumption):
        
        raise_assign_step = self.harvester_targeted_step[target_hid]
        self.step_reward_dict[raise_assign_step] +=  add_amount*W_S - this_move_fuel_consumption * W_C
        
        
        lack_fuel_harvester_num = 0
        
        #!!!!!!!!!!!!!!!这里有一个bug，应该把每个任务队列中的农机停机时间惩罚分配给每个任务队列中的农机，而不是只分配给第一个农机
        ###############需要修改！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
        # for hid in env.tanker_target_hid_list[tid]:
        #     if env.harvester_remaining_fuel[hid]<=1e-3:
        #         lack_fuel_harvester_num+=1
                
        # step_reward_dict[raise_assign_step] -= lack_fuel_harvester_num * W_WAITING
        
        # 改成下面这样
        for hid in env.tanker_target_hid_list[current_tid]:
            # 查看该加油车服务的每一个农机
            # 获取进行该分配动作（分配给该农机）的时间步
            this_harvester_raise_assign_step = self.harvester_targeted_step[hid]
            # 如果没油了，分配给对应的奖励（惩罚项）
            if env.harvester_remaining_fuel[hid]<=1e-3:
                self.step_reward_dict[this_harvester_raise_assign_step] -= W_WAITING     
                
           
                
                
        
        # 成功给第一个目标农机加上了油
        if whether_add_fuel:        
            del self.harvester_targeted_step[target_hid]
            

    # def take_dispatch_action(self, env:HarvesterTankerCorporationEnvironment, idle_tankers:list,need_add_fuel_harvesters:list):
        
    #     actions = []
    #     if need_add_fuel_harvesters:
    #         hid = np.random.choice(need_add_fuel_harvesters)
            
    #         state = env.all_matching_feature_given_hid(hid)
            
    #         action = self.algo.take_action(state,force_greedy=(not DISPATCH_TRAIN_MODE))    
            
    #         self.algo.transition['states'].append(state)
    #         self.algo.transition['actions'].append(action)
            
    #         self.harvester_targeted_step[hid] = env.i_step
    #         self.step_reward_dict[env.i_step] = 0.0
            
            
    #         tid = int(action)
            
            
    #         if self.algo_name=='dqn' and DISPATCH_TRAIN_MODE:
    #             self.algo.learn()
                
            
        
    #     return [(tid,hid)]
    
    def get_d2sn_mask(self, env:HarvesterTankerCorporationEnvironment, online_harvesters:list):
        
        
        
        num_tankers = NUM_TANKERS
        num_online_harvesters = len(online_harvesters)
        
        mask = np.zeros((num_tankers,num_online_harvesters),dtype=bool)
        
        need_add_fuel_harvesters = env.get_need_add_fuel_harvesters()
        
        idle_tankers = env.idle_tankers_list()
        
        for idx,hid in enumerate(online_harvesters):
            if hid not in need_add_fuel_harvesters:
                mask[:,idx] = True
                
        for tid in range(num_tankers):
            if tid not in idle_tankers:
                mask[tid,:] = True
        
        mask = mask.reshape(-1)
        
        assign = np.array([False],dtype=bool)
        
        mask = np.concatenate((mask,assign))
        
        if len(idle_tankers) == NUM_TANKERS:
            mask[-1] = True
        
                    
        return mask
    
    def get_mask(self, env:HarvesterTankerCorporationEnvironment, online_harvesters:list):
        
        
        
        num_tankers = NUM_TANKERS
        num_online_harvesters = len(online_harvesters)
        
        mask = np.zeros((num_tankers,num_online_harvesters),dtype=bool)
        
        need_add_fuel_harvesters = env.get_need_add_fuel_harvesters()
        
        for idx,hid in enumerate(online_harvesters):
            if hid not in need_add_fuel_harvesters:
                mask[:,idx] = True
                    
        return mask.reshape(-1)
    
    def take_dispatch_action(self, env:HarvesterTankerCorporationEnvironment, idle_tankers:list,need_add_fuel_harvesters:list):
        
        actions = []
        if need_add_fuel_harvesters and idle_tankers:
            
            # 3x
            all_tanker_features = self.return_all_tanker_features(env)
            all_harvester_features = self.return_all_harvester_features(env)
            
            online_harvesters = [hid for hid in range(NUM_HARVESTERS) if env.harvester_working_status[hid]==0]
            online_harvesters = np.array(online_harvesters)
            
            online_harvesters_features = all_harvester_features[online_harvesters]
            
            mask = self.get_mask(env,online_harvesters)
            
            
            inter_features = []
            
            for tid in range(NUM_TANKERS):
                for hid in online_harvesters:
                    inter_feature = self.matching_feature(env,tid,hid)
                    inter_features.append(inter_feature)
            
            inter_features = np.array(inter_features)
            
            state_pack = (all_tanker_features,online_harvesters_features,inter_features)
            
            
            action = self.algo.take_action(
                state=state_pack,
                mask=mask
                )
            action = int(action)
            
            
            d2sn_mask = self.get_d2sn_mask(env,online_harvesters)
            
            
            
            
            
            self.algo.transition['states'].append(state_pack)
            self.algo.transition['actions'].append(action)
            self.algo.transition['masks'].append(mask)
            
            self.last_time_action_step = env.i_step
            
            
            chosen_tid = action // len(online_harvesters)
            chosen_idx = action % len(online_harvesters)
            chosen_hid = online_harvesters[chosen_idx]
            
            
            if chosen_tid not in idle_tankers:
                d2sn_action = NUM_TANKERS * len(online_harvesters)
            else:
                d2sn_action = action
                
                
            self.all_transition['states'].append(state_pack)
            self.all_transition['actions'].append(d2sn_action)
            self.all_transition['masks'].append(d2sn_mask)
                
                
            
                        
            self.harvester_targeted_step[chosen_hid] = env.i_step
            self.step_reward_dict[env.i_step] = 0.0
            
            actions.append( (chosen_tid, chosen_hid) )
                
            
        
        return actions
    
            