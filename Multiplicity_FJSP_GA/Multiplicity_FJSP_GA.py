from numpy import random as rd
import matplotlib.pyplot as plt


"""
def calculate(duration, setup, operations):
    end_machines, end_jobs = {}, {}
    for operation in operations:
        end_machines[operation[0]] = 0
        end_jobs[operation[1]] = 0
    for operation in operations:
        start_of_operation = max(end_machines[operation[0]], end_jobs[operation[1]])
        end_machines[operation[0]] = start_of_operation + getattr(duration, f"{operation[0]}{operation[1]}{operation[2]}")
        end_jobs[operation[1]] = start_of_operation + getattr(duration, f"{operation[0]}{operation[1]}{operation[2]}")
    return max(end_machines.values())
"""
def encode(decoded):
    return [(gene[0], gene[2]) for gene in decoded]

def generate_offsprings(duration, setup, mom, dad):
    parents = [encode(parent[0]) for parent in [mom, dad]]
    way_offspring = rd.choice(3)
    i = rd.randint(2) # Main parent

    if way_offspring == 0: # SPC
        point = rd.randint(len(parents[i]))
        offspring =
        """
        jobs = []
        for  in parents[i]:
            if operation[1] not in jobs:
                jobs.append(operation[1])
        fixed_job = rd.choice(jobs, size=1)
        not_fixed_operation = [operation for operation in parents[1 - i] if operation[1] != fixed_job]
        offspring = []
        for idx in range(len(parents[i])):
            if parents[i][idx][1] == fixed_job:
                offspring.append(parents[i][idx])
            else:
                offspring.append(not_fixed_operation.pop(0))
        offsprings.append(offspring)
    """
    elif way_offspring == 1: # UPC
        idx1, idx2 = sorted(rd.choice([i for i in range(len(mom))], size=2, replace=False))
        offsprings.append(
            parents[i][0:idx1] + [(parents[1 - i][idx1][0], parents[i][idx1][1], parents[i][idx1][2])] + parents[i][
                idx1 + 1:idx2] + [(parents[1 - i][idx2][0], parents[i][idx2][1], parents[i][idx2][2])] + parents[i][
                idx2 + 1:])

    elif way_offspring == 2:
        idx_job = rd.randint(len(mom))
        indices = [idx for idx in range(len(parents[i])) if parents[i][idx][1] == parents[i][idx_job][1]]
        place = indices.index(idx_job)
        offspring = [operation for operation in parents[i]]
        if indices[place] != len(mom) - 1 and place != len(indices) - 1 and indices[place] + 1 != indices[
            place + 1]:
            offspring.insert(rd.choice(range(indices[place] + 1, indices[place + 1]), size=1)[0],
                             offspring.pop(idx_job))
        offsprings.append(offspring)

    elif way_offspring == 3:
        idx1, idx2 = rd.choice([i for i in range(len(mom))], size=2, replace=False)
        offsprings.append(parents[i][0:idx1] + [
            (rd.choice([machine for machine in m if machine != parents[i][idx1][0]]), parents[i][idx1][1],
             parents[i][idx1][2])] + parents[i][idx1 + 1:])

    elif way_offspring == 4:
        machine_load = {machine: 0 for machine in m}
        machine_max = m[0], 0
        for operation in parents[i]:
            machine_load[operation[0]] += getattr(origin, f"{operation[0]}{operation[1]}{operation[2]}")
            if machine_load[operation[0]] > machine_max[1]:
                machine_max = operation[0], machine_load[operation[0]]
        machine_min = list(machine_load)[list(machine_load.values()).index(min(machine_load.values()))]
        move_candidate = [operation for operation in parents[i] if operation[0] == machine_max[0]]
        rand_operation = move_candidate[rd.randint(len(move_candidate))]
        new_operation = (machine_min, rand_operation[1], rand_operation[2])
        idx = parents[i].index(rand_operation)
        offsprings.append(parents[i][0:idx] + [new_operation] + parents[i][idx + 1:])

    else:  # Do not reach
        offsprings = 0
    return offsprings

def select_pop(populations, way_select_pop):
    indices = [i for i in range(len(populations))]

    if way_select_pop == 0:  # Binary tournament
        return populations[min(rd.choice(indices, size=2, replace=False), key=lambda idx : populations[idx][1])]

    elif way_select_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(indices, size=rd.randint(3, max(3, int(len(indices)/2.5))), replace=False), key=lambda idx : populations[idx][1])]

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

def start_ga(duration, setup, ini_set, machines, params):
    op_types = []
    for job_type in ini_set:
        for _ in ini_set[job_type]["jobs"]:
            for op in ini_set[job_type]["ops"]:
                op_types.append((job_type, op))
    #ini_chromosome = sorted(op_types, key=lambda op_type:getattr(duration, f"{op_type[0]}{op_type[1]}")) # by using SPT
    ini_pop = []
    for _ in range(params["pop_size"]):
        chromosome = [op_types[i] for i in rd.choice(range(len(op_types)), size=len(op_types), replace=False)]
        ini_pop.append(three_phase_decode(duration, setup, chromosome, ini_set, machines))

    for generation in range(params["num_of_gens"]):
        ini_pop.sort(key=lambda case:case[1])
        mating_pool = [select_pop(ini_pop, rd.randint(3)) for _ in range(params["pop_size"])]

        indices = [i for i in range(len(mating_pool))]
        offsprings = []
        for _ in range(len(mating_pool)//2):
            mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]

            offspring = generate_offsprings(duration, setup, ini_pop[mom], ini_pop[dad])
            offsprings.append(offspring)

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
    params = {"pop_size": 10, "num_of_gens": 35, "ini_assign": [0.1, 0.9], "ini_seq": [0.2, 0.4, 0.4],
              "crossover": [0.45, 0.45, 0.02, 0.02, 0.06]}
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