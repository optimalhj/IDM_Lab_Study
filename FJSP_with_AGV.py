# import numpy as np
from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt

num_job, max_num_op, num_machines, num_AGV, max_time = 3, 3, 3, 3, 5
params = {"pop_size": 10, "mating_pool": 20, "num_of_gens": 5, "s_max": 2}


def select_mp(populations):
    index = list(range(params["pop_size"]))
    way_pop = rd.randint(3)

    if way_pop == 0:  # Binary tournament
        return populations[min(rd.choice(index, size=2, replace=False), key=lambda idx: populations[idx][1])][0]
    elif way_pop == 1:  # n-Size tournament
        return populations[min(rd.choice(index, size=rd.randint(3, max(4, int(params["pop_size"] / 2.5))), replace=False), key=lambda idx: populations[idx][1])][0]
    elif way_pop == 2:  # Linear ranking
        return populations[rd.choice(index, size=1, p=[2 * i / (params["pop_size"] * (params["pop_size"] + 1)) for i in range(params["pop_size"], 0, -1)])[0]][0]
    else: return [] # Do not reach

def correct_procedure(ini_set, agv_info, os_vector, ms_vector):
    seq, info_op = os_vector.copy(), {job: {op: 0 for op in ini_set[job]} for job in ini_set.keys()}
    for l in range(len(seq)):
        job = seq[l]
        op = min(ini_set[job], key=lambda op: info_op[job][op])
        info_op[job][op] += 1
        m = ms_vector[l] if len(ms_vector) else str(rd.choice(ini_set[job][op]))
        seq[l] = (job, op, m)
    return seq

def encoding(seq):
    os_vector, ms_vector = [], []
    for job, _, m in seq:
        os_vector.append(job)
        ms_vector.append(m)
    return os_vector, ms_vector

def decoding(process, setup, agv_move, ini_set, agv_info, vectors):
    se_process, interval = {}, {}
    seq = correct_procedure(ini_set, agv_info, vectors[0], vectors[1])
    horizon = num_job * max_num_op * max_time
    md = cp_model.CpModel()
    for job in ini_set.keys():
        se_process[job], interval[job] = {}, {}
        for l in range(len(ini_set[job])):
            op = list(ini_set[job])[l]
            se_process[job][op] = [md.new_int_var(0, horizon, f'{job}{op}') for _ in range(2)]
            interval[job][op] = md.new_interval_var(se_process[job][op][0], getattr(process, f"{job}{op}"), se_process[job][op][1], f'{job}{op}')
            if l >= 1: md.add(se_process[job][list(ini_set[job])[l - 1]][1] <= se_process[job][op][0])
        md.add_no_overlap(interval[job].values())

    machines, se_setup, interval_setup = {}, {}, {}
    for job, op, m in seq:
        if m not in machines:
            machines[m] = []
            se_setup[m] = []
            interval_setup[m] = []
        machines[m].append((job, op))

    for m in machines.keys():
        for l in range(1, len(machines[m])):
            job1, op1 = machines[m][l - 1]
            job2, op2 = machines[m][l]
            md.add(se_process[job1][op1][1] <= se_process[job2][op2][0])
            if getattr(setup, f"{job1}{op1}{job2}{op2}"):
                se_setup[m].append([md.new_int_var(0, horizon, f'{job1}{op1}_{job2}{op2}') for _ in range(2)])
                idx = len(se_setup[m]) - 1
                interval_setup[m].append(md.new_interval_var(se_setup[m][idx][0], getattr(setup, f"{job1}{op1}{job2}{op2}"), se_setup[m][idx][1], f'{job1}{op1}_{job2}{op2}'))
                md.add(se_setup[m][idx][1] == se_process[job2][op2][0])
        md.add_no_overlap(interval_setup[m] + [interval[job][op] for job, op in machines[m]])
    md.add_cumulative([l for m in interval_setup.keys() for l in interval_setup[m]], [1 for m in interval_setup.keys() for _ in interval_setup[m]], params["s_max"])

    bool_agv, se_agv, interval_agv,machine_bool_agv, size_machine_agv = {}, {}, {}, {}, {}

    for agv in agv_info:
        bool_agv[agv] = {}
        se_agv[agv] = {}
        interval_agv[agv] = {}
        if agv != agv_info[0]:
            machine_bool_agv[agv] = {}
            size_machine_agv[agv] = {}
        for job in ini_set.keys():
            bool_agv[agv][job] = {}
            se_agv[agv][job] = {}
            interval_agv[agv][job] = {}
            for op in ini_set[job].keys():
                bool_agv[agv][job][op] = md.new_bool_var(f"{agv}/{job}/{op}")
                se_agv[agv][job][op] = [md.new_int_var(0, horizon, f"{job}{op}") for _ in range(2)] + [f"({job}, {op})"]

    for job in ini_set.keys():
        for op in ini_set[job].keys():
            md.add(sum(bool_agv[agv][job][op] for agv in agv_info) == 1)

    for l in range(len(seq)):
        job, op, m = seq[l]

        idx_job = list(ini_set[job]).index(op)
        idx_machine = machines[m].index((job, op))
        if idx_job == 0:
            md.add(bool_agv[agv_info[0]][job][op] == 0)
            interval_agv[agv_info[0]][job][op] = md.new_interval_var(se_agv[agv_info[0]][job][op][0], bool_agv[agv_info[0]][job][op], se_agv[agv_info[0]][job][op][1], "Virtual")
            if idx_machine == 0:
                for agv in agv_info[1:]:
                    interval_agv[agv][job][op] = md.new_interval_var(se_agv[agv][job][op][0], bool_agv[agv][job][op] * getattr(agv_move, f"LU{m}"), se_agv[agv][job][op][1], f"LU->{m}/({job}, {op})")
            else:
                for agv in agv_info[1:]:
                    machine_bool_agv[agv][(job, op)] = {}
                    size_machine_agv[agv][(job, op)] = md.new_int_var(0, horizon, f"({job}, {op})")
                    for m_tmp in machines.keys():
                        machine_bool_agv[agv][(job, op)][m_tmp] = md.new_bool_var(f"({job}, {op}, {m_tmp})")
                    md.add(size_machine_agv[agv][(job, op)] == sum(machine_bool_agv[agv][(job, op)][m_tmp] * getattr(agv_move, f"LU{m_tmp}") for m_tmp in machines.keys()) + bool_agv[agv][job][op] * getattr(agv_move, f"LU{m}"))
                md.add(sum(machine_bool_agv[agv][(job, op)][m_tmp] for agv in agv_info[1:] for m_tmp in machines.keys()) == 1)
                for agv in machine_bool_agv.keys():
                    interval_agv[agv][job][op] = md.new_interval_var(se_agv[agv][job][op][0], size_machine_agv[agv][(job, op)], se_agv[agv][job][op][1], f"Comeback->{m}/({job}, {op})")
        else:
            if idx_machine == 0:
                md.add(bool_agv[agv_info[0]][job][op] == 0)
                prior_job_op, prior_job_m = list(ini_set[job])[idx_job - 1], "m"
                for job_tmp, op_tmp, m_tmp in seq[l-1::-1]:
                    if job_tmp == job and op_tmp == prior_job_op:
                        prior_job_m = m_tmp
                        break
                for agv in agv_info:
                    interval_agv[agv][job][op] = md.new_interval_var(se_agv[agv][job][op][0], bool_agv[agv][job][op] * getattr(agv_move, f"{prior_job_m}{m}load"), se_agv[agv][job][op][1],f"{prior_job_m}->{m}/{job}/{prior_job_op}->{op}")
                    md.add(se_process[job][prior_job_op][1] <= se_agv[agv][job][op][0])
            else:
                prior_m_job, prior_m_op = machines[m][idx_machine - 1]
                if prior_m_job == job:
                    if prior_m_op == list(ini_set[job])[idx_job - 1]:
                        md.add(bool_agv[agv_info[0]][job][op] == 1)
                        for agv in agv_info:
                            interval_agv[agv][job][op] = md.new_interval_var(se_agv[agv][job][op][0], bool_agv[agv][job][op] * 2, se_agv[agv][job][op][1],f"Special->{m}/{job}")
                            md.add(se_agv[agv][job][op][0] + se_agv[agv][job][op][1] == 2 * se_process[job][op][0])
                    else:
                        md.add(bool_agv[agv_info[0]][job][op] == 0)
                        prior_job_op, prior_job_m = list(ini_set[job])[idx_job - 1], "m"
                        for job_tmp, op_tmp, m_tmp in seq[l - 1::-1]:
                            if job_tmp == job and op_tmp == prior_job_op:
                                prior_job_m = m_tmp
                                break
                        for agv in agv_info:
                            interval_agv[agv][job][op] = md.new_interval_var(se_agv[agv][job][op][0], bool_agv[agv][job][op] * getattr(agv_move, f"{prior_job_m}{m}load"), se_agv[agv][job][op][1],f"{prior_job_m}->{m}/{job}/{prior_job_op}->{op}")
                            md.add(se_process[job][prior_job_op][1] <= se_agv[agv][job][op][0])
                else:
                    md.add(bool_agv[agv_info[0]][job][op] == 0)
                    prior_job_op, prior_job_m = list(ini_set[job])[idx_job - 1], "m"
                    for job_tmp, op_tmp, m_tmp in seq[l - 1::-1]:
                        if job_tmp == job and op_tmp == prior_job_op:
                            prior_job_m = m_tmp
                            break
                    for agv in agv_info:
                        interval_agv[agv][job][op] = md.new_interval_var(se_agv[agv][job][op][0], bool_agv[agv][job][op] * getattr(agv_move, f"{prior_job_m}{m}load"), se_agv[agv][job][op][1],f"{prior_job_m}->{m}/{job}/{prior_job_op}->{op}")
                        md.add(se_process[job][prior_job_op][1] <= se_agv[agv][job][op][0])
        for agv in agv_info[1:]:
            md.add(se_agv[agv][job][op][1] == se_process[job][op][0])
    for agv in agv_info[1:]:
        md.add_no_overlap(interval_agv[agv][job][op] for job in interval_agv[agv] for op in interval_agv[agv][job])
    obj = md.new_int_var(0, horizon, "c_max")
    md.add_max_equality(obj, [se_process[job][op][1] for job in ini_set.keys() for op in ini_set[job]])
    md.minimize(obj)
    solver = cp_model.CpSolver()
    solver.Solve(md)
    se_agv = {agv : {job : {op : (solver.value(se_agv[agv][job][op][0]), solver.value(se_agv[agv][job][op][1]), str(interval_agv[agv][job][op])) for op in se_agv[agv][job].keys()} for job in se_agv[agv].keys()} for agv in se_agv.keys()}

    return encoding(seq), solver.ObjectiveValue(), {job: {op: [solver.value(time) for time in se_process[job][op]] for op in se_process[job].keys()} for job in se_process.keys()}, {m: [(solver.value(st), solver.value(ed)) for st, ed in se_setup[m]] for m in se_setup.keys()}, se_agv

def swap(os_vector, ms_vector):
    idx1, idx2 = rd.choice(range(len(os_vector)), size=2, replace=False)
    os_vector[idx1], os_vector[idx2], ms_vector[idx1], ms_vector[idx2] = os_vector[idx2], os_vector[idx1], ms_vector[
        idx2], ms_vector[idx1]
    return os_vector, ms_vector


def reverse(os_vector, ms_vector):
    idx1, idx2 = sorted(rd.choice(range(len(os_vector)), size=2, replace=False))
    if idx1 != 0:
        os_vector[idx1:idx2 + 1], ms_vector[idx1:idx2 + 1] = os_vector[idx2:idx1 - 1:-1], ms_vector[idx2:idx1 - 1:-1]
    else:
        os_vector[idx1:idx2 + 1], ms_vector[idx1:idx2 + 1] = os_vector[idx2::-1], ms_vector[idx2::-1]
    return os_vector, ms_vector


def reassign(ini_set, os_vector, ms_vector):
    idx = rd.choice(range(len(os_vector)))
    job, op, m_tmp = correct_procedure(ini_set, os_vector, ms_vector)[idx]
    ms_vector[idx] = rd.choice([m for m in ini_set[job][op] if m != m_tmp]) if len(ini_set[job][op]) != 1 else m_tmp
    return os_vector, ms_vector


def crossover(points, os_vector, ms_vector, pair):
    new_os_vector, new_ms_vector = [], []
    points_pair, os_vector_pair, ms_vector_pair = [], pair[0].copy(), pair[1].copy()

    tmp_set = {}
    for job in os_vector:
        if job not in tmp_set:
            tmp_set[job] = 0

    for point in points:
        tmp_set[os_vector[point]] += 1
    for l in range(len(os_vector_pair)):
        if tmp_set[os_vector_pair[l]] > 0:
            tmp_set[os_vector_pair[l]] -= 1
        else:
            points_pair.append(l)
    for i in range(len(os_vector)):
        if i in points:
            new_os_vector.append(os_vector[i])
            new_ms_vector.append(ms_vector[i])
        else:
            idx = points_pair.pop(0)
            new_os_vector.append(os_vector_pair[idx])
            new_ms_vector.append(ms_vector_pair[idx])

def graph_makespan(ini_set, machines, agv_info, best):
    seq, obj, se_process, se_setup, se_agv = best
    seq = correct_procedure(ini_set, agv_info, seq[0], seq[1])
    _, ax = plt.subplots()
    s_job = list(ini_set.keys())
    for m in machines + agv_info:
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
            if round(setup_ing) != 0:
                ax.barh(m, setup_ing, left=st_setup, color='white', edgecolor='black')

    for agv in se_agv.keys():
        for job in se_agv[agv].keys():
            for op in se_agv[agv][job].keys():
                st, ed, attr = se_agv[agv][job][op]
                moving = ed - st
                if round(moving) != 0:
                    ax.barh(agv, moving, left=st, color='orange', edgecolor='black')
                    ax.text(st + moving / 2, agv, "\n".join(attr.split("/")), va='center', ha='center', fontsize=5)
    ax.set_xticks([i for i in range(int(obj) + 2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines) + len(agv_info)))
    ax.set_yticklabels(machines + agv_info)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result (EA-DQN)")
    plt.show()

def fjsp_agv(process, setup, agv_move, ini_set, machines, agv_info):
    ini_os = [job for job in ini_set.keys() for _ in range(len(ini_set[job].keys()))]
    pops1, pops2 = [sorted([decoding(process, setup, agv_move, ini_set, agv_info, (rd.permutation(ini_os).tolist(), [])) for _ in range(params["pop_size"])], key=lambda case: case[1]) for _ in range(2)]
    print(pops1[0][1], pops1[0][0], pops1[0][2:])
    graph_makespan(ini_set, machines, agv_info, pops1[0])
    for gen in range(1, params["num_of_gens"] + 1):
        offsprings = []
        for pops in (pops1, pops2):
            mating_pool = [select_mp(pops) for _ in range(params["mating_pool"])]
            indices = list(range(params["mating_pool"]))
            for _ in range(len(mating_pool) // 2):
                mom, dad = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
                # offsprings.append(generate(process, setup, ini_set, machines, mating_pool[mom], mating_pool[dad]))

    return 0


class Process:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
class AGVMove:
    def __init__(self): pass
def start(processes, setups, machines_tmp, agv_tmp):
    process, setup, ini_set, agv_move, machines = Process(), SetUp(), {}, AGVMove(), []
    for job in processes.keys():
        print(job)
        ini_set[job] = {}
        for op in processes[job]:
            print(f"\t{op} : {processes[job][op]}")
            ms, processing_time = processes[job][op]
            ini_set[job][op] = ms
            for m in ms:
                if m not in machines:
                    machines.append(m)
            setattr(process, f"{job}{op}", processing_time)
    machines.sort(key=lambda machine: machines_tmp.index(machine))
    for job1, op1 in setups:
        for job2, op2 in setups:
            setattr(setup, f"{job1}{op1}{job2}{op2}", setups[(job1, op1)][(job2, op2)])

    for m1, m2, load_time, unload_time in agv_tmp[-1]:
        if m1 != "LU":
            setattr(agv_move, f"{m1}{m2}load", load_time)
            setattr(agv_move, f"{m1}{m2}unload", unload_time)
        else:
            setattr(agv_move, f"LU{m2}", load_time)

    fjsp_agv(process, setup, agv_move, ini_set, machines, agv_tmp[:len(agv_tmp) - 2])

def main():
    machines = [f"M{i}" for i in range(1, num_machines + 1)]
    agv = [f"AGV{i}" for i in range(0, num_AGV + 1)] + [[(m1, m2, rd.randint(1, max(2, (max_time // 3) + 1)), rd.randint(1, max(2, (max_time // 3) + 1))) if m1 != m2 else (m1, m2, 0, 0) if m1 != "LU" else (m1, m2, rd.randint(1, 3), 0) for m1 in machines + ["LU"] for m2 in machines]]

    processes = {f"Job{j}": {f"Op{o + 1}": [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m)), rd.randint(1, max_time + 1)] for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    start(processes, setups, machines, agv)

if __name__ == "__main__":
    main()