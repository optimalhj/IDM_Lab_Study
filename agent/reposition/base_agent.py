from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from environment import HarvesterTankerCorporationEnvironment
from parameter import *


class BaseRepositionAgent(ABC):
    """智能体基类（定义必须实现的核心接口）"""

    def __init__(self,train_mode):
        """基类可实现通用初始化逻辑"""
        self.train_mode = train_mode

    def model_initialization(self,load_episode=-1) -> None:
        """模型初始化接口（可选复用，派生类可重写）"""
        return -1
    
    def before_every_episode(self) -> None:
        """每个新回合开始前的准备工作（可选复用，派生类可重写）"""
        pass
    
    
    def after_every_episode(self,env) -> None:
        """每个回合结束后的收尾工作（可选复用，派生类可重写）"""
        pass
    
    def after_every_step(self, env: HarvesterTankerCorporationEnvironment) -> None:
        """每个时间步结束后的收尾工作（可选复用，派生类可重写）"""
        pass
    
    def before_reposition_move(self, env: HarvesterTankerCorporationEnvironment) -> None:
        pass
    
    def after_reposition_move(self, env: HarvesterTankerCorporationEnvironment) -> None:
        """每次派遣动作执行后的收尾工作（可选复用，派生类可重写）"""
        pass
    
    
    @abstractmethod
    def take_reposition_action(self, env: HarvesterTankerCorporationEnvironment,idle_tankers:list) -> Any:
        
        raise NotImplementedError
    
    

    @classmethod
    def print_info(cls) -> None:
        """打印智能体类型信息（静态辅助接口）"""
        print(f"智能体类型：{cls.__name__}")