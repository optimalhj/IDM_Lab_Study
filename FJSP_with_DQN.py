from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt

# Parameter Input
num_job, max_num_op, num_machines, max_time = 5, 5, 7, 9
params = {"num_of_gens": 20, "mating_pool": 20, "num_offs": 10, "s_max": 2, "Np1": 10, "Np2": 20}

def correct_procedure(ini_set, os_vector, ms_vector):
    seq, info_op = os_vector.copy(), {job: {op: 0 for op in ini_set[job]} for job in ini_set.keys()}
    for l in range(len(seq)):
        op = min(ini_set[seq[l]], key=lambda op: info_op[seq[l]][op])
        m = rd.choice(ini_set[seq[l]][op]) if len(ms_vector) == 0 else ms_vector[l]
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
    return encoding(seq), solver.ObjectiveValue(), {job : {op : [solver.value(time) for time in se_process[job][op]] for op in se_process[job].keys()} for job in se_process.keys()}, {m:[(solver.value(st), solver.value(ed)) for st, ed in se_setup[m]] for m in se_setup.keys()}

def evolution_guided(process, setup, ini_set, pops):
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
        else: os_vector, ms_vector = [], [] # Do not reach
        new_pops.append(decoding(process, setup, ini_set, (os_vector, ms_vector)))
    for _ in range(len(winner_pops)):
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

def knowledge_drived(process, setup, ini_set, pops):
    seq = []
    return decoding(process, setup, ini_set, seq)

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
    ax.set_title("Makespan_Result")
    plt.show()

def cp_aea(process, setup, ini_set, machines):
    ini_os_vector = [job for job in ini_set.keys() for _ in range(len(ini_set[job]))]
    pops = sorted([decoding(process, setup, ini_set, (rd.permutation(ini_os_vector).tolist(), ())) for _ in range(params["Np1"] + params["Np2"])], key=lambda case: case[1])
    print("Gen 0", "="*30)
    print("Ini Pop :")
    for pop in pops:
        print("\t", pop[1], pop)
    for gen in range(1, params["num_of_gens"] + 1):
        print(f"Gen {gen}", "=" * 30)
        print("Pops :")
        for pop in pops:
            print("\t", pop[1], pop)
        egp, kdp = pops[:params["Np1"]], pops[:params["Np2"]]
        offsprings = sorted(evolution_guided(process, setup, ini_set, egp), key=lambda case: case[1])
        print("Offspring :")
        for off in offsprings:
            print("\t", off[1], off)
        pops = sorted(pops + offsprings, key=lambda case: case[1])[:params["Np1"]]
        print()


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

    for job in processes.keys():
        print(job)
        print(f"\t{processes[job]}")

    for op1 in setups.keys():
        print(op1," -> ", end="")
        for op2 in setups[op1]:
            if setups[op1][op2] != 0:
                print(f"{op2}({setups[op1][op2]})", end=" / ")
        print()
    print("\n-----------------------------------------------------------------------------------------------------")

    start(processes, setups, machines)

if __name__ == "__main__":
    main()