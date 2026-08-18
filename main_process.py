
from environment import *

from toolkit.geocal import *

from toolkit.time import print_with_time, return_second_timestamp_str
from toolkit.log_analysis import *

from agent.dispatch.base_agent import BaseDispatchAgent
# from agent.dispatch.nearest_tanker import NearestTankerAgent
# from agent.dispatch.random_select import RandomSelectAgent
from agent.dispatch.easy_match import EasyMatchAgent
# from agent.dispatch.km import KMAgent
# from agent.dispatch.cvnet import CVNetAgent
# from agent.dispatch.polar import PolarDispatchAgent
# from agent.dispatch.JDRL import JDRLAgent
# from agent.dispatch.D2SN import D2SNAgent

from agent.reposition.base_agent import BaseRepositionAgent
from agent.reposition.chihaya import ChihayaRepositionAgent
from agent.reposition.none import NoneRepositionAgent


from parameter import *



# import os
# os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

# 在农田区域，加油车移动速度慢，1min只能移动0.2个格子
# 在非农田区域，加油车移动速度快，1min能移动1个格子（速度是5倍）

print_with_time('-----------------Start-------------------') # 程序运行参数
print_with_time(args)



env = HarvesterTankerCorporationEnvironment()


if not os.path.exists(MODEL_REPOSITION_SAVE_DIR):
    os.makedirs(MODEL_REPOSITION_SAVE_DIR)
if not os.path.exists(MODEL_DISPATCH_SAVE_DIR):
    os.makedirs(MODEL_DISPATCH_SAVE_DIR)

np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)




# if DISPATCH_METHOD == 'NearestTanker':
#     dispatch_agent = NearestTankerAgent(train_mode=DISPATCH_TRAIN_MODE,only_idle_tanker=False,multi_assign=False)
# elif DISPATCH_METHOD == 'NearestIdleTanker':
#     dispatch_agent = NearestTankerAgent(train_mode=DISPATCH_TRAIN_MODE,only_idle_tanker=True,multi_assign=False)
# elif DISPATCH_METHOD == 'RandomDispatch':
#     dispatch_agent = RandomSelectAgent(train_mode=DISPATCH_TRAIN_MODE,only_idle_tanker=True,multi_assign=True)
if DISPATCH_METHOD == 'EasyMatch':
    dispatch_agent = EasyMatchAgent(train_mode=DISPATCH_TRAIN_MODE,algo_name='reinforce')
# elif DISPATCH_METHOD == 'EasyMatch-DQN':
#     dispatch_agent = EasyMatchAgent(train_mode=DISPATCH_TRAIN_MODE,algo_name='dqn')
# elif DISPATCH_METHOD == 'KM':
#     dispatch_agent = KMAgent(train_mode=DISPATCH_TRAIN_MODE)
# elif DISPATCH_METHOD == 'Polar':
#     dispatch_agent = PolarDispatchAgent(train_mode=DISPATCH_TRAIN_MODE)
#     # second_agent = NearestTankerAgent(train_mode=DISPATCH_TRAIN_MODE,only_idle_tanker=False,multi_assign=False)
# elif DISPATCH_METHOD == "CVNet":
#     dispatch_agent = CVNetAgent(train_mode=DISPATCH_TRAIN_MODE)
# elif DISPATCH_METHOD == 'JDRL':
#     dispatch_agent = JDRLAgent(train_mode=DISPATCH_TRAIN_MODE)
# elif DISPATCH_METHOD == 'D2SN':
#     dispatch_agent = D2SNAgent(train_mode=DISPATCH_TRAIN_MODE)
else:
    raise NotImplementedError('未知的订单分配方法')
    
    
    
if REPOSITION_METHOD == 'Chihaya':    
    reposition_agent = ChihayaRepositionAgent(train_mode=REPOSITION_TRAIN_MODE)
elif REPOSITION_METHOD == 'None':
    reposition_agent = NoneRepositionAgent(train_mode=REPOSITION_TRAIN_MODE)
else:
    raise NotImplementedError('未知的重定位方法')
    




if REPOSITION_TRAIN_MODE or DISPATCH_TRAIN_MODE:
    episode_num = REPOSITION_EPISODE_NUM
    episode_num+=1
    test_num = 1
else:
    episode_num = env.total_day_num_of_data
    test_num = TEST_REPEAT_NUM
    # 可视化模式下，只跑一天，且保存可视化数据
    if KEEP_VISUALIZATION_DATA_DAY_IDX!=-1:
        episode_num = 1  # 
        test_num = 1

dispacth_begin_episode = dispatch_agent.model_initialization()
reposition_begin_episode = reposition_agent.model_initialization()


if DISPATCH_TRAIN_MODE:
    begin_episode = dispacth_begin_episode
elif REPOSITION_TRAIN_MODE:
    begin_episode = reposition_begin_episode



print_with_time('-----------------Execution Mode-------------------') # 程序运行模式


print_with_time('Dispatch Method: ' + DISPATCH_METHOD) # 订单分配方法
print_with_time('REPOSITION_METHOD: '+ REPOSITION_METHOD) # 重定位方法

if REPOSITION_TRAIN_MODE:
    if DISPATCH_TRAIN_MODE:
        print_with_time('Integrated Train for REPOSITION and DISPATCH') # 重定位-订单分配联合训练
    else:
        print_with_time('REPOSITION Training - DISPATCH Testing Mode') # 重定位训练-订单分配测试模式
else:
    if DISPATCH_TRAIN_MODE:
        print_with_time('REPOSITION Testing - DISPATCH Training Mode') # 重定位测试-订单分配训练模式
    else:
        # 双测试模式
        print_with_time('REPOSITION Testing - DISPATCH Testing Mode') # 重定位测试-订单分配测试模式
        begin_episode = 0

print_with_time('----------------------------------------------')




# episode训练模式 
for i_e in range(begin_episode,episode_num*test_num):  

# 每个episode开头---------------------------------------------------------------
  
    idle_available_count = 0
    
    dispatch_agent.before_every_episode()
    reposition_agent.before_every_episode()
    
    print_with_time('-------------------------------------------------------------')
    
    if KEEP_VISUALIZATION_DATA_DAY_IDX!=-1:
        # 以下是为了可视化路线
        check_harvester_loc = np.zeros((TOTAL_STEP,NUM_HARVESTERS,2),dtype=int)
        check_tanker_loc = np.zeros((TOTAL_STEP,NUM_TANKERS,2),dtype=float)
        check_harvester_still = np.zeros((TOTAL_STEP,NUM_HARVESTERS),dtype=int)
        check_harvester_request = np.zeros((TOTAL_STEP,NUM_HARVESTERS),dtype=int)
    
    
    if REPOSITION_TRAIN_MODE or DISPATCH_TRAIN_MODE:
        print_with_time(f'Training，episode {i_e}') # 训练模式，episode {i_e}
        env.reset()
        env.resample_threshold_all_harvesters()
        
    else:        
        day_idx = i_e % env.total_day_num_of_data 
        
        if KEEP_VISUALIZATION_DATA_DAY_IDX!=-1:
            day_idx = KEEP_VISUALIZATION_DATA_DAY_IDX
        
        test_idx = i_e // env.total_day_num_of_data
        print_with_time(f'Testing，episode {test_idx} - {day_idx}') # 测试模式，第 {test_idx} 轮，第 {day_idx} 天
        env.reset(day_idx)
        np.random.seed(SEED + test_idx)
        env.resample_threshold_all_harvesters()
            
         
    env.i_episode = i_e
    
    # 数据集里面，每个i是农机是当前时间步开始时刻的位置，所以在开始更新农机位置
    for i_step in range(TOTAL_STEP):
        # 每个时间步开头---------------------------------------------------------------
        
        env.i_step = i_step
        if i_step == 0:
            env.harvester_current_position = env.harvester_all_position[:,0,:]

        
        
        # 如果农机有油，更新农机位置，并且计算油耗，要么基于距离，要么基于时间
        for hid in range(NUM_HARVESTERS):
            if env.harvester_working_status[hid] == 1:
                continue
            
            # 说明有油，这里的有油，是对于上一个时间步一整个时间段的check
            if env.harvester_remaining_fuel[hid]>1e-3:
                
                env.harvester_current_position[hid] = env.harvester_all_position[hid,i_step-env.harvester_waiting_step[hid],:]
                current_col = env.harvester_current_position[hid,0]
                
                # 在工作中，上一个时间步还没在工作中
                if current_col >0 and env.harvester_working_status[hid] == -1:
                    env.harvester_working_status[hid] = 0
                # 不在工作，
                elif current_col ==0:
                    # 且上一个时间步还在工作中，说明已经结束工作了
                    if env.harvester_working_status[hid] == 0:
                        env.harvester_working_status[hid] = 1
                        # 结束工作，没有加油等待时间了
                        env.harvester_request_status[hid] = -1
                        
                        # 结束工作还需要让那些target是这个的取消target
                        env.cancel_refuel_target_given_hid(hid)
                        
                                
                        continue
                    
              
                    # 不在工作，且上一个时间步也不在工作中，说明还没开始工作
                    elif env.harvester_working_status[hid] == -1:
                        # env.harvester_working_status[hid] = -1
                        continue                       
                        
                
                # 计算油耗，假设每个时间步消耗2单位油，这里是针对为了移到当前时间步begin节点的位置所耗的油
                env.harvester_remaining_fuel[hid] -= FUEL_COMSUMPTION_PER_STEP
                env.harvester_remaining_fuel[hid] = max(env.harvester_remaining_fuel[hid],0)
                env.harvester_working_time_count[hid] += 1
                
        
        # 计算完油耗后，更新农机的油量，然后查看是否低于阈值，然后决定是不是要发出请求
                # 小于阈值了
                if env.harvester_remaining_fuel[hid] <= env.harvester_fuel_threshold[hid]:
                    # 一种是还没发出请求
                    
                    if env.harvester_request_status[hid] == -1:
                        env.harvester_request_status[hid] = 0
                        
                        
                        
                        
                    # 另一种是已经发出请求了，那么请求时间步+1,表示等待的时间
                    else:
                        env.harvester_request_status[hid] +=1  
            # 否则说明在上一个时间步油量耗尽，农机位置不变，一些统计，如停止时间，指标需要++     
            else:
                
                
                if KEEP_VISUALIZATION_DATA_DAY_IDX!=-1:
                    check_harvester_still[i_step,hid] = 1
                
                env.harvester_waiting_step[hid] += 1
                # 继续发出请求
                env.harvester_request_status[hid] += 1
                
                env.harvester_current_position[hid] = env.harvester_all_position[hid,i_step-env.harvester_waiting_step[hid],:]
            
        # check_hid = 5
        
        # print(f'时间步{i_step}，农机位置{harvester_current_position[check_hid]}，油量{env.harvester_remaining_fuel[check_hid]}，请求状态{env.harvester_request_status[check_hid]}，工作状态{env.harvester_working_status[check_hid]}，等待时间{env.harvester_waiting_step[check_hid]}')


        # 订单分配方法---------------------------------------------------------------------------------
        
        # 根据订单进行请求的分配，分配给加油车，dispatch
        # 如果假设每个时间步都重新分配，那么就重新设置目标，否则保持全局不变
        # 下面一行代码是每个时间步重新分配农机
        # env.tanker_target_hid = np.full((NUM_TANKERS,),-1,dtype=int)  # 每个油罐车的目标农机id，-1表示无目标
        
        
        
        dispatch_agent.before_every_step(env)
        
        
        
        idle_tankers = env.idle_tankers_list()
        targeted_harvesters = env.targeted_harvesters_list()
        need_add_fuel_harvesters = [hid for hid in range(NUM_HARVESTERS) if env.harvester_request_status[hid]!=-1 and hid not in targeted_harvesters]   
        
        # print(f'时间步{i_step}，需要加油的农机有{need_add_fuel_harvesters}，空闲的加油车有{idle_tankers}')

        if (need_add_fuel_harvesters and idle_tankers):
            # 订单分配动作-------------------------------------------------------------------------------
            # if need_add_fuel_harvesters:
            #     print_with_time(f'时间步{i_step}，需要加油的农机有{need_add_fuel_harvesters}，空闲的加油车有{idle_tankers}')
            actions = dispatch_agent.take_dispatch_action(env,idle_tankers,need_add_fuel_harvesters)
            
            if not actions:
                # print_with_time(f'时间步{env.i_step}，选择不进行分配动作，此时有可加油车{idle_tankers}，需要加油农机{need_add_fuel_harvesters}')
                pass
                
            else:    
            
                for tid,hid in actions:
                    
                    # 加一项，只允许分配给idletanker
                    
                    if tid not in idle_tankers:
                        # print_with_time(f'时间步{env.i_step}，选择不进行分配动作，此时有可加油车{idle_tankers}，需要加油农机{need_add_fuel_harvesters}')
                        continue
                    
                    
                    if hid not in need_add_fuel_harvesters:
                        print_with_time(f'Warning: Harvester ID {hid} is not in the need_add_fuel_harvesters list') # 警告：农机ID{hid}不在need_add_fuel_harvesters列表中
                    
                    print_with_time(f'{i_step} step : RF{tid}-> AM{hid}') # 时间步{i_step}，本次派遣动作：加油车ID {tid} ->农机ID {hid}
                    env.add_refuel_target_given_tid_hid(tid,hid)
          
        
        
        
        
        if KEEP_VISUALIZATION_DATA_DAY_IDX!=-1:
            check_harvester_loc[i_step] = env.harvester_current_position
            check_tanker_loc[i_step] = env.tanker_current_position
            check_harvester_request[i_step] = env.harvester_request_status
        
        
        # 剩余空闲的加油车进行reposition----------------------------------------------------------------------------------
        # 这里采用基于MobRef的reposition策略

        idle_tankers = env.idle_tankers_list()
        busy_tankers = [tid for tid in range(NUM_TANKERS) if tid not in idle_tankers]
        
        
        # 重定位动作--------------------------------------------------------------------
        
        reposition_agent.before_reposition_move(env)
        
        ava_harvesters = env.working_but_not_requesting_harvesters_list()
        
        if idle_tankers and ava_harvesters:
            
            # print_with_time(f'时间步{i_step}，空闲加油车有{idle_tankers}，进行重定位决策')
            
            idle_available_count+= len(idle_tankers)
            
            reposition_agent.take_reposition_action(env,idle_tankers)
            
            
        
        # 以下是时间流逝----------------------------------------------------------------------
        
        # 每个加油车按照dispatch或者reposition的目标位置进行移动
        # 加油车位置改变
        
        
        # 以下是dispatch朝着目标位置--------------------------------------------------------------
        for tid in range(NUM_TANKERS):
            # 没目标的加油车跳过      
            if not env.tanker_target_hid_list[tid]:
                continue
            # 任务队列的第一个作为目标
            target_hid = env.tanker_target_hid_list[tid][0]
            
            # 获取位置
            target_pos = env.harvester_current_position[target_hid]
            current_pos = env.tanker_current_position[tid]
            
            # 计算移动方向和距离
            move_direction, move_distance = get_next_move(current_pos, target_pos)
            
            # 进行移动
            this_move_fuel_consumption=env.handle_tanker_move(tid,move_direction,move_distance)
        
            # 检查是否和目标农机重合，由于此处是dipatch，所以要求必须是目标农机
            whether_add_fuel,add_amount = env.try_refuel_given_tid_hid(tid,target_hid,i_step,must_be_target=True)
            
            
            # dispatch_agent进行after move的处理
            dispatch_agent.after_dispatch_move(env,target_hid,tid,whether_add_fuel,add_amount,this_move_fuel_consumption)
            
            # 到这里的逻辑是，首先进来肯定是有目标的，这里判断是否加完油变为无目标
            
            
            
            
        
        # # 接下来进行reposition的动作....................................
        # 出于方便，在决策reposition时就已经移动过了（为了计算势能差值）
        # 上面已经reposition过了
            
        env.reposition_tanker_with_target_position()
    
        # 时间流逝结束==============================
        # 到了当前step的结束-------------------------------------------

        dispatch_agent.after_every_step(env)
        reposition_agent.after_every_step(env)
        
        
        
                
    
    env.cal_metric_and_save()

    print_with_time(f'Total Fuel Added: {env.total_add_fuel_amount} L')
    print_with_time(f'Total Fuel Consumption of Tankers: {env.total_tanker_fuel_consumption}')
    print_with_time(f'Number of Fueling Operations Today: {env.add_fuel_num}')
    print_with_time(f'Harvester Working Status: {env.harvester_working_status}')
    print_with_time(f'Waiting Time for Low Fuel: {np.sum(env.harvester_waiting_step)}')
    print_with_time(f'Total Time Steps Available for Idle Tankers Today: {idle_available_count}')

    
    dispatch_agent.after_every_episode(env)
    reposition_agent.after_every_episode(env)
    
    

# 每个episode结束---------------------------------------------------------------  
       
    


if KEEP_VISUALIZATION_DATA_DAY_IDX!=-1:
    prefix = './outputs/'
    np.save(prefix+'check_harvester_loc.npy',check_harvester_loc)
    np.save(prefix+'check_tanker_loc.npy',check_tanker_loc)
    np.save(prefix+'check_harvester_still.npy',check_harvester_still)
    np.save(prefix+'check_harvester_request.npy',check_harvester_request)



print_with_time('-----------------End-------------------') # 训练/测试结束


print_with_time(env.cal_total_object(test_num*episode_num))
