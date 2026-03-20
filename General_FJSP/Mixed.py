from numpy import random
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

def versus(origin, candidates):
    makespans = [calculate(origin, case) for case in candidates]
    return candidates[makespans.index(min(makespans))]

def generate_offsprings(origin, mom,dad,rates,m):
    offsprings = []
    parents = (mom, dad)
    way_offspring = random.choice([i for i in range(len(rates))], size=1, p=rates, replace=False)

    for i in range(2):
        if way_offspring == 0:
            jobs = []
            for operation in parents[i]:
                if operation[1] not in jobs:
                    jobs.append(operation[1])
            fixed_job = random.choice(jobs, size=1)
            not_fixed_operation = [operation for operation in parents[1 - i] if operation[1] != fixed_job]
            offspring = []
            for idx in range(len(parents[i])):
                if parents[i][idx][1] == fixed_job:
                    offspring.append(parents[i][idx])
                else:
                    offspring.append(not_fixed_operation.pop(0))
            offsprings.append(offspring)

        elif way_offspring == 1:
            idx1, idx2 = sorted(random.choice([i for i in range(len(mom))], size=2, replace=False))
            offsprings.append(
                parents[i][0:idx1] + [(parents[1 - i][idx1][0], parents[i][idx1][1], parents[i][idx1][2])] + parents[i][
                    idx1 + 1:idx2] + [(parents[1 - i][idx2][0], parents[i][idx2][1], parents[i][idx2][2])] + parents[i][
                    idx2 + 1:])

        elif way_offspring == 2:
            idx_job = random.randint(len(mom))
            indices = [idx for idx in range(len(parents[i])) if parents[i][idx][1] == parents[i][idx_job][1]]
            place = indices.index(idx_job)
            offspring = [operation for operation in parents[i]]
            if indices[place] != len(mom) - 1 and place != len(indices) - 1 and indices[place] + 1 != indices[
                place + 1]:
                offspring.insert(random.choice(range(indices[place] + 1, indices[place + 1]), size=1)[0],
                                 offspring.pop(idx_job))
            offsprings.append(offspring)

        elif way_offspring == 3:
            idx1, idx2 = random.choice([i for i in range(len(mom))], size=2, replace=False)
            offsprings.append(parents[i][0:idx1] + [
                (random.choice([machine for machine in m if machine != parents[i][idx1][0]]), parents[i][idx1][1],
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
            rand_operation = move_candidate[random.randint(len(move_candidate))]
            new_operation = (machine_min, rand_operation[1], rand_operation[2])
            idx = parents[i].index(rand_operation)
            offsprings.append(parents[i][0:idx] + [new_operation] + parents[i][idx + 1:])

        else:  # Do not reach
            offsprings = 0
    return offsprings

def select_pop(origin, ini_pop, way_select_pop):

    if way_select_pop == 0: # Binary tournament
        indices = [i for i in range(len(ini_pop))]
        candidates = []
        while len(indices) > 0:
            if len(indices) < 2:
                candidates.append(indices)
                break
            else:
                candidates.append([indices.pop(random.randint(len(indices))) for _ in range(2)])
        new_candidates = [versus(origin, [ini_pop[idx] for idx in candidate]) for candidate in candidates]

        if len(new_candidates) > 2:
            return select_pop(origin, new_candidates, 0)
        else:
            return new_candidates

    elif way_select_pop == 1: # n-Size tournament
        indices = [i for i in range(len(ini_pop))]
        candidates = []
        while len(indices) > 0:
            if len(indices) >= 3:
                n_size = random.randint(2, len(indices))
            else:
                n_size = len(indices)
            if len(indices) < n_size:
                candidates.append(indices)
                break
            else:
                candidates.append([indices.pop(random.randint(len(indices))) for _ in range(n_size)])
        new_candidates = [versus(origin, [ini_pop[idx] for idx in candidate]) for candidate in candidates]
        if len(new_candidates) == 2:
            return new_candidates
        else:
            return select_pop(origin, new_candidates, 1)

    elif way_select_pop == 2:  # Linear ranking
        tmp = sorted(ini_pop, key=lambda case: calculate(origin, case))
        idx1, idx2 = random.choice([i for i in range(0, len(ini_pop))], size=2, replace=False, p=[2 * i / (len(tmp) * (len(tmp) + 1)) for i in range(1, len(tmp) + 1)])
        return tmp[idx1], tmp[idx2]

    else:  # Do not reach
        return 0

def initial_pop(origin, m, jo, assign, seq):

    way_assign = random.choice([i for i in range(len(assign))], size = 1, p = assign)
    popped = []

    if way_assign == 0: # The Global Minimum
        tmp_set = {machine :
                       {job :
                            {operation : getattr(origin,f"{machine}{job}{operation}") for operation in jo[job]}
                        for job in jo}
                   for machine in m}

        for _ in range(sum(len(jo[job]) for job in jo)):
            plus_time, new_machine, new_job, new_operation = 99999, 0, 0, 0
            for job in tmp_set[m[0]]:
                for operation in tmp_set[m[0]][job]:
                    for machine in m:
                        if tmp_set[machine][job][operation] < plus_time:
                            plus_time, new_machine, new_job, new_operation = tmp_set[machine][job][operation], machine, job, operation

            popped.append((new_machine, new_job, new_operation))

            for machine in tmp_set:
                tmp_set[machine][new_job].pop(new_operation)
            for job in tmp_set[new_machine]:
                for operation in tmp_set[new_machine][job]:
                    tmp_set[new_machine][job][operation] += plus_time

    elif way_assign == 1: # Randomly Permute Jobs and Machins
        random_machine_seq = random.choice(m, size=len(m), replace=False)
        random_job_seq = random.choice([job for job in jo], size=len(jo), replace=False)
        tmp_set = {machine:
                       {job:
                            {operation: getattr(origin, f"{machine}{job}{operation}") for operation in jo[job]}
                        for job in random_job_seq}
                   for machine in random_machine_seq}

        for job in random_job_seq:
            for operation in tmp_set[m[0]][job]:
                plus_time, new_machine, new_job, new_operation = 999999, 0, 0, 0
                for machine in random_machine_seq:
                    if tmp_set[machine][job][operation] < plus_time:
                        plus_time, new_machine, new_job, new_operation = tmp_set[machine][job][
                            operation], machine, job, operation
                popped.append((new_machine, new_job, new_operation))

                for job_tmp in jo:
                    for operation_tmp in tmp_set[m[0]][job_tmp]:
                        tmp_set[new_machine][job_tmp][operation_tmp] += plus_time

    else: # Do not reach
        popped.append(0)
    
    way_seq = random.choice([i for i in range(len(seq))], size = 1, p = seq)
    set_tmp = []
    length = sum(len(jo[job]) for job in jo)

    if way_seq == 0: # Randomly select a job
        indices = list(random.choice(range(length), size=length, replace=False))
        while len(set_tmp) < length:
            for idx in indices:
                selected = popped[idx]
                if (jo[selected[1]].index(selected[2]) == 0
                    or jo[selected[1]].index(selected[2]) - 1 in [jo[operation[1]].index(operation[2]) for operation in set_tmp if operation[1] == selected[1]]):
                    set_tmp.append(selected)
                    indices.remove(idx)

    elif way_seq == 1: # Most Work Remaining(MWR)
        reference = {job: [[], 0] for job in jo}
        for operation in popped:
            reference[operation[1]][0].append(operation)
            reference[operation[1]][0].sort(key=lambda job: jo[job[1]].index(job[2]))
            reference[operation[1]][1] += getattr(origin, f"{operation[0]}{operation[1]}{operation[2]}")

        reference_job = [job for job in reference]
        while len(set_tmp) < length:
            reference_job.sort(key=lambda job: reference[job][1], reverse=True)
            set_tmp.append(reference[reference_job[0]][0].pop(0))
            reference[reference_job[0]][1] -= getattr(origin,
                                                      f"{set_tmp[-1][0]}{set_tmp[-1][1]}{set_tmp[-1][2]}")

    elif way_seq == 2: # Most Number of Operations Remaining(MOR)
        reference = {job: [[], 0] for job in jo}
        for operation in popped:
            reference[operation[1]][0].append(operation)
            reference[operation[1]][0].sort(key=lambda job: jo[job[1]].index(job[2]))
            reference[operation[1]][1] += 1

        reference_job = [job for job in reference]
        while len(set_tmp) < length:
            reference_job.sort(key=lambda job: reference[job][1], reverse=True)
            set_tmp.append(reference[reference_job[0]][0].pop(0))
            reference[reference_job[0]][1] -= 1

    else: # Do not reach
        set_tmp = 0

    return set_tmp

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

class JOBS:
    def __init__(self):
        pass
def ini_op_set(ini_set):
    original = JOBS
    for machine in ini_set:
        for job in ini_set[machine]:
            for operation in ini_set[machine][job]:
                setattr(original, f"{machine}{job}{operation}", ini_set[machine][job][operation])

    for machine in ini_set:
        print(machine)
        print(ini_set[machine])
    print()

    machines = list(ini_set)
    jobs_and_operations = {job : list(ini_set[machines[0]][job]) for job in ini_set[machines[0]]}

    return original, machines, jobs_and_operations

def start():
    # Parameter Input / You can use your custom Job set including Machine, Job, Operation Information
    params = {"pop_size": 10, "num_of_gens": 35, "ini_assign": [0.1, 0.9], "ini_seq": [0.2, 0.4, 0.4], "crossover": [0.45, 0.45, 0.02, 0.02, 0.06]}
    machines, jobs, maximum_operation, longest_duration = 4, 4, 4, 9
    operations = [random.randint(2, maximum_operation + 1) for _ in range(jobs)]
    ini_set = {"M%d" % (machine + 1)
               : {"J%d" % (job + 1)
                  : {"O%d" % (operation + 1): random.randint(1, longest_duration + 1)
                     for operation in range(operations[job])}
                  for job in range(jobs)}
               for machine in range(machines)}

    original, machines, jobs_and_operations = ini_op_set(ini_set)

    ini_pop = [initial_pop(origin=original, m=machines, jo=jobs_and_operations, assign=params["ini_assign"], seq=params["ini_seq"])
               for _ in range(params["pop_size"])]

    generations, best_child, horizon = {}, 0, 9999999
    for Gen in range(1, params["num_of_gens"] + 1):
        offsprings = []
        mother, father = select_pop(original, ini_pop, random.randint(3))
        for _ in range(params["pop_size"]):
            offspring = generate_offsprings(original, mother, father, params["crossover"], machines)
            offsprings.extend(offspring)

        candidate = versus(original, offsprings)
        score_candidate = calculate(original, candidate)

        if score_candidate < horizon:
            best_child = candidate
            horizon = score_candidate

        generations[f"Gen {Gen}"] = horizon, best_child

        ini_pop = sorted(ini_pop + offsprings, key=lambda case: calculate(original, case))[0:params["pop_size"]]
    return generations

if __name__ == "__main__":
    result = start()

    for gen in result:
        print(gen)
        print(result[gen])
    print()

    graph(result)