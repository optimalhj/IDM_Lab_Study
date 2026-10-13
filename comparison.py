import main_single_stage_cp, main_single_stage_gp, main_single_stage_cp_various_trucks, main_single_stage_gp_various_trucks
import random
from copy import deepcopy

def lower_bound(boms, factories, deliveries, params):
    # 어떤 실행 가능해도 이보다 빨리 끝날 수 없는 makespan 하한 (트럭 / lot / 재료 경합을 무시한 완화)
    target = dict(zip(params["final_product"], params["amount"]))
    producers = {}
    for fc in factories:
        for jt in factories[fc]:
            producers.setdefault(jt, []).append(fc)

    # 최종 제품은 "공장별 최대 재고의 합 >= amount" 로만 요구되므로 (같은 1 개가 배송 전후로 두 번 셀 수 있음) 1 개만 확실히 필요
    # 재료는 상위 job 시작 시 bom 만큼 실제로 소비되므로 그 양은 반드시 생산해야 함
    req = {}
    def need(jt):
        if jt not in req:
            req[jt] = max(1 if jt in target else 0, sum(need(parent) * boms[parent][jt] for parent in boms if jt in boms[parent]))
        return req[jt]

    gap = lambda g, fc: 0 if g == fc else deliveries[g][fc] # 같은 공장이면 배송 없이 바로 소비

    ends = {}
    def end_times(g, jt, k): # g 가 jt 를 k 개 만들 때 각 job 의 최소 종료 시점 (같은 공장 같은 job 은 순차 생산)
        lst = ends.setdefault((g, jt), [])
        while len(lst) < k:
            n = len(lst) + 1
            ready = max([0] + [avail(ing, n * boms[jt][ing], g) for ing in boms.get(jt, {})]) # n 번째 job 시작 전 재료 n * bom 개 확보
            lst.append(max(ready, lst[-1] if lst else 0) + factories[g][jt]["time"])
        return lst[:k]

    def count(jt, q, T, fc=None): # T 까지 fc 에 도착할 수 있는 jt 개수 (fc=None : 어디서든 생산 완료)
        return sum(sum(e + (gap(g, fc) if fc else 0) <= T for e in end_times(g, jt, q)) for g in producers[jt])

    memo = {}
    def avail(jt, q, fc=None): # jt 를 q 개 확보할 수 있는 가장 빠른 시점
        if (jt, q, fc) not in memo:
            T = 0
            while count(jt, q, T, fc) < q: T += 1
            memo[(jt, q, fc)] = T
        return memo[(jt, q, fc)]

    for jt in producers: need(jt)
    return max(avail(jt, req[jt]) for jt in producers if req[jt]) # 모든 job 종료 <= makespan

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
    horizon = lower_bound(boms, factories, deliveries, params) + 1 # job 종료 시점 <= horizon - 1 이므로 이보다 작은 horizon 은 무조건 infeasible
    while horizon:
        calculating_time = 0
        for idx, (system, times_list) in enumerate(zip((main_single_stage_gp.system, main_single_stage_cp.system), (cp_times, lp_times))):
            params_tmp = deepcopy(params)
            if idx == 1: params_tmp.pop("float_unit")

            params_tmp["tps"] = len(trucks)
            calculating_time = system(process, deliver, boms, holding_cost, ini_set, params_tmp, horizon)

            if not calculating_time:
                break
            times_list.append(calculating_time)
        if calculating_time:
            break
        horizon += 1
    while horizon:
        calculating_time = 0
        for idx, (system, times_list) in enumerate(zip((main_single_stage_gp_various_trucks.system, main_single_stage_cp_various_trucks.system), (cp_various_trucks_times, lp_various_trucks_times))):
            params_tmp = deepcopy(params)
            if idx == 1: params_tmp.pop("float_unit")
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
              "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}}

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