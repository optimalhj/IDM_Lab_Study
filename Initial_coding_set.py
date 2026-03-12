from numpy import random

def setting():
    params = {"pop_size": 50,
              "num_of_gens": 35,
              "ini_assign": [0.1, 0.9],
              "ini_seq": [0.2, 0.4, 0.4],
              "crossover": [0.45, 0.45, 0.02, 0.02, 0.06]}

    machines = 4
    jobs = 4
    maximum_operation = 4
    operations = [random.randint(2, maximum_operation + 1) for job in range(jobs)]
    longest_duration = 9

    ini_set = {"M%d" % (machine + 1)
                   : {"J%d" % (job + 1)
                      : {"O%d" % (operation + 1): random.randint(1, longest_duration + 1)
                         for operation in range(operations[job])}
                      for job in range(jobs)}
                   for machine in range(machines)}

    for machine in ini_set:
        print(machine, "\n", ini_set[machine])
    print()

    return ini_set, params

def start():
    return setting()

if __name__ == "__main__":
    result = start()