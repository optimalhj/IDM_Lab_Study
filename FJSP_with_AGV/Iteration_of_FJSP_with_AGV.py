from FJSP_with_AGV import *

num_job, max_num_op, num_machines, max_time = 5, 5, 5, 10
params = {"pop_size": 10, "mating_pool": 10, "num_of_gens": 20, "s_max": 2}

def main():
    machines = [f"M{i}" for i in range(1, num_machines + 1)]
    processes = {f"Job{j}": {f"Op{o + 1}": [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m)), rd.randint(1, max_time + 1)] for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}
    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    for num_AGV in sorted([1,2,3,4,5,6]):
        agv = [f"AGV{i}" for i in range(0, num_AGV + 1)] + [[(m1, m2, 4, 3) if m1 != m2 else (m1, m2, 0, 0) for m1 in machines + ["LU"] for m2 in machines + ["LU"]]]
        start(processes, setups, machines, agv)

    return 0

if __name__ == '__main__':
    main()