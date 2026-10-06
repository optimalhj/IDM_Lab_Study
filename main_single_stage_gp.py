import random
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import gurobipy as gp
from gurobipy import GRB

def system(process, deliver, boms, holding_cost, ini_set, params, horizon):
    need = {}
    def explode(jt, qty):
        need[jt] = need.get(jt, 0) + qty
        for ingredient in boms.get(jt, {}).keys(): explode(ingredient, qty * boms[jt][ingredient])
    for final_product, amount in zip(params["final_product"], params["amount"]): explode(final_product, amount)
    max_job = {fc: {jt: -(-need.get(jt, 0) // min(ini_set[fc][jt])) * min(ini_set[fc][jt]) for jt in ini_set[fc].keys()} for fc in ini_set.keys()}

    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    fc_wip_t, delivering = {}, {}
    for fc in ini_set.keys():
        fc_wip_t[fc] = {}
        for jt in ini_set[fc].keys():
            fc_wip_t[fc][jt] = {t: md.addVar(vtype=GRB.CONTINUOUS if jt in params["float_unit"] else GRB.INTEGER, lb=0, name=f"{fc}_{jt}_{t}") if t else 0 for t in range(horizon)}

            for fc_prime in set([fc_prime for fc_prime in ini_set.keys() if fc_prime != fc for jt_prime in ini_set[fc_prime] if jt_prime in boms and jt in boms[jt_prime]]): # 같은 공장 안에서 쓰는 재료는 배송 없이 fc_wip_t 에서 바로 소비
                if fc not in delivering: delivering[fc] = {}
                if fc_prime not in delivering[fc]: delivering[fc][fc_prime] = {}
                delivering[fc][fc_prime][jt] = {t: {lot_unit: md.addVar(vtype=GRB.INTEGER, lb=0, ub=max_job[fc][jt] // lot_unit, name=f"{fc}_{jt}_{t}_deliver_to_{fc_prime}_{lot_unit}") for lot_unit in ini_set[fc][jt]} for t in range(1, horizon)}
    for fc in delivering.keys():
        for fc_prime in delivering[fc].keys():
            for ingredient in delivering[fc][fc_prime].keys():
                if ingredient not in fc_wip_t[fc_prime]:
                    fc_wip_t[fc_prime][ingredient] = {t: md.addVar(vtype=GRB.CONTINUOUS if ingredient in params["float_unit"] else GRB.INTEGER,  lb=0, name=f"{fc_prime}_{ingredient}_{t}") if t else 0 for t in range(horizon)}

    sem = {} # Start End Make => Interval
    produced, consumed = {}, {}
    se_event = {}
    for fc in ini_set.keys():
        sem[fc] = {}
        produced[fc] = {}
        consumed[fc] = {}
        se_event[fc] = {}
        for jt in ini_set[fc].keys():
            process_time = getattr(process, f"{fc}{jt}")
            sem[fc][jt] = {}
            produced[fc][jt] = {t: md.addVar(vtype=GRB.CONTINUOUS if jt in params["float_unit"] else GRB.INTEGER, lb=0, name=f"{fc}_{jt}_{t}_produced") for t in range(1, horizon)}
            if jt in boms:
                consumed[fc][jt] = {ingredient: {t: md.addVar(vtype=GRB.CONTINUOUS if ingredient in params["float_unit"] else GRB.INTEGER, lb=0, ub=boms[jt][ingredient], name=f"{fc}_{ingredient}_{t}_consumed") for t in range(1, horizon)} for ingredient in boms[jt].keys()}

            se_event[fc][jt] = {}
            for k in range(max_job[fc][jt]):
                se_event[fc][jt][k] = {}
                sem[fc][jt][k] = [md.addVar(vtype=GRB.CONTINUOUS, lb=1, ub=horizon - 1, name=f"{fc}_{jt}_{k}_st"), md.addVar(vtype=GRB.CONTINUOUS, lb=1, ub=horizon - 1, name=f"{fc}_{jt}_{k}_ed"), md.addVar(vtype=GRB.BINARY, name=f"{fc}_{jt}_{k}_mk")]
                md.addConstr(sem[fc][jt][k][0] + process_time * sem[fc][jt][k][2]== sem[fc][jt][k][1])
                if k:
                    md.addConstr(sem[fc][jt][k - 1][2] >= sem[fc][jt][k][2])
                    md.addConstr(sem[fc][jt][k - 1][1] <= sem[fc][jt][k][0])

                # t에 실제로 시작하면 1 : 활성(mk=1)이면 정확히 한 시점에서만 1, 비활성이면 전부 0
                # 생산 시간이 고정이므로 종료 이벤트는 따로 두지 않고 se_event[t - 생산시간]으로 대체
                for t in range(1, horizon):
                    se_event[fc][jt][k][t] = md.addVar(vtype=GRB.BINARY, name=f"{fc}{jt}{k}_start_{t}")
                    md.addGenConstrIndicator(se_event[fc][jt][k][t], True, sem[fc][jt][k][0] == t)
                md.addConstr(gp.quicksum(se_event[fc][jt][k].values()) == sem[fc][jt][k][2])

            if jt in boms:
                for ingredient in boms[jt].keys():
                    for t in range(1, horizon):
                        md.addConstr(consumed[fc][jt][ingredient][t] == boms[jt][ingredient] * gp.quicksum(se_event[fc][jt][k][t] for k in range(max_job[fc][jt])))

            for t in range(1, horizon):
                md.addConstr(produced[fc][jt][t] == gp.quicksum(se_event[fc][jt][k][t - process_time] for k in range(max_job[fc][jt]) if t - process_time >= 1))

    fcs, tps = list(ini_set), params["tps"]
    arcs = [(fc1, fc2) for fc1 in fcs for fc2 in fcs if fc1 != fc2]
    truck_move = {arc: {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps, name=f"truck_{arc[0]}_to_{arc[1]}_{t}") for t in range(1, horizon)} for arc in arcs} # t에 f -> g 출발하는 트럭 수 (빈 차 이동 포함)
    truck_idle = {fc: {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps, name=f"truck_idle_{fc}_{t}") for t in range(horizon)} for fc in fcs} # t 시점 f에 대기 중인 트럭 수
    truck_used = md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps, name="truck_used")
    md.addConstr(gp.quicksum(truck_idle[f][0] for f in fcs) == truck_used)

    for fc1, fc2 in arcs:
        for t in range(1, horizon):
            if t + getattr(deliver, f"{fc1}{fc2}") >= horizon:
                md.addConstr(truck_move[(fc1, fc2)][t] == 0)

    for fc1 in fcs:
        for t in range(1, horizon):
            arrive = gp.quicksum(truck_move[(fc2, fc1)][t - getattr(deliver, f"{fc2}{fc1}")] for fc2 in fcs if fc2 != fc1 and t - getattr(deliver, f"{fc2}{fc1}") >= 1)
            depart = gp.quicksum(truck_move[(fc1, fc2)][t] for fc2 in fcs if fc2 != fc1)
            md.addConstr(truck_idle[fc1][t] == truck_idle[fc1][t - 1] + arrive - depart)

    for fc in delivering.keys():
        for fc_prime in delivering[fc].keys():
            for t in range(1, horizon):
                load = sum(delivering[fc][fc_prime][jt][t][lot_unit] * lot_unit for jt in delivering[fc][fc_prime] for lot_unit in ini_set[fc][jt])
                md.addConstr(load <= sum(max_job[fc][jt] for jt in delivering[fc][fc_prime]) * truck_move[(fc, fc_prime)][t])

    truck_travel = md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps * horizon, name="truck_travel")
    md.addConstr(truck_travel == sum(truck_move[(fc1, fc2)][t] * getattr(deliver, f"{fc1}{fc2}") for fc1, fc2 in arcs for t in range(1, horizon)))

    for fc in fc_wip_t.keys():
        for wip in fc_wip_t[fc].keys():
            for t in range(1, horizon):
                plus = (produced[fc][wip][t] if wip in produced[fc] else 0) + sum(delivering[fc1][fc][wip][t - getattr(deliver, f"{fc1}{fc}")][lot_unit] * lot_unit for fc1 in delivering if wip in delivering[fc1].get(fc, {}) and t - getattr(deliver, f"{fc1}{fc}") >= 1 for lot_unit in ini_set[fc1][wip])
                minus = sum(consumed[fc][jt_prime][wip][t] for jt_prime in consumed[fc] if wip in consumed[fc][jt_prime]) + sum(delivering[fc][fc_prime][wip][t][lot_unit] * lot_unit for fc_prime in delivering.get(fc, {}) if wip in delivering[fc][fc_prime] for lot_unit in ini_set[fc][wip])
                md.addConstr(fc_wip_t[fc][wip][t] == fc_wip_t[fc][wip][t - 1] + plus - minus)

    every_final_product_max_set = {} # every_final_product_max_set[final_product][fc] : fc 에서의 최대 재고
    for final_product, amount in zip(params["final_product"], params["amount"]):
        every_final_product_max_set[final_product] = {}
        for fc in ini_set.keys():
            if final_product in ini_set[fc]:
                every_final_product_max_set[final_product][fc] = md.addVar(vtype=GRB.CONTINUOUS if final_product in params["float_unit"] else GRB.INTEGER, lb=0, ub=horizon, name=f"{fc}_{final_product}_FP")
                md.addGenConstrMax(every_final_product_max_set[final_product][fc], fc_wip_t[fc][final_product].values())
        md.addConstr(sum(every_final_product_max_set[final_product].values()) >= amount)

    total_makespan = md.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=horizon, name="total_makespan")
    md.addGenConstrMax(total_makespan, [sem[fc][jt][k][1] for fc in sem.keys() for jt in sem[fc].keys() for k in range(max_job[fc][jt])])

    before_makespan = {t: md.addVar(vtype=GRB.BINARY, name=f"{t}_before_makespan") for t in range(1, horizon)}
    for t in range(1, horizon):
        md.addGenConstrIndicator(before_makespan[t], True, total_makespan >= t + 1)
        md.addGenConstrIndicator(before_makespan[t], False, total_makespan <= t)

    held, holding = {}, {}
    for fc in fc_wip_t.keys():
        held[fc], holding[fc] = {}, {}
        for wip in fc_wip_t[fc].keys():
            held[fc][wip] = {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=horizon, name=f"{fc}_{wip}_{t}_held") for t in range(1, horizon)}
            for t in range(1, horizon):
                md.addConstr(held[fc][wip][t] >= fc_wip_t[fc][wip][t] - horizon * (1 - before_makespan[t]))
            holding[fc][wip] = holding_cost.get(wip, 0) * sum(held[fc][wip].values())
    hold_ub = sum(holding_cost.get(wip, 0) * horizon * (horizon - 1) for fc in fc_wip_t for wip in fc_wip_t[fc])

    for fc in delivering.keys():
        for fc_prime in delivering[fc].keys():
            deliver_time, route = getattr(deliver, f"{fc}{fc_prime}"), f"{fc}→{fc_prime}"
            held[route], holding[route] = {}, {}
            for jt in delivering[fc][fc_prime]:
                held[route][jt] = {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=horizon * deliver_time, name=f"{route}_{jt}_{t}_held") for t in range(1, horizon)}
                for t in range(1, horizon):
                    in_transit = sum(delivering[fc][fc_prime][jt][s][lot_unit] * lot_unit for s in range(max(1, t - deliver_time + 1), t + 1) for lot_unit in ini_set[fc][jt])
                    md.addConstr(held[route][jt][t] >= in_transit - horizon * deliver_time * (1 - before_makespan[t]))
                holding[route][jt] = holding_cost.get(jt, 0) * sum(held[route][jt].values())
                hold_ub += holding_cost.get(jt, 0) * horizon * deliver_time * (horizon - 1)
    total_holding = md.addVar(vtype=GRB.INTEGER, lb=0, ub=hold_ub, name="total_holding_cost")
    md.addConstr(total_holding == gp.quicksum(holding[fc][wip] for fc in holding for wip in holding[fc]))

    w = params["weights"]
    md.setObjective(w["makespan"] * total_makespan + w["holding"] * total_holding + w["truck_used"] * truck_used + w["truck_travel"] * truck_travel, GRB.MINIMIZE)
    md.optimize()

    if md.Status == GRB.OPTIMAL:
        total_makespan = round(total_makespan.X)
        print("Status :", md.Status, f"(horizon = {horizon})")
        print("Total Makespan :", total_makespan)
        print("Holding Cost :", total_holding.X)
        for fc in holding.keys():
            for wip in holding[fc].keys():
                if cost := holding[fc][wip].getValue():
                    print(f"    {fc} {wip} : {cost} (= {holding_cost.get(wip, 0)} x {sum(v.X for v in held[fc][wip].values())} unit*time)")
        print("Truck Used :", truck_used.X, "/", tps, "(+1 Virtual Truck)")
        print("Truck Travel :", truck_travel.X, "\n")

        jobs = [(fc, jt, k, round(sem[fc][jt][k][0].X), round(sem[fc][jt][k][1].X)) for fc in sem.keys() for jt in sem[fc].keys() for k in range(max_job[fc][jt]) if round(sem[fc][jt][k][2].X)]

        trucks = [{"home": f, "loc": f, "free": 0, "moves": []} for f in fcs for _ in range(round(truck_idle[f][0].X))]
        departures = sorted((t, f, g, truck_move[(f, g)][t].X) for f, g in arcs for t in range(1, horizon) if truck_move[(f, g)][t].X)
        for t, f, g, num in departures:
            cargo = {}
            if g in delivering.get(f, {}):
                cargo = {jt: amount for jt in delivering[f][g] if (amount := sum(delivering[f][g][jt][t][lot_unit].X * lot_unit for lot_unit in ini_set[f][jt]))}
            num = round(num)
            ready = [truck for truck in trucks if truck["loc"] == f and truck["free"] <= t][:num]
            assert len(ready) == num, f"truck flow broken at {f} t={t}"
            for i, truck in enumerate(ready):
                arrive = t + getattr(deliver, f"{f}{g}")
                truck["moves"].append((f, g, t, arrive, cargo if i == 0 else {}))
                truck["loc"], truck["free"] = g, arrive
        for i, truck in enumerate(trucks):
            print(f"tr{i + 1} (start {truck['home']})")
            for f, g, t, arrive, cargo in truck["moves"]:
                print(f"    {f} -> {g} | {t} ~ {arrive} ({arrive - t}) | {cargo if cargo else 'empty'}")

        virtual_moves = [] # Virtual Truck : 같은 공장 생산품이 상위 job 에 투입된 시점 (내부 이송, 시간 0)
        for f in ini_set.keys():
            for t in range(1, horizon):
                if cargo := {ing: amount for ing in ini_set[f] if (amount := round(sum(consumed[f][jt][ing][t].X for jt in consumed[f] if ing in consumed[f][jt])))}:
                    virtual_moves.append((f, t, cargo))
        virtual_moves.sort(key=lambda move: move[1])
        print("vt (Virtual Truck)")
        for f, t, cargo in virtual_moves:
            print(f"    {f} -> {f} | {t} | {cargo}")

        palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
        INK, MUTED, GRID, GO, RETURN, VIRTUAL = "#1f2328", "#6b7280", "#e5e7eb", "#4b5563", "#d1d5db", "#7c3aed"

        jt_order = list(dict.fromkeys(jt for fc in ini_set for jt in ini_set[fc]))
        jt_color = {jt: palette[i % len(palette)] for i, jt in enumerate(jt_order)}
        text_on = lambda hex_color: INK if sum(int(hex_color[i:i + 2], 16) * w for i, w in ((1, 0.299), (3, 0.587), (5, 0.114))) > 140 else "white" # 막대 밝기에 따라 글자색
        n_truck = len(trucks)

        y_of = {f"tr{i + 1} ({truck['home']})": i for i, truck in enumerate(trucks)}
        truck_rows = list(y_of.keys())
        y_of["vt (virtual)"] = n_truck
        fc_first_row = {}
        for fc in ini_set:
            fc_first_row[fc] = len(y_of) + 1
            for jt in ini_set[fc]:
                y_of[f"{fc} · {jt}"] = len(y_of) + 1
        x_max = max([total_makespan] + [move[3] for truck in trucks for move in truck["moves"]]) + 1

        _, ax = plt.subplots(figsize=(max(14, x_max * 0.4), 0.6 * (len(y_of) + 1) + 1.5))
        h = 0.75

        for fc, jt, k, st, ed in jobs:
            y = y_of[f"{fc} · {jt}"]
            ax.barh(y, ed - st, left=st, height=h, color=jt_color[jt], edgecolor="white", linewidth=1.5)
            ax.text((st + ed) / 2, y, f"{k}_th\n({ed - st})", ha="center", va="center", fontsize=5, color=text_on(jt_color[jt]))

        for row, truck in zip(truck_rows, trucks):
            y = y_of[row]
            for fc_from, fc_to, depart, arrive, cargo in truck["moves"]:
                ax.barh(y, arrive - depart, left=depart, height=h, color=GO if cargo else RETURN, edgecolor="white", linewidth=1.5)
                label = f"{fc_from}→{fc_to} ({arrive - depart})"
                label += "\n" + " ".join(f"{jt}×{n}" for jt, n in cargo.items()) if cargo else "\nempty"
                ax.text((depart + arrive) / 2, y, label, ha="center", va="center", fontsize=6, color="white" if cargo else INK)

        for f, t, cargo in virtual_moves: # 이송 시간이 0 이므로 막대 대신 마커 + 라벨
            ax.plot(t, n_truck - 0.2, marker="v", markersize=7, color=VIRTUAL)
            ax.text(t, n_truck + 0.05, f"{f}\n" + "\n".join(f"{jt}×{n}" for jt, n in cargo.items()), ha="center", va="top", fontsize=6, color=VIRTUAL)

        ax.axvline(total_makespan, color=INK, linestyle="--", linewidth=1)
        ax.text(total_makespan, -0.9, f"makespan = {total_makespan} ", ha="right", va="center", fontsize=8, color=INK)
        for fc in list(fc_first_row)[1:]:
            ax.axhline(fc_first_row[fc] - 0.5, color=GRID, linewidth=0.8)
        ax.axhline(n_truck + 1, color=MUTED, linewidth=1)

        ax.set_yticks(list(y_of.values()), list(y_of.keys()))
        ax.set_ylim(len(y_of) + 0.5, -1.4)
        ax.set_xlim(0, x_max)
        ax.set_xlabel("Time", color=MUTED)
        ax.set_title(f"Production & Delivery Gantt  (trucks used {n_truck} / tps {tps} + 1 virtual)", loc="left", color=INK)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUTED, length=0)

        handles = [Patch(color=jt_color[jt], label=jt) for jt in jt_order]
        handles += [Patch(color=GO, label="truck: loaded"), Patch(color=RETURN, label="truck: empty move"), Patch(color=VIRTUAL, label="virtual truck: internal move")]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=8)
        plt.tight_layout()
        plt.show()
    else:
        print("X")
    return

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
def start(boms, factories, holding_cost, deliveries, params):
    process, deliver, ini_set = Process(), Deliver(), {}
    for fc in factories.keys():
        ini_set[fc] = {}
        for jt in factories[fc].keys():
            ini_set[fc][jt] = factories[fc][jt]["lots"]
            setattr(process, f"{fc}{jt}", factories[fc][jt]["time"])
    for fc1 in deliveries.keys():
        for fc2 in deliveries[fc1].keys():
            setattr(deliver, f"{fc1}{fc2}", deliveries[fc1][fc2])
    system(process, deliver, boms, holding_cost, ini_set, params, set_horizon(boms, factories, deliveries, params))

def main():

    params = {"tps": 8, "final_product": ["JT12", "JT9"], "amount": [1, 1], "float_unit": ["JT4", "JT9"],
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

if __name__ == "__main__":
    main()