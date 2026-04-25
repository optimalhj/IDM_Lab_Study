from numpy import random as rd
import matplotlib.pyplot as plt

def three_phase_decode(chromosome):

    # First Phase : Job Index Assignment Phase
    count_optype = {}
    for operation in chromosome:
        if (operation[0],operation[2]) not in count_optype:
            count_optype[(operation[0],operation[2])] = 1
    s_o = []
    for l in range(len(chromosome)):
        o_jk = chromosome[l]
        u = count_optype[o_jk]
        s_o.append((i, ))

class Duration:
    def __init__(self):
        pass
class SetUp:
    def __init__(self):
        pass
def start(params, durations, setups, machines_tmp):
    duration, setup, ini_set, machines = Duration(), SetUp(), {}, []

    for job_type in durations.keys():
        ini_set[job_type] = {"jobs": durations[job_type]["jobs"], "ops": {}}
        for op in durations[job_type]["ops"]:
            ini_set[job_type]["ops"][op] = durations[job_type]["ops"][op][0]
            setattr(duration, f"{job_type}{op}", durations[job_type]["ops"][op][1])
            for m in durations[job_type]["ops"][op][0]:
                if m not in machines:
                    machines.append(m)
    machines.sort(key=lambda machine : machines_tmp.index(machine))

    for job_type1 in ini_set:
        for op1 in ini_set[job_type1]["ops"]:
            for job_type2 in ini_set:
                for op2 in ini_set[job_type2]["ops"]:
                    setattr(setup, f"{job_type1}{op1}{job_type2}{op2}", setups[(job_type1, op1)][(job_type2, op2)])

    ini_pop = [(job_type, job, op) for job_type in ini_set for job in ini_set[job_type]["jobs"] for op in ini_set[job_type]["ops"].keys()]
    print(ini_pop)
    three_phase_decode(ini_pop)
    """
    for gen in range(params["num_of_gens"]):
        print(f"Generation {gen + 1}")
    """
def main():
    # Parameter Input
    params = {"pop_size": 10, "num_of_gens": 35, "ini_assign": [0.1, 0.9], "ini_seq": [0.2, 0.4, 0.4], "crossover": [0.45, 0.45, 0.02, 0.02, 0.06]}
    num_job_types = 2
    max_num_job = 3
    max_num_op = 3
    num_machines = 3
    max_time = 6
    max_setup_time = max(max_time // 2, 1)

    machines = [f"M{i}" for i in range(1, num_machines + 1)]
    durations = {job_type: {"jobs": [f"Job{j + 1}" for j in range(rd.randint(2, max_num_job + 1))],
                            "ops": {f"Op{o + 1}":
                                        [sorted(rd.choice(machines, size=rd.randint(1, len(machines)), replace=False),
                                                key=lambda m: machines.index(m)),
                                         rd.randint(2, max_num_op + 1)]
                                    for o in range(rd.randint(1, max_num_op + 1))}}
                 for job_type in [f"Job_Type{i + 1}" for i in range(rd.randint(2, num_job_types + 1))]}

    every_op = [(job_type, op) for job_type in durations.keys() for op in
                durations[job_type][list(durations[job_type])[1]]]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max_setup_time + 1) for op2 in every_op} for op1 in
              every_op}

    start(params, durations, setups, machines)

if __name__ == "__main__":
    main()