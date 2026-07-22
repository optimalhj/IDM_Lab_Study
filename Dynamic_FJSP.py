import numpy as np
from numpy import random as rd
import itertools
from collections import deque

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
import torch.optim as optim

class Qnet(nn.Module):
    def __init__(self, in_dim, hidden1_dim, embed_dim, num_heads_dim, hidden2_dim, out_dim):
        super(Qnet, self).__init__()
        self.layer1 = GCNConv(in_dim, hidden1_dim)
        self.layer2 = GCNConv(hidden1_dim, embed_dim)
        self.layer3 = nn.MultiheadAttention(embed_dim, num_heads_dim, batch_first=True)
        self.layer4 = nn.Linear(num_heads_dim, hidden2_dim)
        self.layer5 = nn.Linear(hidden2_dim, out_dim)

    def forward(self, data_tensor):
        x = self.layer1(data_tensor.x, data_tensor.edge_index)
        x = self.layer2(x, data_tensor.edge_index)
        x = x.unsqueeze(0)
        x = self.layer3(x, x, x)[0]
        x = torch.mean(x.squeeze(0), dim=0, keepdim=True)
        x = F.relu(self.layer4(x))
        x = self.layer5(x)
        x = F.softmax(x, dim=-1)
        return x

class Memory:
    def __init__(self, mini_batch):
        self.memory = deque(maxlen=100)
        self.mini_batch = mini_batch
    def add_buffer(self, history):
        self.memory.append(history)

    def sample(self):
        s_lst, a_lst, r_lst, s_prime_lst = [], [], [], []
        for s, a, r, s_prime in [self.memory[i] for i in rd.choice(len(self.memory), size=min(len(self.memory), self.mini_batch), replace=False)]:
            s_lst.append(s)
            a_lst.append([a])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
        return s_lst, a_lst, r_lst, s_prime_lst
        #return torch.tensor(s_lst, dtype=torch.float), torch.tensor(a_lst), torch.tensor(r_lst, dtype=torch.float), torch.tensor(s_prime_lst, dtype=torch.float)

def disjunctive_graph(seq, se_process, se_setup): # seq to disjunctive_graph
    n_tensor, ve_tensor, job_info, m_info = [], [], {}, {}

    for l in range(len(seq)):
        job, op, m = seq[l]
        if job not in job_info: job_info[job] = []
        job_info[job].append(l)
        if m not in m_info: m_info[m] = []
        m_info[m].append(l)
        st_setup_tensor, ed_setup_tensor = se_process[job][op][0], se_process[job][op][0]
        for st_setup, ed_setup, _, _, job_tmp, op_tmp in se_setup[m]:
            if job == job_tmp and op == op_tmp:
                st_setup_tensor, ed_setup_tensor = st_setup, ed_setup
                break
        n_tensor.append((int(job.replace("Job", "")), int(op.replace("Op", "")), int(m.replace("M", "")), se_process[job][op][0], se_process[job][op][1], st_setup_tensor, ed_setup_tensor))

    conjunctive_arcs, disjunctive_arcs = [], []
    for job in job_info.keys():
        for l in range(len(job_info[job]) - 1): conjunctive_arcs.append((job_info[job][l], job_info[job][l + 1]))
    ve_tensor.extend(conjunctive_arcs)
    for m in m_info.keys():
        for l in range(len(m_info[m]) - 1):
            idx1, idx2 = m_info[m][l], m_info[m][l+1]
            if seq[idx1][0] != seq[idx2][0]: disjunctive_arcs.extend([(idx1, idx2), (idx2, idx1)])
    ve_tensor.extend(disjunctive_arcs)

    return Data(torch.tensor(n_tensor, dtype=torch.float), torch.tensor(ve_tensor, dtype=torch.long).t().contiguous())
def correct_seq(): # disjunctive_graph to seq
    return 0
def encoding(): # seq to disjunctive_graph
    return
def decoding(process, setup, ini_set, machines, seq):
    s_job, se_process, s_m, se_setup = {}, {}, {}, {}
    for job in ini_set.keys():
        s_job[job] = 0
        se_process[job] = {}
        for op in ini_set[job].keys():
            se_process[job][op] = [0, 0]
    for m in machines:
        s_m[m] = [0, ()]
        se_setup[m] = []

    for l in range(len(seq)):
        job, op, m = seq[l]
        now = max(s_job[job], s_m[m][0])
        if len(s_m[m][1]):
            setup_time = getattr(setup, f"{s_m[m][1][0]}{s_m[m][1][1]}{job}{op}")
            if setup_time:
                now += setup_time
                se_setup[m].append((now - setup_time, now, s_m[m][1][0], s_m[m][1][1], job, op))
        se_process[job][op][0] += now
        now += getattr(process, f"{job}{op}{m}")
        se_process[job][op][1] += now
        s_job[job], s_m[m] = now, [now, (job, op)]

    return disjunctive_graph(seq, se_process, se_setup), max(s_m[m][0] for m in machines), se_process, se_setup

def dynamic_fjsp(process, setup, ini_set, machines, params):
    qnet, qnet_target = [Qnet(in_dim=params["in_dim"], hidden1_dim=params["hidden1_dim"], embed_dim=params["embed_dim"], num_heads_dim=params["num_heads_dim"], hidden2_dim=params["hidden2_dim"], out_dim=params["out_dim"]) for _ in range(2)]
    optimizer, memory = optim.Adam(qnet.parameters(), lr=params["lr"]), Memory(params["mini_batch"])
    qnet_target.load_state_dict(qnet.state_dict())
    qnet_target.eval()

    ini_seq, entire_seq = rd.permutation([job for job in ini_set.keys() for _ in range(len(ini_set[job]))]).tolist(), []
    job_info = {job: 0 for job in ini_set.keys()}
    for l in range(len(ini_seq)):
        job = ini_seq[l]
        op = list(ini_set[job])[job_info[job]]
        ini_seq[l] = (job, op, str(rd.choice(list(ini_set[job][op]))))
        job_info[job] += 1

    for i in range(params["epoch"]):
        data_tensor, _, _, _ = decoding(process, setup, ini_set, machines, ini_seq)
        q_result = qnet(data_tensor).argmax().item()

        p_0, idle_machine, candidate_operation = [], machines.copy(), [(job, list(ini_set[job])[0]) for job in ini_set.keys()]
        q_m, t = {m: [sche for sche in candidate_operation if m in ini_set[sche[0]][sche[1]]] for m in machines}, 0
        while t < params["pop_size"]:
            x = []
            for m in idle_machine:
                if len(q_m[m]):
                    job, op = q_m[m][rd.choice(len(q_m[m]))]
                    x.append((job, op, m))
                    for m_tmp in q_m:
                        if (job, op) in q_m[m_tmp]: q_m[m_tmp].remove((job, op))
            p_0.append(x)
            t += 1

        t, p_0_fitness = 0, []
        while t < params["mating_pool"]:
            cache, identifier, in_cache = [record[3] for record in memory.sample()], [p_t for p_t in p_0 if len(p_t)], False
            for identity in itertools.permutations(identifier):
                if identity in cache:
                    in_cache = (True, cache.index(identity))
                    break

            if in_cache:
                v_best = cache[in_cache[1]][1]
                for p_t in p_0:
                    if len(p_t):
                        p_0_fitness.append((p_t, v_best))
            else:
                v_best = 0
                gamma_tmp = rd.random()
                for p_t in p_0:
                    if len(p_t):
                        p_t, c_max, _, _ = decoding(process, setup, ini_set, machines, p_t)
                        v = 0 + gamma_tmp / c_max
                        if v > v_best:
                            v_best = v
                        p_0_fitness.append((p_t, v))
                if t == params["gens"] - 1:
                    cache.append((identifier, v_best))
        fitness_individual = sorted(p_0_fitness, key=lambda indi: indi[1], reverse=True)
        print(fitness_individual)



        if len(memory.memory) > params["batch_size"]:
            s_batch, a_batch, r_batch, s_prime_batch = memory.sample()
            q_out = qnet(s_batch)
            q_a = q_out.gather(1, a_batch)

            max_q_prime = qnet(s_prime_batch).max(1)[0].unsqueeze(1)
            target = r_batch + params["gamma"] * max_q_prime

            loss = F.smooth_l1_loss(q_a, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        # print(q_result)
        return

class Process:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(processes, setups, machines_tmp, params):
    process, setup, ini_set, machines = Process(), SetUp(), {}, []
    for job in processes.keys():
        print(job)
        ini_set[job] = {}
        for op in processes[job].keys():
            print(f"\t{op} : {processes[job][op]}")
            ini_set[job][op] = []
            for m in processes[job][op].keys():
                ini_set[job][op].append(m)
                if m not in machines:
                    machines.append(m)
                setattr(process, f"{job}{op}{m}", processes[job][op][m])
    machines.sort(key=lambda machine: machines_tmp.index(machine))
    for job1, op1 in setups:
        for job2, op2 in setups:
            setattr(setup, f"{job1}{op1}{job2}{op2}", setups[(job1, op1)][(job2, op2)])
    dynamic_fjsp(process, setup, ini_set, machines, params)

def main():
    num_job, max_num_op, num_machines, max_time = 4, 4, 3, 8
    params = {"pop_size": 10, "mating_pool": 10, "gens": 1, "epoch": 20,
              "in_dim": 7, "hidden1_dim":16, "embed_dim":8, "num_heads_dim":8, "hidden2_dim":32, "out_dim":7,
              "max_len": 100, "batch_size": 50, "mini_batch": 30, "lr": 0.05, "gamma": 0.05}

    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {f"Job{j}": {f"Op{o + 1}": {m: rd.randint(1, max_time + 1) for m in sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m))} for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    start(processes, setups, machines, params)

if __name__ == '__main__':
    main()