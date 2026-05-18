from numpy import random as rd
import matplotlib.pyplot as plt

def select_pop(populations):
    indices = [i for i in range(len(populations))]
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        return populations[min(rd.choice(indices, size=2, replace=False), key=lambda idx : populations[idx][1])]

    elif way_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(indices, size=rd.randint(3, max(4, int(len(indices)/2.5))), replace=False), key=lambda idx : populations[idx][1])]

    elif way_pop == 2:  # Linear ranking
        return populations[rd.choice(indices, size=1, p=[2 * i / (len(indices) * (len(indices) + 1)) for i in range(len(indices), 0 , -1)])[0]]

    else:  # Do not reach
        return 0

def decode(process, setup, chrom, ini_set, machines):

    seq_o, seq_m = [], []
    count = {gene : 0 for gene in chrom}

    for l in range(len(chrom)):
        seq_o.append((ini_set[chrom[l][0]]["jobs"][count[chrom[l]]],chrom[l]))
        count[chrom[l]] += 1

    for jt in ini_set:
        for job in ini_set[jt]["jobs"]:
            l_set = [l for l in range(len(seq_o)) if job == seq_o[l][0] and jt in seq_o[l][1]]
            sort_op = sorted((seq_o[l] for l in l_set), key=lambda op:list(ini_set[jt]["ops"]).index(op[1][1]))
            for l in l_set:
                seq_o[l] = sort_op.pop(0)

    h, c_slash, c = 1, {0:{m:0 for m in machines}}, {jt : {job : {0:0} for job in ini_set[jt]["jobs"]} for jt in ini_set}

    for l in range(len(seq_o)):
        i, j, k = seq_o[l][0], seq_o[l][1][0], list(ini_set[seq_o[l][1][0]]["ops"]).index(seq_o[l][1][1]) + 1
        machines_list = ini_set[j]["ops"][list(ini_set[seq_o[l][1][0]]["ops"])[k - 1]]

        e_m = {}
        for m in machines_list:
            e_m[m] = getattr(process, f"{j}{list(ini_set[j]["ops"])[k - 1]}") + max(c[j][i][k - 1], c_slash[h - 1][m])
            m_tmp = [m_idx for m_idx in range(len(seq_m)) if seq_m[m_idx] == m]
            if len(m_tmp) > 0:
                max_idx = max(m_tmp)
                jp = seq_o[max_idx][1][0]
                e_m[m] += getattr(setup, f"{jp}{list(ini_set[jp]["ops"])[list(ini_set[seq_o[max_idx][1][0]]["ops"]).index(seq_o[max_idx][1][1])]}{j}{list(ini_set[j]["ops"])[k - 1]}")
        seq_m.append(min(machines_list, key=lambda m:e_m[m]))
        c[j][i][k] = min(e_m.values())
        c_slash[h] = {m : c[j][i][k] if m == seq_m[-1] else c_slash[h-1][m] for m in machines}
        h += 1
    return [(seq_o[i][1][0],seq_o[i][0],seq_o[i][1][1],seq_m[i]) for i in range(len(seq_m))], max(c_slash[h-1].values())

def crossover(points, pr1, pr2):
    for gene in [pr1[idx] for idx in points]:
        for l2 in range(len(pr2)-1, -1, -1):
            if pr2[l2] == gene:
                pr2.pop(l2)
                break
    return [pr1[l] if l in points else pr2.pop(0) for l in range(len(pr1))]

def mutation(points, chrom):
    insult = [chrom[idx] for idx in points]
    for l in range(len(chrom)):
        if l in points:
            chrom[l] = insult.pop(0)
    return chrom

def generate_off(ini_set, parent1, parent2):
    pr1, pr2 = [[(gene[0], gene[2]) for gene in parent[0]] for parent in [parent1, parent2]]
    way_off = rd.choice(6)

    if way_off == 0:
        return crossover([i for i in range(rd.randint(1, len(pr1)))], pr1, pr2)

    elif way_off == 1:
        points = []
        r_jts = {jt : rd.randint(len(ini_set[jt]["jobs"])) for jt in ini_set.keys()}
        for l in range(len(pr1)):
            if r_jts[pr1[l][0]] > 0:
                points.append(l)
                r_jts[pr1[l][0]] -= 1
        return crossover(points, pr1, pr2)

    elif way_off == 2:
        rt = rd.choice(list(ini_set), size=rd.randint(1, len(list(ini_set))), replace=False)
        return crossover([l for l in range(len(pr1)) if pr1[l][0] in rt], pr1, pr2)

    elif way_off == 3:
        return mutation(rd.choice([i for i in range(len(pr1))], size=rd.randint(3, len(list(pr1))), replace=False), pr1)

    elif way_off == 4:
        rd_type = list(ini_set)[rd.randint(len(list(ini_set)))]
        return mutation([l for l in range(len(pr1)) if rd_type == pr1[l][0]], pr1)

    elif way_off == 5:
        rd_types = rd.choice(list(ini_set), size=rd.randint(2, len(list(ini_set))), replace=False)
        return mutation([l for l in range(len(pr1)) if pr1[l][0] in rd_types], pr1)

    else:  # Do not reach
        return 0

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
        for jt, job, op, machine in seqs:
            if machine == m:
                m_tmp[m].append((jt, job, op))
            if (jt, job) not in list(s_job):
                s_job[(jt, job)] = 0

    for jt, job, op, m in seqs:
        start_oper, operating = max(s_job[(jt, job)], s_machine[m]), getattr(process, f"{jt}{op}")
        ax.barh(m, operating, left=start_oper, color=plt.get_cmap('tab20', len(s_job))(list(s_job).index((jt,job))), edgecolor='black')
        ax.text(start_oper + operating / 2, m, f"{jt}\n{job}\n{op}\n({operating})", va='center', ha='center', color='black', fontsize=5)
        s_job[(jt, job)], s_machine[m] = [start_oper + operating for _ in range(2)]
        if m_tmp[m].index((jt, job, op)) != len(m_tmp[m]) - 1:
            next_jt, _, next_op = m_tmp[m][m_tmp[m].index((jt, job, op)) + 1]
            set_t = getattr(setup, f"{jt}{op}{next_jt}{next_op}")
            s_machine[m] += set_t
            ax.barh(m, set_t, left=s_machine[m] - set_t, color='white', edgecolor='black')
    ax.set_xticks([i for i in range(int(makespan)+2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def start_ga(process, setup, ini_set, machines, params):
    history = []

    op_types = [(jt, op) for jt in ini_set for _ in ini_set[jt]["jobs"] for op in ini_set[jt]["ops"]]
    pops = sorted([decode(process, setup, [op_types[i] for i in rd.choice(range(len(op_types)), size=len(op_types), replace=False)], ini_set, machines) for _ in range(params["pop_size"])],
                         key=lambda case:case[1])

    for generation in range(params["num_of_gens"]):
        mating_pool = [select_pop(pops) for _ in range(params["mating_pool"])]
        indices = [i for i in range(len(mating_pool))]

        for _ in range(len(mating_pool)//2):
            mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            pops.append(decode(process, setup, generate_off(ini_set, pops[mom], pops[dad]), ini_set, machines))
        """
        for _ in range(params["num_offs"]):
            mom, dad = rd.choice(indices, size=2, replace=False)
            pops.append(decode(process, setup, generate_off(ini_set, mating_pool[mom], mating_pool[dad]), ini_set, machines))
        """
        pops = sorted(pops, key=lambda case:case[1])[:params["pop_size"]]
        history.append(pops[0][1])
        print("Generation : ", generation + 1,"/ Best offspring :", pops[0][1], pops[0][0])
    graph_gen(history)
    graph_makespan(process, setup, pops[0], machines)

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

    return start_ga(process, setup, ini_set, machines, params)

def main():

    # Parameter Input
    params = {"pop_size": 100, "num_of_gens": 5, "mating_pool": 100, "num_offs": 200}
    params["pop_size"] = max(3,params["pop_size"])
    params["mating_pool"] = min(params["pop_size"], params["mating_pool"])
    num_jts ,max_num_job, max_num_op, num_machines, max_time = 3, 3, 4, 4, 9

    jts = [f"Job_Type{i}" for i in range(1, num_jts + 1)]
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {jt : {"jobs":[f"Job{j+1}" for j in range(rd.randint(2,max_num_job+1))], "ops":{f"Op{o+1}" : [sorted(rd.choice(machines, size=rd.randint(1, len(machines)), replace=False),key=lambda machine: machines.index(machine)),rd.randint(2, max_num_op + 1)] for o in range(rd.randint(1, max_num_op + 1))}} for jt in jts}

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