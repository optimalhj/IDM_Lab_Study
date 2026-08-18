
from Dataset import *
from regions import *
from utils.CompleteRegion import *
from parameter import *


from toolkit.state import * 
from toolkit.geocal import *
from toolkit.time import print_with_time
from toolkit.extrafunc import *
from toolkit.sample import *

def measure_func(distance: float):
        """
        0 -> 200
        0.5km -> 200
        1km -> 100

        @param distance:
        @return:
        """
        # scale = 1  #
        # distance_m = 0.001 * distance  # km
        # return scale * (-distance_m)
        # a = 0.01

        return W_R * (math.exp(-W_D * distance))  # max: 0.5->0 0.05 10辆=0.5
    
    
def spatial_proximity_given_distance(distance):
    return math.exp(W_D*distance)

class HarvesterTankerCorporationEnvironment:
    
    
    def __init__(self,threshold_sample_method='gaussian'):
        # 可选 fix_half, gaussian
        
        # 
        # 是列表
        # 每个元素是元组，第一个是农机id没用，第二个是当天的记录
        # 当天的记录(25, 288, 4)是这样的，25农机数量，288x4就是轨迹

        
        self.threshold_sample_method = threshold_sample_method

        # 采用一个基于小数的Grid网络，以提高泛化性
        
        self.train_mode = REPOSITION_TRAIN_MODE or DISPATCH_TRAIN_MODE
        
        
        self.day_sample_policy = 0
        
        self.inner_count = 0
        
        
        # 训练和测试采用不同的数据集
        split = 'train.csv' if (self.train_mode or USE_TRAIN_DATA_FOR_TEST) else 'test.csv'
        self.dataset = TankerDataSetV3(os.path.join(DATA_DIR, split))
                
        self.complete_region = CompleteRegion(COMPLETE_MIN_LAT, COMPLETE_MIN_LNG, N_ROWS, N_COLS, 0.5, 0.5, load_path=None, use_general_distance=True)
        self.complete_region.make_working_regions(WORKING_AREAS)
        
        self.total_day_num_of_data = len(self.dataset.records_data)
        print_with_time('We are using {} days of data'.format(self.total_day_num_of_data)) #总共有{}天的数据
        print_with_time(f'We are using {DEVICE} as our training device') #当前使用的训练设备是{}
        
        self.big_env_tanker_fuel_consumption =0.0
        self.big_env_add_fuel_amount =0.0
        
        self.tanker_fuel_consumption_list = []
        self.add_fuel_amount_list = []
        self.harvester_waiting_step_list = []
        
        
        
        
        np.random.seed(SEED)
        # 提前采好农机的加油阈值，一个数据集内保持不变
        self.harvester_fuel_threshold = np.full((NUM_HARVESTERS,),FUEL_CAPACITY*REQUEST_THRESHOLD_PERCENTAGE)  # 每个农机的油量阈值，低于该值时请求加油
        for hid in range(NUM_HARVESTERS):
            self.resample_threshold_given_hid(hid)
        

        self.reset()    
        

    def step(self,action):
        pass
    
    def resample_threshold_given_hid(self,hid):
        
        if self.threshold_sample_method=='fix_half':
            return
        elif self.threshold_sample_method=='gaussian':
            # sample_gaussian_with_clipping defaults to a length-one array;
            # the per-harvester threshold slot is scalar.
            new_threshold = float(sample_gaussian_with_clipping()[0])
            self.harvester_fuel_threshold[hid]=new_threshold*FUEL_CAPACITY
        
    def resample_threshold_all_harvesters(self):
        for hid in range(NUM_HARVESTERS):
            self.resample_threshold_given_hid(hid)
    
    
        
        
    def refuel_num_min_max(self,day):
        
        all_harvester_working_time = []
        
        all_harvester_trajs = self.dataset.records_data[day][:,:,0]
        
        
        
        for hid in range(NUM_HARVESTERS):
            current_traj = all_harvester_trajs[hid]
            working_time = np.count_nonzero(current_traj)*5
            print(working_time)
            working_fuel_consumption = working_time * FUEL_COMSUMPTION_PER_STEP
            
            if working_fuel_consumption < FUEL_CAPACITY*0.4:
                min_refuel_num = 0
            else:    
                min_refuel_num = math.ceil((working_fuel_consumption-FUEL_CAPACITY)/FUEL_CAPACITY)
                
            max_refuel_num = math.floor(working_fuel_consumption/(FUEL_CAPACITY*0.4))

            
            all_harvester_working_time.append((min_refuel_num,max_refuel_num))

        
        return all_harvester_working_time
            
            
        
    
    def reset(self,day=-1):
        
        self.reposition_state_cost = 0.0
        
        if day != -1:
            day = day
        else:
            if self.day_sample_policy == 0:
                # 如果不指定天数，就随机选一天，通常作为训练集中的采样
                day = np.random.randint(0,self.total_day_num_of_data)
            elif self.day_sample_policy == 1:
                # 按顺序选取一天，通常作为测试集使用
                day = self.inner_count % self.total_day_num_of_data
            
        
        self.inner_count+=1
        
        self.i_step = 0
        self.i_episode = 0
        
        self.harvester_request_status = np.full((NUM_HARVESTERS,),-1)  # -1表示没请求，0表示刚请求，剩余整数表示发出请求过去的时间
        self.harvester_remaining_fuel = np.full((NUM_HARVESTERS,),FUEL_CAPACITY,dtype=float)  # 每个农机的剩余油量，初始为满油
        self.harvester_waiting_step = np.zeros((NUM_HARVESTERS,),dtype=int)  # 每个农机的等待时间步数，用于修正计划路径和实际路径的时间差（因为油不够而停止）
        
        
            
        
        
        # for hid in range(NUM_HARVESTERS):
        #     self.resample_threshold_given_hid(hid)
        
        self.harvester_working_status = np.full((NUM_HARVESTERS,),-1,dtype=int)  # 每个农机的工作状态，-1表示没开始工作，0表示工作中，1表示工作完成
        
        
        self.one_day_record = self.dataset.records_data[day]
        self.one_day_traj = self.one_day_record[:,:,0]

        self.harvester_all_position = np.zeros((NUM_HARVESTERS,288,2),dtype=int)
        self.harvester_current_position = np.zeros((NUM_HARVESTERS,2),dtype=int)  # 每个农机的当前位置，(col,row)
        
        
        
        
        init_arr = np.array([[INITIAL_TANKER_ROW,INITIAL_TANKER_COL]],dtype=float)
        self.tanker_current_position = np.repeat(init_arr,repeats=NUM_TANKERS,axis=0)
        
        tanker_pos_init_list = [np.array([INITIAL_TANKER_ROW,INITIAL_TANKER_COL],dtype=float),
                                np.array([INITIAL_TANKER_ROW+1,INITIAL_TANKER_COL+1],dtype=float),
                                np.array([INITIAL_TANKER_ROW-1,INITIAL_TANKER_COL-1],dtype=float),
                                np.array([INITIAL_TANKER_ROW+1,INITIAL_TANKER_COL-1],dtype=float)]
        
        
        self.tanker_current_position = np.vstack(tanker_pos_init_list[0:NUM_TANKERS])
        
        
        # elif REPOSITION_METHOD == 'chihaya':
        #     first_tanker = np.array([INITIAL_TANKER_ROW,INITIAL_TANKER_COL],dtype=float)
        #     second_tanker = np.array([INITIAL_TANKER_ROW+1,INITIAL_TANKER_COL+1],dtype=float)
        #     third_tanker = np.array([INITIAL_TANKER_ROW-1,INITIAL_TANKER_COL-1],dtype=float)
        #     self.tanker_current_position = np.vstack((first_tanker,second_tanker,third_tanker))
        
        # self.tanker_current_position= np.full((NUM_TANKERS,2),0,dtype=float)  # 每个油罐车的当前位置，(col,row)
        # self.tanker_current_position= np.tile([INITIAL_TANKER_ROW,INITIAL_TANKER_COL],(NUM_TANKERS,1),dtype=float)
        
        
        
        # 这里泛化一下，假设目标可以是队列
        self.tanker_target_hid = np.full((NUM_TANKERS,),-1,dtype=int)  # 每个油罐车的目标农机id，-1表示无目标
        
        self.tanker_target_hid_list = [[] for _ in range(NUM_TANKERS)]  # 每个油罐车的目标农机id列表，可能有多个
        

        # 新增一个target position，主要是为了特殊的reposition情况，即reposition到某个位置，如果是0，代表不是这种情况
        
        self.tanker_reposition_target_position = np.zeros((NUM_TANKERS,2),dtype=float)
        
        self.tanker_move_fuel_consumption = np.zeros((NUM_TANKERS,),dtype=float)  # 每个油罐车的移动油耗，用于统计
        
        self.tanker_add_fuel_amount = np.zeros((NUM_TANKERS,),dtype=float)  # 每个油罐车的加油量，用于统计


        for i in range(NUM_HARVESTERS):
            for j in range(288):
                self.harvester_all_position[i,j,1] = self.complete_region.col_index(self.one_day_traj[i,j])
                self.harvester_all_position[i,j,0] = self.complete_region.row_index(self.one_day_traj[i,j])
                
                
        self.harvester_all_position = np.repeat(self.harvester_all_position,5,axis=1)


        self.total_tanker_fuel_consumption = 0.0  # 总的油耗
        self.total_add_fuel_amount = 0.0  # 总的加油量
        self.harvester_working_time_count = np.zeros((NUM_HARVESTERS,),dtype=int)  # 每个农机的工作时间步数统计
        
        
        
        
        # self.harvester_working_time = np.zeros(self.max_n_harvester, dtype=int) 
        
        self.harvester_last_fuel_step = np.zeros((NUM_HARVESTERS,), dtype=int)
        self.harvester_last_fuel_amount = np.full((NUM_HARVESTERS,),FUEL_CAPACITY)
        

        # 统计信息
        
        
        
        self.add_fuel_num = 0 # 加油次数
        
        
        print_with_time('Initialization complete') #环境初始化完成
        # print('农机请求状态  维度,类型',harvester_request_status.shape,harvester_request_status.dtype)
        # print('农机剩余油量  维度,类型',harvester_remaining_fuel.shape,harvester_remaining_fuel.dtype)
        # print('农机等待时间步数  维度,类型',harvester_waiting_step.shape,harvester_waiting_step.dtype)
        # print('农机工作状态  维度,类型',harvester_working_status.shape,harvester_working_status.dtype)
        # print('农机位置  维度,类型',harvester_all_position.shape,harvester_all_position.dtype)
        # print('农机当前位置  维度,类型',harvester_current_position.shape,harvester_current_position.dtype)
        # print('油罐车位置  维度,类型',tanker_current_position.shape,tanker_current_position.dtype)
        # print('油罐车目标农机  维度,类型',tanker_target_hid.shape,tanker_target_hid.dtype)
        
        
        
        
        
    def cal_metric_and_save(self):    
        
        self.tanker_fuel_consumption_list.append(self.total_tanker_fuel_consumption)
        self.add_fuel_amount_list.append(self.total_add_fuel_amount)
        
        waiting_time = np.sum(self.harvester_waiting_step)
        
        self.harvester_waiting_step_list.append(waiting_time)
        
        metric = W_S*self.total_add_fuel_amount - W_C*self.total_tanker_fuel_consumption - W_WAITING*waiting_time
        
        print_with_time(f'Today\'s metric value: {metric}') #今日指标值
        print_with_time(f'reward = {metric}')
        # 这里存储的是某个数据集上的所有天数的结果
        # self.big_env_tanker_fuel_consumption += self.total_tanker_fuel_consumption 
        # self.big_env_add_fuel_amount += self.total_add_fuel_amount
        # self.harvester_waiting_step_list.append(self.harvester_waiting_step.copy())
        
    def cal_total_object(self,nums = 1):
        # 总目标函数值
        
        
        if not DISPATCH_TRAIN_MODE and not REPOSITION_TRAIN_MODE and KEEP_VISUALIZATION_DATA_DAY_IDX==-1:
            
            
            s_list = average_per_n_elements(self.add_fuel_amount_list,self.total_day_num_of_data)
            c_list = average_per_n_elements(self.tanker_fuel_consumption_list,self.total_day_num_of_data)
            w_list = average_per_n_elements(self.harvester_waiting_step_list,self.total_day_num_of_data)
            
            
            metric_list = []
            
            
            
            
            for i in range(TEST_REPEAT_NUM):
                s = s_list[i]
                c = c_list[i]
                w = w_list[i]
                
                r1 = W_S*s
                r2 = W_C*c
                r3 = W_WAITING*w
                
                metric_list.append(r1 - r2 - r3)
                
                # print_with_time(f'第{i+1}次测试数据集日均农机加油量：{s}')
                # print_with_time(f'第{i+1}次测试数据集日均油罐车油耗：{c}')
                # print_with_time(f'第{i+1}次测试数据集日均农机等待时间总和：{w}分钟')
                # print_with_time(f'第{i+1}次测试总奖励函数值：{r1}-{r2}-{r3}={r1 - r2 - r3}')
            
            print_with_time(f'{self.total_day_num_of_data} Test Results: {metric_list}') # 天测试结果指标列表
            miu,sigma = calculate_mean_std(metric_list)
            
            print_with_time(f'Mean：{miu}，Sigma：{sigma}') # 均值：{miu}，标准差：{sigma}
            
            
            s = sum(self.add_fuel_amount_list)/nums
            c = sum(self.tanker_fuel_consumption_list)/nums
            waiting = sum(self.harvester_waiting_step_list)/nums
            
            print_with_time(f'Daily Average Fuel Added: {s}') # 数据集日均农机加油量：
            print_with_time(f'Daily Average Tanker Fuel Consumption: {c}')
            print_with_time(f'Daily Average Harvester Waiting Time: {waiting} minutes')
            
            
            r1 = W_S*s
            r2 = W_C*c
            r3 = W_WAITING*waiting
            
            print_with_time(f'Total Reward Function Value: {r1}-{r2}-{r3}={r1-r2-r3}')
            
            
            return r1-r2-r3
        
        
        pass
    def render(self):
        pass
    
    
    def get_working_harvester_features(self,idle_tankers:list):
        
        harvesters_list = self.working_but_not_requesting_harvesters_list()
        features = np.zeros((len(idle_tankers),len(harvesters_list),3+1),dtype=float)
        
        for idxh,hid in enumerate(harvesters_list):
            
            refuel_intervel = self.i_step - self.harvester_last_fuel_step[hid]
            
            for idxt,tid in enumerate(idle_tankers):
                cos,sin,dist = get_relative_cos_sin_distance(self.tanker_current_position[tid],self.harvester_current_position[hid])
                features[idxt,idxh,0]=cos
                features[idxt,idxh,1]=sin
                features[idxt,idxh,2]=dist
                features[idxt,idxh,3]=refuel_intervel/TOTAL_STEP
            
        return features
        
    def distance_between_tanker_and_harvester(self,tid,hid):
        return minkowski_distance(self.tanker_current_position[tid],self.harvester_current_position[hid],p=1)
    
    def get_reposition_state(self,i_step):
        
        
        # start = time.perf_counter()
        
        # if self.state_dim == STATE_DIM_RETION_V3:
        # 这应该就是论文最后的状态，除自己外的加油车状态+农机状态+时间步
        
        
        # if self.reposition_dim == REPOSITION_STATE_DIM:

        
        # NxN-1x2
        other_tankers_relative_loc = subtract_self_features(self.tanker_current_position)
        other_tankers_relative_loc[:,:,0]/=ROW_NUMS
        other_tankers_relative_loc[:,:,1]/=COL_NUMS
        
        harvester_relative_loc = generate_machine_relative_location(self.harvester_current_position,self.tanker_current_position)
        harvester_relative_loc[:,:,0]/=ROW_NUMS
        harvester_relative_loc[:,:,1]/=COL_NUMS
        
        
        # if TRANSFORMER_VERSION2:
            
        #     harvester_feature = np.column_stack((self.is_active,self.request_status))
        #     harvester_feature_repeat = np.repeat(harvester_feature[np.newaxis,:,:], self.max_n_tanker, axis=0)
            
        # else:
        harvester_feature = self.generate_harvester_feature_reposition(i_step)
        # print(harvester_feature.shape)
        
        harvester_feature_repeat = np.repeat(harvester_feature[np.newaxis,:,:], NUM_TANKERS, axis=0)
        
        
        # NxDx6
        # NxDx4 if version2
        combine_harvester_feature = np.concatenate([harvester_relative_loc, harvester_feature_repeat], axis=2)
        
        
        # Nx1
        
        time_feature = np.full((NUM_TANKERS, 1), i_step/TOTAL_STEP, dtype=float)
        
        
        # NxN-1x2  
        # NxDx6
        # Nx1
        # self.obs = [other_tankers_relative_loc,combine_harvester_feature,time_feature]
        
        # end = time.perf_counter()
        
        # self.reposition_state_cost += (end-start)
    
        
        return (other_tankers_relative_loc,combine_harvester_feature,time_feature)
    
    
    
    def get_dispatch_state(self, i_step)->list[torch.Tensor]:
        
        
        # 加油车数量为N
        # 农机数量为M
        
        idle_tankers = self.idle_tankers_list()
        busy_tankers = [i for i in range(NUM_TANKERS) if i not in idle_tankers]
        # N维
        is_idle= np.zeros((NUM_TANKERS,),dtype=bool)
        is_idle[idle_tankers]=True
        
        # 3. 处理非空闲加油车：
        ## 3.1 获取所有非空闲加油车的索引
        non_idle_indices = np.where(~is_idle)[0]  # 形状：(K,)，K为非空闲加油车数量
        
        # 初始化目标位置为自身位置
        target_loc = self.tanker_current_position.copy()
        # 如果非空闲加油车有目标农机，则获取这些农机的坐标,作为目标位置
        for tid in busy_tankers:
            # target_hid = self.tanker_target_hid[tid]
            target_hid = self.tanker_target_hid_list[tid][-1]
            target_loc[tid] = self.harvester_current_position[target_hid]
        
        
        
        
        
        # # 取每行第一个元素，得到非空闲加油车对应的目标农机序号
        # # 跑的通的时候是+1，后面重构把这个去掉了
        # first_harvester_indices = np.array([self.tanker_targets[idx][0] for idx in non_idle_indices]).astype(int)
        # ## 批量获取目标农机的坐标
        # harvester_coords = self.cur_loc_harvester[first_harvester_indices]
        # # 批量对非空闲的加油车赋值
        # target_loc[non_idle_indices] = harvester_coords  # 高级索引批量赋值
        
        normalized_loc_tanker = self.tanker_current_position.copy()
        normalized_loc_tanker[:,0]/=ROW_NUMS
        normalized_loc_tanker[:,1]/=COL_NUMS
        
        target_loc[:,0]/=ROW_NUMS
        target_loc[:,1]/=COL_NUMS
        
        tanker_feature = np.hstack((
            normalized_loc_tanker, 
            target_loc, 
            is_idle.reshape(-1, 1)
            ))
        
        normalized_loc_harvester = self.harvester_current_position.copy().astype(float)
        normalized_loc_harvester[:,0]/=ROW_NUMS
        normalized_loc_harvester[:,1]/=COL_NUMS
        
        
        # 农机是否发出请求  self.request_status
        
        # 历史加油记录
        harvester_history_feature = self.generate_harvester_feature_reposition(i_step)
        
        # 是否被target
        # be_targeted_harvester = [self.tanker_target_hid[tid] for tid in busy_tankers ]
        
        be_targeted_harvester = [hid for tid in busy_tankers for hid in self.tanker_target_hid_list[tid]]
        
        harvester_targeted = np.zeros(NUM_HARVESTERS)
        harvester_targeted[be_targeted_harvester]=1
        # for hid in range(self.max_n_harvester):
        #     if hid in be_targeted_harvester_set:
        #         harvester_targeted[hid]=1
                
        harvester_feature = np.hstack([
            normalized_loc_harvester,
            harvester_history_feature,
            self.harvester_request_status.reshape(-1,1),
            harvester_targeted.reshape(-1,1)
            ])
        
        
        # # 筛选出所有空闲加油车的坐标
        # # 本回合已经认为不需要调度的车除外
        # is_idle[tankers_fixed_still]=False
        
        
        
        
        idle_tanker_coordinates = normalized_loc_tanker[idle_tankers]
        # 计算平均坐标，若无空闲加油车则返回[0.5, 0.5]
        if len(idle_tanker_coordinates) > 0:
            average_coordinate = np.mean(idle_tanker_coordinates, axis=0)
        else:
            average_coordinate = np.array([0.5, 0.5])
            
        # 构造一个假的农机特征，位置为平均坐标，其他特征为0或1
        no_action_fake_harvester_feature = np.array([
            average_coordinate[0],average_coordinate[1],
            0,0,1,1,1,0
        ])
        
        harvester_feature = np.vstack([harvester_feature,no_action_fake_harvester_feature])
            
        time_feature = np.array([i_step/TOTAL_STEP], dtype=float)
        
        
        dispatch_state = [
            torch.tensor(tanker_feature,dtype=torch.float32,device=DEVICE).unsqueeze(0),
            torch.tensor(harvester_feature,dtype=torch.float32,device=DEVICE).unsqueeze(0),
            torch.tensor(time_feature,dtype=torch.float32,device=DEVICE).unsqueeze(0)
        ]
        
        return dispatch_state
    
    
    def get_dispatch_mask(self):
        
        
        idle_tankers = self.idle_tankers_list()
        busy_tankers = [i for i in range(NUM_TANKERS) if i not in idle_tankers]
        # targeted_harvesters = [self.tanker_target_hid[tid] for tid in range(NUM_TANKERS) if self.tanker_target_hid[tid]!=-1]
        targeted_harvesters = self.targeted_harvesters_list()
        # 不需要加油的农机有两种情况，一种是没请求的，一种是已经被其他加油车锁定的
        no_need_add_fuel_harvesters = [hid for hid in range(NUM_HARVESTERS) if self.harvester_request_status[hid]==-1 or hid in targeted_harvesters]
        
        
        
        # need_add_fuel_harvesters = [hid for hid in range(NUM_HARVESTERS) if self.harvester_request_status[hid]!=-1 and hid not in targeted_harvesters] 
        
        # 初始化所有动作均可行,mask都为False
        mask = np.zeros((NUM_TANKERS,NUM_HARVESTERS+1),dtype=bool)
        
        mask[:,no_need_add_fuel_harvesters] = True  # 不需要加油的农机不能被调度
        
        # 为了保证每个加油车至少有一个可选动作
        
        mask[:,NUM_HARVESTERS] = False  # "不调度"动作始终可行
        
        # mask[:,NUM_HARVESTERS] =True # "不调度"始终不可行，用于测试
        
        # 当需要调度时,至少存在一个idletanker,理论上无需担心
        mask[busy_tankers,:] = True  # 忙碌的加油车不能调度
        
        
        
        flatterned_mask = mask.reshape(-1)
        
        
        
        return torch.tensor(flatterned_mask,dtype=torch.bool,device=DEVICE).unsqueeze(0)
        
    
    
    
    def tanker_move_towards_target_position(self,tid):
        # 加油车tid朝向目标位置移动一步
        
        
        current_pos = self.tanker_current_position[tid]
        target_pos = self.tanker_reposition_target_position[tid]
        
        direction,move_distance = get_next_move(current_pos,target_pos)
        
        self.handle_tanker_move(tid,direction,move_distance)
        
        
        # 如果到达目标位置，则清空目标位置
        if np.isclose(self.tanker_current_position[tid],target_pos,rtol=1e-3).all():
            self.tanker_reposition_target_position[tid]=0
    
    def reposition_tanker_with_target_position(self):
        for tid in range(NUM_TANKERS):
            if self.tanker_reposition_target_position[tid][0]!=0.0:
                self.tanker_move_towards_target_position(tid)
    
    
    def get_tid_hid_from_dispatch_action(self, action: int):
        
        # 要明确,动作是一个二维矩阵,被压平为一维向量
        # 行是加油车,列是农机,最后一列是"不调度"
        # 所以列数是 农机数量+1
       
        tanker_id = action // (NUM_HARVESTERS + 1)  # 整数除法计算行索引
        harvester_id = action % (NUM_HARVESTERS + 1)  # 取模运算计算列索引

        return tanker_id,harvester_id
    
    
    
    
    
    def generate_harvester_feature_reposition(self,i_step):
        
        # 农机数量x1
        how_long_since_last_fuel =i_step-self.harvester_last_fuel_step

        # print(how_long_since_last_fuel.shape)
        # print(self.harvester_working_time.shape)
        # print(self.harvester_last_fuel_amount.shape)
        # print(self.is_active.shape)
        
        harvester_feature = np.column_stack([
            self.harvester_working_time_count/TOTAL_STEP,
            how_long_since_last_fuel/TOTAL_STEP,
            self.harvester_last_fuel_amount/FUEL_CAPACITY,
            self.harvester_working_status
        ])
        
        '''大小为Mx4，M为农机数量'''
        return harvester_feature
    
    
    def idle_tankers_list(self):
        # return [i for i in range(NUM_TANKERS) if self.tanker_target_hid[i]==-1]
        return [i for i in range(NUM_TANKERS) if not self.tanker_target_hid_list[i]]
    
    
    def targeted_harvesters_list(self):
        return [hid for sublist in self.tanker_target_hid_list for hid in sublist]
    
    
    def get_need_add_fuel_harvesters(self):
        targeted_harvesters = self.targeted_harvesters_list()
        
        need_add_fuel_harvesters = [hid for hid in range(NUM_HARVESTERS) if self.harvester_request_status[hid]!=-1 and hid not in targeted_harvesters]   
        
        return need_add_fuel_harvesters
    
    def halting_but_not_targeted_harvesters_list(self):
        
        targeted_harvesters = self.targeted_harvesters_list()
        return [hid for hid in range(NUM_HARVESTERS) if self.harvester_remaining_fuel[hid]<=1e-3 and hid not in targeted_harvesters]
    
    
    def working_but_not_requesting_harvesters_list(self):
        return [hid for hid in range(NUM_HARVESTERS) if self.harvester_working_status[hid]==0 and self.harvester_request_status[hid]==-1]
        
    
    def add_refuel_target_given_tid_hid(self,tid,hid):
        # 给加油车tid添加农机hid作为目标
        
        
        self.tanker_reposition_target_position[tid] = 0
        
        if hid == NUM_HARVESTERS:
            return # 不进行任何调度
        
        
        if hid in self.tanker_target_hid_list[tid]:
            raise ValueError('该农机已是该加油车的目标')
        
        if hid not in self.tanker_target_hid_list[tid]:
            self.tanker_target_hid_list[tid].append(hid)
    
    
    def cancel_refuel_target_given_hid(self,hid):
        # 取消所有加油车对该农机的目标锁定
        for tid in range(NUM_TANKERS):
            if hid in self.tanker_target_hid_list[tid]:
                self.tanker_target_hid_list[tid].remove(hid)
                
                
    
    
    
    def matching_feature(self,tid,hid):
        
        current_cost = self.current_tasks_path_length(tid)
        
        
        extra_cost = self.extra_task_cost(tid,hid)
        total_cost = current_cost + extra_cost
        
        whether_idle = 1 if not self.tanker_target_hid_list[tid] else 0
        
        
        return [whether_idle,total_cost,extra_cost]
    
    
        
        
    def all_matching_feature_given_hid(self,hid):    
        f = []
        for tid in range(NUM_TANKERS):
            f.append(self.matching_feature(tid,hid)) 
        
        return np.array(f)
    
           
    
    
                
    def extra_task_cost(self,tid,hid):
        
        if not self.tanker_target_hid_list[tid]:
            current_pos = self.tanker_current_position[tid]
        else:
            last_hid = self.tanker_target_hid_list[tid][-1]
            current_pos = self.harvester_current_position[last_hid]
            
        target_pos = self.harvester_current_position[hid]
        
        
        return minkowski_distance(current_pos,target_pos,p=1)
        
        
        
            
        
    def current_tasks_path_length(self,tid):
        
        
        if not self.tanker_target_hid_list[tid]:
            return 0.0
        
        current_pos = self.tanker_current_position[tid]
        total_distance = 0.0
        
        
        
        for hid in self.tanker_target_hid_list[tid]:
            harvester_pos = self.harvester_current_position[hid]
            dist = minkowski_distance(current_pos,harvester_pos,p=1)
            current_pos = harvester_pos
            total_distance += dist
            
        return total_distance
            
        
        

        
        
    
    
    def get_potential_energy_given_tid_hid(self,tid,hid):
        # tid油罐车id
        # hid农机id
        
        tanker_pos = self.tanker_current_position[tid]
        harvester_pos = self.harvester_current_position[hid]
        
        distance = minkowski_distance(tanker_pos,harvester_pos,p=2)
        spatial_promixity = measure_func(distance)
        
        this_harvester_request_status = self.harvester_request_status[hid]
        
        return spatial_promixity
        
        # if this_harvester_request_status==-1:
        #     return spatial_promixity
        # else:
            
        #     this_harvester_request_status+=1
        #     return W_REQ*this_harvester_request_status*spatial_promixity
        
        
    def get_sum_potential_energy_given_tid(self,tid):
        
        # working_harvesters = [i for i in range(NUM_HARVESTERS) if self.harvester_working_status[i]==0]
        
        left_harvesters = self.working_but_not_requesting_harvesters_list()
        
        return sum([self.get_potential_energy_given_tid_hid(tid,hid) for hid in left_harvesters])
        
        
    def count_this_step_halting_harvesters(self,include_targeted = True):
        count = 0
        targeted_harvesters = self.targeted_harvesters_list()
        
        for hid in range(NUM_HARVESTERS):
            if self.harvester_remaining_fuel[hid]<=1e-3:
                # 如果include_targeted为真，则统计所有停机农机
                # 否则只统计未被锁定的停机农机
                if include_targeted or (hid not in targeted_harvesters):
                    count+=1
                    
        return count
            
    def try_refuel_given_tid_hid(self,tid,hid,i_step,must_be_target=True):
        
        
        if self.harvester_request_status[hid]==-1:
            return False,0
        
        if must_be_target and hid != self.tanker_target_hid_list[tid][0]:
            return False,0
        
        
        this_tanker_position = self.tanker_current_position[tid]
        this_harvester_position = self.harvester_current_position[hid]
        
        
        if not np.isclose(this_tanker_position,this_harvester_position,rtol=1e-3).all():
            return False,0
            
        else:    
            # 重合了
            # 给农机加油
            
            add_fuel_amount = FUEL_CAPACITY - self.harvester_remaining_fuel[hid]
            
            # add_record[hid].append(add_fuel_amount)
            
            
            self.total_add_fuel_amount += add_fuel_amount
            self.tanker_add_fuel_amount[tid] += add_fuel_amount
            
            
            self.harvester_remaining_fuel[hid] = FUEL_CAPACITY
            # 重置请求状态
            self.harvester_request_status[hid] = -1
            
            # 该加油车没有目标了
            # 转向下一个目标
            if self.tanker_target_hid_list[tid]:
                self.tanker_target_hid_list[tid].pop(0)
            
            # self.resample_threshold_given_hid(hid)
            
            
            self.harvester_last_fuel_amount[hid] = add_fuel_amount
            self.harvester_last_fuel_step[hid] = i_step
            
            
            
            
            self.add_fuel_num += 1
            return True,add_fuel_amount
    
    def is_tanker_in_working_region(self,tid):
        # return False
    
        r,c = self.tanker_current_position[tid]

        for i in range(1, self.complete_region.n_working_regions):
            wr = self.complete_region.working_regions[i]
            if wr.min_r <= r <= wr.max_r and wr.min_c <= c <= wr.max_c:
                return True
        return False
    
    
    def get_reposition_move_mask(self,tid):
        
        mask = np.zeros((5,),dtype=bool)
        
        this_tanker_position = self.tanker_current_position[tid]
        
        # 直接截断取整好了
        r = int(this_tanker_position[0])
        c = int(this_tanker_position[1])
        
        if r== N_ROWS:
            mask[ACTION_RIGHT] = True
        if r==0:
            mask[ACTION_LEFT] = True
        if c== N_COLS:
            mask[ACTION_UP] = True
        if c==0:
            mask[ACTION_DOWN] = True
        
        return mask
        
        
        
    def handle_tanker_move(self,tid,move_direction,move_distance = -1):
        
        # 表示未指定移动距离
        if move_distance == -1:
            move_distance = 1
            
        whether_in_farmland = self.is_tanker_in_working_region(tid)    
        
        if whether_in_farmland:
            move_distance = min(move_distance,FARMLAND_TANKER_SPEED_GRID_PER_MIN)
        else:
            move_distance = min(move_distance,NORMALLAND_TANKER_SPEED_GRID_PER_MIN)
        
        
        
        if move_direction == ACTION_RIGHT:
            self.tanker_current_position[tid,0] += move_distance
        elif move_direction == ACTION_LEFT:
            self.tanker_current_position[tid,0] -= move_distance
        elif move_direction == ACTION_UP:
            self.tanker_current_position[tid,1] += move_distance
        elif move_direction == ACTION_DOWN:
            self.tanker_current_position[tid,1] -= move_distance
        
        
        this_move_fuel_comsumption = 0
        
        if move_direction!= ACTION_STAY:
            
            this_move_fuel_comsumption = TANKER_FUEL_CONSUMPTION_PER_GRID * move_distance
            self.total_tanker_fuel_consumption += this_move_fuel_comsumption
            
        self.tanker_move_fuel_consumption[tid] += this_move_fuel_comsumption    
            
            
        return this_move_fuel_comsumption

if __name__ == '__main__':
    env = HarvesterTankerCorporationEnvironment()