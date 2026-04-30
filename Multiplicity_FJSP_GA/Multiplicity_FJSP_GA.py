from numpy import random as rd
import matplotlib.pyplot as plt

def select_pop(populations, way_select_pop):
    indices = [i for i in range(len(populations))]

    if way_select_pop == 0:  # Binary tournament
        return populations[min(rd.choice(indices, size=2, replace=False), key=lambda idx : populations[idx][1])]

    elif way_select_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(indices, size=rd.randint(3, max(4, int(len(indices)/2.5))), replace=False), key=lambda idx : populations[idx][1])]

    elif way_select_pop == 2:  # Linear ranking
        return populations[rd.choice(indices, size=1, p=[2 * i / (len(indices) * (len(indices) + 1)) for i in range(1, len(indices) + 1)])[0]]

    else:  # Do not reach
        return 0

"""
def graph(final):
    x = [Gen for Gen in final]
    y = [final[Gen][0] for Gen in final]

    print("Best Seq :", final[x[-1]][1])

    plt.plot(x, y)
    plt.xticks(rotation=45, fontsize=5)
    plt.title("Makespan of FJSP")
    plt.xlabel("Generations")
    plt.ylabel("Tardiness")
    plt.show()
"""

def three_phase_decode(duration, setup, chromosome, ini_set, machines):

    seq_o, seq_m = [], []
    count = {gene : 1 for gene in chromosome}

    for l in range(len(chromosome)):
        seq_o.append((ini_set[chromosome[l][0]]["jobs"][count[chromosome[l]]-1],chromosome[l]))
        count[chromosome[l]] += 1

    for job_type in ini_set:
        for job in ini_set[job_type]["jobs"]:
            l_set = [l for l in range(len(seq_o)) if job == seq_o[l][0] and job_type in seq_o[l][1]]
            sort_op = sorted((seq_o[l] for l in l_set), key=lambda op:list(ini_set[job_type]["ops"]).index(op[1][1]))
            for l in l_set:
                seq_o[l] = sort_op.pop(0)

    h, c_slash, c = 1, {0:{m:0 for m in machines}}, {job_type : {job : {0:0} for job in ini_set[job_type]["jobs"]} for job_type in ini_set}

    for l in range(len(seq_o)):
        i, j, k = seq_o[l][0], seq_o[l][1][0], list(ini_set[seq_o[l][1][0]]["ops"]).index(seq_o[l][1][1]) + 1
        machines_list = ini_set[j]["ops"][list(ini_set[seq_o[l][1][0]]["ops"])[k - 1]]

        e_m = {}
        for m in machines_list:
            e_m[m] = getattr(duration, f"{j}{list(ini_set[j]["ops"])[k - 1]}") + max(c[j][i][k - 1], c_slash[h - 1][m])
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

def gene_crossover(points, parent1, parent2):
    chromosome = []
    for gene in [parent1[idx] for idx in points]:
        for l2 in range(len(parent2)-1, -1, -1):
            if parent2[l2] == gene:
                parent2.pop(l2)
                break
    for l in range(len(parent1)):
        if l in points:
            chromosome.append(parent1[l])
        else:
            chromosome.append(parent2.pop(0))
    return chromosome

def gene_mutation(points, chromosome):
    insulting = [chromosome[idx] for idx in points]
    for l in range(len(chromosome)):
        if l in points:
            chromosome[l] = insulting.pop(0)
    return chromosome

def encode(decoded):
    return [(gene[0], gene[2]) for gene in decoded]

def generate_offsprings(ini_set, parent1, parent2):
    parents = [encode(parent[0]) for parent in [parent1, parent2]]
    way_offspring = rd.choice(6)
    if way_offspring == 0:
        points = [i for i in range(rd.randint(1, len(parents[0])))]
        return gene_crossover(points, parents[0], parents[1])

    elif way_offspring == 1:
        points = []
        r_job_types = {job_type : rd.randint(len(ini_set[job_type]["jobs"])) for job_type in ini_set.keys()}
        for l in range(len(parents[0])):
            if r_job_types[parents[0][l][0]] > 0:
                points.append(l)
                r_job_types[parents[0][l][0]] -= 1
        return gene_crossover(points, parents[0], parents[1])

    elif way_offspring == 2:
        points = []
        rt = rd.choice(list(ini_set), size=rd.randint(1, len(list(ini_set))), replace=False)
        for l in range(len(parents[0])):
            job_type, op = parents[0][l]
            if job_type in rt:
                points.append(l)
        return gene_crossover(points, parents[0], parents[1])

    elif way_offspring == 3:
        points = rd.choice([i for i in range(len(parents[0]))], size=rd.randint(3, len(list(parents[0]))), replace=False)
        return gene_mutation(points, parents[0])

    elif way_offspring == 4:
        rd_type = list(ini_set)[rd.randint(len(list(ini_set)))]
        points = [l for l in range(len(parents[0])) if rd_type == parents[0][l][0]]
        return gene_mutation(points, parents[0])

    elif way_offspring == 5:
        rd_types = rd.choice(list(ini_set), size=rd.randint(2, len(list(ini_set))), replace=False)
        points = [l for l in range(len(parents[0])) if parents[0][l][0] in rd_types]
        return gene_mutation(points, parents[0])

    else:  # Do not reach
        return 0

def start_ga(duration, setup, ini_set, machines, params):

    ini_pop = []
    op_types = [(job_type, op) for job_type in ini_set for _ in ini_set[job_type]["jobs"] for op in ini_set[job_type]["ops"]]
    for _ in range(params["pop_size"]):
        chromosome = [op_types[i] for i in rd.choice(range(len(op_types)), size=len(op_types), replace=False)]
        ini_pop.append(three_phase_decode(duration, setup, chromosome, ini_set, machines))

    populations = sorted(ini_pop, key=lambda case:case[1])
    for generation in range(params["num_of_gens"]):
        print("Generation : ", generation + 1)
        mating_pool = [select_pop(populations, rd.randint(3)) for _ in range(params["mating_pool"])]
        indices = [i for i in range(len(mating_pool))]
        offsprings = []
        """
        for _ in range(len(mating_pool)//2):
            mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            offsprings.append(three_phase_decode(duration, setup, generate_offsprings(ini_set, populations[mom], populations[dad]), ini_set, machines))
        """
        for _ in range(params["num_offs"]):
            mom, dad = rd.choice(indices, size=2, replace=False)
            offsprings.append(three_phase_decode(duration, setup, generate_offsprings(ini_set, populations[mom], populations[dad]), ini_set, machines))

        children = sorted(populations + offsprings, key=lambda case:case[1])
        populations = children[:params["pop_size"]]
        print("Best offspring :", populations[0][1], populations[0][0])
    return populations[0]

class Duration:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(durations, setups, machines_tmp, params):
    duration, setup, ini_set, machines = Duration(), SetUp(), {}, []

    for job_type in durations.keys():
        ini_set[job_type] = {"jobs": durations[job_type]["jobs"], "ops": {}}
        for op in durations[job_type]["ops"]:
            ms,processing_time = durations[job_type]["ops"][op]
            ini_set[job_type]["ops"][op] = ms
            for m in ms:
                if m not in machines:
                    machines.append(m)
            setattr(duration, f"{job_type}{op}", processing_time)
    machines.sort(key=lambda machine: machines_tmp.index(machine))

    for op_type1 in setups:
        for op_type2 in setups:
            (job_type1, op1), (job_type2, op2) = op_type1, op_type2
            setattr(setup, f"{job_type1}{op1}{job_type2}{op2}", setups[(job_type1, op1)][(job_type2, op2)])

    return start_ga(duration, setup, ini_set, machines, params)

def main():

    # Parameter Input
    params = {"pop_size": 10, "num_of_gens": 15, "mating_pool": 10, "num_offs": 8}
    num_job_types ,max_num_job, max_num_op, num_machines, max_time = 5, 7, 4, 7, 9

    job_types = [f"Job_Type{i}" for i in range(1, num_job_types + 1)]
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    durations = {job_type : {"jobs":[f"Job{j+1}" for j in range(rd.randint(2,max_num_job+1))], "ops":{f"Op{o+1}" : [sorted(rd.choice(machines, size=rd.randint(1, len(machines)), replace=False),key=lambda machine: machines.index(machine)),rd.randint(2, max_num_op + 1)] for o in range(rd.randint(1, max_num_op + 1))}} for job_type in job_types}

    op_types = [(job_type, op) for job_type in job_types for op in durations[job_type]["ops"]]
    setups = {op1:{op2:0 if op1[0] == op2[0] else rd.randint(1, max(max_time//2, 1) + 1) for op2 in op_types} for op1 in op_types}

    for job_type in durations.keys():
        print(job_type)
        for job in durations[job_type]:
            print("\t", end="")
            print(job)
            print("\t", end="")
            print(durations[job_type][job])
        print()
    print("-----------------------------------------------------------------------------------------------------")

    start(durations, setups, machines, params)

if __name__ == "__main__":
    main()