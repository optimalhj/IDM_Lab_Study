import main_single_stage_cp, main_single_stage_gp, main_single_stage_cp_various_trucks, main_single_stage_gp_various_trucks
import random
from copy import deepcopy

class Process:
    def __init__(self): pass
class Deliver:
    def __init__(self): pass
def start(boms, factories, holding_cost, deliveries, trucks, params, comparison_num=1):
    process, deliver, ini_set = Process(), Deliver(), {}
    for fc in factories.keys():
        ini_set[fc] = {}
        for jt in factories[fc].keys():
            ini_set[fc][jt] = factories[fc][jt]["lots"]
            setattr(process, f"{fc}{jt}", factories[fc][jt]["time"])
    for fc1 in deliveries.keys():
        for fc2 in deliveries[fc1].keys():
            setattr(deliver, f"{fc1}{fc2}", deliveries[fc1][fc2])

    cp_times, lp_times, cp_various_trucks_times, lp_various_trucks_times = [], [], [], []
    horizon = 1
    while horizon:
        calculating_time = 0
        for idx, (system, times_list) in enumerate(zip((main_single_stage_cp.system, main_single_stage_gp.system, main_single_stage_cp_various_trucks.system, main_single_stage_gp_various_trucks.system), (cp_times, lp_times, cp_various_trucks_times, lp_various_trucks_times))):
            params_tmp = deepcopy(params)

            if idx in (0, 2):
                params_tmp.pop("float_unit")
            if idx in (0, 1):
                params_tmp["tps"] = len(trucks)
                calculating_time = system(process, deliver, boms, holding_cost, ini_set, params_tmp, horizon)
            else:
                calculating_time = system(process, deliver, boms, holding_cost, ini_set, trucks, params_tmp, horizon)
            if not calculating_time:
                break
            times_list.append(calculating_time)
        if calculating_time:
            break
        horizon += 1


    print("cp :", sum(cp_times) / comparison_num, cp_times)
    print("lp :", sum(lp_times) / comparison_num, lp_times)
    print("var_tr_cp :", sum(cp_various_trucks_times) / comparison_num, cp_various_trucks_times)
    print("var_tr_lp :", sum(lp_various_trucks_times) / comparison_num, lp_various_trucks_times)
def main():
    params = {"final_product":["JT12"], "amount": [1], "float_unit": ["JT4", "JT9"],
              "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}}  # 목적함수 가중치

    boms = {
        "JT4": {
            "JT1": 2,
            "JT2": 2},
        "JT5": {
            "JT1": 3},
        "JT9": {
            "JT4": 3,
            "JT5": 1},
        "JT12": {
            "JT9": 1,
            "JT5": 1}}

    factories = {
        "Fc1": {
            "JT1": {"lots": [1], "time": 1},
            "JT2": {"lots": [1], "time": 1}},

        "Fc2": {
            "JT1": {"lots": [1], "time": 2},
            "JT5": {"lots": [1], "time": 2}},

        "Fc3": {
            "JT4": {"lots": [1], "time": 2},
            "JT5": {"lots": [1], "time": 2},
            "JT9": {"lots": [1], "time": 3}},

        "Fc4": {
            "JT9": {"lots": [1], "time": 3}},

        "Fc5": {
            "JT12": {"lots": [1], "time": 4}}}

    holding_cost = {"JT1": 1, "JT2": 1, "JT4": 3, "JT5": 3, "JT9": 6, "JT12": 10}

    # 트럭별 feature (cap : 적재 용량) → feature 가 모두 같은 트럭끼리는 자동으로 대칭 제거
    trucks = {f"tr{i + 1}": {"cap": cap} for i, cap in enumerate([8, 8, 5, 5, 3, 3])}

    fcs = list(factories)
    random.seed(4233)
    deliveries = {fc1: {fc2: random.randint(3, 8) if fc1 != fc2 else 1 for fc2 in fcs} for fc1 in fcs}
    start(boms, factories, holding_cost, deliveries, trucks, params)

if __name__ =="__main__":
    main()