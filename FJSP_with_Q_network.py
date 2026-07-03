from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt

# --- [추가된 딥러닝/강화학습 라이브러리] ---
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import collections
import random

# Parameter Input
num_job, max_num_op, num_machines, max_time = 5, 5, 7, 9
params = {"num_of_gens": 20, "mating_pool": 20, "num_offs": 10, "s_max": 2, "Np1": 10, "Np2": 20}

# --- [DQN 하이퍼파라미터] ---
LR = 0.001
GAMMA = 0.9
BATCH_SIZE = 32
MEMORY_SIZE = 10000

# =====================================================================
# 1. DQN 아키텍처 및 리플레이 버퍼 (논문 4.6.1절 반영)
# =====================================================================
class FJSP_QNet(nn.Module):
    def __init__(self, state_dim, action_dim=6):
        super(FJSP_QNet, self).__init__()
        # 논문 구조: Input -> 512 -> 256 -> 128 -> 64 -> 6(Actions)
        self.fc1 = nn.Linear(state_dim, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, 128)
        self.fc4 = nn.Linear(128, 64)
        self.fc5 = nn.Linear(64, action_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = F.relu(self.fc4(x))
        return self.fc5(x)

class ReplayBuffer():
    def __init__(self):
        self.buffer = collections.deque(maxlen=MEMORY_SIZE)
    def put(self, transition):
        self.buffer.append(transition)
    def sample(self, n):
        mini_batch = random.sample(self.buffer, n)
        s_lst, a_lst, r_lst, s_prime_lst = [], [], [], []
        for transition in mini_batch:
            s, a, r, s_prime = transition
            s_lst.append(s)
            a_lst.append([a])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
        return torch.tensor(s_lst, dtype=torch.float), torch.tensor(a_lst), \
               torch.tensor(r_lst, dtype=torch.float), torch.tensor(s_prime_lst, dtype=torch.float)
    def size(self):
        return len(self.buffer)

# =====================================================================
# 2. 기존 로직 (수정 최소화)
# =====================================================================
def correct_procedure(ini_set, os_vector, ms_vector):
    seq, info_op = os_vector.copy(), {job: {op: 0 for op in ini_set[job]} for job in ini_set.keys()}
    for l in range(len(seq)):
        op = min(ini_set[seq[l]], key=lambda op: info_op[seq[l]][op])
        m = rd.choice(ini_set[seq[l]][op]) if len(ms_vector) <= l else ms_vector[l]
        info_op[seq[l]][op] += 1
        seq[l] = (seq[l], op, m)
    return seq

def encoding(seq):
    os_vector, ms_vector = [], []
    for l in range(len(seq)):
        job, _, m = seq[l]
        os_vector.append(job)
        ms_vector.append(m)
    return os_vector, ms_vector

def decoding(process, setup, ini_set, vectors):
    se_process, interval = {}, {}
    seq = correct_procedure(ini_set, vectors[0], vectors[1])
    horizon = num_job * max_num_op * max_time
    md = cp_model.CpModel()

    for job in ini_set.keys():
        se_process[job], interval[job] = {}, {}
        for l in range(len(ini_set[job])):
            op = list(ini_set[job])[l]
            se_process[job][op] = [md.new_int_var(0, horizon, f'{job}{op}') for _ in range(2)]
            interval[job][op] = md.new_interval_var(se_process[job][op][0], getattr(process, f"{job}{op}"), se_process[job][op][1], f'{job}{op}')
            if l >= 1: md.add(se_process[job][op][0] >= se_process[job][list(ini_set[job])[l-1]][1])
        md.add_no_overlap(interval[job].values())

    machines, se_setup, interval_setup = {}, {}, {}
    for sche in seq:
        if sche[2] not in machines:
            machines[sche[2]] = []
            interval_setup[sche[2]] = []
            se_setup[sche[2]] = []
        machines[sche[2]].append(sche)
    for m in machines.keys():
        for l in range(1, len(machines[m])):
            job1, op1, _ = machines[m][l-1]
            job2, op2, _ = machines[m][l]
            md.add(se_process[job1][op1][1] <= se_process[job2][op2][0])
            if getattr(setup, f"{job1}{op1}{job2}{op2}"):
                se_setup[m].append([md.new_int_var(0, horizon, f'{job1}{op1}_{job2}{op2}') for _ in range(2)])
                idx = len(se_setup[m]) - 1
                interval_setup[m].append(md.new_interval_var(se_setup[m][idx][0], getattr(setup, f"{job1}{op1}{job2}{op2}"), se_setup[m][idx][1], f'{job1}{op1}_{job2}{op2}'))
                md.add(se_setup[m][idx][1] == se_process[job2][op2][0])
        md.add_no_overlap(interval_setup[m] + [interval[job][op] for job, op, _ in machines[m]])
    md.add_cumulative([l for m in interval_setup.keys() for l in interval_setup[m]], [1 for m in interval_setup.keys() for _ in interval_setup[m]], params["s_max"])

    obj = md.new_int_var(0, horizon, "c_max")
    md.add_max_equality(obj, [se_process[job][op][1] for job in ini_set.keys() for op in ini_set[job]])
    md.minimize(obj)
    solver = cp_model.CpSolver()
    solver.Solve(md)
    return vectors, solver.ObjectiveValue(), {job : {op : [solver.value(time) for time in se_process[job][op]] for op in se_process[job].keys()} for job in se_process.keys()}, {m:[(solver.value(st), solver.value(ed)) for st, ed in se_setup[m]] for m in se_setup.keys()}

def evolution_guided(process, setup, ini_set, pops):
    # EGP (진화 유도) - 기존 로직 유지
    winner_pops, loser_pops = pops[:(params["Np1"] + 1)//2], pops[params["Np1"]//2:]
    new_pops = []
    for seq, _, _, _ in winner_pops:
        os_vector, ms_vector = seq[0].copy(), seq[1].copy()
        way = rd.randint(3)
        if way == 0:
            idx1, idx2 = rd.choice(range(len(os_vector)), size=2, replace=False)
            os_vector[idx1], os_vector[idx2], ms_vector[idx1], ms_vector[idx2] = os_vector[idx2], os_vector[idx1], ms_vector[idx2], ms_vector[idx1]
        elif way == 1:
            idx1, idx2 = sorted(rd.choice(range(len(os_vector)), size=2, replace=False))
            if idx1 != 0: os_vector[idx1:idx2+1], ms_vector[idx1:idx2+1] = os_vector[idx2:idx1-1:-1], ms_vector[idx2:idx1-1:-1]
            else: os_vector[idx1:idx2 + 1], ms_vector[idx1:idx2 + 1] = os_vector[idx2::-1], ms_vector[idx2::-1]
        elif way == 2:
            idx = rd.choice(range(len(os_vector)))
            job, op, m_tmp = correct_procedure(ini_set, os_vector, ms_vector)[idx]
            ms_vector[idx] = rd.choice([m for m in ini_set[job][op] if m != m_tmp]) if len(ini_set[job][op]) != 1 else m_tmp
        new_pops.append(decoding(process, setup, ini_set, (os_vector, ms_vector)))

    for _ in range(len(winner_pops)):
        if not loser_pops: break
        pr1, pr2 = rd.permutation([winner_pops.pop(rd.randint(len(winner_pops)))[0], loser_pops.pop(rd.randint(len(loser_pops)))[0]]).tolist()
        os_vector = pr1[0]
        pr1, pr2 = correct_procedure(ini_set, pr1[0], pr1[1]), correct_procedure(ini_set, pr2[0], pr2[1])
        ms_vector = []
        for job, op, _ in pr1:
            for job2, op2, m in pr2:
                if job == job2 and op == op2:
                    ms_vector.append(m)
                    break
        new_pops.append(decoding(process, setup, ini_set, (os_vector, ms_vector)))
    return new_pops

# =====================================================================
# 3. KDP (지식 기반 집단) - DQN 연동
# =====================================================================
def get_state_vector(os_vector, ms_vector):
    """ 문자열인 Job1, M1 등을 신경망이 인식할 수 있게 정수(int) 배열로 변환하여 Concatenation """
    state = []
    for j in os_vector: state.append(int(j.replace("Job", "")))
    for m in ms_vector: state.append(int(m.replace("M", "")))
    return state

def knowledge_driven(process, setup, ini_set, kdp_pops, all_pops, q_net, memory, epsilon):
    """ DQN이 kdp_pops(지식 기반 집단)의 상태를 보고 탐색 오퍼레이터를 선택하여 진화 """
    new_pops = []
    
    for pop in kdp_pops:
        os_vector, ms_vector = pop[0][0].copy(), pop[0][1].copy()
        current_makespan = pop[1]
        
        # 1. State(상태) 형성 (OS + MS 벡터 정수화)
        state_list = get_state_vector(os_vector, ms_vector)
        state_tensor = torch.tensor(state_list, dtype=torch.float)
        
        # 2. Action(행동) 선택 - 입실론 탐욕 전략
        if rd.random() < epsilon:
            action = rd.randint(6)  # 탐험
        else:
            action = q_net(state_tensor).argmax().item() # Q-Network 예측
            
        # 3. Action 수행 (6개의 탐색 오퍼레이터)
        new_os, new_ms = os_vector.copy(), ms_vector.copy()
        
        if action == 0: # 로컬 1: Swap
            idx1, idx2 = rd.choice(range(len(new_os)), size=2, replace=False)
            new_os[idx1], new_os[idx2], new_ms[idx1], new_ms[idx2] = new_os[idx2], new_os[idx1], new_ms[idx2], new_ms[idx1]
        elif action == 1: # 로컬 2: Reverse
            idx1, idx2 = sorted(rd.choice(range(len(new_os)), size=2, replace=False))
            new_os[idx1:idx2+1], new_ms[idx1:idx2+1] = new_os[idx1:idx2+1][::-1], new_ms[idx1:idx2+1][::-1]
        elif action == 2: # 로컬 3: Reassign
            idx = rd.choice(range(len(new_os)))
            job, op, m_tmp = correct_procedure(ini_set, new_os, new_ms)[idx]
            if len(ini_set[job][op]) > 1:
                new_ms[idx] = rd.choice([m for m in ini_set[job][op] if m != m_tmp])
        elif action >= 3: # 협력 1,2,3: Crossover (다른 개체와 유전자 섞기)
            partner = all_pops[rd.randint(len(all_pops))][0]
            split_point = len(new_os) // 2
            new_os = new_os[:split_point] + partner[0][split_point:]
            new_ms = new_ms[:split_point] + partner[1][split_point:]
            # 잘못 섞인 유전자는 decoding 내의 correct_procedure가 자동 보정함
            
        # 4. 평가 (Decoding)
        new_pop = decoding(process, setup, ini_set, (new_os, new_ms))
        new_makespan = new_pop[1]
        
        # 5. 보상 (Makespan 단축 시 +10, 아니면 0)
        reward = 10.0 if new_makespan < current_makespan else 0.0
        
        # 6. 다음 상태 (Next State) 및 버퍼 저장
        next_state_list = get_state_vector(new_pop[0][0], new_pop[0][1])
        memory.put((state_list, action, reward, next_state_list))
        
        new_pops.append(new_pop)
        
    return new_pops

def graph_makespan(ini_set, machines, best):
    seq, obj, se_process, se_setup = best
    seq = correct_procedure(ini_set, seq[0], seq[1])

    _, ax = plt.subplots()
    s_job, s_machine, m_tmp = list(se_process.keys()), {}, {}
    for m in machines:
        ax.barh(m, 0, left=0)
        s_machine[m] = 0
        m_tmp[m] = []

    for l in range(len(seq)):
        job, op, m = seq[l]
        operating = se_process[job][op][1] - se_process[job][op][0]
        start_process = se_process[job][op][0]
        ax.barh(m, operating, left=start_process, color=plt.get_cmap('tab20', len(s_job))(list(s_job).index(job)), edgecolor='black')
        ax.text(start_process + operating / 2, m, f"{job}\n{op}\n({operating})", va='center', ha='center', color='black', fontsize=5)

    for m in se_setup.keys():
        for st_setup, ed_setup in se_setup[m]:
            setup_ing = ed_setup - st_setup
            if round(setup_ing) != 0:
                ax.barh(m, setup_ing, left=st_setup, color='white', edgecolor='black')
    ax.set_xticks([i for i in range(int(max(se_process[job][op][1] for job in se_process.keys() for op in se_process[job].keys())) + 2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result (EA-DQN)")
    plt.show()

# =====================================================================
# 4. Main EA-DQN-CP 루프 (Algorithm 2)
# =====================================================================
def cp_aea(process, setup, ini_set, machines):
    ini_os_vector = [job for job in ini_set.keys() for _ in range(len(ini_set[job]))]
    
    print("Gen 0", "="*30)
    print("Initial Population 생성을 위해 CP 모델 해석 중...")
    pops = sorted([decoding(process, setup, ini_set, (rd.permutation(ini_os_vector).tolist(), [])) for _ in range(params["Np1"] + params["Np2"])], key=lambda case: case[1])
    
    # 1. DQN 초기화
    state_dim = len(ini_os_vector) * 2 # OS 벡터 길이 + MS 벡터 길이
    q_net = FJSP_QNet(state_dim=state_dim, action_dim=6)
    optimizer = optim.Adam(q_net.parameters(), lr=LR)
    memory = ReplayBuffer()
    epsilon = 0.5 # 초기 탐험 확률

    for gen in range(1, params["num_of_gens"] + 1):
        print(f"Gen {gen}", "=" * 30)
        
        # 2. 집단 분리: EGP(우수 절반)와 KDP(나머지 절반)
        egp = pops[:params["Np1"]]
        kdp = pops[:params["Np2"]]
        
        # 3. EGP: 진화적 메타휴리스틱으로 자식 생성
        offsprings_egp = evolution_guided(process, setup, ini_set, egp)
        
        # 4. KDP: DQN 강화학습 판단으로 자식 생성 (새로 구현된 부분)
        offsprings_kdp = knowledge_driven(process, setup, ini_set, kdp, pops, q_net, memory, epsilon)
        
        # 5. 세대 통합 및 우수 개체 선별
        pops = sorted(pops + offsprings_egp + offsprings_kdp, key=lambda case: case[1])[:(params["Np1"] + params["Np2"])]
        
        print(f"Best Makespan: {pops[0][1]}")

        # 6. DQN 신경망 학습 (경험 리플레이)
        if memory.size() > BATCH_SIZE:
            s_batch, a_batch, r_batch, s_prime_batch = memory.sample(BATCH_SIZE)
            q_out = q_net(s_batch)
            q_a = q_out.gather(1, a_batch)
            max_q_prime = q_net(s_prime_batch).max(1)[0].unsqueeze(1)
            
            target = r_batch + GAMMA * max_q_prime
            loss = F.smooth_l1_loss(q_a, target)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
        # 입실론 점진적 감소 (탐험 비율 줄이고 지식 활용 늘림)
        epsilon = max(0.01, epsilon * 0.95)

    print("\n최종 최적화 완료!")
    graph_makespan(ini_set, machines, pops[0])
    return 0

class Process:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
def start(processes, setups, machines_tmp):
    process, setup, ini_set, machines = Process(), SetUp(), {}, []

    for job in processes.keys():
        ini_set[job] = {}
        for op in processes[job]:
            ms,processing_time = processes[job][op]
            ini_set[job][op] = ms
            for m in ms:
                if m not in machines:
                    machines.append(m)
            setattr(process, f"{job}{op}", processing_time)
    machines.sort(key=lambda machine: machines_tmp.index(machine))

    for job1, op1 in setups:
        for job2, op2 in setups:
            setattr(setup, f"{job1}{op1}{job2}{op2}", setups[(job1, op1)][(job2, op2)])

    cp_aea(process, setup, ini_set, machines)

def main():

    machines = [f"M{i}" for i in range(1, num_machines + 1)]
    processes = {f"Job{j+1}": {f"Op{o+1}" : [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m)), rd.randint(1, max_time + 1)] for o in range(rd.randint(1, max_num_op + 1))} for j in range(rd.randint(2,num_job+1))}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1:{op2:0 if op1[0] == op2[0] else rd.randint(1, max(max_time//2, 1) + 1) for op2 in op_types} for op1 in op_types}

    print("-----------------------------------------------------------------------------------------------------")
    start(processes, setups, machines)

if __name__ == "__main__":
    main()