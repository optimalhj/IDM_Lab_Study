import random
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from ortools.sat.python import cp_model
import time

def system(process, deliver, boms, holding_cost, ini_set, trucks, params, horizon):
    need = {}
    def explode(jt, qty):
        need[jt] = need.get(jt, 0) + qty
        for ingredient in boms.get(jt, {}).keys(): explode(ingredient, qty * boms[jt][ingredient])
    for final_product, amount in zip(params["final_product"], params["amount"]): explode(final_product, amount)
    max_job = {fc: {jt: -(-need.get(jt, 0) // min(ini_set[fc][jt])) * min(ini_set[fc][jt]) for jt in ini_set[fc].keys()} for fc in ini_set.keys()}
    qty_ub = {} # qty_ub[jt] : jt 가 시스템 전체에 존재할 수 있는 최대량 (CP-SAT 은 모든 정수 변수에 유한한 범위가 필요)
    for fc in ini_set.keys():
        for jt in ini_set[fc].keys():
            qty_ub[jt] = qty_ub.get(jt, 0) + max_job[fc][jt]

    md = cp_model.CpModel() # 모든 변수는 정수형

    st_time = time.time()
    fcs = list(ini_set)
    arcs = [(fc1, fc2) for fc1 in fcs for fc2 in fcs if fc1 != fc2]
    lead = {(f, g): getattr(deliver, f"{f}{g}") for f, g in arcs}
    p_time = {(fc, jt): getattr(process, f"{fc}{jt}") for fc in fcs for jt in ini_set[fc]}
    uses = {fc: {ing for jt in ini_set[fc] for ing in boms.get(jt, {})} for fc in fcs} # uses[fc] : fc 에서 소비하는 재료
    senders = {jt: [o for o in fcs if jt in ini_set[o] and any(jt in uses[d] for d in fcs if d != o)] for jt in qty_ub} # 다른 공장에 보낼 수 있는 공장 (gp 의 delivering 과 같은 조건)
    receivers = {jt: [d for d in fcs if jt in uses[d] and any(o != d for o in senders[jt])] for jt in qty_ub}
    ships = [jt for jt in qty_ub if senders[jt]] # 공장 사이를 오가는 품목

    # 생산 : 시작 시점마다 optional interval 하나 (k 번째 job 슬롯 대신) → 같은 공장·품목은 no_overlap 으로 한 번에 하나씩
    # job 이 모두 똑같으므로 "t 에 시작하는가" 만 정하면 되고, 생산·소비량이 바로 make 의 선형식이 됨
    make = {}
    for fc in fcs:
        make[fc] = {}
        for jt in ini_set[fc]:
            p = p_time[(fc, jt)]
            make[fc][jt] = {t: md.new_bool_var(f"{fc}_{jt}_start_{t}") for t in range(horizon - p)} # 종료 시점 <= horizon - 1
            md.add_no_overlap([md.new_optional_fixed_size_interval_var(t, p, x, f"{fc}_{jt}_make_{t}") for t, x in make[fc][jt].items()])
            md.add(sum(make[fc][jt].values()) <= max_job[fc][jt])
    produced = lambda fc, jt, t: make[fc][jt].get(t - p_time[(fc, jt)], 0) if jt in ini_set[fc] else 0
    consumed = lambda fc, ing, t: sum(boms[jt][ing] * make[fc][jt].get(t, 0) for jt in ini_set[fc] if ing in boms.get(jt, {}))

    # 배송 : 품목별 흐름 flow[(f, g)][jt][t] (t 에 f -> g 로 출발하는 jt 수량, 모든 트럭 합)
    # 같은 품목은 어느 공장에서 왔든 똑같으므로 (출발, 목적지, lot) 별 commodity 대신 품목 하나로 흘리고,
    # 경유 공장에서 다음 트럭을 기다리는 화물은 relay[f][jt][t] 로 받음 → 트럭 사이 환적도 그대로 표현
    flow = {arc: {jt: {t: md.new_int_var(0, qty_ub[jt], f"flow_{arc[0]}_to_{arc[1]}_{jt}_{t}") for t in range(horizon - lead[arc])} for jt in ships} for arc in arcs} # 도착 시점 <= horizon - 1
    send, receive = {}, {} # send : 생산 공장 재고 -> 화물, receive : 화물 -> 소비 공장 재고
    for jt in ships:
        for o in senders[jt]:
            lots = [lot for lot in ini_set[o][jt] if lot == min(ini_set[o][jt]) or lot % min(ini_set[o][jt])] # 최소 lot 의 배수인 lot 은 최소 lot 여러 개와 같음
            n_lot = {lot: {t: md.new_int_var(0, max_job[o][jt] // lot, f"{o}_{jt}_{t}_send_lot{lot}") for t in range(horizon)} for lot in lots}
            send[(o, jt)] = {t: sum(lot * n_lot[lot][t] for lot in lots) for t in range(horizon)}
        for d in receivers[jt]:
            receive[(d, jt)] = {t: md.new_int_var(0, qty_ub[jt], f"{d}_{jt}_{t}_receive") for t in range(horizon)}

    stock, relay = {}, {} # stock[fc][jt][t] : 공장 재고, relay[f][jt][t] : 공장 f 에 내려져 다음 트럭을 기다리는 화물
    for fc in fcs:
        stock[fc] = {jt: {t: md.new_int_var(0, qty_ub[jt], f"{fc}_{jt}_{t}") if t >= 0 else 0 for t in range(-1, horizon)} for jt in set(ini_set[fc]) | uses[fc]}
        relay[fc] = {jt: {t: md.new_int_var(0, qty_ub[jt], f"relay_{fc}_{jt}_{t}") if t >= 0 else 0 for t in range(-1, horizon)} for jt in ships}
        for t in range(horizon):
            for jt in stock[fc]:
                md.add(stock[fc][jt][t] == stock[fc][jt][t - 1] + produced(fc, jt, t) - consumed(fc, jt, t) + (receive[(fc, jt)][t] if (fc, jt) in receive else 0) - (send[(fc, jt)][t] if (fc, jt) in send else 0))
            for jt in ships:
                arrive = sum(flow[(e, fc)][jt][t - lead[(e, fc)]] for e in fcs if e != fc and t - lead[(e, fc)] >= 0)
                depart = sum(flow[(fc, g)][jt][t] for g in fcs if g != fc and t in flow[(fc, g)][jt])
                md.add(relay[fc][jt][t] == relay[fc][jt][t - 1] + arrive - depart + (send[(fc, jt)][t] if (fc, jt) in send else 0) - (receive[(fc, jt)][t] if (fc, jt) in receive else 0))

    # 트럭 : feature 가 같은 트럭은 한 타입으로 묶어 "대수" 로 흘림 (트럭 이름만 바뀐 대칭해가 처음부터 없음)
    groups = {}
    for v, spec in trucks.items():
        groups.setdefault(tuple(sorted(spec.items())), []).append(v)
    types = [(dict(spec), names) for spec, names in groups.items()]
    truck_move = {k: {arc: {t: md.new_int_var(0, len(names), f"type{k}_{arc[0]}_to_{arc[1]}_{t}") for t in range(horizon - lead[arc])} for arc in arcs} for k, (_, names) in enumerate(types)} # t 에 f -> g 로 출발하는 타입 k 트럭 수 (빈 차 이동 포함)
    truck_idle = {k: {fc: {t: md.new_int_var(0, len(names), f"type{k}_idle_{fc}_{t}") for t in range(-1, horizon)} for fc in fcs} for k, (_, names) in enumerate(types)} # t 시점 f 에 대기 중인 타입 k 트럭 수 (t = -1 : 초기 배치)
    truck_used = {k: md.new_int_var(0, len(names), f"type{k}_used") for k, (_, names) in enumerate(types)}
    for k, (_, names) in enumerate(types):
        md.add(truck_used[k] == sum(truck_idle[k][fc][-1] for fc in fcs))
        for fc in fcs:
            for t in range(horizon):
                arrive = sum(truck_move[k][(e, fc)][t - lead[(e, fc)]] for e in fcs if e != fc and t - lead[(e, fc)] >= 0)
                depart = sum(truck_move[k][(fc, g)][t] for g in fcs if g != fc and t in truck_move[k][(fc, g)])
                md.add(truck_idle[k][fc][t] == truck_idle[k][fc][t - 1] + arrive - depart)
        # 이동 중인 트럭 수 <= 배치한 트럭 수 : 흐름 보존식에서 나오는 성질이지만 cumulative 로 한 번 더 걸어 전파를 강화
        moves = [(md.new_fixed_size_interval_var(t, lead[arc], f"type{k}_{arc[0]}_to_{arc[1]}_{t}_trip"), truck_move[k][arc][t]) for arc in arcs for t in truck_move[k][arc]]
        md.add_cumulative([interval for interval, _ in moves], [n for _, n in moves], truck_used[k])

    # 용량 : 같은 arc 에 같은 시점 출발하는 트럭들의 용량 합 (lot 이 1 이면 화물을 트럭별로 정수로 나눌 수 있으므로 트럭별 용량과 동일)
    for arc in arcs:
        for t in range(horizon - lead[arc]):
            md.add(sum(flow[arc][jt][t] for jt in ships) <= sum(spec["cap"] * truck_move[k][arc][t] for k, (spec, _) in enumerate(types)))

    truck_travel = md.new_int_var(0, len(trucks) * horizon, "truck_travel")
    md.add(truck_travel == sum(truck_move[k][arc][t] * lead[arc] for k in truck_move for arc in arcs for t in truck_move[k][arc]))

    every_final_product_max_set = {} # every_final_product_max_set[final_product][fc] : fc 에서의 최대 재고
    for final_product, amount in zip(params["final_product"], params["amount"]):
        every_final_product_max_set[final_product] = {}
        for fc in fcs:
            if final_product in ini_set[fc]:
                every_final_product_max_set[final_product][fc] = md.new_int_var(0, qty_ub[final_product], f"{fc}_{final_product}_FP")
                md.add_max_equality(every_final_product_max_set[final_product][fc], [stock[fc][final_product][t] for t in range(horizon)])
        md.add(sum(every_final_product_max_set[final_product].values()) >= amount)

    total_makespan = md.new_int_var(0, horizon, "total_makespan")
    md.add_max_equality(total_makespan, [(t + p_time[(fc, jt)]) * x for fc in fcs for jt in ini_set[fc] for t, x in make[fc][jt].items()])

    # 재고 비용 : 화물은 어디에 있든 (공장 / 트럭 / 경유 대기) 같은 단가로 makespan 까지 쌓이므로 경로와 무관
    # Σ_{t<makespan} (생산 누적 - 소비 누적) = Σ_job (makespan - 종료) - Σ_job bom (makespan - 시작)
    # = makespan x W - Q  (W : 부가 단가 합, Q : 시점 가중합) → 곱셈 하나로 끝나서 held / before_makespan 변수가 필요 없음
    value_added = {jt: holding_cost.get(jt, 0) - sum(holding_cost.get(ing, 0) * n for ing, n in boms.get(jt, {}).items()) for jt in qty_ub}
    w_lb = sum(min(0, value_added[jt]) * max_job[fc][jt] for fc in fcs for jt in ini_set[fc])
    w_ub = sum(max(0, value_added[jt]) * max_job[fc][jt] for fc in fcs for jt in ini_set[fc])
    weight_sum = md.new_int_var(w_lb, w_ub, "value_added_sum")
    md.add(weight_sum == sum(value_added[jt] * x for fc in fcs for jt in ini_set[fc] for x in make[fc][jt].values()))
    span_weight = md.new_int_var(min(0, w_lb * horizon), max(0, w_ub * horizon), "makespan_x_value_added")
    md.add_multiplication_equality(span_weight, [total_makespan, weight_sum])
    hold_ub = sum(holding_cost.get(jt, 0) * qty_ub[jt] * horizon for jt in qty_ub)
    total_holding = md.new_int_var(0, hold_ub, "total_holding_cost")
    md.add(total_holding == span_weight - sum(x * (holding_cost.get(jt, 0) * (t + p_time[(fc, jt)]) - sum(holding_cost.get(ing, 0) * n * t for ing, n in boms.get(jt, {}).items())) for fc in fcs for jt in ini_set[fc] for t, x in make[fc][jt].items()))

    w = params["weights"]
    md.minimize(w["makespan"] * total_makespan + w["holding"] * total_holding + w["truck_used"] * sum(truck_used.values()) + w["truck_travel"] * truck_travel)
    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        calculating_time = time.time() - st_time
        print("Calculated time =", calculating_time)
        total_makespan = solver.value(total_makespan)
        print("Status :", solver.status_name(status), f"(horizon = {horizon})")
        print("Total Makespan :", total_makespan)
        print("Holding Cost :", solver.value(total_holding))
        jobs = [] # (fc, jt, k, 시작, 종료)
        for fc in fcs:
            for jt in ini_set[fc]:
                starts = [t for t, x in make[fc][jt].items() if solver.value(x)]
                jobs += [(fc, jt, k, t, t + p_time[(fc, jt)]) for k, t in enumerate(starts)]
        unit_time = {} # unit_time[jt] : makespan 까지 jt 가 머문 시간 합 (생산 ~ 소비)
        for fc, jt, k, st, ed in jobs:
            unit_time[jt] = unit_time.get(jt, 0) + total_makespan - ed
            for ing, n in boms.get(jt, {}).items():
                unit_time[ing] = unit_time.get(ing, 0) - n * (total_makespan - st)
        for jt, amount in unit_time.items():
            if cost := holding_cost.get(jt, 0) * amount:
                print(f"    {jt} : {cost} (= {holding_cost.get(jt, 0)} x {amount} unit*time)")
        print("Truck Used :", sum(solver.value(n) for n in truck_used.values()), "/", len(trucks), "(+1 Virtual Truck)")
        print("Truck Travel :", solver.value(truck_travel), "\n")

        # 타입별 대수로 푼 해를 트럭 한 대씩의 경로로 풀어 씀 (같은 arc·시점에 출발한 화물은 용량 안에서 나눠 실음)
        fleet = []
        for k, (spec, names) in enumerate(types):
            homes = [fc for fc in fcs for _ in range(solver.value(truck_idle[k][fc][-1]))]
            fleet += [{"name": name, "type": k, "cap": spec["cap"], "home": fc, "loc": fc, "free": -1, "moves": []} for name, fc in zip(names, homes)]
        for t, f, g in sorted((t, f, g) for f, g in arcs for t in range(horizon - lead[(f, g)])):
            leaving = [truck for k in truck_move for truck in sorted((truck for truck in fleet if truck["type"] == k and truck["loc"] == f and truck["free"] <= t), key=lambda truck: truck["free"])[:solver.value(truck_move[k][(f, g)][t])]]
            if not leaving:
                continue
            loads, room = [{} for _ in leaving], [truck["cap"] for truck in leaving]
            for jt in ships:
                left = solver.value(flow[(f, g)][jt][t])
                for i in range(len(leaving)):
                    if n := min(left, room[i]):
                        loads[i][jt], room[i], left = n, room[i] - n, left - n
            for truck, load in zip(leaving, loads):
                truck["moves"].append((f, g, t, t + lead[(f, g)], load))
                truck["loc"], truck["free"] = g, t + lead[(f, g)]
        routes = [truck for truck in fleet]

        fmt = lambda load: ", ".join(f"{jt}×{n}" for jt, n in load.items()) or "empty"
        for route in routes:
            print(f"{route['name']} (cap {route['cap']}, start {route['home']}) : {' → '.join([route['home']] + [move[1] for move in route['moves']])}")
            for f, g, t, arrive, load in route["moves"]:
                print(f"    {f} -> {g} | {t} ~ {arrive} ({arrive - t}) | {fmt(load)} | {sum(load.values())}/{route['cap']}")

        virtual_moves = [] # Virtual Truck : 같은 공장 생산품이 상위 job 에 투입된 시점 (내부 이송, 시간 0)
        for f in fcs:
            for t in range(horizon):
                if load := {ing: amount for ing in ini_set[f] if (amount := solver.value(consumed(f, ing, t)))}:
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
        n_truck = len(routes)
        truck_rows = [f"{route['name']} ({route['home']}, cap {route['cap']})" for route in routes] + ["vt (virtual)"]
        prod_rows = [(fc, jt) for fc in ini_set for jt in ini_set[fc]]
        x_max = max([total_makespan] + [move[3] for route in routes for move in route["moves"]]) + 1

        fig, (ax_tr, ax_pd) = plt.subplots(2, 1, sharex=True, figsize=(max(14, x_max * 0.45), 1.1 * len(truck_rows) + 0.55 * len(prod_rows) + 2.5), gridspec_kw={"height_ratios": [2 * len(truck_rows) + 1, len(prod_rows) + 1]})
        h = 0.62

        # 물류 패널 : 트럭 한 줄 = 한 대의 경로, 구간 막대는 실린 품목 비율만큼 색 띠, 막대 위에는 정차 공장
        for y, route in enumerate(routes):
            for i, (f, g, depart, arrive, load) in enumerate(route["moves"]):
                waited = i and depart > route["moves"][i - 1][3]
                if waited: # 정차 대기
                    ax_tr.plot([route["moves"][i - 1][3], depart], [y, y], color=MUTED, linestyle=":", linewidth=1.5, zorder=1)
                if load:
                    bottom, total = y - h / 2, sum(load.values())
                    for jt, amount in load.items():
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

        for ax, rows, title in ((ax_tr, truck_rows, f"Logistics  (trucks used {sum(1 for route in routes if route['moves'])} / {len(trucks)} + 1 virtual)"), (ax_pd, [f"{fc} · {jt}" for fc, jt in prod_rows], "Production")):
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
        return calculating_time
    else:
        print("X")

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
def start(boms, factories, holding_cost, deliveries, trucks, params):
    process, deliver, ini_set = Process(), Deliver(), {}
    for fc in factories.keys():
        ini_set[fc] = {}
        for jt in factories[fc].keys():
            ini_set[fc][jt] = factories[fc][jt]["lots"]
            setattr(process, f"{fc}{jt}", factories[fc][jt]["time"])
    for fc1 in deliveries.keys():
        for fc2 in deliveries[fc1].keys():
            setattr(deliver, f"{fc1}{fc2}", deliveries[fc1][fc2])
    system(process, deliver, boms, holding_cost, ini_set, trucks, params, set_horizon(boms, factories, deliveries, params))

def main():

    params = {"final_product": ["JT12", "JT9"], "amount": [2, 1],
              "weights": {"makespan": 100, "holding": 1, "truck_used": 10, "truck_travel": 1}} # 목적함수 가중치

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
    deliveries = {fc1: {fc2 : random.randint(3, 8) if fc1 != fc2 else 1 for fc2 in fcs} for fc1 in fcs}
    start(boms, factories, holding_cost, deliveries, trucks, params)

if __name__ == "__main__":
    main()
