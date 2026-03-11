
from numpy import random

def setting():
    params = {"pop_size": 10,
              "num_of_gens": 40,
              "ini_assign": [0.1, 0.9],
              "ini_seq": [0.2, 0.4, 0.4],
              "crossover": [0.45, 0.45, 0.2, 0.2, 0.6]}

    Machines = 4
    Jobs = 4
    Maximum_operation = 4
    Operations = [random.randint(2, Maximum_operation + 1) for job in range(Jobs)]
    Longest_duration = 9

    Ini_Job_Set = {"M%d" % (machine + 1)
                   : {"J%d" % (job + 1)
                      : {"O%d" % (operation + 1): random.randint(1, Longest_duration + 1)
                         for operation in range(Operations[job])}
                      for job in range(Jobs)}
                   for machine in range(Machines)}
    for machine in Ini_Job_Set:
        print(machine, "\n", Ini_Job_Set[machine])
    print()

    return Ini_Job_Set, params

def start():
    return setting()

if __name__ == "__main__":
    result = start()