import random
from ortools.sat.python import cp_model

def lot_stream(process, deliver, boms, ini_set, params):
    horizon = params["horizon"]

    md = cp_model.CpModel()

    factory_num_jobs, product_property, ingredient_property, making_t, lot_assigned = {}, {}, {}, {}, {}
    intervals, sts, eds, mks = {}, {}, {}, {}
    for fc in ini_set.keys():
        factory_num_jobs[fc], product_property[fc], ingredient_property[fc], making_t[fc], lot_assigned[fc] = {}, {}, {}, {}, {}
        intervals[fc], sts[fc], eds[fc], mks[fc] = {}, {}, {}, {}
        for jt in ini_set[fc].keys():
            factory_num_jobs[fc][jt], product_property[fc][jt], making_t[fc][jt], lot_assigned[fc][jt] = md.new_int_var(0, horizon, f"{fc}_{jt}"), {}, {}, {lot_unit: {} for lot_unit in ini_set[fc][jt] + ["Not_Assigned"]}
            for t in range(horizon):
                product_property[fc][jt][t] = md.new_int_var(0, horizon, f"{fc}_{jt}_{t}_product")
                making_t[fc][jt][t] = md.new_bool_var(f"{fc}_{jt}_{t}")
                for lot_unit in lot_assigned[fc][jt].keys():
                    lot_assigned[fc][jt][lot_unit][t] = md.new_int_var(0, horizon, f"{fc}_{jt}_{t}_{lot_unit}")
            if jt in boms:
                ingredient_property[fc][jt] = {ingredient: {t: md.new_int_var(0, horizon, f"{fc}_{ingredient}_{t}_for_{jt}") for t in range(horizon)} for ingredient in boms[jt]}

            intervals[fc][jt], sts[fc][jt], eds[fc][jt], mks[fc][jt] = [], [], [], []

            for k in range(horizon//10):
                st, ed, mk = md.new_int_var(0, horizon, f"{fc}_{jt}_{k + 1}_sts"), md.new_int_var(0, horizon, f"{fc}_{jt}_{k + 1}_eds"), md.new_bool_var(f"{fc}_{jt}_{k + 1}th_mks")
                for t_start in range(horizon - getattr(process, f"{fc}{jt}")):
                    start_match = md.new_bool_var(f"{fc}_{jt}_{k + 1}_{t_start}start_match")
                    md.add(st == t_start).only_enforce_if(start_match)
                    md.add(st != t_start).only_enforce_if(start_match.Not())
                    for t_doing in range(getattr(process, f"{fc}{jt}")):
                        md.add(making_t[fc][jt][t_start + t_doing] == 1).only_enforce_if([mk, start_match])

                sts[fc][jt].append(st)
                eds[fc][jt].append(ed)
                mks[fc][jt].append(mk)
                intervals[fc][jt].append(md.new_optional_interval_var(st, getattr(process, f"{fc}{jt}"), ed, mk, f"{fc}_{jt}_{k + 1}th_mks"))
                if k:
                    md.add(eds[fc][jt][k-1] <= sts[fc][jt][k])
                    md.add(mks[fc][jt][k-1] >= mks[fc][jt][k])
            md.add_no_overlap(intervals[fc][jt])
            md.add(sum(mks[fc][jt]) == factory_num_jobs[fc][jt])

            for t in range(horizon):
                produce = md.new_int_var(0, horizon, f"produce{fc}{jt}{t}")
                consume = md.new_int_var(0, horizon, f"consume{fc}{jt}{t}")
                if t:
                    md.add(product_property[fc][jt][t] == product_property[fc][jt][t - 1] + produce - consume)
                else: md.add(product_property[fc][jt][t] == 0)

                if jt in boms:
                    ingredient_ready = {}
                    for ingredient in boms[jt]:
                        ingredient_ready[ingredient] = md.new_bool_var(f"ready_to_make_{ingredient}")
                        md.add(ingredient_property[fc][jt][ingredient][t] >= boms[jt][ingredient]).only_enforce_if(ingredient_ready[ingredient])
                        md.add(ingredient_property[fc][jt][ingredient][t] < boms[jt][ingredient]).only_enforce_if(ingredient_ready[ingredient].Not())
                    md.add(sum(ingredient_ready.values()) < len(ingredient_ready)).only_enforce_if(making_t[fc][jt][t].Not())


    total_makespan = md.new_int_var(0, horizon, "total_makespan")
    md.add_max_equality(total_makespan, [ed for fc in ini_set.keys() for jt in ini_set[fc].keys() for ed in eds[fc][jt]])
    md.minimize(total_makespan)

    solver = cp_model.CpSolver()
    status = solver.Solve(md)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("O")
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
    # num_job_types, max_num_job, max_num_op, num_machines, max_time = 12, 10, 5, 16, 9
    # num_factories = 10
    # params = {"num_of_gens": 5, "s_max": 2, "Np1": 10, "Np2": 20}
    #
    # processes = {f"JT{jt}": {"jobs": random.randint(1, max_num_job), "ops": {f"Op{op}": random.randint(1, max_time) for op in range(1, random.randint(1, max_num_op) + 1)}} for jt in range(1, num_job_types + 1)}
    #
    # for jt in processes.keys():
    #     print("Job Type:", jt, f"/ {processes[jt]["jobs"]} jobs")
    #     for op in processes[jt]["ops"].keys():
    #         print(f"\t{op}: {processes[jt]["ops"][op]}")
    # print()
    #
    # op_types = [(jt, op) for jt in processes.keys() for op in processes[jt]["ops"].keys()]
    # machines = {f"M{m}": random.sample(op_types, k=random.randint(1, 4)) for m in range(1, num_machines + 1)}
    #
    # added_op_types = []
    # for op_type_set in machines.values():
    #     for op_type in op_type_set:
    #         if op_type not in added_op_types:
    #             added_op_types.append(op_type)
    #
    # for op_type in op_types:
    #     if op_type not in added_op_types:
    #         for m in random.sample(list(machines), k=random.randint(1, 2)):
    #             machines[m].append(op_type)
    #
    # for m in machines.keys():
    #     machines[m].sort(key=lambda opt: op_types.index(opt))
    #     print(f"{m} works {machines[m]}")
    # print()
    #
    # factories = {f"Fc{fc}": random.sample(list(machines), k=random.randint(1, 6)) for fc in range(1, num_factories + 1)}
    # added_machines = []
    # for ms in factories.values():
    #     for m in ms:
    #         if m not in added_machines: added_machines.append(m)
    # for m in machines.keys():
    #     if m not in added_machines:
    #         for fc in random.sample(list(factories), k=random.randint(1, 2)):
    #             factories[fc].append(m)
    # for fc in factories.keys():
    #     factories[fc].sort(key=lambda m: list(machines).index(m))
    #     print(f"{fc} has {factories[fc]}")
    #
    # setups = {}
    # for jt1, op1 in added_op_types:
    #     if jt1 not in setups:
    #         setups[jt1] = {}
    #     if op1 not in setups[jt1]:
    #         setups[jt1][op1] = {}
    #     for jt2, op2 in added_op_types:
    #         if jt2 not in setups[jt1][op1]:
    #             setups[jt1][op1][jt2] = {}
    #         setups[jt1][op1][jt2][op2] = 0 if jt1 == jt2 else random.randint(1, max_time//2 + 1)
    #
    # boms = {}

    params = {"tps": 8, "final_product": "JT12", "amount": 1, "horizon": 1000}

    # processes = [f"JT{jt}" for jt in range(1, num_job_types + 1)]
    boms = {"JT12": {"JT9": 2, "JT10": 2, "JT11": 1},
            "JT11": {"JT5": 2, "JT7": 4, "JT9": 2},
            "JT10": {"JT4": 6, "JT6": 4, "JT9": 2},
            "JT9": {"JT8": 3, "JT10": 2, "JT11": 1},
            "JT8": {"JT5": 1, "JT6": 1, "JT7": 1},
            "JT7": {"JT1": 8, "JT2": 10, "JT3": 18},
            "JT6": {"JT2": 5, "JT4": 2, "JT5": 1},
            "JT5": {"JT1": 6, "JT3": 5},
            "JT4": {"JT1": 5, "JT3": 6}}
    # factories = {f"Fc{fc}": random.sample(processes, k=random.randint(1, 3)) for fc in range(1, num_factories + 1)}
    # added_jts = []
    # for jts in factories.values():
    #     for jt in jts:
    #         if jt not in added_jts: added_jts.append(jt)
    # for jt in processes:
    #     if jt not in added_jts:
    #         for fc in random.sample(list(factories), k=random.randint(1, 2)):
    #             factories[fc].append(jt)
    # for fc in factories.keys():
    #     factories[fc].sort(key=lambda jt: processes.index(jt))
    #     print(f"{fc} works {factories[fc]}")
    factories = {"Fc1": {'JT4': {"lots": [5], "time": 2}, 'JT11': {"lots": [1], "time": 5}},
                 "Fc2": {'JT9': {"lots": [3], "time": 4}},
                 "Fc3": {'JT7': {"lots": [5], "time": 4}, 'JT8': {"lots": [5], "time": 4}},
                 "Fc4": {'JT1': {"lots": [20, 40], "time": 1}, 'JT2': {"lots": [20, 30], "time": 1}},
                 "Fc5": {'JT5': {"lots": [5, 10], "time": 3}, 'JT6': {"lots": [6, 8, 10], "time": 3}, 'JT9': {"lots": [2], "time": 3}},
                 "Fc6": {'JT7': {"lots": [3], "time": 4}, 'JT9': {"lots": [2], "time": 4}, "JT11": {"lots": [1], "time": 4}},
                 "Fc7": {'JT2': {"lots": [7], "time": 1}, 'JT3': {"lots": [10], "time": 2}, 'JT4': {"lots": [2], "time": 3}},
                 "Fc8": {'JT5': {"lots": [5], "time": 4}, 'JT12': {"lots": [1], "time": 5}},
                 "Fc9": {'JT3': {"lots": [4, 8, 10], "time": 1}, 'JT6': {"lots": [4], "time": 3}, 'JT10': {"lots": [1], "time": 4}}}

    fcs = list(factories)
    random.seed(4233)
    deliveries = {fc1: {fc2 : random.randint(1, 5) if fc1 != fc2 else 0 for fc2 in fcs } for fc1 in fcs}
    print("-----------------------------------------------------------------------------------------------------")
    start(boms, factories, deliveries, params)

if __name__ == "__main__":
    main()