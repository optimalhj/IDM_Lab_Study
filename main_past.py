import random
from ortools.sat.python import cp_model

def lot_stream(process, deliver, boms, ini_set, params):
    horizon = params["horizon"]
    job_interval_horizon = params["horizon"]

    md = cp_model.CpModel()

    fc_wip_t, ingredients = {}, {}
    for fc in ini_set.keys():
        fc_wip_t[fc] = {}
        for jt in ini_set[fc].keys():
            fc_wip_t[fc][jt] = {}
            if jt in boms:
                for ingredient in boms[jt]:
                    if ingredient not in fc_wip_t[fc]: fc_wip_t[fc][ingredient] = {}
                    if fc not in ingredients: ingredients[fc] = set()
                    ingredients[fc].add(ingredient)

        for wip in fc_wip_t[fc].keys():
            fc_wip_t[fc][wip][0] = 0
            for t in range(1, horizon):
                fc_wip_t[fc][wip][t] = md.new_int_var(0, horizon, f"{fc}_{wip}_{t}")

    delivered = {}
    for fc in ini_set.keys():
        delivered[fc] = {}
        for jt in ini_set[fc].keys():
            if jt in boms:
                for ingredient in boms[jt]:
                    make_ingredient_fc = [fc_prime for fc_prime in ini_set.keys() if ingredient in ini_set[fc_prime]]
                    delivered[fc][ingredient] = {fc_prime: {t: md.new_int_var(0, horizon, f"{fc}_{ingredient}_{t}_delivered") for t in range(1, horizon)} for fc_prime in make_ingredient_fc}


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
                    md.add(fc_wip_t[fc][ingredient][t - 1] + sum(delivered[fc][ingredient][fc_prime][t] for fc_prime in ini_set.keys() if ingredient in ini_set[fc_prime]) >= sum(boms[jt][ingredient] * sum(se_event[fc][jt][k][t][2] for k in range(job_interval_horizon)) for jt in use_this_ingredient_jt))

    delivering = {}
    for fc in ini_set.keys():
        delivering[fc] = {}
        for jt in ini_set[fc].keys():
            delivering[fc][jt] = {}
            use_ingredient_fc, lot_units = set([fc_prime for fc_prime in ini_set.keys() for jt_prime in ini_set[fc_prime] if jt_prime in boms and jt in boms[jt_prime]]), ini_set[fc][jt]
            for t in range(1, horizon):
                delivering[fc][jt][t] = {}
                for fc_prime in use_ingredient_fc:
                    delivering[fc][jt][t][fc_prime] = {}
                    for lot_unit in lot_units:
                        delivering[fc][jt][t][fc_prime][lot_unit] = md.new_int_var(0, horizon // 10, f"{fc}_{jt}_{t}_deliver_to_{fc_prime}_{lot_unit}")
                md.add(fc_wip_t[fc][jt][t - 1] + produced[fc][jt][t] - sum(consumed[fc][jt_prime][jt][t] for jt_prime in ini_set[fc].keys() if jt_prime in boms and jt in boms[jt_prime])>= sum(delivering[fc][jt][t][fc_prime][lot_unit] * lot_unit for fc_prime in use_ingredient_fc for lot_unit in lot_units))

            for fc_prime in use_ingredient_fc:
                deliver_time = getattr(deliver, f"{fc}{fc_prime}")
                for t in range(1, horizon):
                    if t + deliver_time < horizon:
                        md.add(sum(delivering[fc][jt][t][fc_prime][lot_unit] * lot_unit for lot_unit in lot_units) == delivered[fc_prime][jt][fc][t + deliver_time])
                    else:
                        md.add(sum(delivering[fc][jt][t][fc_prime][lot_unit] * lot_unit for lot_unit in lot_units) == 0)
                for t in range(1, min(horizon, deliver_time + 1)):
                    md.add(delivered[fc_prime][jt][fc][t] == 0)

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

                md.add(plus[fc][wip][t] == (produced[fc][wip][t] if wip in produced[fc] else 0) + (sum(delivered[fc][wip][fc_prime][t] for fc_prime in delivered[fc][wip]) if wip in delivered[fc] else 0))
                md.add(minus[fc][wip][t] == sum(consumed[fc][jt_prime][wip][t] for jt_prime in consumed[fc] if wip in consumed[fc][jt_prime]) + (sum(delivering[fc][wip][t][fc_prime][lot_unit] * lot_unit for fc_prime in delivering[fc][wip][t].keys() for lot_unit in delivering[fc][wip][t][fc_prime].keys()) if wip in delivering[fc] and t in delivering[fc][wip] else 0))
                md.add(fc_wip_t[fc][wip][t] == fc_wip_t[fc][wip][t - 1] + plus[fc][wip][t] - minus[fc][wip][t])

    every_final_product_max_set = {}
    for fc in ini_set.keys():
        if params["final_product"] in ini_set[fc]:
            every_final_product_max_set[fc] = md.new_int_var(0, params["amount"], f"{fc}_FP")
            md.add_max_equality(every_final_product_max_set[fc], fc_wip_t[fc][params["final_product"]].values())
    print("BottleNeck1")
    md.add(sum(every_final_product_max_set.values()) >= params["amount"])
    total_makespan = md.new_int_var(0, horizon, "total_makespan")
    md.add_max_equality(total_makespan, [sem[fc][jt][k][1] for fc in sem.keys() for jt in sem[fc].keys() for k in range(job_interval_horizon)])
    md.minimize(total_makespan)
    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("O")
        for fc in fc_wip_t.keys():
            print(fc)
            for wip in fc_wip_t[fc].keys():
                print(wip)
                print([fc_wip_t[fc][wip][t] for t in range(horizon)])
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
        "horizon": 100,
    }
    # boms = {
    #     "JT12": {"JT8": 2, "JT10": 2, "JT11": 1},
    #     "JT11": {"JT5": 2, "JT7": 4, "JT9": 2},
    #     "JT10": {"JT4": 6, "JT8": 4, "JT9": 2},
    #     "JT9": {"JT4": 3, "JT5": 2, "JT6": 1},
    #     "JT8": {"JT5": 1, "JT6": 1, "JT7": 1},
    #     "JT7": {"JT1": 4, "JT2": 3, "JT3": 3},
    #     "JT6": {"JT2": 5, "JT4": 2, "JT5": 1},
    #     "JT5": {"JT1": 6, "JT3": 5},
    #     "JT4": {"JT1": 5, "JT3": 6}
    #     }
    #
    # factories = {"Fc1": {'JT4': {"lots": [5], "time": 2}, 'JT11': {"lots": [1], "time": 5}},
    #              "Fc2": {'JT9': {"lots": [3], "time": 4}},
    #              "Fc3": {'JT7': {"lots": [5], "time": 4}, 'JT8': {"lots": [5], "time": 4}},
    #              "Fc4": {'JT1': {"lots": [20, 40], "time": 1}, 'JT2': {"lots": [20, 30], "time": 1}},
    #              "Fc5": {'JT5': {"lots": [5, 10], "time": 3}, 'JT6': {"lots": [6, 8, 10], "time": 3}, 'JT9': {"lots": [2], "time": 3}},
    #              "Fc6": {'JT7': {"lots": [3], "time": 4}, 'JT9': {"lots": [2], "time": 4}, "JT11": {"lots": [1], "time": 4}},
    #              "Fc7": {'JT2': {"lots": [7], "time": 1}, 'JT3': {"lots": [10], "time": 2}, 'JT4': {"lots": [2], "time": 3}},
    #              "Fc8": {'JT5': {"lots": [5], "time": 4}, 'JT12': {"lots": [1], "time": 5}},
    #              "Fc9": {'JT3': {"lots": [4, 8, 10], "time": 1}, 'JT6': {"lots": [4], "time": 3}, 'JT10': {"lots": [1], "time": 4}}}
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