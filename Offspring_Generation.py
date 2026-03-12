import Makespan_Calculation
from Initial_coding_set import setting
import Initial_Population
import Population_Selection
from numpy import random

def pox(mom_cho, dad_cho):
    offsprings = []
    parents = (mom_cho, dad_cho)
    for i in range(2):
        jobs = []
        for operation in parents[i]:
            if operation[1] not in jobs:
                jobs.append(operation[1])
        fixed_job = random.choice(jobs, size=1)
        not_fixed_operation = [operation for operation in parents[1-i] if operation[1] != fixed_job]
        offspring = []
        for idx in range(len(parents[i])):
            if parents[i][idx][1] == fixed_job:
                offspring.append(parents[i][idx])
            else:
                offspring.append(not_fixed_operation.pop(0))
        offsprings.append(offspring)
    return offsprings
def assignment_crossover(mom_cho,dad_cho):
    offsprings = []
    parents = (mom_cho, dad_cho)
    for i in range(2):
        idx1, idx2 = sorted(random.choice([i for i in range(len(mom_cho))], size=2, replace=False))
        offsprings.append(parents[i][0:idx1] + [(parents[1-i][idx1][0],parents[i][idx1][1],parents[i][idx1][2])] + parents[i][idx1 + 1:idx2] + [(parents[1-i][idx2][0],parents[i][idx2][1],parents[i][idx2][2])] + parents[i][idx2 + 1:])
    return offsprings

def pps(mom_cho,dad_cho):
    offsprings = []
    parents = (mom_cho, dad_cho)
    for i in range(2):
        idx_job = random.randint(len((mom_cho)))
        indices = [idx for idx in range(len(parents[i])) if parents[i][idx][1] == parents[i][idx_job][1]]
        place = indices.index(idx_job)
        offspring = [operation for operation in parents[i]]
        if indices[place] != len(mom_cho) - 1 and place != len(indices) - 1 and indices[place] + 1 != indices[place + 1]:
            offspring.insert(random.choice(range(indices[place] + 1, indices[place + 1]), size = 1)[0], offspring.pop(idx_job))
        offsprings.append(offspring)

    return offsprings
def assignment_mutation(ini_set, mom_cho, dad_cho):
    offsprings = []
    parents = (mom_cho, dad_cho)
    for i in range(2):
        idx1, idx2 = random.choice([i for i in range(len(mom_cho))], size=2, replace=False)
        offsprings.append(parents[i][0:idx1]+[(random.choice([machine for machine in ini_set if machine != parents[i][idx1][0]]), parents[i][idx1][1], parents[i][idx1][2])]+parents[i][idx1 + 1:])
    return offsprings

def assignment_intelligent_mutation(origin, ini_set, mom_cho,dad_cho):
    offspring = []
    for parent in (mom_cho, dad_cho):
        machine_load = {machine: 0 for machine in ini_set}
        machine_max = list(ini_set)[0],0
        for operation in parent:
            machine_load[operation[0]] += getattr(origin, "%s%s%s"%(operation[0],operation[1],operation[2]))
            if machine_load[operation[0]] > machine_max[1]:
                machine_max = operation[0], machine_load[operation[0]]
        machine_min = list(machine_load)[list(machine_load.values()).index(min(machine_load.values()))]
        move_candidate = [operation for operation in parent if operation[0] == machine_max[0]]
        rand_operation = move_candidate[random.randint(len(move_candidate))]
        new_operation = (machine_min, rand_operation[1], rand_operation[2])
        idx = parent.index(rand_operation)
        offspring.append(parent[0:idx] + [new_operation] + parent[idx + 1:])
    return offspring

def way_select(origin, ini_job, ini_set, mom_cho, dad_cho, rates):

    way_operator = random.choice([i for i in range(len(rates))], size=1, p=rates, replace=False)
    way_operator = 3
    if way_operator == 0:
        offspring = pox(mom_cho, dad_cho)
    elif way_operator == 1:
        offspring = assignment_crossover(mom_cho,dad_cho)
    elif way_operator == 2:
        offspring = pps(mom_cho,dad_cho)
    elif way_operator == 3:
        offspring = assignment_mutation(ini_set, mom_cho, dad_cho)
    elif way_operator == 4:
        offspring = assignment_intelligent_mutation(origin, ini_set, mom_cho,dad_cho)
    else: # Do not reach
        offspring = 0
    return offspring

def start(origin, ini_pop, ini_set, crossover, pop_size):
    offsprings = []
    for _ in range(pop_size):
        mother, father = Population_Selection.start(origin, ini_pop)
        offsprings.extend(way_select(origin, ini_pop, ini_set, mother, father, crossover))
    return offsprings

if __name__ == "__main__":
    Ini_Set, params = setting()
    Original, Initial_Pop = Initial_Population.start(Ini_Set,
                                        population_size = params["pop_size"],
                                        ini_assign = params["ini_assign"],
                                        ini_seq = params["ini_seq"])
    result = start(Original, Initial_Pop, Ini_Set, params["crossover"], params["pop_size"])

    count = 0
    total_count = 0
    for off in result:
        print(Makespan_Calculation.calculate(Original, off), off)
        total_count += 1
        if off != result[0]:
            count += 1
    print("not same rate =",count/total_count*100)