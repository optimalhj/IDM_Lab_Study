from numpy import random as rd
import matplotlib.pyplot as plt

def select_pop(populations):
    indices = list(range(len(populations)))
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        return populations[min(rd.choice(indices, size=2, replace=False), key=lambda idx : populations[idx][1])]

    elif way_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(indices, size=rd.randint(3, max(4, int(len(indices)/2.5))), replace=False), key=lambda idx : populations[idx][1])]

    elif way_pop == 2:  # Linear ranking
        return populations[rd.choice(indices, size=1, p=[2 * i / (len(indices) * (len(indices) + 1)) for i in range(len(indices), 0 , -1)])[0]]

    else:  # Do not reach
        return 0

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

def crossover(points, pr1, pr2):
    pr2 = pr2.copy()
    for jt_1, job_1, op_1, _ in [pr1[idx] for idx in points]:
        for l2 in range(len(pr2)-1, -1, -1):
            if pr2[l2][0] == jt_1 and pr2[l2][1] == job_1 and pr2[l2][2] == op_1:
                pr2.pop(l2)
                break
    return [pr1[l] if l in points else pr2.pop(0) for l in range(len(pr1))]

def first_stage(process, setup, ini_set, machines, seq):

    ops_machine, st_machine = {}, {}
    for m in machines:
        ops_machine[m] = []
        st_machine[m] = 0
    st_job = {jt : {job : 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    for l in range(len(seq)):
        jt, job, op = seq[l]
        eligible_m = ini_set[jt]["ops"][op]

        now = [max(st_machine[m], st_job[jt][job]) if len(ops_machine[m]) == 0 else max(st_machine[m] + getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}"), st_job[jt][job]) for m in eligible_m]
        real_now = min(now)
        select_m = eligible_m[now.index(real_now)]
        ops_machine[select_m] = (jt, op)
        st_machine[select_m], st_job[jt][job] = [real_now + getattr(process, f"{jt}{op}") for _ in range(2)]
        seq[l] = (jt, job, op, select_m)
    return seq, max(st_machine.values())

def second_stage(process, setup, ini_set, machines, pr1, pr2):
    way_cross = rd.randint(2)
    if way_cross == 0:  # SCO : Single-Point Crossover Operator
        seq = crossover([i for i in range(rd.randint(1, len(pr1)))], pr1, pr2)

    elif way_cross == 1:  # JCO : Job(Job Type) Crossover Operator
        seq = crossover([l for l in range(len(pr1)) if pr1[l][0] in rd.choice(list(ini_set), size=1)], pr1, pr2)

    elif way_cross == 2:  # ACO : Assignment Crossover
        seq = pr1.copy()
        for l in range(len(seq)):
            jt_1, job_1, op_1 = seq[l][0], seq[l][1], seq[l][2]
            for jt_2, job_2, op_2, m_2 in pr2:
                if jt_1 == jt_2 and job_1 == job_2 and op_1 == op_2:
                    seq[l] = (jt_1, job_1, op_1, m_2)
                    break
    else:
        seq = 0

    way_mutation = rd.randint(2)
    if way_mutation == 0: # OSM : Operation Swaping Mutation
        idx1, idx2 = 0, 0
        while seq[idx1][0] != seq[idx2][0] and seq[idx1][1] != seq[idx2][1] :
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
    else:
        seq = 0

    ops_machine, st_machine = {}, {}
    for m in machines:
        ops_machine[m] = []
        st_machine[m] = 0
    st_job = {jt: {job: 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    for l in range(len(seq)):
        jt, job, op, m = seq[l]
        print("Selected :", jt, job, op, m)
        if len(ops_machine[m]) == 0:
            now = max(st_machine[m], st_job[jt][job])
            print(f"Machine {m} 기준 : {st_machine[m]}  /  작업({jt}, {job}) 기준 : {st_job[jt][job]} --> 현재시점 : {now}")
        else:
            now = max(st_machine[m] + getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}"), st_job[jt][job])
            print(f"Machine {m} 기준 : {st_machine[m]} + Setup(({ops_machine[m][0]},{ops_machine[m][1]}) -> ({jt},{op})({getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}")}) = {now} /  작업({jt}, {job}) 기준 : {st_job[jt][job]} --> 현재시점 : {now}")
        ops_machine[m] = (jt, op)
        st_machine[m], st_job[jt][job] = [now + getattr(process, f"{jt}{op}") for _ in range(2)]
        print(f"작업 시간 : {getattr(process, f"{jt}{op}")} --> 작업 완료 시간 : {st_machine[m]}")
        print(f"Machine 별")
        for m in machines:
            print(f"\t{m} : {st_machine[m]}")
        print()
    return seq, max(st_machine.values())

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
    pops = sorted([first_stage(process, setup, ini_set, machines, correct_procedure(ini_set, list(rd.permutation(ini_pop)))) for _ in range(params["pop_size"])], key=lambda case:case[1])

    for gen in range(params["num_of_gens"]):
        mating_pool = [select_pop(pops) for _ in range(params["mating_pool"])]
        for case in mating_pool:
            print("\t",case)
        indices = list(range(params["mating_pool"]))
        """
        for _ in range(len(mating_pool) // 2):
            mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            pops.append(second_stage(process, setup, ini_set, machines, mating_pool[mom][0], mating_pool[dad][0]))
        """
        for _ in range(params["num_offs"]):
            mom, dad = rd.choice(indices, size=2, replace=False)
            pops.append(second_stage(process, setup, ini_set, machines, mating_pool[mom][0], mating_pool[dad][0]))

        pops = sorted(pops, key=lambda case:case[1])[:params["pop_size"]]
        for case in pops:
            print(case[1], case[0])
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
    params = {"pop_size": 15, "num_of_gens": 20, "mating_pool": 15, "num_offs": 15}
    num_jts ,max_num_job, max_num_op, num_machines, max_time = 3, 5, 4, 4, 9

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