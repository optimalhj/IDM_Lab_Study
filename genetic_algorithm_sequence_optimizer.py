from numpy import random as rd
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB

def select_pop(populations):
    indices = list(range(len(populations)))
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        return populations[min(rd.choice(indices, size=2, replace=False), key=lambda idx : populations[idx][1])]

    elif way_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(indices, size=rd.randint(3, max(4, int(len(populations)/2.5))), replace=False), key=lambda idx : populations[idx][1])]

    elif way_pop == 2:  # Linear ranking
        return populations[rd.choice(indices, size=1, p=[2 * i / (len(populations) * (len(populations) + 1)) for i in range(len(indices), 0 , -1)])[0]]

    else:  # Do not reach
        return 0

def objective(process, setup, ini_set, machines, seq, o_max, s_max, T, w):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    se_each = {}
    for jt in ini_set.keys():
        se_each[jt] = {}
        for job in ini_set[jt]["jobs"]:
            se_each[jt][job] = {}
            for op in ini_set[jt]["ops"]:
                se_each[jt][job][op] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                md.addConstrs(se_each[jt][job][op][i] >= 0 for i in range(2))
                md.addConstr(se_each[jt][job][op][1] == se_each[jt][job][op][0] + getattr(process, f"{jt}{op}"))
                if op != list(ini_set[jt]["ops"])[0]:
                    md.addConstr(se_each[jt][job][op][0] >= se_each[jt][job][list(ini_set[jt]["ops"])[list(ini_set[jt]["ops"]).index(op) - 1]][1])

    st_setup = {jt1: {op1: {jt2: {op2: md.addVar(vtype=GRB.CONTINUOUS) for op2 in ini_set[jt2]["ops"]} for jt2 in ini_set.keys()} for op1 in ini_set[jt1]["ops"]} for jt1 in ini_set.keys()}
    for m in machines:
        seq_m = [sche for sche in seq if sche[3] == m]
        for l in range(len(seq_m) - 1):
            jt, job, op, _ = seq_m[l]
            next_jt, next_job, next_op, _ = seq_m[l + 1]
            md.addConstr(st_setup[jt][op][next_jt][next_op] >= se_each[jt][job][op][1])
            md.addConstr(se_each[next_jt][next_job][next_op][0] >= st_setup[jt][op][next_jt][next_op] + getattr(setup, f"{jt}{op}{next_jt}{next_op}"))

    m_time = {}
    f_u, f_s, t_pm, t_sm = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(4)]
    for m in machines:
        m_time[m] = {}
        seq_m = [sche for sche in seq if sche[3] == m]
        for t in range(T):
            m_time[m][t] = {"p":{}, "s":{}}

            for jt, job, op, _ in seq_m:
                m_time[m][t]["p"][f"{jt}{job}{op}"] = [md.addVar(vtype=GRB.BINARY) for _ in range(3)]
                md.addConstr(sum(m_time[m][t]["p"][f"{jt}{job}{op}"]) == 1)

                md.addGenConstrIndicator(m_time[m][t]["p"][f"{jt}{job}{op}"][0], True, se_each[jt][job][op][0] >= t + 1)
                md.addGenConstrIndicator(m_time[m][t]["p"][f"{jt}{job}{op}"][1], True, se_each[jt][job][op][0] <= t)
                md.addGenConstrIndicator(m_time[m][t]["p"][f"{jt}{job}{op}"][1], True, se_each[jt][job][op][1] >= t + 1)
                md.addGenConstrIndicator(m_time[m][t]["p"][f"{jt}{job}{op}"][2], True, se_each[jt][job][op][1] <= t)
            md.addConstr(f_u == )

    return 0

def correct_procedure(process, setup, ini_set, machines, seq, o_max, s_max, t, w):
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
    return objective(process, setup, ini_set, machines, seq, o_max, s_max, t, w)

def graph_gen(final):

    plt.plot([f"Gen{i+1}" for i in range(len(final))], final)

    plt.xticks(rotation=45, fontsize=0.5)
    plt.title("Makespan of FJSP")

    plt.xlabel("Gen")
    plt.ylabel("Tardiness")

    plt.show()

def graph_makespan(process, setup, best, machines):
    seqs, makespan = best
    _, ax = plt.subplots()
    s_job, s_machine, m_tmp = {}, {}, {}
    for m in machines:
        ax.barh(m, 0, left=0)
        s_machine[m] = 0
        m_tmp[m] = []
    for jt, job, _, _ in seqs:
        if (jt, job) not in list(s_job):
            s_job[(jt, job)] = 0

    for jt, job, op, m in seqs:
        if len(m_tmp[m]) == 0:
            start_oper = max(s_job[(jt, job)], s_machine[m])
        else:
            prior_jt, prior_op = m_tmp[m]
            set_t = getattr(setup, f"{prior_jt}{prior_op}{jt}{op}")
            start_oper = max(s_job[(jt, job)], s_machine[m] + set_t)
            ax.barh(m, set_t, left=start_oper - set_t, color='white', edgecolor='black')
        m_tmp[m] = (jt, op)
        operating = getattr(process, f"{jt}{op}")
        ax.barh(m, operating, left=start_oper, color=plt.get_cmap('tab20', len(s_job))(list(s_job).index((jt,job))), edgecolor='black')
        ax.text(start_oper + operating / 2, m, f"{jt}\n{job}\n{op}\n({operating})", va='center', ha='center', color='black', fontsize=5)
        s_job[(jt, job)], s_machine[m] = [start_oper + operating for _ in range(2)]

    ax.set_xticks([i for i in range(int(makespan)+2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def ga(process, setup, ini_set, machines, params):
    history = []
    ini_pop = [(jt, job, op) for jt in ini_set.keys() for job in ini_set[jt]["jobs"] for op in ini_set[jt]["ops"]]

    pops = sorted([correct_procedure(process, setup, ini_set, machines, rd.permutation(ini_pop).tolist(), params["o_max"], params["s_max"], params["T"], params["w"])
                   for _ in range(params["pop_size"])] , key=lambda case:case[1])

    for gen in range(params["num_of_gens"]):
        mating_pool = [select_pop(pops) for _ in range(params["mating_pool"])]
        # for case in mating_pool:
        #     print("\t",case)
        indices = list(range(params["mating_pool"]))
        """
        for _ in range(len(mating_pool) // 2):
            mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            pops.append(second_stage(process, setup, ini_set, machines, mating_pool[mom][0], mating_pool[dad][0]))
        """
        for _ in range(params["num_offs"]):
            mom, dad = rd.choice(indices, size=2, replace=False)
            # pops.append(second_stage(process, setup, ini_set, machines, mating_pool[mom][0], mating_pool[dad][0]))

        pops = sorted(pops, key=lambda case:case[1])[:params["pop_size"]]
        # for case in pops:
        #     print(case[1], case[0])
        history.append(pops[0][1])

    graph_gen(history)
    graph_makespan(process, setup, pops[0], machines)
    print(history)


class Duration:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(processes, setups, machines_tmp, params):
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

    ga(process, setup, ini_set, machines, params)

def main():

    # Parameter Input
    num_jts ,max_num_job, max_num_op, num_machines, max_time = 3, 5, 4, 4, 9
    params = {"pop_size": 5, "num_of_gens": 10, "mating_pool": 100, "num_offs": 200, "o_max": 20, "s_max": 2, "T": 20, "w": 0.5}

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

    start(processes, setups, machines, params)

if __name__ == "__main__":
    main()