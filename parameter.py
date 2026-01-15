import os

# 随机性参数
SEED = 2333


# 运行设备参数
GPU_ID = 0


# 环境格子参数
ROW_NUMS = 155
COL_NUMS = 185

# 自然参数

LAT_PER_METER = 8.993203677616966e-06
LNG_PER_METER = 1.1700193970443768e-05


# INITIAL_TANKER_ROW = 0
# INITIAL_TANKER_COL = 0
INITIAL_TANKER_ROW = ROW_NUMS//2
INITIAL_TANKER_COL = COL_NUMS//2

TOTAL_STEP = 288*5


#环境运行参数，油耗，各种个体的数量等
NUM_HARVESTERS = 25
NUM_TANKERS = 3
FUEL_CAPACITY = 200  # 农机油箱容量
FUEL_COMSUMPTION_PER_STEP = 0.4 # 农机每个时间步的油耗，单位L

FARMLAND_TANKER_SPEED_GRID_PER_MIN = 0.2 # 每分钟加油车在农田内的移动速度，单位：网格/分钟
NORMALLAND_TANKER_SPEED_GRID_PER_MIN = 1 # 每分钟加油车在普通地面的移动速度，单位：网格/分钟

SIDE_LENGTH_OF_GRID = 0.5  # 每个网格的边长，单位km

TANKER_FUEL_CONSUMPTION_PER_KM = 0.15 # 加油车每公里的油耗，单位L/km
TANKER_FUEL_CONSUMPTION_PER_GRID = TANKER_FUEL_CONSUMPTION_PER_KM * SIDE_LENGTH_OF_GRID # 加油车每个网格的油耗，单位L/网格

REQUEST_THRESHOLD_PERCENTAGE = 0.5  # 当农机剩余油量低于该百分比时，发出加油请求（默认改均值下的高斯分布）


# 移动参数
ACTION_UP = 0
# ACTION_RU = 2
ACTION_LEFT = 1
ACTION_STAY = 2
ACTION_RIGHT = 3
# ACTION_LD = 6
ACTION_DOWN = 4

TRACK_METHOD = 'x-first' # 'y-first' 'diagonal'



# reward shaping 参数
W_D = 1e-2


W_R = 1.0


# 奖励和评估系数
W_S = 0.1   #每L加油奖励

W_C = 0.1


W_WAITING = 0.02 # 每分钟等待惩罚0.02


INCLUDE_WAITING_PENALTY = True

# 学习相关参数
MEMORY_CAPACITY = 100
LR = 0.001
BEGIN_LERAN_MEMORY_PERCENTAGE = 0.8  # 达到多少记忆容量后开始学习
BEGIN_LERAN_MEMORY_SIZE = int(MEMORY_CAPACITY*BEGIN_LERAN_MEMORY_PERCENTAGE)

GAMMA = 0.99

EPS_START = 0.9
EPSILON = 0.01

EPS_END = 0.1

BATCH_SIZE = 32

TARGET_UPDATE_FREQUENCY = 10  # 目标网络更新频率

LEARN_FREQUENCY = 1  # 每隔多少步进行一次学习

# 模型保存参数
SAVE_MODEL_FREQUENCY = 10  # 每隔多少episode保存一次模型


# 表示上限episodenum
REPOSITION_EPISODE_NUM = 2000
DISPATCH_EPISODE_NUM = 2000

# 消融实验
NO_USE_PBRS = False

# 双策略训练还是测试模式
REPOSITION_TRAIN_MODE = False
DISPATCH_TRAIN_MODE = False

TEST_REPEAT_NUM = 5

DISPATCH_METHOD = 'EasyMatch'

REPOSITION_METHOD = 'Chihaya'


DATASET_ID = 1

# 指定要保存哪一天的训练数据，-1代表不保存。指定某一天后，仅在该天进行测试，可视化数据
KEEP_VISUALIZATION_DATA_DAY_IDX = -1

USE_TRAIN_DATA_FOR_TEST = False


MODEL_SAVE_DIR = 'model/EasyMatch'


# 跟POLAR相关




import argparse
import inspect

def auto_generate_args():
    """自动扫描当前模块中的大写变量，生成对应的argparse参数"""
    parser = argparse.ArgumentParser()
    
    # 获取当前模块的所有变量
    current_module = inspect.currentframe().f_back.f_globals
    
    # 筛选出大写变量（通常宏变量用全大写命名）
    uppercase_vars = {
        name: value for name, value in current_module.items()
        if name.isupper() and not name.startswith('_')  # 排除内置变量
    }
    
    # 为每个大写变量自动生成add_argument
    for var_name, default_value in uppercase_vars.items():
        # 转换变量名为命令行参数名（全大写转小写，如LR→--lr）
        arg_name = f"--{var_name.lower()}"
        
        # 自动推断参数类型（根据默认值）
        arg_type = type(default_value)
        
        # 生成帮助信息（可自定义格式）
        help_msg = f"{var_name}的默认值: {default_value}"
        
        # 特殊处理布尔类型（避免命令行传入值的问题）
        if arg_type is bool:
            # 布尔参数用action='store_true'/'store_false'
            if default_value is False:
                parser.add_argument(arg_name, action='store_true', help=help_msg)
            else:
                parser.add_argument(arg_name, action='store_false', help=help_msg)
        else:
            parser.add_argument(
                arg_name,
                type=arg_type,
                default=default_value,
                help=help_msg
            )
    
    return parser.parse_args()

# 第二步：自动生成参数解析并更新变量值
args = auto_generate_args()

# 第三步：将解析结果更新回大写变量（保持变量名一致）
for var_name in [name for name in globals() if name.isupper() and not name.startswith('_')]:
    arg_name = var_name.lower()
    if hasattr(args, arg_name):
        globals()[var_name] = getattr(args, arg_name)
        
        

import torch 
DEVICE = torch.device("cuda:" + str(GPU_ID) if torch.cuda.is_available() else "cpu")

# 现在统一一下，模型的参数和模型的输出等都应该放在统一的文件夹下

# MODEL_SAVE_DIR = os.path.join('./result/',MODEL_SAVE_DIR)
MODEL_REPOSITION_SAVE_DIR = os.path.join(MODEL_SAVE_DIR,'reposition/')
MODEL_DISPATCH_SAVE_DIR = os.path.join(MODEL_SAVE_DIR,'dispatch/')
