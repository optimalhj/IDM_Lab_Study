from numpy import random
from copy import deepcopy as dc
from Initial_coding_set import setting

def global_minimum(ini_job_tmp, order_per_job):
    ini_job = dc(ini_job_tmp)
    first_set = []
    for _ in range(sum(len(order_per_job[job]) for job in order_per_job)):
        plus_time, new_machine, new_job, new_operation = 99999, 0, 0, 0
        for job in ini_job[list(ini_job)[0]].keys():
            for operation in ini_job[list(ini_job)[0]][job]:
                for machine in ini_job:
                    if ini_job[machine][job][operation] < plus_time:
                        plus_time, new_machine, new_job, new_operation = ini_job[machine][job][operation], machine, job, operation
        first_set.append((new_machine, new_job, new_operation))
        for machine in ini_job:
            ini_job[machine][new_job].pop(new_operation)
        for job in ini_job[new_machine]:
            for operation in ini_job[new_machine][job]:
                ini_job[new_machine][job][operation] += plus_time
    return first_set

def random_permutation(ini_job_tmp):
    ini_job = dc(ini_job_tmp)
    first_set = []
    random_machine_seq = random.choice(list(ini_job), size = len(ini_job), replace = False)
    random_job_seq = random.choice([job for job in ini_job[list(ini_job)[0]]], size = len(ini_job[list(ini_job)[0]]), replace = False)

    for job in random_job_seq:
        for operation in ini_job[random_machine_seq[0]][job]:
            plus_time, new_machine, new_job, new_operation = 999999, 0, 0, 0
            for machine in random_machine_seq:
                if ini_job[machine][job][operation] < plus_time:
                    plus_time, new_machine, new_job, new_operation = ini_job[machine][job][operation], machine, job, operation
            first_set.append((new_machine, new_job, new_operation))
            for job_tmp in random_job_seq:
                for operation_tmp in ini_job[random_machine_seq[0]][job_tmp]:
                    ini_job[new_machine][job_tmp][operation_tmp] += plus_time
    return first_set

def random_rule(ini_job, order_per_job):
    set_tmp = []
    indices = list(random.choice(range(len(ini_job)), size=len(ini_job), replace=False))
    while len(set_tmp) < len(ini_job):
        for idx in indices:
            selected = ini_job[idx]
            if (order_per_job[selected[1]].index(selected[2]) == 0
                    or order_per_job[selected[1]].index(selected[2]) - 1
                    in [order_per_job[operation[1]].index(operation[2]) for operation in set_tmp if operation[1] == selected[1]]):
                set_tmp.append(selected)
                indices.remove(idx)
    return set_tmp

def mwr_rule(origin, ini_job, order_per_job):
    set_tmp = []
    reference = {job : [[], 0] for job in order_per_job}
    for operation in ini_job:
        reference[operation[1]][0].append(operation)
        reference[operation[1]][0].sort(key=lambda job: order_per_job[job[1]].index(job[2]))
        reference[operation[1]][1] += getattr(origin, "%s%s%s" % (operation[0], operation[1], operation[2]))
    reference_job = [job for job in reference]
    while len(set_tmp) < len(ini_job):
        reference_job.sort(key=lambda job: reference[job][1], reverse=True)
        set_tmp.append(reference[reference_job[0]][0].pop(0))
        reference[reference_job[0]][1] -= getattr(origin, "%s%s%s" % (set_tmp[-1][0], set_tmp[-1][1], set_tmp[-1][2]))
    return set_tmp

def mor_rule(ini_job, order_per_job):
    set_tmp = []
    reference = {job: [[], 0] for job in order_per_job}
    for operation in ini_job:
        reference[operation[1]][0].append(operation)
        reference[operation[1]][0].sort(key=lambda job: order_per_job[job[1]].index(job[2]))
        reference[operation[1]][1] += 1
    reference_job = [job for job in reference]
    while len(set_tmp) < len(ini_job):
        reference_job.sort(key=lambda job: reference[job][1], reverse=True)
        set_tmp.append(reference[reference_job[0]][0].pop(0))
        reference[reference_job[0]][1] -= 1
    return set_tmp

def initial_pop(origin, ini_job, order_per_job, ini_assign, ini_seq):

    way_assign = random.choice([i for i in range(len(ini_assign))], size = 1, p = ini_assign)
    if way_assign == 0:
        ini_set = global_minimum(ini_job, order_per_job)
    elif way_assign == 1:
        ini_set = random_permutation(ini_job)
    else: # Do not reach
        ini_set = 0

    way_seq = random.choice([i for i in range(len(ini_seq))], size = 1, p = ini_seq)
    if way_seq == 0:
        ini_set = random_rule(ini_set, order_per_job)
    elif way_seq == 1:
        ini_set = mwr_rule(origin, ini_set, order_per_job)
    elif way_seq == 2:
        ini_set = mor_rule(ini_set, order_per_job)
    else: # Do not reach
        ini_set = 0
    return ini_set

class JOBS:
    def __init__(self):
        pass

def start(ini_job, population_size, ini_assign, ini_seq):
    original = JOBS
    for machine in ini_job:
        for job in ini_job[machine]:
            for operation in ini_job[machine][job]:
                setattr(original, "%s%s%s"%(machine, job, operation), ini_job[machine][job][operation])
    order_per_job = {job: list(ini_job[list(ini_job)[0]][job]) for job in ini_job[list(ini_job)[0]]}
    sets = []
    for _ in range(population_size):
        sets.append(initial_pop(original, ini_job, order_per_job,ini_assign, ini_seq))
    return original, sets

if __name__ == "__main__":

    Ini_Job_Set, params = setting()
    result = start(Ini_Job_Set, population_size=params["pop_size"],
                         ini_assign=params["ini_assign"], ini_seq=params["ini_seq"])

    print("Total :", len(result))
    for case in result:
        print(len(case), case)
