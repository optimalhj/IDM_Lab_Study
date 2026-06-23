from numpy import random as rd
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

# Parameter Input
num_jts ,max_num_job, max_num_op, num_machines, max_time = 3, 2, 3, 3, 9
params = {"pop_size": 5, "num_of_gens": 1, "mating_pool": 100, "num_offs": 200, "o_max": 20, "s_max": 2, "T": 20, "w": 0.5}

def select_pop(populations):
    indices = list(range(len(populations)))
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        chosen = populations[min(rd.choice(indices, size=2, replace=False), key=lambda idx: populations[idx][1])]
    elif way_pop == 1:  # n-Size tournament
        chosen = populations[min(rd.choice(indices, size=rd.randint(3, max(4, int(len(indices) / 2.5))), replace=False), key=lambda idx: populations[idx][1])]
    elif way_pop == 2:  # Linear ranking
        chosen = populations[rd.choice(indices, size=1, p=[2 * i / (len(indices) * (len(indices) + 1)) for i in range(len(indices), 0, -1)])[0]]
    else:  # Do not reach
        chosen = []
    return chosen

def choose_parents(mating_pool, way_pr_select):
    indices = list(range(len(mating_pool)))
    if way_pr_select == 0:
        mom, dad = rd.choice(indices, size=2, replace=False)
    elif way_pr_select == 1:
        mom, dad = 0, 1
    elif way_pr_select == 2:
        mom, dad = 0, 1
    elif way_pr_select == 3:
        mom, dad = 0, 1
    else:
        mom, dad = 0, 0
    return mom, dad

def objective(process, setup, ini_set, machines, seq):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    se_process = {}
    for jt in ini_set.keys():
        se_process[jt] = {}
        for job in ini_set[jt]["jobs"]:
            se_process[jt][job] = {}
            for op in ini_set[jt]["ops"]:
                se_process[jt][job][op] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                md.addConstrs(se_process[jt][job][op][i] >= 0 for i in range(2))
                md.addConstr(se_process[jt][job][op][1] == se_process[jt][job][op][0] + getattr(process, f"{jt}{op}"))
                if op != list(ini_set[jt]["ops"])[0]:
                    md.addConstr(se_process[jt][job][op][0] >= se_process[jt][job][list(ini_set[jt]["ops"])[list(ini_set[jt]["ops"]).index(op) - 1]][1])

    m_time = {}
    f_u, f_s, t_pm, t_sm = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(4)]
    se_setup = {}
    for m in machines:
        m_time[m], se_setup[m] = {"p":{},"s":{}}, {}
        seq_m = [sche for sche in seq if sche[3] == m]
        for l in range(len(seq_m) - 1):
            jt, job, op, _ = seq_m[l]
            next_jt, next_job, next_op, _ = seq_m[l + 1]
            se_setup[m][f"{l}{l+1}"] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)] + [(jt, op, next_jt, next_op)]
            md.addConstr(se_setup[m][f"{l}{l + 1}"][1] == se_setup[m][f"{l}{l + 1}"][0] + getattr(setup,f"{jt}{op}{next_jt}{next_op}"))
            md.addConstr(se_setup[m][f"{l}{l + 1}"][0] >= se_process[jt][job][op][1])
            md.addConstr(se_process[next_jt][next_job][next_op][0] >= se_setup[m][f"{l}{l + 1}"][1])

            m_time[m]["p"][l] = {}
            m_time[m]["s"][f"{l}{l+1}"] = {}
            for t in range(sum(getattr(process, f"{jt}{op}") for jt in ini_set.keys() for _ in range(len(ini_set[jt]["jobs"])) for op in ini_set[jt]["ops"])):
                m_time[m]["p"][l][t] = [md.addVar(vtype=GRB.BINARY) for _ in range(3)]
                md.addConstr(gp.quicksum(m_time[m]["p"][l][t]) == 1)
                md.addGenConstrIndicator(m_time[m]["p"][l][t][0], True, se_process[jt][job][op][0] >= t + 1)
                md.addGenConstrIndicator(m_time[m]["p"][l][t][1], True, se_process[jt][job][op][0] <= t)
                md.addGenConstrIndicator(m_time[m]["p"][l][t][1], True, se_process[jt][job][op][1] >= t + 1)
                md.addGenConstrIndicator(m_time[m]["p"][l][t][2], True, se_process[jt][job][op][1] <= t)

                m_time[m]["s"][f"{l}{l+1}"][t] = [md.addVar(vtype=GRB.BINARY) for _ in range(3)]
                md.addConstr(gp.quicksum(m_time[m]["s"][f"{l}{l+1}"][t]) == 1)
                md.addGenConstrIndicator(m_time[m]["s"][f"{l}{l+1}"][t][0], True, se_setup[m][f"{l}{l+1}"][0] >= t + 1)
                md.addGenConstrIndicator(m_time[m]["s"][f"{l}{l+1}"][t][1], True, se_setup[m][f"{l}{l+1}"][0] <= t)
                md.addGenConstrIndicator(m_time[m]["s"][f"{l}{l+1}"][t][1], True, se_setup[m][f"{l}{l+1}"][1] >= t + 1)
                md.addGenConstrIndicator(m_time[m]["s"][f"{l}{l+1}"][t][2], True, se_setup[m][f"{l}{l+1}"][1] <= t)

        if len(seq_m) >= 1:
            m_time[m]["p"][len(seq_m) - 1] = {}
            jt, job, op, _ = seq_m[-1]
            for t in range(sum(getattr(process, f"{jt}{op}") for jt in ini_set.keys() for _ in range(len(ini_set[jt]["jobs"])) for op in ini_set[jt]["ops"])):

                m_time[m]["p"][len(seq_m) - 1][t] = [md.addVar(vtype=GRB.BINARY) for _ in range(3)]
                md.addConstr(gp.quicksum(m_time[m]["p"][len(seq_m) - 1][t]) == 1)
                md.addGenConstrIndicator(m_time[m]["p"][len(seq_m) - 1][t][0], True, se_process[jt][job][op][0] >= t + 1)
                md.addGenConstrIndicator(m_time[m]["p"][len(seq_m) - 1][t][1], True, se_process[jt][job][op][0] <= t)
                md.addGenConstrIndicator(m_time[m]["p"][len(seq_m) - 1][t][1], True, se_process[jt][job][op][1] >= t + 1)
                md.addGenConstrIndicator(m_time[m]["p"][len(seq_m) - 1][t][2], True, se_process[jt][job][op][1] <= t)

    for t in range(sum(getattr(process, f"{jt}{op}") for jt in ini_set.keys() for _ in range(len(ini_set[jt]["jobs"])) for op in ini_set[jt]["ops"])):
        md.addConstr(sum(m_time[m]["s"][f"{l}{l+1}"][t][1] for m in machines for l in range(len([sche for sche in seq if sche[3] == m]) - 1)) <= params["s_max"])

    md.addConstr(f_u == gp.quicksum(m_time[m]["p"][l][t][1] for m in machines for l in range(len([sche for sche in seq if sche[3] == m])) for t in range(params["T"])) / params["T"] / len(machines))
    md.addConstr(f_s == gp.quicksum(m_time[m]["s"][f"{l}{l+1}"][t][1] for m in machines for l in range(len([sche for sche in seq if sche[3] == m]) - 1) for t in range(params["T"])) / params["T"] / len(machines))
    md.setObjective(params["w"] * f_u - (1 - params["w"]) * f_s, GRB.MAXIMIZE)
    md.optimize()

    se_process = {jt : {job : {op : [se_process[jt][job][op][i].X for i in range(2)] for op in ini_set[jt]["ops"]} for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    se_setup = {m:{f"{l}{l+1}" : [se_setup[m][f"{l}{l+1}"][i].X for i in range(2)] + [se_setup[m][f"{l}{l+1}"][2]] for l in range(len([sche for sche in seq if sche[3] == m]) - 1)} for m in machines}
    f_c = sum(1 for m in se_setup for place in se_setup[m] if se_setup[m][place][0] != se_setup[m][place][1])
    f_i = 1 - f_u.X - f_s.X
    m_load = {m : sum(getattr(process, f"{jt}{op}") for jt, _, op, m_tmp in seq if m_tmp == m) for m in machines}
    for m in machines:
        if m_load[m] == 0: m_load.pop(m)
    print("Machine Loads :", m_load)
    f_b = max(m_load.values()) / min(m_load.values()) - 1
    return seq, (md.ObjVal, f_u.X, f_s.X, f_c, f_i, f_b), se_process, se_setup

def crossing(points, pr1, pr2, apx=True):
    print("\n               Before                         -->                     After")
    for idx in points:

        print(pr1[idx], end="    /   ")
        jt1, job1, op1, _ = pr1[idx]
        for jt2, job2, op2, m in pr2:
            if jt1 == jt2 and job1 == job2 and op1 == op2:
                if apx:
                    pr1[idx] = (jt1, job1, op1, m)
                print(pr1[idx])
                pr2.remove((jt2, job2, op2, m))
                break

    print(f"\n\tpr1 : ({len(points)})", [pr1[i] for i in points])
    print(f"\tpr2 : ({len(pr2)})", pr2)
    return [pr1[i] if i in points else pr2.pop(0) for i in range(len(pr1))]

def crossover(process, setup, ini_set, machines, pr1, pr2):
    way_cross = rd.randint(4)
    way_cross = 0
    points = []

    print(f"pr1 : ({len(pr1)})", pr1)
    print(f"pr2 : ({len(pr2)})", pr2)

    if way_cross == 0: #CR1
        chosen_jt = rd.choice(list(ini_set))
        print("\t", chosen_jt, end="  /  ")
        for idx in range(len(pr1)):
            if pr1[idx][0] == chosen_jt:
                points.append(idx)
        print("points :", points)
        child = crossing(points, pr1, pr2, apx=False)
    elif way_cross == 1: #CR2
        child = []
    else: # Do not reach
        child = []
    print(f"\nchd : ({len(child)})", child)
    print("-"*50)

    return objective(process, setup, ini_set, machines, child)

def correct_procedure(process, setup, ini_set, machines, seq):
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
        seq[i] = (jt, using_job, op, rd.choice(ini_set[jt]["ops"][op]))
    return objective(process, setup, ini_set, machines, seq)

def graph_gen(final):

    plt.plot([f"Gen{i+1}" for i in range(len(final))], final)

    plt.xticks(rotation=45, fontsize=0.5)
    plt.title("Objective of FJSP")

    plt.xlabel("Gen")
    plt.ylabel("Objective")

    plt.show()

def graph_makespan(best, machines):
    seq, obj, se_process, se_setup = best
    _, ax = plt.subplots()
    s_job, s_machine, m_tmp = [(jt, job) for jt in se_process.keys() for job in se_process[jt].keys()], {}, {}
    for m in machines:
        ax.barh(m, 0, left=0)
        s_machine[m] = 0
        m_tmp[m] = []

    for l in range(len(seq)):
        jt, job, op, m = seq[l]
        operating = se_process[jt][job][op][1] - se_process[jt][job][op][0]
        start_process = se_process[jt][job][op][0]
        ax.barh(m, operating, left=start_process, color=plt.get_cmap('tab20', len(s_job))(list(s_job).index((jt, job))), edgecolor='black')
        ax.text(start_process + operating / 2, m, f"{jt}\n{job}\n{op}\n({operating})", va='center', ha='center', color='black', fontsize=5)

    for m in se_setup.keys():
        for st_setup, ed_setup, sets in se_setup[m].values():
            setup_ing = ed_setup - st_setup
            if round(setup_ing) != 0:
                ax.barh(m, setup_ing, left=st_setup, color='white', edgecolor='black')
    ax.set_xticks([i for i in range(int(max(se_process[jt][job][op][1] for jt in se_process.keys() for job in se_process[jt] for op in se_process[jt][job]))+2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def ga(process, setup, ini_set, machines):
    history = []
    ini_pop = [(jt, job, op) for jt in ini_set.keys() for job in ini_set[jt]["jobs"] for op in ini_set[jt]["ops"]]
    pops = sorted([correct_procedure(process, setup, ini_set, machines, rd.permutation(ini_pop).tolist()) for _ in range(params["pop_size"])], key=lambda case:-case[1][0])
    cr = 1
    for gen in range(params["num_of_gens"]):
        mating_pool = [select_pop(pops) for _ in range(params["mating_pool"])]
        offsprings = []
        """
        for _ in range(len(mating_pool) // 2):
            mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            pops.append(second_stage(process, setup, ini_set, machines, mating_pool[mom][0], mating_pool[dad][0]))
        """
        for _ in range(params["num_offs"]):
            mom, dad = choose_parents(mating_pool, cr)
            offsprings.append(crossover(process, setup, ini_set, machines, mating_pool[mom][0].copy(), mating_pool[dad][0].copy()))
        offsprings.sort(key=lambda offs:offs[1][0])

        # seq, (md.ObjVal, f_u.X, f_s.X, f_c, f_i, f_b), se_process, se_setup
        print(offsprings)
        print(offsprings[0][1][0])
        if offsprings[0][1][0] < pops[0][1][0]:
            cr = 1
            pops = sorted(pops + offsprings, key=lambda case: (-case[1][0], -case[1][1]))[:params["pop_size"]]
        elif offsprings[0][1][3] >= pops[0][1][3]:
            cr = 2
        elif offsprings[0][1][5] > pops[0][1][5]:
            cr = 3
        elif offsprings[0][1][4] > pops[0][1][4]:
            cr = 4
        else:
            cr = 1


        # for case in pops:
        #     print(case[1], case[0])
        history.append(pops[0][1][0])

    graph_gen(history)
    graph_makespan(pops[0], machines)

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

    ga(process, setup, ini_set, machines)

def main():

    jts = [f"Job_Type{i}" for i in range(1, num_jts + 1)]
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {jt : {"jobs":[f"Job{j+1}" for j in range(rd.randint(2,max_num_job+1))], "ops":{f"Op{o+1}" : [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False),key=lambda machine: machines.index(machine)),rd.randint(2, max_num_op + 1)] for o in range(rd.randint(1, max_num_op + 1))}} for jt in jts}

    op_types = [(jt, op) for jt in jts for op in processes[jt]["ops"]]
    setups = {op1:{op2:0 if op1[0] == op2[0] else rd.randint(1, max(max_time//2, 1) + 1) for op2 in op_types} for op1 in op_types}

    for jt in processes.keys():
        print(jt)
        for job in processes[jt]:
            print("\t", end="")
            print(job)
            print("\t", end="")
            print(processes[jt][job])
        print()

    for op1 in setups.keys():
        print(op1," -> ", end="")
        for op2 in setups[op1]:
            if setups[op1][op2] != 0:
                print(f"{op2}({setups[op1][op2]})", end=" / ")
        print()

    print("\n-----------------------------------------------------------------------------------------------------")

    start(processes, setups, machines)

if __name__ == "__main__":
    main()