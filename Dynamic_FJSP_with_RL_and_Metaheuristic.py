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
params = {"pop_size": 10, "mating_pool": 10, "num_of_gens": 20}
dqn_params = {"LR": 0.001, "GAMMA": 0.1, "BATCH_SIZE": 10, "MEMORY_SIZE": 20}

class Q_net(nn.Module):
    def __init__(self, in_features=6, gcn_hidden=16, embed_dim=8, num_heads=2, num_actions=7):
        super(Q_net, self).__init__()
        # 1단계: GCN 레이어 (구조 정보 추출)
        self.GCN_layer_1 = GCNConv(in_features, gcn_hidden)
        self.GCN_layer_2 = GCNConv(gcn_hidden, embed_dim)

        # 2단계: Multi-head Self-Attention (공정 간 관계 및 제약 학습)
        self.Multi_Head_Attention = nn.MultiheadAttention(embed_dim=embed_dim, num_heads=num_heads, batch_first=True)

        # 3단계: 완전 연결 레이어 (Q값 예측)
        self.FC_layer_1 = nn.Linear(embed_dim, 32)
        self.FC_layer_2 = nn.Linear(32, num_actions)

    def forward(self, tensors, batch=None):
        # [1단계] GCN 연산 및 활성화 함수(sigma) 적용
        x_tensor, edge_tensor = tensors
        H_1 = F.relu(self.GCN_layer_1(x_tensor, edge_tensor))
        H_2 = self.GCN_layer_2(H_1, edge_tensor)  # 은닉 노드 표현 벡터 H_2

        # [2단계] 가변 그래프 크기를 고려한 어텐션 및 풀링 연산
        if batch is None:
            # 단일 그래프 추론
            H_seq = H_2.unsqueeze(0)
            attn_out, _ = self.Multi_Head_Attention(H_seq, H_seq, H_seq)
            graph_embed = torch.mean(attn_out.squeeze(0), dim=0, keepdim=True)
        else:
            # 미니배치 학습 (여러 개의 서로 다른 크기 그래프 처리)
            graph_embeds = []
            for g_id in torch.unique(batch):
                mask = (batch == g_id)
                H_g = H_2[mask].unsqueeze(0)
                attn_out_g, _ = self.Multi_Head_Attention(H_g, H_g, H_g)
                graph_embed_g = torch.mean(attn_out_g.squeeze(0), dim=0, keepdim=True)
                graph_embeds.append(graph_embed_g)
            graph_embed = torch.cat(graph_embeds, dim=0)

            # [3단계] FC 레이어를 통한 최종 Q값 출력
        out = F.relu(self.FC_layer_1(graph_embed))
        Q_values = self.FC_layer_2(out)
        return Q_values

class Memory():
    def __init__(self):
        self.buffer = deque(maxlen=dqn_params["MEMORY_SIZE"])
    def put(self, transition):
        self.buffer.append(transition)
    def sample(self, n):
        mini_batch = [self.buffer[i] for i in rd.choice(len(self.buffer), size=n, replace=False)]

        s_lst, a_lst, r_lst, s_prime_lst = [], [], [], []
        for transition in mini_batch:
            s, a, r, s_prime = transition
            s_lst.append(s)
            a_lst.append([a])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
        return torch.tensor(s_lst, dtype=torch.float), torch.tensor(a_lst), torch.tensor(r_lst, dtype=torch.float), torch.tensor(s_prime_lst, dtype=torch.float)
    def size(self):
        return len(self.buffer)

def select_mp(length):
    index = list(range(length))
    way = rd.randint(3)
    if way == 0:  # Binary tournament
        return min(rd.choice(index, size=2, replace=False))
    elif way == 1:  # n-Size tournament
        return min(rd.choice(index, size=rd.randint(3, max(4, int(params["pop_size"] / 2.5))), replace=False))
    elif way == 2:  # Linear ranking
        return rd.choice(index, size=1, p=[2 * i / (params["pop_size"] * (params["pop_size"] + 1)) for i in range(params["pop_size"], 0, -1)])
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

def disjunctive_graph(ini_set, machines, os_vector, ms_vector, se_process, se_setup):
    conjunctive_arcs, disjunctive_arcs, x_tensor = [], [], []

    for job in ini_set.keys():
        for l1 in range(len(os_vector)):
            for l2 in range(l1 + 1, len(os_vector)):
                if job == os_vector[l1] and job == os_vector[l2]:
                    conjunctive_arcs.append([l1, l2])
                    break
    for m in machines:
        for l1 in range(len(ms_vector)):
            for l2 in range(l1 + 1, len(ms_vector)):
                if m == ms_vector[l1] and m == ms_vector[l2]:
                    disjunctive_arcs.extend([[l1, l2], [l2, l1]])
                    break
    for job, op, m in correct_procedure(ini_set, os_vector, ms_vector):
        setup_time = 0
        for m_tmp in machines:
            for st, ed, (prior_job, prior_op, now_job, now_op) in se_setup[m_tmp]:
                if now_job == job and now_op == op:
                    setup_time = ed - st
                    break
        x_tensor.append([int(job.replace("Job", "")), int(op.replace("Op", "")), int(m.replace("M", "")), int(se_process[job][op][0]), int(se_process[job][op][1]), int(setup_time)])

    for arc in disjunctive_arcs:
        if arc not in conjunctive_arcs:
            conjunctive_arcs.append(arc)
    return torch.tensor(x_tensor, dtype=torch.float), torch.tensor(conjunctive_arcs, dtype=torch.long).t().contiguous() if conjunctive_arcs else torch.empty((2, 0), dtype=torch.long)

def encoding(seq):
    os_vector, ms_vector = [], []
    for job, _, m in seq:
        os_vector.append(job)
        ms_vector.append(m)
    return os_vector, ms_vector

def decoding(process, setup, ini_set, machines, vectors):
    seq, s_job, s_m = correct_procedure(ini_set, vectors[0], vectors[1]), {job: 0 for job in ini_set.keys()}, {m: [0, ()] for m in machines}
    se_process, se_setup = {job: {op :[0, 0] for op in ini_set[job].keys()} for job in ini_set.keys()}, {m: [] for m in machines}
    for job, op, m in seq:
        now = max(s_job[job], s_m[m][0])
        if len(s_m[m][1]):
            setup_time = getattr(setup, f"{s_m[m][1][0]}{s_m[m][1][1]}{job}{op}")
            if setup_time:
                se_setup[m].append([now, now + setup_time, (s_m[m][1][0], s_m[m][1][1], job, op)])
                now += setup_time
        else: now += 0
        se_process[job][op][0] += now
        now += getattr(process, f"{job}{op}{m}")
        se_process[job][op][1] += now
        s_job[job], s_m[m] = now, [now, (job, op)]
    reward = sum(getattr(process, f"{job}{op}{m}") for job, op, m in seq) / sum(1 if s_m[m][0] else 0 for m in s_m.keys()) / max(s_m[m][0] for m in s_m.keys())
    return encoding(seq), reward, se_process, se_setup

def mutation(process, setup, ini_set, machines, pr, action):
    os_vector, ms_vector = pr[0].copy(), pr[1].copy()

    if action in [0, 1]:
        tmp_set = {job: [ms_vector[i] for i in range(len(os_vector)) if os_vector[i] == job] for job in ini_set.keys()}
        if action == 0:
            idx1, idx2 = rd.choice(range(len(os_vector)), size=2, replace=False)
            os_vector[idx1], os_vector[idx2] = os_vector[idx2], os_vector[idx1]
        elif action == 1:
            idx1, idx2 = sorted(rd.choice(range(len(os_vector)), size=2, replace=False))
            if idx1 != 0: os_vector[idx1:idx2 + 1] = os_vector[idx2:idx1 - 1:-1]
            else: os_vector[:idx2 + 1] = os_vector[idx2::-1]
        ms_vector = [tmp_set[job].pop(0) for job in os_vector]
    elif action == 2:
        idx = rd.choice(range(len(os_vector)))
        job, op, m_tmp = correct_procedure(ini_set, os_vector, ms_vector)[idx]
        ms_vector[idx] = rd.choice([m for m in ini_set[job][op] if m != m_tmp]) if len(ini_set[job][op]) != 1 else m_tmp
    else: pass # Do not reach
    return decoding(process, setup, ini_set, machines, (os_vector, ms_vector))

def crossover(process, setup, ini_set, machines, pr1, pr2, action):
    os_vector, ms_vector, os_vector_pair, ms_vector_pair = pr1[0].copy(), pr1[1].copy(), pr2[0].copy(), pr2[1].copy()
    if len(os_vector) <= 3 and action == 2: action = 1
    if len(os_vector) <= 2 and action == 1: action = 0
    if action == 0:
        chosen_job = os_vector[rd.randint(len(os_vector))]
        points = [i for i in range(len(os_vector)) if os_vector[i] == chosen_job]
    elif action == 1:
        idx1, idx2 = sorted(rd.choice(list(range(1, max(2, len(os_vector) - 1))), size=2, replace=False))
        points = [i for i in range(len(os_vector)) if i < idx1 or i >= idx2]
    elif action == 2:
        indices = [0] + sorted(rd.choice(list(range(1, max(2, len(os_vector) - 1))), size=rd.randint(3, max(4, len(os_vector)//2)), replace=False)) + [len(os_vector) - 1]
        points = []
        for l in range(len(indices) - 1):
            if l % 2 == 0: points.extend(list(range(indices[l], indices[l + 1])))
        if len(indices) % 2 == 1: points.extend(list(range(indices[len(indices) - 1], len(os_vector))))
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

    tmp_set = {job: [ms_vector[i] for i in range(len(os_vector)) if os_vector[i] == job] for job in ini_set.keys()}

    for i in range(len(os_vector)):
        if i in points:
            job = os_vector[i]
            new_os_vector.append(job)
            new_ms_vector.append(tmp_set[job].pop(0))

        else:
            job = os_vector_pair[points_pair.pop(0)]
            new_os_vector.append(job)
            new_ms_vector.append(tmp_set[job].pop(0))

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
    history, q_net, memory = [], Q_net(), Memory()
    pops = sorted([decoding(process, setup, ini_set, machines,(rd.permutation(ini_os).tolist(), [])) for _ in range(params["pop_size"])], key=lambda case: case[1], reverse=True)
    for gen in range(1, params["num_of_gens"] + 1):
        offsprings, mating_pool, indices = [], [select_mp(len(pops)) for _ in range(params["mating_pool"])], list(range(params["mating_pool"]))
        for _ in range(len(mating_pool) // 2):
            pr1, pr2 = [indices.pop(rd.randint(len(indices))) for _ in range(2)]

            if rd.random() < dqn_params["GAMMA"]:
                action = rd.randint(6)
            else:
                action = q_net(disjunctive_graph(ini_set, machines, pops[pr1][0][0], pops[pr1][0][1], pops[pr1][2], pops[pr1][3])).argmax().item()

            if rd.random() < 0.8:
                off = crossover(process, setup, ini_set, machines, pops[pr1][0], pops[pr2][0], action)
            elif rd.random() < 0.9:
                off = mutation(process, setup, ini_set, machines, pops[pr1][0], action)
            else:
                off = pops[pr2]
            offsprings.append(off)
        offsprings.sort(key=lambda case: case[1], reverse=True)
        if offsprings[0][1] > pops[0][1]:
            pops = sorted(offsprings + pops, key=lambda case: case[1], reverse=True)[:params["pop_size"]]
        history.append(pops[0][1])
        dqn_params["GAMMA"] = max(0.95 * dqn_params["GAMMA"], 0.01)
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