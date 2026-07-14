import numpy as np
from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
import torch.optim as optim
from collections import deque

num_job, max_num_op, num_machines, num_AGV, max_time = 4, 4, 3, 3, 8
params = {"pop_size": 10, "mating_pool": 10, "num_of_gens": 1}
dqn_params = {"LR": 0.001, "GAMMA": 0.1, "BATCH_SIZE": 10, "MEMORY_SIZE": 20}

class Process:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def main():
    machines_tmp = [f"M{i}" for i in range(1, num_machines + 1)]
    processes = {f"Job{j}": {f"Op{o + 1}": {m : rd.randint(1, max_time + 1) for m in sorted(rd.choice(machines_tmp, size=rd.randint(2, len(machines_tmp)), replace=False).tolist(), key=lambda m: machines_tmp.index(m))} for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    process, setup, ini_set, machines = Process(), SetUp(), {}, []
    for job in processes.keys():
        print(job)
        ini_set[job] = {}
        for op in processes[job].keys():
            print(f"\t{op}", end="\t")
            ini_set[job][op] = []
            for m in processes[job][op].keys():
                print(f"\t{m} : {processes[job][op][m]}", end="")
                if m not in machines: machines.append(m)
                ini_set[job][op].append(m)
                setattr(process, f"{job}{op}{m}", processes[job][op][m])
            print()
    machines.sort(key=lambda machine: machines_tmp.index(machine))

    for job1, op1 in setups:
        for job2, op2 in setups: setattr(setup, f"{job1}{op1}{job2}{op2}", setups[(job1, op1)][(job2, op2)])

    seq = []
    os_vector, ms_vector = rd.permutation([job for job in ini_set.keys() for _ in range(len(ini_set[job]))]).tolist(), []
    tmp_set = {job : 0 for job in ini_set.keys()}
    for job in os_vector:
        ms_vector.append(str(rd.choice(list(ini_set[job][list(ini_set[job])[tmp_set[job]]]))))
        tmp_set[job] += 1



if __name__ == "__main__":
    main()