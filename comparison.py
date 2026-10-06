import main_single_stage_cp, main_single_stage_gp
import time
import random

def set_horizon(boms, factories, deliveries, params):

    target = dict(zip(params["final_product"], params["amount"]))
    producers = {}
    for fc in factories:
        for jt in factories[fc]:
            producers.setdefault(jt, []).append(fc)

    req = {} # 필요 생산량 : 최종 목표량과 상위 제품의 소비량 중 큰 값
    def need(jt):
        if jt not in req:
            req[jt] = max(target.get(jt, 0), sum(need(parent) * boms[parent][jt] for parent in boms if jt in boms[parent]))
        return req[jt]

    def make_time(jt): # 생산 공장들이 나눠서 need(jt) 개를 만드는 최소 시간 (배송은 lot 단위이므로 공장별 생산량은 최소 lot 의 배수로 내림)
        t = 0
        while sum(t // factories[fc][jt]["time"] // min(factories[fc][jt]["lots"]) * min(factories[fc][jt]["lots"]) for fc in producers[jt]) < need(jt): t += 1
        return t

    finish = {}
    def finish_time(jt):
        if jt not in finish:
            arrive = [finish_time(ing) + max(deliveries[fc1][fc2] if fc1 != fc2 else 0 for fc1 in producers[ing] for fc2 in producers[jt]) for ing in boms.get(jt, {})]
            finish[jt] = max([1] + arrive) + make_time(jt)
        return finish[jt]

    return max(finish_time(jt) for jt in target) + 1 # job 종료 시점 <= horizon - 1

class Process:
    def __init__(self): pass
class Deliver:
    def __init__(self): pass
def start(boms, factories, holding_cost, deliveries, params, comparison_num=15):
    process, deliver, ini_set = Process(), Deliver(), {}
    for fc in factories.keys():
        ini_set[fc] = {}
        for jt in factories[fc].keys():
            ini_set[fc][jt] = factories[fc][jt]["lots"]
            setattr(process, f"{fc}{jt}", factories[fc][jt]["time"])
    for fc1 in deliveries.keys():
        for fc2 in deliveries[fc1].keys():
            setattr(deliver, f"{fc1}{fc2}", deliveries[fc1][fc2])

    horizon_info = set_horizon(boms, factories, deliveries, params)
    cp_times, lp_times = [], []
    print("Cp")
    for _ in range(comparison_num):
        st = time.time()
        main_single_stage_cp.system(process, deliver, boms, holding_cost, ini_set, params, horizon_info)
        cp_times.append(time.time() - st)

    for _ in range(comparison_num):
        st = time.time()
        main_single_stage_gp.system(process, deliver, boms, holding_cost, ini_set, params, horizon_info)
        lp_times.append(time.time() - st)

    print("cp :", sum(cp_times) / comparison_num, cp_times)
    print("lp :", sum(lp_times) / comparison_num, lp_times)

def main():

    params = {"tps": 8, "final_product": ["JT12", "JT9"], "amount": [1, 1],
                  "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}} # 목적함수 가중치
    
    boms = {
        "JT4": {
            "JT1": 2,
            "JT2": 2},
        "JT5": {
            "JT1": 3},
        "JT9": {
            "JT4": 1,
            "JT5": 1},
        "JT12": {
            "JT9": 1,
            "JT5": 1}}

    factories = {
        "Fc1": {
            "JT1": {"lots": [3], "time": 1},
            "JT2": {"lots": [4, 8], "time": 1}},

        "Fc2": {
            "JT1": {"lots": [1, 2, 3, 4], "time": 2},
            "JT5": {"lots": [1, 2], "time": 2}},
        
        "Fc3": {
            "JT4": {"lots": [2], "time": 2},
            "JT5": {"lots": [2], "time": 2},
            "JT9": {"lots": [1], "time": 3}},

        "Fc4": {
            "JT9": {"lots": [1], "time": 3}},

        "Fc5": {
            "JT12": {"lots": [1], "time": 4}}}

    holding_cost = {"JT1": 1, "JT2": 1, "JT4": 3, "JT5": 3, "JT9": 6, "JT12": 10}

    fcs = list(factories)
    random.seed(4233)
    deliveries = {fc1: {fc2 : random.randint(3, 8) if fc1 != fc2 else 1 for fc2 in fcs} for fc1 in fcs}
    start(boms, factories, holding_cost, deliveries, params)

if __name__ =="__main__":
    main()