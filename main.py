import random
from ortools.sat.python import cp_model

def lot_stream(process, deliver, boms, ini_set, params):
    horizon = params["horizon"]
    job_interval_horizon = params["horizon"]

    md = cp_model.CpModel()

    fc_wip_t, fc_deliver_to = {}, {}
    for fc in ini_set.keys():
        fc_wip_t[fc] = {}
        for jt in ini_set[fc].keys():
            fc_wip_t[fc][jt] = {t: md.new_int_var(0, horizon, f"{fc}_{jt}_{t}") if t else 0 for t in range(horizon)}
            for fc_prime in set([fc_prime for fc_prime in ini_set.keys() for jt_prime in ini_set[fc_prime] if jt_prime in boms and jt in boms[jt_prime]]):
                if fc not in fc_deliver_to: fc_deliver_to[fc] = {}
                if fc_prime not in fc_deliver_to[fc]: fc_deliver_to[fc][fc_prime] = []
                fc_deliver_to[fc][fc_prime].append(jt)

    delivered, ingredients = {}, {}
    for fc1 in fc_deliver_to.keys():
        for fc2 in fc_deliver_to[fc1].keys():
            if fc2 not in delivered: delivered[fc2] = {}
            if fc2 not in ingredients: ingredients[fc2] = set()
            delivered[fc2][fc1] = {}
            for ingredient in fc_deliver_to[fc1][fc2]:
                delivered[fc2][fc1][ingredient] = {t: md.new_int_var(0, horizon, f"{fc2}_{ingredient}_{t}_delivered_from_{fc1}") for t in range(1, horizon)}
                ingredients[fc2].add(ingredient)
    for fc in ingredients.keys():
        for ingredient in ingredients[fc]:
            if ingredient not in fc_wip_t[fc]:
                fc_wip_t[fc][ingredient] = {t: md.new_int_var(0, horizon, f"{fc}_{ingredient}_{t}") if t else 0 for t in range(horizon)}

    sem, intervals = {}, {} # Start End Make => Interval
    produced, consumed = {}, {}
    se_event = {}
    for fc in ini_set.keys():
        sem[fc] = {}
        intervals[fc] = {}
        produced[fc] = {}
        consumed[fc] = {}
        se_event[fc] = {}
        for jt in ini_set[fc].keys():
            sem[fc][jt] = {}
            intervals[fc][jt] = {}
            produced[fc][jt] = {t: md.new_bool_var(f"{fc}_{jt}_{t}_produced") for t in range(1, horizon)}
            if jt in boms:
                consumed[fc][jt] = {ingredient: {t: md.new_int_var(0, boms[jt][ingredient], f"{fc}_{ingredient}_{t}_consumed") for t in range(1, horizon)} for ingredient in boms[jt].keys()}

            se_event[fc][jt] = {}
            for k in range(job_interval_horizon):
                se_event[fc][jt][k] = {}
                sem[fc][jt][k] = [md.new_int_var(1, horizon - 1, f"{fc}_{jt}_{k}_st"), md.new_int_var(1, horizon - 1, f"{fc}_{jt}_{k}_ed"), md.new_bool_var(f"{fc}_{jt}_{k}_mk")]
                intervals[fc][jt][k] = md.new_optional_interval_var(sem[fc][jt][k][0], getattr(process, f"{fc}{jt}"), sem[fc][jt][k][1], sem[fc][jt][k][2], f"{fc}_{jt}_{k}_make")

                if k:
                    md.add(sem[fc][jt][k - 1][2] >= sem[fc][jt][k][2])
                    md.add(sem[fc][jt][k - 1][1] <= sem[fc][jt][k][0])

                for t in range(1, horizon):
                    se_event[fc][jt][k][t] = [md.new_bool_var(f"{fc}{jt}{k}_{when}_{t}") for when in ("start", "end","real_start","real_end")]
                    md.add(sem[fc][jt][k][0] == t).only_enforce_if(se_event[fc][jt][k][t][0])
                    md.add(sem[fc][jt][k][0] != t).only_enforce_if(se_event[fc][jt][k][t][0].Not())

                    md.add(sem[fc][jt][k][1] == t).only_enforce_if(se_event[fc][jt][k][t][1])
                    md.add(sem[fc][jt][k][1] != t).only_enforce_if(se_event[fc][jt][k][t][1].Not())

                    md.add_min_equality(se_event[fc][jt][k][t][2], [se_event[fc][jt][k][t][0], sem[fc][jt][k][2]])
                    md.add_min_equality(se_event[fc][jt][k][t][3], [se_event[fc][jt][k][t][1], sem[fc][jt][k][2]])

            md.add_no_overlap(intervals[fc][jt].values())

            if jt in boms:
                for ingredient in boms[jt].keys():
                    for t in range(1, horizon):
                        md.add(consumed[fc][jt][ingredient][t] == boms[jt][ingredient] * sum(se_event[fc][jt][k][t][2] for k in range(job_interval_horizon)))

            for t in range(1, horizon):
                md.add(produced[fc][jt][t] == 1 * sum(se_event[fc][jt][k][t][3] for k in range(job_interval_horizon)))

        if fc in ingredients:
            for ingredient in ingredients[fc]:
                use_this_ingredient_jt = [jt for jt in ini_set[fc].keys() if jt in boms and ingredient in boms[jt]]
                for t in range(1, horizon):
                    md.add(fc_wip_t[fc][ingredient][t - 1] + sum(delivered[fc][fc1][ingredient][t] for fc1 in delivered[fc].keys() if ingredient in delivered[fc][fc1]) >= sum(boms[jt][ingredient] * sum(se_event[fc][jt][k][t][2] for k in range(job_interval_horizon)) for jt in use_this_ingredient_jt))

    delivering = {}
    for fc in fc_deliver_to.keys():
        delivering[fc] = {}
        for jt in ini_set[fc].keys():
            delivering[fc][jt] = {}
            use_ingredient_fc, lot_units = [fc2 for fc2 in fc_deliver_to[fc] if jt in fc_deliver_to[fc][fc2]], ini_set[fc][jt]
            for t in range(1, horizon):
                delivering[fc][jt][t] = {fc_prime: {lot_unit: md.new_int_var(0, horizon // 10, f"{fc}_{jt}_{t}_deliver_to_{fc_prime}_{lot_unit}") for lot_unit in lot_units} for fc_prime in use_ingredient_fc}
                md.add(fc_wip_t[fc][jt][t - 1] + produced[fc][jt][t] - sum(consumed[fc][jt_prime][jt][t] for jt_prime in ini_set[fc].keys() if jt_prime in boms and jt in boms[jt_prime]) >= sum(delivering[fc][jt][t][fc_prime][lot_unit] * lot_unit for fc_prime in use_ingredient_fc for lot_unit in lot_units))

            for fc_prime in use_ingredient_fc:
                deliver_time = getattr(deliver, f"{fc}{fc_prime}")
                for t in range(1, horizon):
                    if t + deliver_time < horizon:
                        md.add(sum(delivering[fc][jt][t][fc_prime][lot_unit] * lot_unit for lot_unit in lot_units) == delivered[fc_prime][fc][jt][t + deliver_time])
                    else:
                        md.add(sum(delivering[fc][jt][t][fc_prime][lot_unit] * lot_unit for lot_unit in lot_units) == 0)
                for t in range(1, min(horizon, deliver_time + 1)):
                    md.add(delivered[fc_prime][fc][jt][t] == 0)

    plus, minus = {}, {}
    for fc in fc_wip_t.keys():
        plus[fc] = {}
        minus[fc] = {}

        for wip in fc_wip_t[fc].keys():
            plus[fc][wip] = {}
            minus[fc][wip] = {}

            for t in range(1, horizon):
                plus[fc][wip][t] = md.new_int_var(0, horizon // 10, f"{fc}_{wip}_{t}_plus")
                minus[fc][wip][t] = md.new_int_var(0, horizon // 10, f"{fc}_{wip}_{t}_minus")

                md.add(plus[fc][wip][t] == (produced[fc][wip][t] if wip in produced[fc] else 0) + (sum(delivered[fc][fc_prime][wip][t] for fc_prime in delivered[fc] if wip in delivered[fc][fc_prime]) if fc in delivered else 0))
                md.add(minus[fc][wip][t] == sum(consumed[fc][jt_prime][wip][t] for jt_prime in consumed[fc] if wip in consumed[fc][jt_prime]) + (sum(delivering[fc][wip][t][fc_prime][lot_unit] * lot_unit for lot_unit in ini_set[fc][wip] for fc_prime in fc_deliver_to[fc].keys() if wip in fc_deliver_to[fc][fc_prime]) if fc in delivering and wip in delivering[fc] else 0))
                md.add(fc_wip_t[fc][wip][t] == fc_wip_t[fc][wip][t - 1] + plus[fc][wip][t] - minus[fc][wip][t])

    every_final_product_max_set = {}
    for fc in ini_set.keys():
        if params["final_product"] in ini_set[fc]:
            every_final_product_max_set[fc] = md.new_int_var(0, params["amount"], f"{fc}_FP")
            md.add_max_equality(every_final_product_max_set[fc], fc_wip_t[fc][params["final_product"]].values())
    md.add(sum(every_final_product_max_set.values()) >= params["amount"])

    every_fc_num_job = {}
    for fc in ini_set.keys():
        every_fc_num_job[fc] = md.new_int_var(0, job_interval_horizon * len(ini_set[fc]), f"{fc}_total_job_num")
        md.add(every_fc_num_job[fc] == sum(sem[fc][jt][k][2] for k in range(job_interval_horizon) for jt in ini_set[fc]))

    total_makespan = md.new_int_var(0, horizon, "total_makespan")
    md.add_max_equality(total_makespan, [sem[fc][jt][k][1] for fc in sem.keys() for jt in sem[fc].keys() for k in range(job_interval_horizon)])

    md.minimize(9999 * total_makespan + sum(every_fc_num_job.values()))
    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        total_makespan = round(solver.ObjectiveValue())
        print("Total Makespan :", total_makespan, "\n")
    else:
        print("X")
    return

class Process:
    def __init__(self): pass
class Deliver:
    def __init__(self): pass
def start(boms, factories, deliveries, params):
    process, deliver, ini_set = Process(), Deliver(), {}
    for fc in factories.keys():
        ini_set[fc] = {}
        for jt in factories[fc].keys():
            ini_set[fc][jt] = factories[fc][jt]["lots"]
            setattr(process, f"{fc}{jt}", factories[fc][jt]["time"])
    for fc1 in deliveries.keys():
        for fc2 in deliveries[fc1].keys():
            setattr(deliver, f"{fc1}{fc2}", deliveries[fc1][fc2])
    lot_stream(process, deliver, boms, ini_set, params)


def main():

    params = {
        "tps": 8,
        "final_product": "JT12",
        "amount": 2,
        "horizon": 50,
    }

    boms = {
        "JT4": {
            "JT1": 2,
            "JT2": 1,
        },
        "JT5": {
            "JT1": 1,
        },
        "JT9": {
            "JT4": 1,
            "JT5": 1,
        },
        "JT12": {
            "JT9": 1,
            "JT5": 1,
        },
    }

    factories = {
        # 원재료 생산
        "Fc1": {
            "JT1": {"lots": [5, 10], "time": 1},
            "JT2": {"lots": [5, 10], "time": 1},
        },

        # 1차 가공
        "Fc2": {
            "JT4": {"lots": [2], "time": 2},
            "JT5": {"lots": [2], "time": 2},
        },

        # 2차 가공
        "Fc3": {
            "JT9": {"lots": [1], "time": 3},
        },

        # 최종 제품
        "Fc4": {
            "JT12": {"lots": [1], "time": 4},
        },
    }
    fcs = list(factories)
    random.seed(4233)
    deliveries = {fc1: {fc2 : random.randint(3, 8) if fc1 != fc2 else 1 for fc2 in fcs} for fc1 in fcs}
    start(boms, factories, deliveries, params)

if __name__ == "__main__":
    main()