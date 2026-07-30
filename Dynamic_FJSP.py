from numpy import random as rd
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
        x = F.relu(x)
        x = self.layer2(x, data_tensor.edge_index)
        x = x.unsqueeze(0)
        x, _ = self.layer3(x, x, x)
        x = torch.mean(x.squeeze(0), dim=0, keepdim=True)
        x = self.layer4(x)
        x = F.relu(x)
        x = self.layer5(x)
        x = F.softmax(x, dim=-1)
        return x

class Memory:
    def __init__(self, mini_batch): self.memory, self.mini_batch = deque(maxlen=100), mini_batch
    def add_buffer(self, buffer): self.memory.append(buffer)
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
        if m in se_setup:
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

    ve_tensor = torch.tensor(ve_tensor, dtype=torch.long).t().contiguous()
    if ve_tensor.numel() == 0: ve_tensor = torch.empty((2, 0), dtype=torch.long)
    else: ve_tensor = ve_tensor
    return Data(torch.tensor(n_tensor, dtype=torch.float), ve_tensor)
def correct_seq(x_tensor): # disjunctive_graph to seq
    seq = []
    for job, op, m, _, _, _, _ in x_tensor:
        job, op, m = f"Job{int(job)}", f"Op{int(op)}", f"M{int(m)}"
        seq.append((job, op, m))
    return seq
def decoding(process, setup, machines, seq, decision_point=None):
    if decision_point is None: decision_point = {}
    s_job, se_process, s_m, se_setup = {}, {}, {}, {}
    total_process_time = 0

    for m in decision_point.keys():
        if decision_point[m][-1] != "setup":
            remain, (job_tmp, op_tmp) = decision_point[m]
            if job_tmp not in s_job: s_job[job_tmp], se_process[job_tmp] = remain, {}
            se_process[job_tmp][op_tmp] = [0, remain, m]
            if m not in s_m: s_m[m], se_setup[m] = [remain, (job_tmp, op_tmp)], []
        else:
            remain_setup, (prior_job, prior_op, now_job, now_op), _ = decision_point[m]
            if m not in s_m: s_m[m], se_setup[m] = [remain_setup, (now_job, now_op)], [(0, remain_setup, prior_job, prior_op, now_job, now_op)]
    for l in range(len(seq)):
        job, op, m = seq[l]

        if job not in s_job: s_job[job], se_process[job] = 0, {}
        se_process[job][op] = [0, 0, m]
        if m not in s_m: s_m[m], se_setup[m] = [0, ()], []

        now = max(s_job[job], s_m[m][0])
        if len(s_m[m][1]):

            if s_m[m][1] == (job, op):
                setup_time = s_m[m][0]
            else:
                setup_time = getattr(setup, f"{s_m[m][1][0]}{s_m[m][1][1]}{job}{op}")
                if s_m[m][1][0] == job: setup_time += 2

            if setup_time:
                now += setup_time
                se_setup[m].append((now - setup_time, now, s_m[m][1][0], s_m[m][1][1], job, op))
        se_process[job][op][0] += now
        process_time = getattr(process, f"{job}{op}{m}")
        total_process_time += process_time
        now += process_time
        se_process[job][op][1] += now
        s_job[job], s_m[m] = now, [now, (job, op)]
    c_max = max(s_m[m][0] for m in s_m.keys())
    reward = total_process_time / len(machines) / c_max
    se_setup = {m: se_setup[m] for m in se_setup.keys() if len(se_setup[m])}
    return disjunctive_graph(seq, se_process, se_setup), reward, c_max, se_process, se_setup

def sequence_rule(process, ini_set, action, seq):
    if action in (0, 1, 4, 5):
        new_seq, job_info = [], {}
        for job, op, m in seq:
            if job not in job_info: job_info[job] = sum(getattr(process, f"{job}{op_tmp}{min(ini_set[job][op_tmp], key=lambda cand_m: getattr(process, f"{job}{op_tmp}{cand_m}"))}") for op_tmp in list(ini_set[job])[list(ini_set[job]).index(op):]) if action in (0, 1) else len(ini_set[job]) - list(ini_set[job]).index(op)
        choose_job = sorted(list(job_info), key=lambda cand_job: job_info[cand_job], reverse=True if action % 2 else False)

        for job in choose_job:
            for sche in seq:
                if sche[0] == job:
                    new_seq.append(sche)
                    break

    elif action in (2, 3): new_seq = sorted(seq, key=lambda sche: getattr(process, f"{sche[0]}{sche[1]}{sche[2]}"), reverse=True if action % 2 else False)
    else: new_seq = rd.permutation(seq).tolist()
    return new_seq

def single_crossover(p1, p2):
    (p1, p2) = [correct_seq(p) for p in (p1, p2)]
    indices = list(range(rd.choice(len(p1))))

    off1, off2 = [p1[idx] for idx in indices], [p2[idx] for idx in indices]
    for l in range(len(p1)):
        sche1, sche2 = p1[l], p2[l]
        if sche2 not in off1: off1.append(sche2)
        if sche1 not in off2: off2.append(sche1)
    return off1, off2

def dynamic_fjsp(process, setup, ini_set, machines, params):
    qnet, qnet_target = [Qnet(in_dim=params["in_dim"], hidden1_dim=params["hidden1_dim"], embed_dim=params["embed_dim"], num_heads_dim=params["num_heads_dim"], hidden2_dim=params["hidden2_dim"], out_dim=params["out_dim"]) for _ in range(2)]
    optimizer, memory, cache = optim.Adam(qnet.parameters(), lr=params["lr"]), Memory(params["mini_batch"]), []
    qnet_target.load_state_dict(qnet.state_dict())
    qnet_target.eval()

    ini_seq_tmp, entire_seq = rd.permutation([job for job in ini_set.keys() for _ in range(len(ini_set[job]))]).tolist(), []
    job_info = {job: 0 for job in ini_set.keys()}
    for l in range(len(ini_seq_tmp)):
        job = ini_seq_tmp[l]
        op = list(ini_set[job])[job_info[job]]
        ini_seq_tmp[l] = (job, op, str(rd.choice(ini_set[job][op])))
        job_info[job] += 1

    idle_machine, candidate_operation, decision_point_issue = machines.copy(), [(job, list(ini_set[job])[0]) for job in ini_set.keys()], {}

    while len(entire_seq) < len(ini_seq_tmp):
        p_0 = []
        for _ in range(params["pop_size"]):
            individual = []
            for l in range(len(candidate_operation)):
                job, op = candidate_operation[l]
                candidate_operation_m = []
                for m in ini_set[job][op]:
                    if m in idle_machine: candidate_operation_m.append(m)
                if len(candidate_operation_m):
                    individual.append((job, op, min(candidate_operation_m, key=lambda cand_m:getattr(process, f"{job}{op}{cand_m}")))) # SPTM Rule Applied
            p_0.append(individual)
        if len(p_0[0]):

            s, q_results = decoding(process, setup, machines, p_0[0], decision_point_issue)[0], torch.distributions.Categorical(qnet(decoding(process, setup, machines, entire_seq if len(entire_seq) else ini_seq_tmp)[0])).sample((params["pop_size"],))
            p_0 = [decoding(process, setup, machines, p_t2, decision_point_issue) for p_t2 in (sequence_rule(process, ini_set, action, p_t) for action, p_t in zip(q_results, p_0))]

            for i in range(params["epoch"]):

                in_cache = -1
                for p_t in p_0:
                    cache_tmp = [state for state, _ in cache]
                    if p_t[0] in cache_tmp:
                        in_cache = cache_tmp.index(p_t[0])

                if in_cache >= 0:
                    v = cache[in_cache][1]
                    v_stars = [v for _ in range(len(p_0))]
                else:
                    v_best, v_stars = 0, []
                    for p_t in p_0:
                        p_t, reward, c_max = p_t[:3]   # p_t, reward, c_max0 = p_t[:3] <-- Tarry's code lol
                        v = reward + params["gamma"] / c_max
                        if v > v_best:
                            v_best = v
                        v_stars.append(v)
                    cache.append((p_0[v_stars.index(v_best)][0], v_best))

                for j in range(len(p_0)):
                    memory.add_buffer(buffer=[s, q_results[j], v_stars[j], p_0[j][0]])
                if len(memory.memory) > params["batch_size"]:
                    s_batch, a_batch, r_batch, s_prime_batch = memory.sample()

                    q_out = torch.stack([qnet(s_tensor).squeeze() for s_tensor in s_batch])
                    q_a = q_out.gather(1, torch.tensor(a_batch))

                    with torch.no_grad():
                        max_q_prime = torch.stack([qnet_target(s_prime).squeeze() for s_prime in s_prime_batch]).max(dim=1, keepdim=True)[0]
                        target = torch.tensor(r_batch, dtype=torch.float) + params["gamma"] * max_q_prime

                    loss = F.smooth_l1_loss(q_a, target)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                offs, break_count, v_stars_off = [], 0, []
                while len(offs) < len(p_0):
                    p1, p2, prior_len = 0, 0, len(offs)
                    while p_0[p1] == p_0[p2]:
                        if len(p_0) == 1: break
                        p1, p2 = rd.choice(len(p_0), size=2, replace=False)

                    if len(p_0[p1][0].x) >= 2 and rd.random() < params["crossover"]: born_offs = single_crossover(p_0[p1][0].x, p_0[p2][0].x)
                    else:born_offs =  correct_seq(p_0[p1][0].x), correct_seq(p_0[p2][0].x)
                    for off in born_offs:
                        if off not in offs: offs.append(off)
                    if not len(offs) - prior_len:
                        break_count += 1
                        if break_count == 10: break
                    else: break_count = 0

                for k in range(len(offs)):
                    off = offs[k]
                    if len(off) and rd.random() < params["mutation"]:
                        rd_idx = rd.choice(len(off))
                        job, op, m_origin = off[rd_idx]
                        alternative_m = [m for m in idle_machine if m != m_origin and m in ini_set[job][op]]
                        if len(alternative_m):
                            alter_m = str(rd.choice(alternative_m))
                            off[rd_idx] = (job, op, alter_m)
                    decode_result = decoding(process, setup, machines, off, decision_point_issue)
                    x_t, reward, c_max = decode_result[:3]
                    offs[k] = (decode_result, reward + params["gamma"] / c_max)
                g_0 = [(p_0[i], v_stars[i]) for i in range(len(p_0))]


                state_tmp_list = [state_tmp.x for (state_tmp, _, _, _, _), _ in g_0]
                for off in offs:
                    done = True
                    for state_tmp in state_tmp_list:
                        if torch.all(off[0][0].x == state_tmp).tolist():
                            done = False
                            break
                    if done: g_0.append(off)

                p_0 = [g_t[0] for g_t in sorted(g_0, key=lambda x: x[1], reverse=True)[:params["pop_size"]]]
        else:
            p_0 = [decoding(process, setup, machines, [], decision_point_issue)]
        winner_data, _, _, winner_se_process, winner_se_setup = p_0[0]
        print({job: winner_se_process[job] for job in ini_set.keys() if job in winner_se_process})
        addition = correct_seq(winner_data.x)
        print("----->>>>>", addition)
        print({m: winner_se_setup[m] for m in machines if m in winner_se_setup})
        print()
        print("Origin DP :", {m: decision_point_issue[m] for m in machines if m in decision_point_issue})
        for job in winner_se_process.keys():
            for op in winner_se_process[job].keys():
                m = winner_se_process[job][op][2]
                if m not in decision_point_issue: decision_point_issue[m] = [winner_se_process[job][op][1], (job, op)]
                # if 0 < winner_se_process[job][op][1] and (winner_se_process[job][op][1] < decision_point_issue[m][0] or decision_point_issue[m][0] == 0):
                #     decision_point_issue[m] = [winner_se_process[job][op][1], (job, op)]
                if decision_point_issue[m][0] == 0 and winner_se_process[job][op][1] > 0:
                    print("Fully new operation in Machine", decision_point_issue[m], end=" --> ")
                    decision_point_issue[m] = [winner_se_process[job][op][1], (job, op)]
                    print(decision_point_issue[m])
                if 0 < winner_se_process[job][op][1] < decision_point_issue[m][0]:
                    print("New one is lower   /  ", decision_point_issue[m], end=" --> ")
                    decision_point_issue[m] = [winner_se_process[job][op][1], (job, op)]
                    print(decision_point_issue[m])

        print("Added  DP :", {m: decision_point_issue[m] for m in machines if m in decision_point_issue}, end=" --> ")
        decision_point = min(decision_point_issue[m][0] for m in decision_point_issue.keys() if decision_point_issue[m][0])
        print(decision_point)
        print()
        print("Setups")
        for m in winner_se_setup.keys():
            for st, ed, prior_job, prior_op, now_job, now_op in winner_se_setup[m]:
                if st < decision_point <= ed:
                    print(f"{m} : {st} < {decision_point} <= {ed}(origin_setup_time={getattr(setup, f"{prior_job}{prior_op}{now_job}{now_op}")})   /   {prior_job}, {prior_op}, {now_job}, {now_op}")
                    decision_point_issue[m] = [ed, (prior_job, prior_op, now_job, now_op), "setup"]
        print()
        for job, op, m in addition:
            if (job, op, m) not in entire_seq:
                if winner_se_process[job][op][0] < decision_point: entire_seq.append((job, op, m))
        for m in decision_point_issue.keys():
            decision_point_issue[m][0] = max(decision_point_issue[m][0] - decision_point, 0)
        print("New    DP :", {m: decision_point_issue[m] for m in machines if m in decision_point_issue}, end=" --> ")
        idle_machine = [m for m in machines if m not in decision_point_issue or not decision_point_issue[m][0]]
        candidate_operation, entire_seq_tmp = [], [(job_tmp, op_tmp) for job_tmp, op_tmp, _ in entire_seq]
        print("Idle Machine :", sorted(idle_machine, key=lambda machine:machines.index(machine)))

        for job in ini_set.keys():
            for op in ini_set[job].keys():
                if op == list(ini_set[job])[0] and (job, op) not in entire_seq_tmp:
                    candidate_operation.append((job, op))
                    break

                elif op != list(ini_set[job])[-1]:
                    next_op = list(ini_set[job])[list(ini_set[job]).index(op) + 1]
                    if (job, op) in entire_seq_tmp and (job, next_op) not in entire_seq_tmp:
                        for job_tmp, op_tmp, m in entire_seq:
                            if job_tmp == job and op_tmp == op:
                                if decision_point_issue[m][1] != (job, op): candidate_operation.append((job, next_op))
                                else:
                                    if decision_point_issue[m][0] == 0: candidate_operation.append((job, next_op))
                                break
                        break
        print("Candidate Operation :", candidate_operation)
        print()
        print("Entire_seq :", entire_seq)
        print("-"*50)
    return entire_seq

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
    print()
    print(dynamic_fjsp(process, setup, ini_set, machines, params))

def main():
    num_job, max_num_op, num_machines, max_time = 5, 4, 3, 8
    params = {"pop_size": 10, "mating_pool": 10, "gens": 1, "epoch": 1, "crossover": 0.8, "mutation": 0.1,
              "in_dim": 7, "hidden1_dim":16, "embed_dim":8, "num_heads_dim":8, "hidden2_dim":32, "out_dim":7,
              "max_len": 100, "batch_size": 50, "mini_batch": 30, "lr": 0.05, "gamma": 0.05}

    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    processes = {f"Job{j}": {f"Op{o + 1}": {m: rd.randint(1, max_time + 1) for m in sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m))} for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    start(processes, setups, machines, params)

if __name__ == '__main__':
    main()