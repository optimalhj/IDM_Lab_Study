import random
from collections import defaultdict

from ortools.sat.python import cp_model

def get_all_jts(boms, factories):

    jts = set()

    for parent, children in boms.items():
        jts.add(parent)
        jts.update(children.keys())

    for fc in factories.values():
        jts.update(fc.keys())

    return sorted(jts)


def get_parents(boms):
    """
    parents[jt] = [(parent_jt, quantity), ...]
    """
    parents = defaultdict(list)

    for parent, children in boms.items():
        for child, qty in children.items():
            parents[child].append((parent, qty))

    return parents


def validate_bom(boms):
    """
    BOM cycle을 검사한다.
    현재 데이터에서는 cycle이 없어야 한다.
    """

    graph = defaultdict(list)

    for parent, children in boms.items():
        for child in children:
            graph[parent].append(child)

    WHITE = 0
    GRAY = 1
    BLACK = 2

    state = defaultdict(lambda: WHITE)

    def dfs(node):
        state[node] = GRAY

        for child in graph[node]:

            if state[child] == GRAY:
                return False

            if state[child] == WHITE:
                if not dfs(child):
                    return False

        state[node] = BLACK
        return True

    nodes = set(graph.keys())

    for children in graph.values():
        nodes.update(children)

    for node in nodes:
        if state[node] == WHITE:
            if not dfs(node):
                return False

    return True


# ============================================================
# Main CP-SAT model
# ============================================================

def lot_stream(process, deliver, boms, ini_set, factories, deliveries,
    num_vehicles,
    max_jobs_per_fc_jt=20,
    max_deliveries_per_route_jt=20,
    horizon=10000):

    md = cp_model.CpModel()

    all_jts = get_all_jts(boms, factories)
    parents = get_parents(boms)

    # --------------------------------------------------------
    # Initial inventory
    #
    # 현재 문제에서는 초기재고가 없다고 가정.
    #
    # 추후 ini_inventory를 별도로 넣으면 이 부분만 바꾸면 됨.
    # --------------------------------------------------------

    initial_inventory = {(fc, jt): 0 for fc in factories for jt in all_jts}

    # --------------------------------------------------------
    # Production variables
    #
    # 하나의 (FC, JT)에 대해 최대 N개의 production job을
    # 미리 만들어놓고 active 여부를 CP-SAT이 결정한다.
    # --------------------------------------------------------

    prod_active = {}
    prod_qty = {}
    prod_start = {}
    prod_end = {}
    prod_interval = {}

    # lot 선택 변수
    prod_lot_choice = {}

    production_intervals = defaultdict(list)

    for fc, products in factories.items():

        for jt, info in products.items():

            lots = info["lots"]
            unit_time = info["time"]

            for job in range(max_jobs_per_fc_jt):
                active = md.new_bool_var(f"prod_active_{fc}_{jt}_{job}")
                qty = md.new_int_var(0, max(lots), f"prod_qty_{fc}_{jt}_{job}")
                start = md.new_int_var(0, horizon, f"prod_start_{fc}_{jt}_{job}")
                end = md.new_int_var(0, horizon, f"prod_end_{fc}_{jt}_{job}")

                prod_active[fc, jt, job] = active
                prod_qty[fc, jt, job] = qty
                prod_start[fc, jt, job] = start
                prod_end[fc, jt, job] = end

                # --------------------------------------------
                # Lot choice
                #
                # lots=[20,50]
                #
                # active=0 -> qty=0
                # active=1 -> qty=20 or 50
                # --------------------------------------------

                choices = []

                for k, lot in enumerate(lots):

                    choice = md.new_bool_var(f"prod_lot_{fc}_{jt}_{job}_{k}")
                    prod_lot_choice[fc, jt, job, k] = choice
                    choices.append(choice)

                md.add(sum(choices) == active)

                md.add(qty== sum(lots[k] * choices[k] for k in range(len(lots))))

                # --------------------------------------------
                # Duration = quantity * unit_time
                # --------------------------------------------

                duration = md.new_int_var(0, horizon, f"prod_duration_{fc}_{jt}_{job}")

                md.add(duration == unit_time * qty)

                # --------------------------------------------
                # Optional interval
                # --------------------------------------------

                interval = md.new_optional_interval_var(start, duration, end, active,f"prod_interval_{fc}_{jt}_{job}")

                prod_interval[fc, jt, job] = interval

                production_intervals[fc, jt].append(interval)

    # --------------------------------------------------------
    # Same FC + same JT cannot overlap
    #
    # Same FC + different JT CAN overlap.
    # --------------------------------------------------------

    for key, intervals in production_intervals.items():
        md.add_no_overlap(intervals)

    # --------------------------------------------------------
    # Total production quantity by FC / JT
    # --------------------------------------------------------

    total_production = {}

    for fc, products in factories.items():

        for jt in products:

            total_production[fc, jt] = md.new_int_var(
                0,
                max_lots_sum := max(lots)
                * max_jobs_per_fc_jt
                if (lots := products[jt]["lots"])
                else 0,
                f"total_production_{fc}_{jt}"
            )

            md.add(
                total_production[fc, jt]
                ==
                sum(
                    prod_qty[fc, jt, job]
                    for job in range(max_jobs_per_fc_jt)
                )
            )

    # --------------------------------------------------------
    # Delivery variables
    #
    # delivery:
    #
    # source FC
    # destination FC
    # JT
    # delivery number
    #
    # Delivery quantity는 자유롭게 분할 가능.
    #
    # 예:
    # production = 50
    #
    # delivery 0 = 20
    # delivery 1 = 30
    #
    # 가능.
    # --------------------------------------------------------

    del_active = {}
    del_qty = {}
    del_start = {}
    del_end = {}
    del_interval = {}

    delivery_intervals = []
    delivery_by_vehicle = []

    # route별 delivery interval
    route_intervals = defaultdict(list)

    for src in factories:

        for dst in factories:

            if src == dst:
                continue

            travel_time = deliveries[src][dst]

            if travel_time <= 0:
                raise ValueError(
                    f"{src}->{dst} delivery time이 0 이하입니다."
                )

            for jt in factories[src]:

                # 실제로 source에서 만들 수 있는 JT만 출하 가능
                for d in range(max_deliveries_per_route_jt):
                    active = md.new_bool_var(f"del_active_{src}_{dst}_{jt}_{d}")
                    qty = md.new_int_var(0, horizon, f"del_qty_{src}_{dst}_{jt}_{d}")
                    start = md.new_int_var(0, horizon,f"del_start_{src}_{dst}_{jt}_{d}")
                    end = md.new_int_var(0, horizon, f"del_end_{src}_{dst}_{jt}_{d}")

                    del_active[src, dst, jt, d] = active

                    del_qty[src, dst, jt, d] = qty

                    del_start[src, dst, jt, d] = start

                    del_end[src, dst, jt, d] = end

                    # active=0 -> qty=0
                    md.add(qty <= horizon * active)

                    # ------------------------------------------------
                    # Delivery interval
                    #
                    # duration = travel time
                    # ------------------------------------------------

                    interval = md.new_optional_interval_var(start, travel_time, end, active, f"del_interval_{src}_{dst}_{jt}_{d}")

                    del_interval[src, dst, jt, d] = interval

                    delivery_intervals.append(interval)

                    route_intervals[src, dst].append(interval)

    # --------------------------------------------------------
    # Delivery ordering on same route
    #
    # 같은 source -> destination route에서
    # delivery를 순차적으로 보낼 필요가 있는지는
    # 차량 공유 모델과 별개.
    #
    # 여기서는 여러 차량이 존재할 수 있으므로 route 자체에는
    # NoOverlap을 걸지 않는다.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Vehicle capacity
    #
    # 모든 delivery interval의 동시에 운행 중인 차량 수 <= 8
    #
    # AddCumulative(intervals, demands, num_vehicles)
    # --------------------------------------------------------

    if delivery_intervals:
        md.add_cumulative(delivery_intervals, [1] * len(delivery_intervals), num_vehicles)

    # --------------------------------------------------------
    # Delivery must start after source production exists
    #
    # 여기서는 하나의 delivery가 source에서 생산된 물량을
    # 여러 production job에서 가져올 수 있도록 허용한다.
    #
    # 따라서 delivery start 시점까지 source에서 충분한
    # 생산량이 완료되어 있어야 한다.
    #
    # 이 부분은 아래 time-indexed flow 제약에서 처리한다.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Production completion quantity at each time
    #
    # Inventory를 time-indexed로 계산하기 위한 변수.
    #
    # 모든 시간 t에 대해:
    #
    # production completed by t
    # delivery arrived by t
    # production consumed by t
    #
    # 를 계산한다.
    # --------------------------------------------------------

    # horizon을 그대로 모두 사용하면 변수 수가 커질 수 있으므로
    # 현재는 0..horizon의 integer time grid 사용.
    #
    # 실전에서는 event-based 방식으로 줄이는 것을 추천.
    # --------------------------------------------------------

    # 완료 여부 / 시작 여부 BoolVar
    prod_completed_by = {}
    prod_started_by = {}

    for fc, products in factories.items():

        for jt in products:

            for job in range(max_jobs_per_fc_jt):

                for t in range(horizon + 1):

                    completed = md.new_bool_var(f"prod_completed_{fc}_{jt}_{job}_{t}")

                    started = md.new_bool_var(f"prod_started_{fc}_{jt}_{job}_{t}")

                    prod_completed_by[fc, jt, job, t] = completed

                    prod_started_by[fc, jt, job, t] = started

                    # end <= t <=> completed
                    md.add(prod_end[fc, jt, job] <= t).OnlyEnforceIf(completed)

                    md.add(prod_end[fc, jt, job] > t).OnlyEnforceIf(completed.Not())

                    # start <= t <=> started
                    md.add(prod_start[fc, jt, job] <= t).OnlyEnforceIf(started)

                    md.add(prod_start[fc, jt, job] > t).OnlyEnforceIf(started.Not())

                    # inactive job은 started/completed 될 수 없음
                    md.add(completed <= prod_active[fc, jt, job])

                    md.add(started <= prod_active[fc, jt, job])

    # --------------------------------------------------------
    # Delivery arrival indicators
    # --------------------------------------------------------

    del_arrived_by = {}
    del_started_by = {}

    for src in factories:

        for dst in factories:

            if src == dst: continue

            for jt in factories[src]:

                for d in range(max_deliveries_per_route_jt):

                    for t in range(horizon + 1):

                        arrived = md.new_bool_var(f"del_arrived_{src}_{dst}_{jt}_{d}_{t}")

                        started = md.new_bool_var(f"del_started_{src}_{dst}_{jt}_{d}_{t}")

                        del_arrived_by[src, dst, jt, d, t] = arrived

                        del_started_by[src, dst, jt, d, t] = started

                        md.add(del_end[src, dst, jt, d] <= t).OnlyEnforceIf(arrived)

                        md.add(del_end[src, dst, jt, d] > t).OnlyEnforceIf(arrived.Not())

                        md.add(del_start[src, dst, jt, d] <= t).OnlyEnforceIf(started)

                        md.add(del_start[src, dst, jt, d] > t).OnlyEnforceIf(started.Not())

                        md.add(arrived <= del_active[src, dst, jt, d])

                        md.add(started <= del_active[src, dst, jt, d])

    # --------------------------------------------------------
    # Inventory
    #
    # inventory[fc,jt,t]
    #
    # t 시점에서 사용 가능한 재고.
    # --------------------------------------------------------

    inventory = {}

    for fc in factories:

        for jt in all_jts:

            # inventory upper bound
            inv_vars = []

            for t in range(horizon + 1):

                inv = md.new_int_var(0, horizon * 100, f"inventory_{fc}_{jt}_{t}")
                inventory[fc, jt, t] = inv
                inv_vars.append(inv)

    # --------------------------------------------------------
    # Material balance
    #
    # inventory(t)
    #
    # = initial
    # + production completed
    # + delivery arrived
    # - production consumption started
    #
    # 생산 Job이 시작하는 순간 필요한 BOM material을 소비한다고
    # 가정한다.
    # --------------------------------------------------------

    for fc in factories:

        for jt in all_jts:

            initial = initial_inventory[fc, jt]

            for t in range(horizon + 1):

                production_in = []

                # 해당 FC에서 JT 생산 완료
                if jt in factories[fc]:

                    for job in range(max_jobs_per_fc_jt):

                        # completed_by(t) * qty
                        #
                        # aux variable로 linearize
                        cq = md.new_int_var(0, horizon * 100,f"completed_qty_{fc}_{jt}_{job}_{t}")

                        completed = prod_completed_by[fc, jt, job, t]

                        qty = prod_qty[fc, jt, job]

                        md.add(cq <= qty)

                        md.add(cq <= horizon * 100 * completed)

                        md.add(cq >= qty - horizon * 100 * (1 - completed))

                        production_in.append(cq)

                # 다른 FC에서 도착한 JT
                delivery_in = []

                for src in factories:

                    if src == fc: continue

                    if jt not in factories[src]: continue

                    for d in range(max_deliveries_per_route_jt):
                        aq = md.new_int_var(0, horizon * 100,f"arrival_qty_{src}_{fc}_{jt}_{d}_{t}")
                        arrived = del_arrived_by[src, fc, jt, d, t]
                        qty = del_qty[src, fc, jt, d]
                        md.add(aq <= qty)
                        md.add(aq <= horizon * 100 * arrived)
                        md.add(aq >= qty - horizon * 100 * (1 - arrived))
                        delivery_in.append(aq)

                # 생산 소비
                consumption = []

                for parent, bom_qty in parents[jt]:

                    # parent를 fc에서 생산할 때 JT를 소비
                    if parent not in factories[fc]: continue

                    for job in range(max_jobs_per_fc_jt):

                        cq = md.new_int_var(0, horizon * 100, f"consume_{fc}_{jt}_{parent}_{job}_{t}")

                        started = prod_started_by[fc, parent, job, t]

                        parent_qty = prod_qty[fc, parent, job]

                        md.add(cq <= bom_qty * parent_qty)

                        md.add(cq <= horizon * 100 * started)

                        md.add(cq >= bom_qty * parent_qty - horizon * 100 * (1 - started))

                        consumption.append(cq)

                md.add(
                    inventory[fc, jt, t]
                    ==
                    initial
                    + sum(production_in)
                    + sum(delivery_in)
                    - sum(consumption)
                )

    # --------------------------------------------------------
    # Delivery quantity cannot exceed source available stock
    #
    # 위의 source inventory balance와 함께 사용.
    #
    # Delivery가 시작되는 시점까지 생산된 물량을 넘어서
    # 출하할 수 없도록 cumulative constraint 추가.
    # --------------------------------------------------------

    for src in factories:

        for jt in factories[src]:

            for t in range(horizon + 1):

                outgoing = []

                for dst in factories:

                    if src == dst:
                        continue

                    for d in range(max_deliveries_per_route_jt):

                        sq = md.new_int_var(
                            0,
                            horizon * 100,
                            f"ship_qty_{src}_{dst}_{jt}_{d}_{t}"
                        )

                        started = del_started_by[
                            src, dst, jt, d, t
                        ]

                        qty = del_qty[
                            src, dst, jt, d
                        ]

                        md.add(
                            sq <= qty
                        )

                        md.add(
                            sq <= horizon * 100 * started
                        )

                        md.add(
                            sq >=
                            qty -
                            horizon * 100 * (1 - started)
                        )

                        outgoing.append(sq)

                # source production completed by t
                produced = []

                for job in range(max_jobs_per_fc_jt):

                    cq = md.new_int_var(
                        0,
                        horizon * 100,
                        f"source_completed_{src}_{jt}_{job}_{t}"
                    )

                    completed = prod_completed_by[
                        src, jt, job, t
                    ]

                    qty = prod_qty[
                        src, jt, job
                    ]

                    md.add(cq <= qty)

                    md.add(
                        cq <= horizon * 100 * completed
                    )

                    md.add(
                        cq >=
                        qty -
                        horizon * 100 * (1 - completed)
                    )

                    produced.append(cq)

                md.add(
                    sum(outgoing)
                    <=
                    initial_inventory[src, jt]
                    + sum(produced)
                )

    # --------------------------------------------------------
    # Production lot/job ordering
    #
    # 같은 FC/JT의 job을 활성화할 경우,
    # job index 순서대로 사용하도록 symmetry breaking.
    #
    # active[0] >= active[1] >= active[2] ...
    #
    # 이렇게 하면 solver가 불필요하게
    # Job 17만 사용하는 식의 대칭해를 탐색하지 않는다.
    # --------------------------------------------------------

    for fc, products in factories.items():

        for jt in products:

            for job in range(max_jobs_per_fc_jt - 1):

                md.add(
                    prod_active[fc, jt, job]
                    >=
                    prod_active[fc, jt, job + 1]
                )

    # --------------------------------------------------------
    # Delivery ordering
    #
    # 같은 src/dst/JT에 대해서도 delivery index symmetry 제거.
    # --------------------------------------------------------

    for src in factories:

        for dst in factories:

            if src == dst:
                continue

            for jt in factories[src]:

                for d in range(max_deliveries_per_route_jt - 1):

                    md.add(
                        del_active[src, dst, jt, d]
                        >=
                        del_active[src, dst, jt, d + 1]
                    )

    # --------------------------------------------------------
    # Final product JT12 = 1
    #
    # JT12는 Fc8에서 생산 가능.
    # --------------------------------------------------------

    if "JT12" not in all_jts:
        raise ValueError("JT12가 존재하지 않습니다.")

    jt12_production = []

    for fc in factories:

        if "JT12" not in factories[fc]:
            continue

        for job in range(max_jobs_per_fc_jt):

            jt12_production.append(
                prod_qty[fc, "JT12", job]
            )

    if not jt12_production:
        raise ValueError(
            "JT12를 생산할 수 있는 factory가 없습니다."
        )

    md.add(
        sum(jt12_production) == 1
    )

    # --------------------------------------------------------
    # Makespan
    #
    # JT12 생산 완료시간.
    # --------------------------------------------------------

    makespan = md.new_int_var(
        0,
        horizon,
        "makespan"
    )

    for fc in factories:

        if "JT12" not in factories[fc]:
            continue

        for job in range(max_jobs_per_fc_jt):

            md.add(
                makespan >= prod_end[fc, "JT12", job]
            ).OnlyEnforceIf(
                prod_active[fc, "JT12", job]
            )

    # --------------------------------------------------------
    # Inventory objective
    #
    # 시간별 재고량의 합.
    #
    # 즉 inventory-time:
    #
    # 10개가 1시간 존재 -> 10
    # 10개가 10시간 존재 -> 100
    #
    # JT12 최종재고도 inventory에 들어가지만,
    # 최종 목적지에서 1개 생산하는 순간 종료하기 때문에
    # 영향은 제한적이다.
    # --------------------------------------------------------

    total_inventory = md.new_int_var(0, horizon * 100000, "total_inventory")

    md.add(
        total_inventory
        ==
        sum(
            inventory[fc, jt, t]
            for fc in factories
            for jt in all_jts
            for t in range(horizon + 1)
        )
    )

    # --------------------------------------------------------
    # Phase 1
    #
    # makespan 최소
    # --------------------------------------------------------

    md.minimize(makespan)

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 120
    solver.parameters.num_search_workers = 8

    status = solver.Solve(md)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible solution.")
        return None

    optimal_makespan = solver.Value(makespan)

    print()
    print("=" * 100)
    print("PHASE 1")
    print("=" * 100)
    print(f"Optimal makespan = {optimal_makespan}")

    # --------------------------------------------------------
    # Phase 2
    #
    # makespan을 고정하고 inventory 최소화
    # --------------------------------------------------------

    md.add(makespan == optimal_makespan)
    md.minimize(total_inventory)

    status = solver.Solve(md)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Phase 2 failed.")
        return None

    optimal_inventory = solver.Value(
        total_inventory
    )

    print()
    print("=" * 100)
    print("PHASE 2")
    print("=" * 100)
    print(f"Optimal makespan   = {solver.Value(makespan)}")
    print(f"Total inventory    = {optimal_inventory}")

    # ========================================================
    # Solution output
    # ========================================================

    print()
    print("=" * 100)
    print("PRODUCTION PLAN")
    print("=" * 100)

    production_result = []

    for fc, products in factories.items():

        for jt in products:

            for job in range(max_jobs_per_fc_jt):

                if solver.Value(
                    prod_active[fc, jt, job]
                ) == 0:
                    continue

                qty = solver.Value(
                    prod_qty[fc, jt, job]
                )

                st = solver.Value(
                    prod_start[fc, jt, job]
                )

                en = solver.Value(
                    prod_end[fc, jt, job]
                )

                production_result.append({
                    "fc": fc,
                    "jt": jt,
                    "job": job,
                    "qty": qty,
                    "start": st,
                    "end": en,
                    "duration": en - st,
                })

                print(
                    f"{fc:4s} | "
                    f"{jt:4s} | "
                    f"job={job:2d} | "
                    f"qty={qty:4d} | "
                    f"{st:5d} -> {en:5d} | "
                    f"duration={en-st:5d}"
                )

    print()
    print("=" * 100)
    print("DELIVERY PLAN")
    print("=" * 100)

    delivery_result = []

    for src in factories:

        for dst in factories:

            if src == dst:
                continue

            for jt in factories[src]:

                for d in range(max_deliveries_per_route_jt):

                    if solver.Value(
                        del_active[src, dst, jt, d]
                    ) == 0:
                        continue

                    qty = solver.Value(
                        del_qty[src, dst, jt, d]
                    )

                    st = solver.Value(
                        del_start[src, dst, jt, d]
                    )

                    en = solver.Value(
                        del_end[src, dst, jt, d]
                    )

                    delivery_result.append({
                        "src": src,
                        "dst": dst,
                        "jt": jt,
                        "delivery": d,
                        "qty": qty,
                        "start": st,
                        "end": en,
                    })

                    print(
                        f"{src:4s} -> {dst:4s} | "
                        f"{jt:4s} | "
                        f"delivery={d:2d} | "
                        f"qty={qty:4d} | "
                        f"{st:5d} -> {en:5d}"
                    )

    print()
    print("=" * 100)
    print("INVENTORY")
    print("=" * 100)

    inventory_result = []

    for fc in factories:

        for jt in all_jts:

            values = []

            for t in range(
                optimal_makespan + 1
            ):

                value = solver.Value(
                    inventory[fc, jt, t]
                )

                if value > 0:
                    values.append(
                        (t, value)
                    )

            if values:

                inventory_result.append({
                    "fc": fc,
                    "jt": jt,
                    "values": values,
                })

                print(
                    f"{fc:4s} | "
                    f"{jt:4s} | "
                    f"{values}"
                )

    print()
    print("=" * 100)
    print("SOLVER STATISTICS")
    print("=" * 100)

    print(f"status      = {solver.StatusName(status)}")
    print(f"objective   = {solver.ObjectiveValue()}")
    print(f"wall time   = {solver.WallTime():.3f} sec")
    print(f"branches    = {solver.NumBranches()}")
    print(f"conflicts   = {solver.NumConflicts()}")

    return {
        "solver": solver,
        "model": md,
        "makespan": optimal_makespan,
        "inventory": optimal_inventory,
        "production": production_result,
        "delivery": delivery_result,
        "inventory_detail": inventory_result,
    }

class Process:
    def __init__(self): pass
class Deliver:
    def __init__(self): pass
def start(boms, factories, deliveries,num_vehicles=8):

    process, deliver, ini_set = Process(), Deliver(), {}
    for fc in factories.keys():
        ini_set[fc] = {}
        for jt in factories[fc].keys():
            ini_set[fc][jt] = factories[fc][jt]["lots"]
            setattr(process, f"{fc}_{jt}", factories[fc][jt]["time"])
    for fc1 in deliveries.keys():
        for fc2 in deliveries[fc1].keys():
            setattr(deliver,f"{fc1}_{fc2}", deliveries[fc1][fc2])

    result = lot_stream(process=process, deliver=deliver, boms=boms, ini_set=ini_set, factories=factories, deliveries=deliveries, num_vehicles=num_vehicles)
    return result


# ============================================================
# Main
# ============================================================

def main():

    boms = {"JT12": {"JT9": 2, "JT10": 2, "JT11": 1},
            "JT9": {"JT8": 3, "JT10": 2, "JT11": 1},
            "JT10": {"JT4": 6, "JT6": 4, "JT8": 2},
            "JT11": {"JT5": 2, "JT7": 4, "JT8": 2},
            "JT8": {"JT5": 1, "JT6": 1, "JT7": 1},
            "JT7": {"JT1": 8, "JT2": 10, "JT3": 18},
            "JT6": {"JT2": 5, "JT4": 2, "JT5": 1},
            "JT5": {"JT1": 20, "JT3": 25},
            "JT4": {"JT1": 10, "JT3": 15}}

    factories = {
        "Fc1": {"JT4": {"lots": [5],"time": 2},
                "JT11": {"lots": [1],"time": 5}},

        "Fc2": {"JT9": {"lots": [3], "time": 4}},

        "Fc3": {"JT7": {"lots": [5], "time": 4},
                "JT8": {"lots": [5], "time": 4}},

        "Fc4": {"JT1": {"lots": [20, 40], "time": 1},
                "JT2": {"lots": [20, 30], "time": 1}},

        "Fc5": {"JT5": {"lots": [5, 10],"time": 3},
                "JT6": {"lots": [6, 8, 10], "time": 3},
                "JT9": {"lots": [2], "time": 3}},

        "Fc6": {"JT7": {"lots": [3], "time": 4},
                "JT9": {"lots": [2], "time": 4},
                "JT11": {"lots": [1], "time": 4}},

        "Fc7": {"JT2": {"lots": [7],"time": 1},
                "JT3": {"lots": [10],"time": 2},
                "JT4": {"lots": [2], "time": 3}},

        "Fc8": {"JT5": {"lots": [5], "time": 4},
                "JT12": {"lots": [1], "time": 5}},

        "Fc9": {"JT3": {"lots": [4, 8, 10], "time": 1},
                "JT6": {"lots": [4],"time": 3},
                "JT10": {"lots": [1],"time": 4}}}

    # --------------------------------------------------------
    # Delivery travel time
    # --------------------------------------------------------

    fcs = list(factories)

    deliveries = {fc1: {fc2: random.randint(1, 5) if fc1 != fc2 else 0 for fc2 in fcs} for fc1 in fcs}

    print("DELIVERY TIMES")
    print("=" * 100)

    for fc1 in fcs:
        print(fc1, deliveries[fc1])
    print()

    # --------------------------------------------------------
    # Vehicle parameter
    # --------------------------------------------------------

    num_vehicles = 8

    print(f"Number of vehicles = {num_vehicles}")

    print("---------------------------------------------------------")

    # --------------------------------------------------------
    # Solve
    # --------------------------------------------------------

    result = start(boms=boms, factories=factories, deliveries=deliveries, num_vehicles=num_vehicles)
    return result


if __name__ == "__main__":
    main()