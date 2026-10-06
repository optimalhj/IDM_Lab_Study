import random
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
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
            fc_wip_t[fc][jt] = {t: md.addVar(vtype=GRB.CONTINUOUS if jt in params["float_unit"] else GRB.INTEGER, lb=0, name=f"{fc}_{jt}_{t}") if t >= 0 else 0 for t in range(-1, horizon)}

            for fc_prime in set([fc_prime for fc_prime in ini_set.keys() if fc_prime != fc for jt_prime in ini_set[fc_prime] if jt_prime in boms and jt in boms[jt_prime]]): # 같은 공장 안에서 쓰는 재료는 배송 없이 fc_wip_t 에서 바로 소비
                if fc not in delivering: delivering[fc] = {}
                if fc_prime not in delivering[fc]: delivering[fc][fc_prime] = {}
                delivering[fc][fc_prime][jt] = {t: {lot_unit: md.addVar(vtype=GRB.INTEGER, lb=0, ub=max_job[fc][jt] // lot_unit, name=f"{fc}_{jt}_{t}_deliver_to_{fc_prime}_{lot_unit}") for lot_unit in ini_set[fc][jt]} for t in range(horizon)}
    for fc in delivering.keys():
        for fc_prime in delivering[fc].keys():
            for ingredient in delivering[fc][fc_prime].keys():
                if ingredient not in fc_wip_t[fc_prime]:
                    fc_wip_t[fc_prime][ingredient] = {t: md.addVar(vtype=GRB.CONTINUOUS if ingredient in params["float_unit"] else GRB.INTEGER,  lb=0, name=f"{fc_prime}_{ingredient}_{t}") if t >= 0 else 0 for t in range(-1, horizon)}

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
            produced[fc][jt] = {t: md.addVar(vtype=GRB.CONTINUOUS if jt in params["float_unit"] else GRB.INTEGER, lb=0, name=f"{fc}_{jt}_{t}_produced") for t in range(horizon)}
            if jt in boms:
                consumed[fc][jt] = {ingredient: {t: md.addVar(vtype=GRB.CONTINUOUS if ingredient in params["float_unit"] else GRB.INTEGER, lb=0, ub=boms[jt][ingredient], name=f"{fc}_{ingredient}_{t}_consumed") for t in range(horizon)} for ingredient in boms[jt].keys()}

            se_event[fc][jt] = {}
            for k in range(max_job[fc][jt]):
                se_event[fc][jt][k] = {}
                sem[fc][jt][k] = [md.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=horizon - 1, name=f"{fc}_{jt}_{k}_st"), md.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=horizon - 1, name=f"{fc}_{jt}_{k}_ed"), md.addVar(vtype=GRB.BINARY, name=f"{fc}_{jt}_{k}_mk")]
                md.addConstr(sem[fc][jt][k][0] + process_time * sem[fc][jt][k][2]== sem[fc][jt][k][1])
                if k:
                    md.addConstr(sem[fc][jt][k - 1][2] >= sem[fc][jt][k][2])
                    md.addConstr(sem[fc][jt][k - 1][1] <= sem[fc][jt][k][0])

                # t에 실제로 시작하면 1 : 활성(mk=1)이면 정확히 한 시점에서만 1, 비활성이면 전부 0
                # 생산 시간이 고정이므로 종료 이벤트는 따로 두지 않고 se_event[t - 생산시간]으로 대체
                for t in range(horizon):
                    se_event[fc][jt][k][t] = md.addVar(vtype=GRB.BINARY, name=f"{fc}{jt}{k}_start_{t}")
                    md.addGenConstrIndicator(se_event[fc][jt][k][t], True, sem[fc][jt][k][0] == t)
                md.addConstr(gp.quicksum(se_event[fc][jt][k].values()) == sem[fc][jt][k][2])

            if jt in boms:
                for ingredient in boms[jt].keys():
                    for t in range(horizon):
                        md.addConstr(consumed[fc][jt][ingredient][t] == boms[jt][ingredient] * gp.quicksum(se_event[fc][jt][k][t] for k in range(max_job[fc][jt])))

            for t in range(horizon):
                md.addConstr(produced[fc][jt][t] == gp.quicksum(se_event[fc][jt][k][t - process_time] for k in range(max_job[fc][jt]) if t - process_time >= 0))

    fcs, tps = list(ini_set), params["tps"]
    arcs = [(fc1, fc2) for fc1 in fcs for fc2 in fcs if fc1 != fc2]
    truck_move = {arc: {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps, name=f"truck_{arc[0]}_to_{arc[1]}_{t}") for t in range(horizon)} for arc in arcs} # t에 f -> g 출발하는 트럭 수 (빈 차 이동 포함)
    truck_idle = {fc: {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps, name=f"truck_idle_{fc}_{t}") for t in range(-1, horizon)} for fc in fcs} # t 시점 f에 대기 중인 트럭 수 (t = -1 : 초기 배치)
    truck_used = md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps, name="truck_used")
    md.addConstr(gp.quicksum(truck_idle[f][-1] for f in fcs) == truck_used)

    for fc1, fc2 in arcs:
        for t in range(horizon):
            if t + getattr(deliver, f"{fc1}{fc2}") >= horizon:
                md.addConstr(truck_move[(fc1, fc2)][t] == 0)

    for fc1 in fcs:
        for t in range(horizon):
            arrive = gp.quicksum(truck_move[(fc2, fc1)][t - getattr(deliver, f"{fc2}{fc1}")] for fc2 in fcs if fc2 != fc1 and t - getattr(deliver, f"{fc2}{fc1}") >= 0)
            depart = gp.quicksum(truck_move[(fc1, fc2)][t] for fc2 in fcs if fc2 != fc1)
            md.addConstr(truck_idle[fc1][t] == truck_idle[fc1][t - 1] + arrive - depart)

    # VRP 방식 : 화물을 (출발 o, 목적지 d, 품목 jt, lot 단위) 별 "lot 개수" 로 트럭 arc 위에 흘림
    # → lot 은 쪼개지지 않고 통째로 이동, 트럭은 여러 공장을 들르며 다른 공장의 lot 을 추가로 싣거나 내릴 수 있음
    commodities = [(fc, fc_prime, jt, lot_unit) for fc in delivering for fc_prime in delivering[fc] for jt in delivering[fc][fc_prime] for lot_unit in ini_set[fc][jt]]
    ship_max = {jt: sum(max_job[fc][jt] for fc in delivering for fc_prime in delivering[fc] if jt in delivering[fc][fc_prime]) for _, _, jt, _ in commodities} # jt 가 공장 사이를 오갈 수 있는 최대량
    cargo, waiting = {}, {} # cargo[key][(f, g)][t] : t 에 f -> g 로 출발하는 트럭에 실린 lot 수, waiting[key][f][t] : 경유 공장 f 에서 다음 트럭을 기다리는 lot 수
    for key in commodities:
        o, d, jt, lot_unit = key
        cargo[key] = {(f, g): {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=max_job[o][jt] // lot_unit, name=f"cargo_{o}_{d}_{jt}_{lot_unit}_{f}_to_{g}_{t}") for t in range(horizon)} for f, g in arcs if f != d and g != o}
        waiting[key] = {f: {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=max_job[o][jt] // lot_unit, name=f"wait_{o}_{d}_{jt}_{lot_unit}_{f}_{t}") if t >= 0 else 0 for t in range(-1, horizon)} for f in fcs if f not in (o, d)}
        for t in range(horizon):
            md.addConstr(gp.quicksum(cargo[key][(o, g)][t] for g in fcs if g != o) == delivering[o][d][jt][t][lot_unit]) # 출발 공장에서는 대기 없이 보낸 시점에 바로 출발
            for f in waiting[key].keys():
                arrive = gp.quicksum(cargo[key][(e, f)][t - getattr(deliver, f"{e}{f}")] for e in fcs if e not in (f, d) and t - getattr(deliver, f"{e}{f}") >= 0)
                depart = gp.quicksum(cargo[key][(f, g)][t] for g in fcs if g not in (f, o))
                md.addConstr(waiting[key][f][t] == waiting[key][f][t - 1] + arrive - depart)

    truck_cap = params.get("truck_capacity") or sum(max_job[fc][jt] for fc in delivering for fc_prime in delivering[fc] for jt in delivering[fc][fc_prime]) # None 이면 사실상 무제한
    for f, g in arcs:
        for t in range(horizon):
            md.addConstr(gp.quicksum(cargo[key][(f, g)][t] * key[3] for key in commodities if (f, g) in cargo[key]) <= truck_cap * truck_move[(f, g)][t])

    truck_travel = md.addVar(vtype=GRB.INTEGER, lb=0, ub=tps * horizon, name="truck_travel")
    md.addConstr(truck_travel == sum(truck_move[(fc1, fc2)][t] * getattr(deliver, f"{fc1}{fc2}") for fc1, fc2 in arcs for t in range(horizon)))

    for fc in fc_wip_t.keys():
        for wip in fc_wip_t[fc].keys():
            for t in range(horizon):
                plus = (produced[fc][wip][t] if wip in produced[fc] else 0) + sum(cargo[key][(e, fc)][t - getattr(deliver, f"{e}{fc}")] * key[3] for key in commodities if key[1:3] == (fc, wip) for e in fcs if (e, fc) in cargo[key] and t - getattr(deliver, f"{e}{fc}") >= 0)
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

    before_makespan = {t: md.addVar(vtype=GRB.BINARY, name=f"{t}_before_makespan") for t in range(horizon)}
    for t in range(horizon):
        md.addGenConstrIndicator(before_makespan[t], True, total_makespan >= t + 1)
        md.addGenConstrIndicator(before_makespan[t], False, total_makespan <= t)

    held, holding = {}, {}
    for fc in fc_wip_t.keys():
        held[fc], holding[fc] = {}, {}
        for wip in fc_wip_t[fc].keys():
            held[fc][wip] = {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=horizon, name=f"{fc}_{wip}_{t}_held") for t in range(horizon)}
            for t in range(horizon):
                md.addConstr(held[fc][wip][t] >= fc_wip_t[fc][wip][t] - horizon * (1 - before_makespan[t]))
            holding[fc][wip] = holding_cost.get(wip, 0) * sum(held[fc][wip].values())
    hold_ub = sum(holding_cost.get(wip, 0) * horizon * horizon for fc in fc_wip_t for wip in fc_wip_t[fc])

    held["in-transit"], holding["in-transit"] = {}, {} # 트럭에 실려 이동 중 + 다음 트럭 대기 중인 화물
    for jt in ship_max.keys():
        held["in-transit"][jt] = {t: md.addVar(vtype=GRB.INTEGER, lb=0, ub=ship_max[jt], name=f"transit_{jt}_{t}_held") for t in range(horizon)}
        for t in range(horizon):
            moving = sum(cargo[key][(f, g)][s] * key[3] for key in commodities if key[2] == jt for f, g in cargo[key] for s in range(max(0, t - getattr(deliver, f"{f}{g}") + 1), t + 1))
            parked = sum(waiting[key][f][t] * key[3] for key in commodities if key[2] == jt for f in waiting[key])
            md.addConstr(held["in-transit"][jt][t] >= moving + parked - ship_max[jt] * (1 - before_makespan[t]))
        holding["in-transit"][jt] = holding_cost.get(jt, 0) * sum(held["in-transit"][jt].values())
        hold_ub += holding_cost.get(jt, 0) * ship_max[jt] * horizon
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

        trucks = [{"home": f, "loc": f, "free": -1, "moves": []} for f in fcs for _ in range(round(truck_idle[f][-1].X))]
        departures = sorted((t, f, g, round(truck_move[(f, g)][t].X)) for f, g in arcs for t in range(horizon) if round(truck_move[(f, g)][t].X))
        for t, f, g, num in departures:
            leg = sorted(((key, n) for key in commodities if (f, g) in cargo[key] and (n := round(cargo[key][(f, g)][t].X))), key=lambda lots: -lots[0][3])
            loads, room = [{} for _ in range(num)], [truck_cap] * num # 같은 arc 에 여러 대가 출발하면 lot 을 통째로 남은 용량이 있는 트럭에 싣기
            for (o, d, jt, lot_unit), n in leg:
                for _ in range(n):
                    i = next((i for i in range(num) if room[i] >= lot_unit), max(range(num), key=lambda i: room[i]))
                    loads[i].setdefault((d, jt), []).append(lot_unit) # load[(d, jt)] : 실린 lot 크기 목록
                    room[i] -= lot_unit
            ready = [truck for truck in trucks if truck["loc"] == f and truck["free"] <= t]
            ready.sort(key=lambda truck: -sum(sum(lots) for (d, _), lots in (truck["moves"][-1][4] if truck["moves"] else {}).items() if d != f)) # 경유 화물을 싣고 온 트럭이 이어서 출발
            assert len(ready) >= num, f"truck flow broken at {f} t={t}"
            for truck, load in zip(ready[:num], loads):
                arrive = t + getattr(deliver, f"{f}{g}")
                truck["moves"].append((f, g, t, arrive, load))
                truck["loc"], truck["free"] = g, arrive

        fmt = lambda load: ", ".join(f"{jt}×{sum(lots):g}→{d} [{'+'.join(f'{lot:g}' for lot in lots)}]" for (d, jt), lots in load.items()) or "empty" # [ ] : lot 구성
        for i, truck in enumerate(trucks):
            print(f"tr{i + 1} (start {truck['home']}) : {' → '.join([truck['home']] + [move[1] for move in truck['moves']])}")
            for f, g, t, arrive, load in truck["moves"]:
                print(f"    {f} -> {g} | {t} ~ {arrive} ({arrive - t}) | {fmt(load)}")

        virtual_moves = [] # Virtual Truck : 같은 공장 생산품이 상위 job 에 투입된 시점 (내부 이송, 시간 0)
        for f in ini_set.keys():
            for t in range(horizon):
                if load := {ing: amount for ing in ini_set[f] if (amount := round(sum(consumed[f][jt][ing][t].X for jt in consumed[f] if ing in consumed[f][jt])))}:
                    virtual_moves.append((f, t, load))
        virtual_moves.sort(key=lambda move: move[1])
        print("vt (Virtual Truck)")
        for f, t, load in virtual_moves:
            print(f"    {f} -> {f} | {t} | {load}")

        palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
        INK, MUTED, GRID, BAND, EMPTY, VIRTUAL = "#1f2328", "#6b7280", "#e5e7eb", "#f3f4f6", "#9ca3af", "#7c3aed"

        jt_order = list(dict.fromkeys(jt for fc in ini_set for jt in ini_set[fc]))
        jt_color = {jt: palette[i % len(palette)] for i, jt in enumerate(jt_order)}
        text_on = lambda hex_color: INK if sum(int(hex_color[i:i + 2], 16) * w for i, w in ((1, 0.299), (3, 0.587), (5, 0.114))) > 140 else "white" # 막대 밝기에 따라 글자색
        n_truck = len(trucks)
        truck_rows = [f"tr{i + 1} ({truck['home']})" for i, truck in enumerate(trucks)] + ["vt (virtual)"]
        prod_rows = [(fc, jt) for fc in ini_set for jt in ini_set[fc]]
        x_max = max([total_makespan] + [move[3] for truck in trucks for move in truck["moves"]]) + 1

        fig, (ax_tr, ax_pd) = plt.subplots(2, 1, sharex=True, figsize=(max(14, x_max * 0.45), 1.1 * len(truck_rows) + 0.55 * len(prod_rows) + 2.5), gridspec_kw={"height_ratios": [2 * len(truck_rows) + 1, len(prod_rows) + 1]})
        h = 0.62

        # 물류 패널 : 트럭 한 줄 = 한 대의 경로, 구간 막대는 실린 품목 비율만큼 색 띠, 막대 위에는 정차 공장
        for y, truck in enumerate(trucks):
            for i, (f, g, depart, arrive, load) in enumerate(truck["moves"]):
                waited = i and depart > truck["moves"][i - 1][3]
                if waited: # 정차 대기
                    ax_tr.plot([truck["moves"][i - 1][3], depart], [y, y], color=MUTED, linestyle=":", linewidth=1.5, zorder=1)
                if load:
                    bottom, total = y - h / 2, sum(map(sum, load.values()))
                    for (d, jt), amount in ((key, sum(lots)) for key, lots in load.items()):
                        ax_tr.barh(bottom + h * amount / total / 2, arrive - depart, left=depart, height=h * amount / total, color=jt_color[jt], linewidth=0, zorder=2)
                        bottom += h * amount / total
                else:
                    ax_tr.barh(y, arrive - depart, left=depart, height=h, color="white", hatch="////", edgecolor=EMPTY, linewidth=0, zorder=2)
                ax_tr.barh(y, arrive - depart, left=depart, height=h, fill=False, edgecolor=INK, linewidth=1, zorder=3)
                ax_tr.text((depart + arrive) / 2, y, fmt(load).replace(", ", "\n"), ha="center", va="center", fontsize=6, color=INK, zorder=4, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
                for x, stop in ((depart, f), (arrive, g)) if not i or waited else ((arrive, g),):
                    ax_tr.plot(x, y - h / 2, marker="o", markersize=5, color=INK, markeredgecolor="white", zorder=5)
                    ax_tr.text(x, y - h / 2 - 0.08, stop, ha="center", va="bottom", fontsize=7, fontweight="bold", color=INK, zorder=5)

        for f, t, load in virtual_moves: # 이송 시간이 0 이므로 막대 대신 마커 + 라벨
            ax_tr.plot(t, n_truck - 0.25, marker="v", markersize=7, color=VIRTUAL)
            ax_tr.text(t, n_truck - 0.1, f"{f}\n" + "\n".join(f"{jt}×{n}" for jt, n in load.items()), ha="center", va="top", fontsize=6, color=VIRTUAL)
        ax_tr.axhline(n_truck - 0.6, color=GRID, linewidth=1)

        # 생산 패널 : 공장별로 배경 띠를 번갈아 깔아 구분
        y_of = {row: y for y, row in enumerate(prod_rows)}
        for i, fc in enumerate(ini_set):
            if i % 2 == 0:
                ax_pd.axhspan(y_of[(fc, list(ini_set[fc])[0])] - 0.5, y_of[(fc, list(ini_set[fc])[-1])] + 0.5, color=BAND, zorder=0)
        for fc, jt, k, st, ed in jobs:
            ax_pd.barh(y_of[(fc, jt)], ed - st, left=st, height=0.75, color=jt_color[jt], edgecolor="white", linewidth=1.5, zorder=2)
            ax_pd.text((st + ed) / 2, y_of[(fc, jt)], f"{k}_th\n({ed - st})", ha="center", va="center", fontsize=5, color=text_on(jt_color[jt]), zorder=3)

        for ax, rows, title in ((ax_tr, truck_rows, f"Logistics  (VRP routes, trucks used {n_truck} / tps {tps} + 1 virtual)"), (ax_pd, [f"{fc} · {jt}" for fc, jt in prod_rows], "Production")):
            ax.axvline(total_makespan, color=INK, linestyle="--", linewidth=1, zorder=1)
            ax.set_yticks(range(len(rows)), rows)
            ax.set_ylim(len(rows) - 0.4, -0.9)
            ax.set_title(title, loc="left", color=INK, fontsize=10)
            ax.grid(axis="x", color=GRID, linewidth=0.8)
            ax.set_axisbelow(True)
            for side in ("top", "right", "left"):
                ax.spines[side].set_visible(False)
            ax.tick_params(colors=MUTED, length=0)
        ax_tr.text(total_makespan, -0.75, f"makespan = {total_makespan} ", ha="right", va="center", fontsize=8, color=INK)
        ax_pd.set_xlim(-1, x_max)
        ax_pd.set_xlabel("Time", color=MUTED)

        handles = [Patch(color=jt_color[jt], label=jt) for jt in jt_order]
        handles += [Patch(facecolor="white", edgecolor=EMPTY, hatch="////", label="truck: empty move"),
                    Line2D([], [], color=MUTED, linestyle=":", linewidth=1.5, label="truck: waiting at stop"),
                    Line2D([], [], color=INK, marker="o", linestyle="", markersize=5, label="stop (factory)"),
                    Line2D([], [], color=VIRTUAL, marker="v", linestyle="", markersize=7, label="virtual truck: internal move")]
        fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.83, 0.95), frameon=False, fontsize=8)
        fig.tight_layout(rect=(0, 0, 0.83, 1))
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
            finish[jt] = max([0] + arrive) + make_time(jt)
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