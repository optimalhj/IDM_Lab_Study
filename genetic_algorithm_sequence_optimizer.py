from numpy import random as rd
import matplotlib.pyplot as plt

# Parameter Input
num_jts ,max_num_job, max_num_op, num_machines, max_time = 4, 5, 5, 7, 9
params = {"pop_size": 5, "num_of_gens": 20, "mating_pool": 20, "num_offs": 10, "s_max": 2, "T": 20, "w": 0.5, "K": 0.25}

def select_mp(populations):
    index = list(range(params["pop_size"]))
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        return populations[min(rd.choice(index, size=2, replace=False), key=lambda idx: populations[idx][1][0])]
    elif way_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(index, size=rd.randint(3, max(4, int(params["pop_size"] / 2.5))), replace=False), key=lambda idx: populations[idx][1][0])]
    elif way_pop == 2:  # Linear ranking
        return populations[rd.choice(index, size=1, p=[2 * i / (params["pop_size"] * (params["pop_size"] + 1)) for i in range(params["pop_size"], 0, -1)])[0]]
    else:  # Do not reach
        return []

def objective(process, setup, ini_set, seq):
    se_process = {jt: {job: {op: [] for op in ini_set[jt]["ops"]} for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    st_job = {jt: {job: 0 for job in ini_set[jt]["jobs"]} for jt in ini_set.keys()}
    se_setup = {}
    ops_machine, st_machine = {}, {}
    t_setup = {}
    for _, _, _, m in seq:
        if m not in se_setup:
            se_setup[m] = {}
            ops_machine[m] = []
            st_machine[m] = 0
    for l in range(len(seq)):
        jt, job, op, m = seq[l]
        if len(ops_machine[m]) == 0: now = max(st_machine[m], st_job[jt][job])
        else:
            setup_time = getattr(setup, f"{ops_machine[m][0]}{ops_machine[m][1]}{jt}{op}")
            now = max(st_machine[m] + setup_time, st_job[jt][job])
            while True:
                pass_count = 0
                for t in range(now - setup_time, now):
                    if t in t_setup and t_setup[t] == params["s_max"]:
                        now += 1
                        break
                    else: pass_count += 1
                if pass_count == setup_time: break

            if setup_time != 0:
                se_setup[m][l] = [now - setup_time, now]
                for t in range(se_setup[m][l][0], se_setup[m][l][1]):
                    if t not in t_setup: t_setup[t] = 1
                    else: t_setup[t] += 1
        se_process[jt][job][op].append(now)
        ops_machine[m] = (jt, op)
        st_machine[m], st_job[jt][job] = [now + getattr(process, f"{jt}{op}") for _ in range(2)]
        se_process[jt][job][op].append(st_machine[m])

    f_u = 0
    for jt in ini_set.keys():
        for job in ini_set[jt]["jobs"]:
            for op in ini_set[jt]["ops"]:
                if params["T"] >= se_process[jt][job][op][1]:
                    f_u += se_process[jt][job][op][1] - se_process[jt][job][op][0]
                elif se_process[jt][job][op][0] <= params["T"] < se_process[jt][job][op][1]:
                    f_u += params["T"] - se_process[jt][job][op][0]
                else: break
    f_u /= (len(ops_machine) * params["T"])
    f_s = 0
    f_c = {}
    for m in se_setup:
        f_c[m] = 0
        for l in se_setup[m]:
            if params["T"] >= se_setup[m][l][1]:
                f_s += se_setup[m][l][1] - se_setup[m][l][0]
                f_c[m] += 1
            elif se_setup[m][l][0] <= params["T"] < se_setup[m][l][1]:
                f_s += params["T"] - se_setup[m][l][0]
                f_c[m] += 1
            else: break
    f_s /= (len(ops_machine) * params["T"])
    f_i = 1 - f_u - f_s
    f_b = max(st_machine.values()) / min(st_machine.values()) - 1
    obj = params["w"] * f_u - (1 - params["w"]) * f_s
    return seq, (obj, f_u, f_s, f_c, f_i, f_b), se_process, se_setup

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

    print(f"\npr1 : ({len(points)})", [pr1[i] for i in points])
    print(f"pr2 : ({len(pr2)})", pr2)
    return [pr1[i] if i in points else pr2.pop(0) for i in range(len(pr1))]

def crossover(mating_pool, cr):
    print(f"CR{cr}")

    index = list(range(params["mating_pool"]))

    if cr == 1: # Based on Job Type
        pr1, pr2 = [mating_pool[pr][0].copy() for pr in rd.choice(index, size=2, replace=False)]
        print(f"pr1 : ({len(pr1)})", pr1)
        print(f"pr2 : ({len(pr2)})", pr2)

        chosen_jt = pr1[rd.randint(len(pr1))][0]
        print("\t", chosen_jt, end="  /  ")
        points = [idx for idx in range(len(pr1)) if pr1[idx][0] == chosen_jt]
        print("points :", points)
        child = crossing(points, pr1, pr2, apx=False)
    else:
        if cr == 2: # Based on F_c(# of Setup Change)
            index.sort(key=lambda idx:sum(mating_pool[idx][1][3].values()))
        elif cr == 3: # Based on F_b(Degree of Machine Load)
            index.sort(key=lambda idx:-mating_pool[idx][1][5])
        elif cr == 4: # Based on F_i(Degree of Idle Time)
            index.sort(key=lambda idx:mating_pool[idx][1][4])
        else: pass # Do not reach

        pr1, pr2 = [mating_pool[pr][0].copy() for pr in (rd.choice(index[:max(1, int(params["mating_pool"] * params["K"]))]), rd.choice(index[-max(1, int(params["mating_pool"] * params["K"])):]))]
        print(f"pr1 : ({len(pr1)})", pr1)
        print(f"pr2 : ({len(pr2)})", pr2)
        child = crossing(list(range(len(pr1))), pr1, pr2)

    print(f"\nchd : ({len(child)})", child)
    print("-"*50)
    return child

def mutation(process, setup, ini_set, machines, seq, cr):
    print(f"MU{cr}", seq, "\n")
    seq, (obj, f_u, f_s, f_c, f_i, f_b), se_process, se_setup = seq
    seq = seq.copy()
    if cr == 1:
        random_idx = rd.randint(len(seq))
        jt, job, op, m = seq.pop(random_idx)
        print("Pop_op :" ,(jt, job, op, m), " /  Index :", random_idx)
        place_in_job = list(ini_set[jt]["ops"]).index(op)
        if place_in_job == 0:
            print("First Op Popped")
            if len(list(ini_set[jt]["ops"])) > 1:
                for l in range(random_idx, len(seq)):
                    if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job + 1]:
                        next_idx = l
                        print("Next_Op :", seq[next_idx], " /  Index :", next_idx)
                        break
            else:
                print("Only one Op, So Every Position Able")
                next_idx = len(seq) + 1
            if next_idx == 0:
                print("Only First Able")
                seq.insert(0, (jt, job, op, m))
            else: seq.insert(rd.choice([i for i in range(next_idx + 1) if i != random_idx]), (jt, job, op, m))

        elif place_in_job == len(ini_set[jt]["ops"]) - 1:
            print("Final Op Popped")
            for l in range(random_idx - 1, -1, -1):
                if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job - 1]:
                    prior_idx = l
                    print("Prior_Op :", seq[prior_idx], " /  Index :", prior_idx)
                    break
            if prior_idx == len(seq) - 1:
                print("Only Final Able")
                seq.append((jt, job, op, m))
            else: seq.insert(rd.choice([i for i in range(prior_idx + 1, len(seq) + 1) if i != random_idx]), (jt, job, op, m))

        else:
            for l in range(random_idx - 1, -1, -1):
                if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job - 1]:
                    prior_idx = l
                    break
            for l in range(random_idx, len(seq)):
                if seq[l][0] == jt and seq[l][1] == job and seq[l][2] == list(ini_set[jt]["ops"])[place_in_job + 1]:
                    next_idx = l
                    break
            print("Prior_Op :", seq[prior_idx], " /  Index :", prior_idx, "   //   Next_Op :", seq[next_idx], " /  Index :", next_idx)
            seq.insert(rd.choice(list(range(prior_idx + 1, next_idx + 1))), (jt, job, op, m))
    elif cr == 2:
        chosen_m = max(f_c, key=lambda m : f_c[m])
        print(se_setup[chosen_m])
        if len(se_setup[chosen_m]) != 0:
            chosen_idx = rd.choice(list(se_setup[chosen_m]))
            chosen_jt, chosen_job, chosen_op, _ = seq[chosen_idx]
            alternative_m = rd.permutation([m for m in ini_set[chosen_jt]["ops"][chosen_op] if m != chosen_m]).tolist()
            print(f"{ini_set[chosen_jt]["ops"][chosen_op]} - [{chosen_m}] == {alternative_m}")
            if len(alternative_m) != 0:
                print("Origin :", seq[chosen_idx])
                for m in alternative_m:
                    go_break = False
                    seq_tmp = seq.copy()
                    seq_tmp[chosen_idx] = (chosen_jt, chosen_job, chosen_op, m)

                    prior_op_found = False
                    print("Change :", seq_tmp[chosen_idx], end=" --> ")

                    for prior_idx in range(chosen_idx - 1, -1, -1):
                        if seq_tmp[prior_idx][3] == m:
                            prior_op_found = True
                            print(getattr(setup, f"{seq_tmp[prior_idx][0]}{seq_tmp[prior_idx][2]}{seq_tmp[chosen_idx][0]}{seq_tmp[chosen_idx][2]}"))
                            if getattr(setup, f"{seq_tmp[prior_idx][0]}{seq_tmp[prior_idx][2]}{seq_tmp[chosen_idx][0]}{seq_tmp[chosen_idx][2]}") == 0:
                                seq = seq_tmp.copy()
                                go_break = True
                            break
                    if not prior_op_found:
                        print("None")
                        seq = seq_tmp.copy()
                        go_break = True
                    if go_break: break
    elif cr == 3:
        using_machine = []
        for _, _, _, m in seq:
            if m not in using_machine:
                using_machine.append(m)
        using_machine.sort(key=lambda using_m:-sum(getattr(process, f"{jt}{op}") for jt, _, op, m in seq if m == using_m))
        print("Using M :", using_machine)
        for using_m in using_machine:
            print(using_m, ":", sum(getattr(process, f"{jt}{op}") for jt, _, op, m in seq if m == using_m), end= " / ")
        from_m = rd.choice(using_machine[:max(1, int(len(using_machine) * params["K"]))])
        print("\nFrom :", from_m)
        to_m = min(machines, key=lambda m:sum(1 for sche in seq if m==sche[3]))
        for m in machines:
            print(m, ":", sum(1 for sche in seq if m==sche[3]), end= " / ")
        print("\n To  :", to_m)

        for idx in rd.permutation(list(range(len(seq)))):
            jt, job, op, m = seq[idx]
            if m == from_m and to_m in ini_set[jt]["ops"][op]:
                seq[idx] = (jt, job, op, to_m)
                print(f"{(jt, job, op, m)} -> {seq[idx]}")
                break

    elif cr == 4:
        using_machine = []
        for sche in seq:
            if sche[3] not in using_machine:
                using_machine.append(sche[3])
        t_p, t_s = {}, {}
        for tmp_m in using_machine:
            t_p[tmp_m], t_s[tmp_m] = 0, 0
            for jt, job, op, m in seq:
                if m == tmp_m:
                    if params["T"] >= se_process[jt][job][op][1]:
                        t_p[tmp_m] += se_process[jt][job][op][1] - se_process[jt][job][op][0]
                    elif se_process[jt][job][op][0] <= params["T"] < se_process[jt][job][op][1]:
                        t_p[tmp_m] += params["T"] - se_process[jt][job][op][0]
                    else: pass # Do not reach
            for l in se_setup[tmp_m]:
                if params["T"] >= se_setup[tmp_m][l][1]:
                    t_s[tmp_m] += se_setup[tmp_m][l][1] - se_setup[tmp_m][l][0]
                elif se_setup[tmp_m][l][0] <= params["T"] < se_setup[tmp_m][l][1]:
                    t_s[tmp_m] += params["T"] - se_setup[tmp_m][l][0]
                else: break
        print("t_p(0, T) :", t_p)
        print("t_s(0, T) :", t_p)
        using_machine.sort(key=lambda m:t_p[m] + t_s[m])
        print("Using M :", using_machine)
        from_m = rd.choice(using_machine[:max(1, int(len(using_machine) * params["K"]))])
        print("\nFrom :", from_m)

        for idx in rd.permutation(list(range(len(seq)))):
            jt, job, op, m = seq[idx]
            if seq[idx][3] == from_m and list(ini_set[jt]["ops"]).index(op) != 0:
                print("Chosen :", (jt, job, op, m), "-->", end=" ")
                for first_idx in range(len(seq)):
                    first_jt, first_job, first_op, first_m = seq[first_idx]
                    if first_jt == jt and first_job == job and list(ini_set[jt]["ops"]).index(first_op) == 0:
                        print(seq[first_idx])
                        seq.insert(0, seq.pop(first_idx))
                        break
                break
    else: pass # Do not reach
    print(f"\nchd : ({len(seq)})", seq)
    print("-" * 50)
    return seq

def correct_procedure(process, setup, ini_set, seq):
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
    return objective(process, setup, ini_set, seq)

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
        for st_setup, ed_setup in se_setup[m].values():
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
    print("Initial_Population")
    for pop in pops:
        print(pop)
    print("*"*50)
    cr = 1
    for gen in range(1, params["num_of_gens"] + 1):
        mating_pool = [select_mp(pops) for _ in range(params["mating_pool"])]
        offsprings = []
        for _ in range(params["num_offs"]):
            offspring = crossover(mating_pool.copy(), cr) if rd.random() < 0.5 else mutation(process, setup, ini_set, machines, mating_pool[rd.choice(list(range(params["mating_pool"])))], cr)
            offsprings.append(objective(process, setup, ini_set, offspring))
        offsprings.sort(key=lambda offs:(-offs[1][0], offs[1][1]))

        # seq, (md.ObjVal, f_u.X, f_s.X, f_c, f_i, f_b), se_process, se_setup
        print("Pops :\n")
        for values in pops:
            print(f"\t{values[1]}")
        print("\nOffsprings :\n")
        for values in offsprings:
            print(f"\t{values[1]}")

        if offsprings[0][1][0] > pops[0][1][0]:
            cr = 1
            pops = sorted(pops + offsprings, key=lambda case: (-case[1][0], -case[1][1]))[:params["pop_size"]]
            print("Replaced")
        elif sum(offsprings[0][1][3].values()) > sum(pops[0][1][3].values()):
            cr = 2
        elif offsprings[0][1][5] > pops[0][1][5]:
            cr = 3
        elif offsprings[0][1][4] > pops[0][1][4]:
            cr = 4
        else:
            cr = 1
        print(f"\nGeneration_{gen}")
        for pop in pops:
            print(pop)
        print("*"*50)
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

    for jt1, op1 in setups:
        for jt2, op2 in setups:
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

if __name__ == "__main__":
    main()