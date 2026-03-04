from numpy import random

Machines = 4
Jobs = 3
Maximum_operation = 5
Operations = [random.randint(2, Maximum_operation + 1) for job in range(Jobs)]
Longest_operation = 9

Ini_Job_Set = {"M%d" % (machine + 1)
               :{"O%d%d" % (job + 1, operation + 1) : random.randint(1, Longest_operation + 1)
                 for job in range(Jobs)
                 for operation in range(Operations[job])}
               for machine in range(Machines)}

for machine in Ini_Job_Set:
    print(machine, "\n", Ini_Job_Set[machine])
print()

def destroy_operation():
    horizon, new_machine , new_operation = Longest_operation * Machines * Maximum_operation, 0, 0
    for machine in Ini_Job_Set:
        for operation in Ini_Job_Set[machine]:
            if Ini_Job_Set[machine][operation] < horizon:
                new_machine = machine
                new_operation = operation
                horizon = Ini_Job_Set[machine][operation]
    return new_machine, new_operation

def modify_operator(job_tmp):
    m, op = job_tmp
    plus_time = Ini_Job_Set[m][op]
    for machine in Ini_Job_Set:
        Ini_Job_Set[machine].pop(op)
    for operation in Ini_Job_Set[m]:
        Ini_Job_Set[m][operation] += plus_time
    return job_tmp

def start():
    return [modify_operator(destroy_operation()) for _ in range(len(Ini_Job_Set[list(Ini_Job_Set.keys())[0]]))]

if __name__ == "__main__":
    result = start()
    print("Initial Sequence :")
    print(result)