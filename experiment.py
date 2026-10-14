import main_single_stage_cp, main_single_stage_gp, main_single_stage_cp_various_trucks, main_single_stage_gp_various_trucks
import random
import os
from copy import deepcopy
import matplotlib.pyplot as plt
import mysql.connector
from private import *

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

def mysql_initialize(): # DB 를 새로 만들고 계산 시간 기록 테이블 생성
    conn = mysql.connector.connect(user=user, password=password)
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`;")
    cursor.execute(f"CREATE DATABASE `{db_name}`;")
    cursor.execute(f"""
        CREATE TABLE `{db_name}`.`{table_time_record}`(
        DATASET varchar(64) NOT NULL PRIMARY KEY,
        TIME float NOT NULL);""")
    conn.commit()
    cursor.close()

def mysql_record(key, calculating_time, info, field="wip"): # key 의 계산 시간 기록 + key 테이블 (행 : 시간, 열 : 공장_JT, 값 : field 수량) 생성
    conn = mysql.connector.connect(user=user, password=password, database=db_name)
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO `{table_time_record}` VALUES (%s, %s);", (key, calculating_time))

    # info : system 반환 dict
    #   "makespan" (int), "holding_cost" / "truck_used" / "truck_travel" (int | float)
    #   "jobs", "in_transit", "trucks", "truck_log", "virtual_moves" (list[dict])
    #   "factory" (list[dict]) : [{"t": int, "fc": str, "jt": str, "wip", "produced", "consumed", "sent", "received": int | float}, ...]
    #       t -> fc -> jt 순서로 모든 (t, fc, jt) 조합이 한 행씩 존재
    table = {} # table[t][(fc, jt)] = 수량
    for row in info["factory"]:
        if row["t"] not in table: table[row["t"]] = {}
        table[row["t"]][(row["fc"], row["jt"])] = row[field]

    cols = list(table[0].keys()) # 열 : t = 0 의 (fc, jt) 순서
    key_wip = key + "wip"
    cursor.execute(f"DROP TABLE IF EXISTS `{key_wip}`;")
    col_defs = "t int NOT NULL PRIMARY KEY"
    for fc, jt in cols:
        col_defs += f", `{fc}_{jt}` float NOT NULL"
    cursor.execute(f"CREATE TABLE `{key_wip}`({col_defs});")

    placeholders = ", ".join(["%s"] * (len(cols) + 1)) # t + 공장_JT 열
    for t in sorted(table.keys()):
        values = [t]
        for fc, jt in cols:
            values.append(table[t][(fc, jt)])
        cursor.execute(f"INSERT INTO `{key_wip}` VALUES ({placeholders});", values)
    conn.commit()
    cursor.close()

class Process:
    def __init__(self): pass
class Deliver:
    def __init__(self): pass
def start(boms, factories, holding_cost, deliveries, trucks, params, printing, saving, key, gantt_dir, repetition=1): # key : mysql 기록 / 간트차트 파일용 dataset 이름
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
    stages = [ # ((gp, cp) 모델, (gp, cp) 결과, (gp, cp) 이름, system 추가 인자, params 추가 항목)
        ((main_single_stage_gp.system, main_single_stage_cp.system), (lp_times, cp_times), ("lp", "cp"), (), {"tps": len(trucks)}),
        ((main_single_stage_gp_various_trucks.system, main_single_stage_cp_various_trucks.system), (lp_various_trucks_times, cp_various_trucks_times), ("lp_various_trucks", "cp_various_trucks"), (trucks,), {})]

    def solved(systems, times_lists, names, extra_args, extra_params, horizon): # 모든 모델이 horizon 에서 repetition 번 모두 풀리면 True
        records = [] # stage 전체가 풀린 경우에만 결과 반영 (실패한 horizon 의 시간은 버림)
        for idx, (system, name) in enumerate(zip(systems, names)):
            params_tmp = {**deepcopy(params), **extra_params}
            if idx == 1: params_tmp.pop("float_unit")

            for rep in range(1, repetition + 1):
                calculating_time, info = system(process, deliver, boms, holding_cost, ini_set, *extra_args, params_tmp, horizon, printing, saving, os.path.join(gantt_dir, f"{name}_{key}_{rep}.png"))
                if not calculating_time: return False
                records.append((idx, f"{name}_{key}_{rep}", calculating_time, info))

        for idx, record_key, calculating_time, info in records:
            times_lists[idx].append(calculating_time)
            mysql_record(record_key, calculating_time, info)
        return True

    stage, horizon = 0, lower_bound(boms, factories, deliveries, params) + 1 # job 종료 시점 <= horizon - 1 이므로 이보다 작은 horizon 은 무조건 infeasible
    while stage < len(stages): # 다음 stage 는 처음부터가 아니라 앞 stage 가 풀린 horizon 부터 이어서 탐색
        if solved(*stages[stage], horizon): stage += 1
        else: horizon += 1

    return [sum(times) / repetition for times in (lp_times, cp_times, lp_various_trucks_times, cp_various_trucks_times)]

def main():

    from experiment_dataset import repetition, datasets
    random.seed(4233)
    printing, saving = False, True
    gantt_dir = "reuslts_gantt_charts"
    if saving: os.makedirs(gantt_dir, exist_ok=True)
    mysql_initialize()

    graph = {}
    for dataset in datasets:
        params, boms, factories, holding_cost, trucks = dataset["params"], dataset["boms"], dataset["factories"], dataset["holding_cost"], dataset["trucks"]
        key = f"fc{len(factories)}_tr{len(trucks)}_jt{len(set([jt for fc in factories.keys() for jt in factories[fc]]))}_fp{len(params["final_product"])}({",".join(str(value) for value in params["amount"])})_b{len(boms)}_"

        fcs = list(factories)
        deliveries = {fc1: {fc2: random.randint(3, 8) if fc1 != fc2 else 1 for fc2 in fcs} for fc1 in fcs}

        i = 1
        while key + str(i) in graph: i += 1
        key_tmp = key + str(i)
        print(key_tmp)
        graph[key_tmp] = start(boms, factories, holding_cost, deliveries, trucks, params, printing, saving, key_tmp, gantt_dir, repetition)
        print()

    x = list(graph)
    for idx, system in enumerate(("lp", "cp", "lp_various_trucks", "cp_various_trucks")):
        plt.plot(x, [graph[key][idx] for key in x], label=system, marker="o", linestyle="--")
    plt.legend()
    plt.xlabel("dataset")
    plt.ylabel("time")
    plt.show()
if __name__ =="__main__":
    main()