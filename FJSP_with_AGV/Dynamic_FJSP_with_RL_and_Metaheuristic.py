import numpy as np
from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque

num_job, max_num_op, num_machines, num_AGV, max_time = 4, 4, 3, 3, 8
params = {"pop_size": 10, "mating_pool": 10, "num_of_gens": 1, "s_max": 2}
train_params = {"max_len": 20}

class Q_net(nn.Module):
    def __init__(self, in_dim, out_dim=5):
        super(Q_net, self).__init__()
        self.layer1 = nn.Linear(in_dim, out_dim)
    def forward(self, status):
        action = self.layer1(status)
        return action

class Memory():
    def __init__(self):
        self.memory = deque(maxlen=train_params["max_len"])

    def train(self, status):
        self.memory.append(status)

def select_mp(populations):
    index = list(range(params["pop_size"]))
    way = rd.randint(3)
    if way == 0:  # Binary tournament
        return populations[min(rd.choice(index, size=2, replace=False), key=lambda idx: populations[idx][1])][0]
    elif way == 1:  # n-Size tournament
        return populations[min(rd.choice(index, size=rd.randint(3, max(4, int(params["pop_size"] / 2.5))), replace=False), key=lambda idx: populations[idx][1])][0]
    elif way == 2:  # Linear ranking
        return populations[rd.choice(index, size=1, p=[2 * i / (params["pop_size"] * (params["pop_size"] + 1)) for i in range(params["pop_size"], 0, -1)])[0]][0]
    else: return [] # Do not reach

def correct_procedure(ini_set, os_vector, ms_vector):
    seq, info_op = os_vector.copy(), {job: {op: 0 for op in ini_set[job]} for job in ini_set.keys()}
    for l in range(len(seq)):
        job = seq[l]
        op = min(ini_set[job], key=lambda op: info_op[job][op])
        info_op[job][op] += 1
        m = ms_vector[l] if len(ms_vector) else str(rd.choice(list(ini_set[job][op])))
        seq[l] = (job, op, m)
    return seq

def encoding(seq):
    os_vector, ms_vector = [], []
    for job, _, m in seq:
        os_vector.append(job)
        ms_vector.append(m)
    return os_vector, ms_vector

def decoding(process, setup, ini_set, machines, vectors):
    seq, s_job, s_m = correct_procedure(ini_set, vectors[0], vectors[1]), {job: 0 for job in ini_set.keys()}, {m: [0, ()] for m in machines}

    for job, op, m in seq:
        now = max(s_job[job], s_m[m][0])
        if len(s_m[m][1]):
            now += getattr(setup, f"{s_m[m][1][0]}{s_m[m][1][1]}{job}{op}")
        else:
            now += 0
        now += getattr(process, f"{job}{op}{m}")
        s_job[job], s_m[m] = now, [now, (job, op)]

    reward = sum(getattr(process, f"{job}{op}{m}") for job, op, m in seq) / sum(1 if s_m[m][0] else 0 for m in s_m.keys()) / max(s_m[m][0] for m in s_m.keys())
    print(f"{sum(getattr(process, f"{job}{op}{m}") for job, op, m in seq)} / ( {sum(1 if s_m[m][0] else 0 for m in s_m.keys())} * {max(s_m[m][0] for m in s_m.keys())} ) = {reward}")

    return encoding(seq), reward

def mutation(process, setup, ini_set, machines, pr):
    os_vector, ms_vector = pr[0].copy(), pr[1].copy()
    way = rd.randint(3)
    if way == 0:
        idx1, idx2 = rd.choice(range(len(os_vector)), size=2, replace=False)
        os_vector[idx1], os_vector[idx2], ms_vector[idx1], ms_vector[idx2] = os_vector[idx2], os_vector[idx1], ms_vector[idx2], ms_vector[idx1]
    elif way == 1:
        idx1, idx2 = sorted(rd.choice(range(len(os_vector)), size=2, replace=False))
        if idx1 != 0: os_vector[idx1:idx2 + 1], ms_vector[idx1:idx2 + 1] = os_vector[idx2:idx1 - 1:-1], ms_vector[idx2:idx1 - 1:-1]
        else: os_vector[idx1:idx2 + 1], ms_vector[idx1:idx2 + 1] = os_vector[idx2::-1], ms_vector[idx2::-1]
    elif way == 2:
        idx = rd.choice(range(len(os_vector)))
        job, op, m_tmp = correct_procedure(ini_set, os_vector, ms_vector)[idx]
        ms_vector[idx] = rd.choice([m for m in ini_set[job][op] if m != m_tmp]) if len(ini_set[job][op]) != 1 else m_tmp
    else: pass # Do not reach
    return decoding(process, setup, ini_set, machines, (os_vector, ms_vector))

def crossover(process, setup, ini_set, machines, pr1, pr2):
    os_vector, ms_vector, os_vector_pair, ms_vector_pair = pr1[0].copy(), pr1[1].copy(), pr2[0].copy(), pr2[1].copy()
    way = rd.randint(3)

    if len(os_vector) <= 3 and way == 2: way = 1
    if len(os_vector) <= 2 and way == 1: way = 0
    if way == 0:
        idx = rd.randint(len(os_vector))
        chosen_job = os_vector[idx]
        points = [i for i in range(len(os_vector)) if os_vector[i] == chosen_job]
    elif way == 1:
        idx1, idx2 = sorted(rd.choice(list(range(1, max(2, len(os_vector) - 1))), size=2, replace=False))
        points = [i for i in range(len(os_vector)) if i < idx1 or i >= idx2]
    elif way == 2:
        indices = [0] + sorted(rd.choice(list(range(1, max(2, len(os_vector) - 1))), size=rd.randint(3, max(4, len(os_vector)//2)), replace=False)) + [len(os_vector) - 1]
        points = []
        for l in range(len(indices) - 1):
            if l % 2 == 0:
                points.extend(list(range(indices[l], indices[l + 1])))
        if len(indices) % 2 == 1:
            points.extend(list(range(indices[len(indices) - 1], len(os_vector))))
    else: points = [] # Do not reach

    new_os_vector, new_ms_vector = [], []
    points_pair = []

    tmp_set = {job: 0 for job in ini_set.keys()}
    for point in points:
        tmp_set[os_vector[point]] += 1
    for l in range(len(os_vector_pair)):
        if tmp_set[os_vector_pair[l]] > 0:
            tmp_set[os_vector_pair[l]] -= 1
        else: points_pair.append(l)

    seq_info = correct_procedure(ini_set, os_vector, ms_vector)

    for i in range(len(os_vector)):
        if i in points:
            new_os_vector.append(os_vector[i])
            new_ms_vector.append(ms_vector[i])

        else:
            idx = points_pair.pop(0)
            new_os_vector.append(os_vector_pair[idx])
            new_ms_vector.append(ms_vector_pair[idx])

    return decoding(process, setup, ini_set, machines, (new_os_vector, new_ms_vector))

def graph_gen(final):

    plt.plot([f"Gen{i+1}" for i in range(len(final))], final)

    plt.xticks(rotation=45, fontsize=5)
    plt.title("Makespan of FJSP")

    plt.xlabel("Gen")
    plt.ylabel("Tardiness")

    plt.show()

def graph_makespan(ini_set, machines, best):
    seq, obj, se_process, se_setup, se_load_agv, se_unload_agv = best
    seq = correct_procedure(ini_set, seq[0], seq[1])
    _, ax = plt.subplots()
    s_job = list(ini_set.keys())
    for m in machines:
        ax.barh(m, 0, left=0)
    for l in range(len(seq)):
        job, op, m = seq[l]
        operating = se_process[job][op][1] - se_process[job][op][0]
        start_process = se_process[job][op][0]
        ax.barh(m, operating, left=start_process, color=plt.get_cmap('tab20', len(s_job))(s_job.index(job)), edgecolor='black')
        ax.text(start_process + operating / 2, m, f"{job}\n{op}\n({operating})", va='center', ha='center', color='black', fontsize=5)

    for m in se_setup.keys():
        for st_setup, ed_setup in se_setup[m]:
            setup_ing = ed_setup - st_setup
            ax.barh(m, setup_ing, left=st_setup, color='white', edgecolor='black')
    ax.set_xticks([i for i in range(int(obj) + 2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def dynamic_fjsp(process, setup, ini_set, machines):
    ini_os = [job for job in ini_set.keys() for _ in range(len(ini_set[job].keys()))]
    history, q_net, memory = [], Q_net(in_dim=len(ini_os)), Memory()
    for gen in range(1, params["num_of_gens"] + 1):
        pops = sorted([decoding(process, setup, ini_set, machines,(rd.permutation(ini_os).tolist(), [])) for _ in range(params["pop_size"])], key=lambda case: case[1], reverse=True)
        for pop in pops:
            print(pop[1], pop[0])
        t = 0
        indices = list(range(params["mating_pool"]))
        while t < params["mating_pool"]//2:
            X = []
            for i in range(1, len(machines)):
                m = machines[i]
                N_q = 0
                for _, _, m_tmp in pop:
                    if m_tmp == m: N_q += 1
                j = rd.randint(N_q)
                X.append(j)


            t += 1
        offsprings = []
        mating_pool = [select_mp(pops) for _ in range(params["mating_pool"])]
        indices = list(range(params["mating_pool"]))
        for _ in range(len(mating_pool) // 2):
            pr1, pr2 = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            offsprings.append(crossover(process, setup, ini_set, machines, mating_pool[pr1], mating_pool[pr2]) if rd.random() < 0.5 else mutation(process, setup, ini_set, machines, mating_pool[pr1]))
        if pops[0][1] > offsprings[0][1]:
            pops = sorted(pops+offsprings, key=lambda case: case[1])[:params["pop_size"]]
        history.append(pops[0][1])
    # graph_gen(history)
    # graph_makespan(ini_set, machines, pops[0])

class Process:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(processes, setups, machines_tmp):
    process, setup, ini_set, machines = Process(), SetUp(), {}, []
    for job in processes.keys():
        print(job)
        ini_set[job] = {}
        for op in processes[job].keys():
            print(f"\t{op}")
            ini_set[job][op] = []
            for m in processes[job][op].keys():
                print(f"\t\t{m} : {processes[job][op][m]}", end="")
                if m not in machines:
                    machines.append(m)
                ini_set[job][op].append(m)
                setattr(process, f"{job}{op}{m}", processes[job][op][m])
            print()

    machines.sort(key=lambda machine: machines_tmp.index(machine))

    for job1, op1 in setups:
        for job2, op2 in setups:
            setattr(setup, f"{job1}{op1}{job2}{op2}", setups[(job1, op1)][(job2, op2)])

    dynamic_fjsp(process, setup, ini_set, machines)

def main():
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {f"Job{j}": {f"Op{o + 1}": {m : rd.randint(1, max_time + 1) for m in sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m))} for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    start(processes, setups, machines)

if __name__ == "__main__":
    main()