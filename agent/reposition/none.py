from agent.reposition.base_agent import BaseRepositionAgent

class NoneRepositionAgent(BaseRepositionAgent):
    """不进行重定位的智能体"""

    def __init__(self, train_mode: bool = True):
        super().__init__(train_mode)

    def take_reposition_action(self, env, idle_tankers: list):
        # 不进行任何重定位操作
        return None