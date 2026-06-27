from numpy import random as rd

# Parameter Input
num_jts ,max_num_job, max_num_op, num_machines, max_time = 4, 5, 5, 7, 9
params = {"pop_size": 5, "num_of_gens": 20, "mating_pool": 20, "num_offs": 10, "s_max": 2, "T": 20, "w": 0.5, "K": 0.25}

def correct_procedure(ini_set, seq):
    info_op = {jt : {job : {op : 0 for op in ini_set[jt]["ops"]} for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    info_job = {jt: {op: {job: 0 for job in ini_set[jt]["jobs"]} for op in ini_set[jt]["ops"]} for jt in ini_set.keys()}
    for i in range(len(seq)):
        jt, job, _ = seq[i]
        using_op = min(ini_set[jt]["ops"], key=lambda op: info_op[jt][job][op])
        info_op[jt][job][using_op] += 1
        seq[i] = (jt, using_op)
    for i in range(len(seq)):
        jt, op = seq[i]
        using_job = min(ini_set[jt]["jobs"], key=lambda job: info_job[jt][op][job])
        info_job[jt][op][using_job] += 1
        seq[i] = (jt, using_job, op)
    return seq

def first_stage(process, setup, ini_set, machines, seq):
    ops_machine, st_machine, p_tot, s_tot = {}, {}, 0, 0
    for m in machines:
        ops_machine[m], st_machine[m] = [], 0
    st_job = {jt : {job : 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    for l in range(len(seq)):
        jt, job, op = seq[l]
        eligible_m, now = ini_set[jt]["ops"][op], []
        for m in eligible_m:
            if len(ops_machine[m]) == 0:
                now.append(max(st_machine[m], st_job[jt][job]))
            else:
                now.append(max(st_machine[m] + getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}"), st_job[jt][job]))
                s_tot += getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}")
        select_m = eligible_m[now.index(min(now))]
        ops_machine[select_m] = (jt, op)
        st_machine[select_m], st_job[jt][job] = [now[eligible_m.index(select_m)] + getattr(process, f"{jt}{op}") for _ in range(2)]
        p_tot += getattr(process, f"{jt}{op}")
        seq[l] = (jt, job, op, select_m)
    alt = (sum(st_machine[m] for m in machines) - p_tot) / len(machines)
    awt = (sum(st_job[jt][job] for jt in ini_set.keys() for job in ini_set[jt]["jobs"]) - p_tot - s_tot) / sum(len(ini_set[jt]["jobs"]) for jt in ini_set.keys())
    return seq, params["w"] * alt + (1 - params["w"]) * awt

def second_stage(process, setup, ini_set, machines, seq, pr2):
    way_cross = rd.randint(2)
    if way_cross == 0:  # SCO : Single-Point Crossover Operator
        seq = crossover([i for i in range(rd.randint(1, len(seq)))], seq, pr2)

    elif way_cross == 1:  # JCO : Job(Job Type) Crossover Operator
        seq = crossover([l for l in range(len(seq)) if seq[l][0] in rd.choice(list(ini_set), size=1)], seq, pr2)

    elif way_cross == 2:  # ACO : Assignment Crossover
        for l in range(len(seq)):
            jt_1, job_1, op_1 = seq[l][0], seq[l][1], seq[l][2]
            for jt_2, job_2, op_2, m_2 in pr2:
                if jt_1 == jt_2 and job_1 == job_2 and op_1 == op_2:
                    seq[l] = (jt_1, job_1, op_1, m_2)
                    break
    else:  # Do not reach
        seq = 0

    way_mutation = rd.randint(2)
    if way_mutation == 0: # OSM : Operation Swaping Mutation
        idx1, idx2 = 0, 0
        while seq[idx1][1] == seq[idx2][1] and seq[idx1][0] == seq[idx2][0]:
            idx1 = rd.randint(len(seq) - 1)
            idx2 = idx1 + 1
        seq[idx1], seq[idx2] = seq[idx2], seq[idx1]

    elif way_mutation == 1: # AAM : Assignment Altering Mutation
        idx = rd.randint(len(seq))
        jt, job, op, m_tmp = seq[idx]
        eligible_m = ini_set[jt]["ops"][op]
        if len(eligible_m) > 1:
            select_m = m_tmp
            while select_m == m_tmp:
                select_m = rd.choice(eligible_m)
            seq[idx] = (jt, job, op, select_m)
    else:  # Do not reach
        seq = 0

    ops_machine, st_machine, p_tot, s_tot = {}, {}, 0, 0
    for m in machines:
        ops_machine[m] = []
        st_machine[m] = 0
    st_job = {jt: {job: 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    for l in range(len(seq)):
        jt, job, op, m = seq[l]
        if len(ops_machine[m]) == 0:
            now = max(st_machine[m], st_job[jt][job])
        else:
            now = max(st_machine[m] + getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}"), st_job[jt][job])
            s_tot += getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}")
        ops_machine[m] = (jt, op)
        st_machine[m], st_job[jt][job] = [now + getattr(process, f"{jt}{op}") for _ in range(2)]
        p_tot += getattr(process, f"{jt}{op}")

    alt = (sum(st_machine[m] for m in machines) - p_tot) / len(machines)
    awt = (sum(st_job[jt][job] for jt in ini_set.keys() for job in ini_set[jt]["jobs"]) - p_tot - s_tot) / sum(len(ini_set[jt]["jobs"]) for jt in ini_set.keys())
    return seq, params["w"] * alt + (1 - params["w"]) * awt

def generate_case(process, setup, ini_set, machines):
    history = []
    ini_pop = [(jt, job, op) for jt in ini_set.keys() for job in ini_set[jt]["jobs"] for op in ini_set[jt]["ops"]]
    pops = sorted([first_stage(process, setup, ini_set, machines, correct_procedure(ini_set, rd.permutation(ini_pop).tolist())) for _ in range(params["pop_size"])], key=lambda case: case[1])

    for gen in range(1, params["num_of_gens"] + 1):
        mating_pool = [select_pop(pops) for _ in range(params["mating_pool"])]
        indices = list(range(params["mating_pool"]))
        for _ in range(params["num_offs"]):
            mom, dad = rd.choice(indices, size=2, replace=False)
            pops.append(second_stage(process, setup, ini_set, machines, mating_pool[mom].copy(), mating_pool[dad].copy(), params["w"]))
        pops = sorted(pops, key=lambda case: case[1])[:params["pop_size"]]

        history.append(pops[0][1])
    return pops

class Duration:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(processes, setups, machines_tmp):
    process, setup, ini_set, machines = Duration(), SetUp(), {}, []

    for jt in processes.keys():
        ini_set[jt] = {"jobs": processes[jt]["jobs"], "ops": {}}
        for op in processes[jt]["ops"]:
            ms,processing_time = processes[jt]["ops"][op]
            ini_set[jt]["ops"][op] = ms
            for m in ms:
                if m not in machines:
                    machines.append(m)
            setattr(process, f"{jt}{op}", processing_time)
    machines.sort(key=lambda machine: machines_tmp.index(machine))

    for op_type1 in setups:
        for op_type2 in setups:
            (jt1, op1), (jt2, op2) = op_type1, op_type2
            setattr(setup, f"{jt1}{op1}{jt2}{op2}", setups[(jt1, op1)][(jt2, op2)])
    generate_case(process, setup, ini_set, machines)

def main():

    jts = [f"Job_Type{i}" for i in range(1, num_jts + 1)]
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {jt : {"jobs":[f"Job{j+1}" for j in range(rd.randint(2,max_num_job+1))], "ops":{f"Op{o+1}" : [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False),key=lambda machine: machines.index(machine)),rd.randint(2, max_num_op + 1)] for o in range(rd.randint(1, max_num_op + 1))}} for jt in jts}

    op_types = [(jt, op) for jt in jts for op in processes[jt]["ops"]]
    setups = {op1:{op2:0 if op1[0] == op2[0] else rd.randint(1, max(max_time//2, 1) + 1) for op2 in op_types} for op1 in op_types}

    for jt in processes.keys():
        print(jt)
        for job in processes[jt]:
            print(f"\t{job}")
            print(f"\t{processes[jt][job]}")
        print()

    for op1 in setups.keys():
        print(op1," -> ", end="")
        for op2 in setups[op1]:
            if setups[op1][op2] != 0:
                print(f"{op2}({setups[op1][op2]})", end=" / ")
        print()

    print("\n-----------------------------------------------------------------------------------------------------")

    start(processes, setups, machines)

if __name__ == '__main__':
    main()