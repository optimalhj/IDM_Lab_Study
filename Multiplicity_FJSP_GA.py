from numpy import random as rd
import matplotlib.pyplot as plt

def calculate(origin, operations):
    machines, jobs = {}, {}
    for operation in operations:
        machines[operation[0]] = 0
        jobs[operation[1]] = 0
    for operation in operations:
        start_of_operation = max(machines[operation[0]], jobs[operation[1]])
        machines[operation[0]] = start_of_operation + getattr(origin, f"{operation[0]}{operation[1]}{operation[2]}")
        jobs[operation[1]] = start_of_operation + getattr(origin, f"{operation[0]}{operation[1]}{operation[2]}")
    return max(machines.values())

def generate_offsprings(origin, mom, dad, rates, m):
    offsprings = []
    parents = (mom, dad)
    way_offspring = rd.choice([i for i in range(len(rates))], size=1, p=rates, replace=False)

    for i in range(2):
        if way_offspring == 0:
            jobs = []
            for operation in parents[i]:
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

        elif way_offspring == 1:
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

def select_pop(origin, ini_pop, way_select_pop):
    if way_select_pop == 0:  # Binary tournament
        indices = [i for i in range(len(ini_pop))]
        candidates = []
        while len(indices) > 0:
            if len(indices) < 2:
                candidates.append(indices)
                break
            else:
                candidates.append([indices.pop(rd.randint(len(indices))) for _ in range(2)])
        new_candidates = [versus(origin, [ini_pop[idx] for idx in candidate]) for candidate in candidates]

        if len(new_candidates) > 2:
            return select_pop(origin, new_candidates, 0)
        else:
            return new_candidates

    elif way_select_pop == 1:  # n-Size tournament
        indices = [i for i in range(len(ini_pop))]
        candidates = []
        while len(indices) > 0:
            if len(indices) >= 3:
                n_size = rd.randint(2, len(indices))
            else:
                n_size = len(indices)
            if len(indices) < n_size:
                candidates.append(indices)
                break
            else:
                candidates.append([indices.pop(rd.randint(len(indices))) for _ in range(n_size)])
        new_candidates = [versus(origin, [ini_pop[idx] for idx in candidate]) for candidate in candidates]
        if len(new_candidates) == 2:
            return new_candidates
        else:
            return select_pop(origin, new_candidates, 1)

    elif way_select_pop == 2:  # Linear ranking
        tmp = sorted(ini_pop, key=lambda case: calculate(origin, case))
        idx1, idx2 = rd.choice([i for i in range(0, len(ini_pop))], size=2, replace=False,
                                   p=[2 * i / (len(tmp) * (len(tmp) + 1)) for i in range(1, len(tmp) + 1)])
        return tmp[idx1], tmp[idx2]

    else:  # Do not reach
        return 0


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

def start_ga(duration, setup, ini_set, machines, params):
    op_types = [(job_type, op) for job_type in ini_set for op in ini_set[job_type]["ops"]]

    ini_pop = sorted(op_types, key=lambda op_type:getattr(duration, f"{op_type[0]}{op_type[1]}")) # by using SPT

class Duration:
    def __init__(self):
        pass
class SetUp:
    def __init__(self):
        pass
def start(durations, setups, machines_tmp, params):
    duration, setup, ini_set, machines = Duration(), SetUp(), {}, []

    for job_type in durations.keys():
        ini_set[job_type] = {"jobs": durations[job_type]["jobs"], "ops": []}
        for op in durations[job_type]["ops"]:
            ini_set[job_type]["ops"].append(op)
            ms,processing_time = durations[job_type]["ops"][op]
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

    op_types = [(job_type, op) for job_type in job_types for op in durations[job_type][list(durations[job_type])[0]]]
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