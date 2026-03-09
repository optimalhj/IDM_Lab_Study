from numpy import random

class JOBS:
    def __init__(self):
        pass

def modify_data(ini_job):
    horizon, new_machine, new_job, new_operation = 99999, 0, 0, 0

    for job in ini_job[list(Ini_Job_Set)[0]].keys():
        for operation in ini_job[list(Ini_Job_Set)[0]][job]:
            for machine in ini_job:
                if ini_job[machine][job][operation] < horizon:
                    new_machine = machine
                    new_job = job
                    new_operation = operation
                    horizon = ini_job[machine][job][operation]

    plus_time = ini_job[new_machine][new_job][new_operation]

    for machine in ini_job:
        ini_job[machine][new_job].pop(new_operation)
    for job in ini_job[new_machine]:
        for operation in ini_job[new_machine][job]:
            ini_job[new_machine][job][operation] += plus_time
    return new_machine, new_job, new_operation

def start(origin, ini_job, Num_of_Pop = 5):
    order_per_job = {job : list(ini_job[list(ini_job)[0]][job]) for job in ini_job[list(ini_job)[0]]}
    assigned = [modify_data(ini_job)
                for _ in range(sum(len(ini_job[machine][job])
                for job in Ini_Job_Set[list(ini_job)[0]]))]
    print(assigned)

    sets = []

    # Randomly select a job
    for _ in range(int(Num_of_Pop * 0.2)):
        set_tmp = []
        indices = list(random.choice(range(len(assigned)), size = len(assigned), replace = False))
        while len(set_tmp) < len(assigned):
            for idx in indices:
                selected = assigned[idx]
                if order_per_job[selected[1]].index(selected[2]) == 0 or order_per_job[selected[1]].index(selected[2]) - 1 in [order_per_job[operation[1]].index(operation[2]) for operation in set_tmp if operation[1] == selected[1]]:
                    set_tmp.append(selected)
                    indices.remove(idx)
        sets.append(set_tmp)

    # Most Work Remaining(MWR)
    for _ in range(int(Num_of_Pop * 0.4)):
        set_tmp = []
        reference = {job : [[],0] for job in order_per_job}
        for operation in assigned:
            reference[operation[1]][0].append(operation)
            reference[operation[1]][0].sort(key = lambda job : order_per_job[job[1]].index(job[2]))
            reference[operation[1]][1] += getattr(origin,"%s%s%s"%(operation[0],operation[1],operation[2]))
        reference_job = [job for job in reference]
        while len(set_tmp) < len(assigned):
            reference_job.sort(key = lambda job : reference[job][1], reverse = True)
            destroyed = reference[reference_job[0]][0].pop(0)
            reference[reference_job[0]][1] -= getattr(origin, "%s%s%s"%(destroyed[0],destroyed[1],destroyed[2]))
            set_tmp.append(destroyed)
        sets.append(set_tmp)

    # Most number of Operations Remaining(MOR)
    for _ in range(int(Num_of_Pop * 0.4)):
        set_tmp = []
        reference = {job : [[],0] for job in order_per_job}
        for operation in assigned:
            reference[operation[1]][0].append(operation)
            reference[operation[1]][0].sort(key=lambda job: order_per_job[job[1]].index(job[2]))
            reference[operation[1]][1] += 1
        reference_job = [job for job in reference]
        while len(set_tmp) < len(assigned):
            reference_job.sort(key = lambda job : reference[job][1], reverse = True)
            destroyed = reference[reference_job[0]][0].pop(0)
            reference[reference_job[0]][1] -= 1
            set_tmp.append(destroyed)
        sets.append(set_tmp)

def initial_pop(ini_job):
    origin = JOBS()
    for machine in ini_job:
        for job in ini_job[machine]:
            for operation in ini_job[machine][job]:
                setattr(origin,
                        "%s%s%s" % (machine, job, operation),
                        ini_job[machine][job][operation])
    return start(origin, ini_job)

if __name__ == "__main__":

    Machines = 4
    Jobs = 4
    Maximum_operation = 4
    Operations = [random.randint(2, Maximum_operation + 1) for job in range(Jobs)]
    Longest_duration = 9

    Ini_Job_Set = {"M%d" % (machine + 1)
                   : {"J%d" % (job + 1)
                      : {"O%d" % (operation + 1) : random.randint(1, Longest_duration + 1)
                         for operation in range(Operations[job])}
                      for job in range(Jobs)}
                   for machine in range(Machines)}
    for machine in Ini_Job_Set:
        print(machine, "\n", Ini_Job_Set[machine])
    print()

    initial_pop(Ini_Job_Set)