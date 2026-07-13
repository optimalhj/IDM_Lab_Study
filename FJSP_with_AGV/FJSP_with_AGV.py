# import numpy as np
from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt

num_job, max_num_op, num_machines, num_AGV, max_time = 4, 4, 3, 3, 8
params = {"pop_size": 10, "mating_pool": 10, "num_of_gens": 1, "s_max": 2}

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
    seq = correct_procedure(ini_set, vectors[0], vectors[1])
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

    bool_agv, se_load_agv, se_unload_agv, interval_load_agv, interval_unload_agv, loading_time_agv, unloading_time_agv, history_agv = {}, {}, {}, {}, {}, {}, {}, {}

    for agv in agv_info:
        bool_agv[agv] = {}
        se_load_agv[agv] = {}
        se_unload_agv[agv] = {}
        interval_load_agv[agv] = {}
        interval_unload_agv[agv] = {}
        loading_time_agv[agv] = {}
        unloading_time_agv[agv] = {}
        history_agv[agv] = {}
        for job in ini_set.keys():
            bool_agv[agv][job] = {}
            se_load_agv[agv][job] = {}
            se_unload_agv[agv][job] = {}
            interval_load_agv[agv][job] = {}
            interval_unload_agv[agv][job] = {}
            loading_time_agv[agv][job] = {}
            unloading_time_agv[agv][job] = {}
            history_agv[agv][job] = {}
            for op in ini_set[job].keys():
                bool_agv[agv][job][op] = md.new_bool_var(f"{agv}/{job}/{op}")
                se_load_agv[agv][job][op] = [md.new_int_var(0, horizon, f"{agv}/{job}/{op}") for _ in range(2)]
                se_unload_agv[agv][job][op] = [md.new_int_var(0, horizon, f"{agv}/{job}/{op}") for _ in range(2)]
                loading_time_agv[agv][job][op] = md.new_int_var(0, horizon, f"{agv}/{job}/{op}")
                unloading_time_agv[agv][job][op] = md.new_int_var(0, horizon, f"{agv}/{job}/{op}")
                m = ""
                for job_tmp, op_tmp, m_tmp in seq:
                    if job_tmp == job and op_tmp == op:
                        m = m_tmp
                        break
                interval_unload_agv[agv][job][op] = md.new_interval_var(se_unload_agv[agv][job][op][0], unloading_time_agv[agv][job][op], se_unload_agv[agv][job][op][1], m)
                interval_load_agv[agv][job][op] = md.new_interval_var(se_load_agv[agv][job][op][0], loading_time_agv[agv][job][op], se_load_agv[agv][job][op][1], m)
                history_agv[agv][job][op] = [md.new_bool_var(f"{agv}/{job}/{op}"), {m_tmp : md.new_bool_var(f"{agv}/{job}/{op}") for m_tmp in machines.keys()}]

    for job in ini_set.keys():
        for op in ini_set[job].keys():
            md.add(sum(bool_agv[agv][job][op] for agv in agv_info) == 1)

    for l in range(len(seq)):
        job, op, m = seq[l]
        idx_job, idx_machine = list(ini_set[job]).index(op), machines[m].index((job, op))
        if idx_job != 0 and idx_machine != 0 and (job, list(ini_set[job])[idx_job - 1]) == machines[m][idx_machine - 1]:
            md.add(bool_agv[agv_info[0]][job][op] == 1)
            md.add(se_process[job][list(ini_set[job])[idx_job-1]][1] == se_process[job][op][0]).OnlyEnforceIf(bool_agv[agv_info[0]][job][op])
            for agv in agv_info:
                md.add(unloading_time_agv[agv][job][op] == 0)
                md.add(se_unload_agv[agv][job][op][1] == se_load_agv[agv][job][op][0])
                md.add(loading_time_agv[agv][job][op] == 2 * bool_agv[agv][job][op])
                md.add(se_load_agv[agv][job][op][0] + se_load_agv[agv][job][op][1] == 2 * se_process[job][op][0])

        else:
            md.add(bool_agv[agv_info[0]][job][op] == 0)
            md.add(unloading_time_agv[agv_info[0]][job][op] == 0)
            md.add(se_unload_agv[agv_info[0]][job][op][1] == se_load_agv[agv_info[0]][job][op][0])
            md.add(loading_time_agv[agv_info[0]][job][op] == bool_agv[agv_info[0]][job][op])

            for agv in agv_info[1:]:
                md.add(sum(bool_agv[agv][seq[l0][0]][seq[l0][1]] for l0 in range(l)) == 0).OnlyEnforceIf(history_agv[agv][job][op][0].Not())
                md.add(sum(bool_agv[agv][seq[l0][0]][seq[l0][1]] for l0 in range(l)) != 0).OnlyEnforceIf(history_agv[agv][job][op][0])
                md.add(sum(history_agv[agv][job][op][1][m_tmp] for m_tmp in machines.keys()) <= history_agv[agv][job][op][0])

                md.add(unloading_time_agv[agv][job][op] == 0).OnlyEnforceIf(bool_agv[agv][job][op].Not())
                was_last_work = [md.new_bool_var(f"{job_tmp}{op_tmp}{m_tmp}") for job_tmp, op_tmp, m_tmp in seq[:l]]
                md.add(sum(was_last_work) == 1).OnlyEnforceIf([history_agv[agv][job][op][0], bool_agv[agv][job][op]])

                for l0 in range(l):
                    job_tmp, op_tmp, m_tmp = seq[l0]
                    md.add(se_process[job_tmp][op_tmp][0] <= se_unload_agv[agv][job][op][0]).OnlyEnforceIf([bool_agv[agv][job_tmp][op_tmp], history_agv[agv][job][op][0]])
                    md.add(was_last_work[l0] <= bool_agv[agv][job_tmp][op_tmp]).OnlyEnforceIf(history_agv[agv][job][op][0])
                    md.add(history_agv[agv][job][op][1][m_tmp] == 1).OnlyEnforceIf(was_last_work[l0])
                    md.add(sum(bool_agv[agv][seq[l1][0]][seq[l1][1]] for l1 in range(l0 + 1, l)) == 0).OnlyEnforceIf(was_last_work[l0])

                prior_job_m = "LU"
                if idx_job == 0:
                    md.add(unloading_time_agv[agv][job][op] == 0).OnlyEnforceIf([history_agv[agv][job][op][0].Not(), bool_agv[agv][job][op]])

                else:
                    prior_job_op = list(ini_set[job])[idx_job - 1]
                    for job_tmp, op_tmp, m_tmp in seq[l - 1::-1]:
                        if job_tmp == job and op_tmp == prior_job_op:
                            prior_job_m = m_tmp
                            break
                    md.add(unloading_time_agv[agv][job][op] == getattr(agv_move, f"LU{prior_job_m}unload")).OnlyEnforceIf([history_agv[agv][job][op][0].Not(), bool_agv[agv][job][op]])
                    md.add(se_process[job][prior_job_op][1] <= se_load_agv[agv][job][op][0])

                md.add(unloading_time_agv[agv][job][op] == sum(history_agv[agv][job][op][1][m_tmp] * getattr(agv_move, f"{m_tmp}{prior_job_m}unload") for m_tmp in machines.keys())).OnlyEnforceIf([history_agv[agv][job][op][0], bool_agv[agv][job][op]])
                md.add(loading_time_agv[agv][job][op] == bool_agv[agv][job][op] * getattr(agv_move,f"{prior_job_m}{m}"))
                md.add(se_unload_agv[agv][job][op][1] <= se_load_agv[agv][job][op][0])

                md.add(se_load_agv[agv][job][op][1] == se_process[job][op][0])

        for agv in agv_info[1:]: md.add_no_overlap([interval_unload_agv[agv][job][op] for job in interval_unload_agv[agv].keys() for op in interval_unload_agv[agv][job].keys()] + [interval_load_agv[agv][job][op] for job in interval_load_agv[agv] for op in interval_load_agv[agv][job]])

    obj = md.new_int_var(0, horizon, "c_max")
    md.add_max_equality(obj, [se_process[job][op][1] for job in ini_set.keys() for op in ini_set[job]])
    md.minimize(obj)
    solver = cp_model.CpSolver()
    solver.Solve(md)

    se_process = {job: {op: [solver.value(time) for time in se_process[job][op]] for op in se_process[job].keys()} for job in se_process.keys()}
    se_setup = {m: [(solver.value(st), solver.value(ed)) for st, ed in se_setup[m] if round(solver.value(ed) - solver.value(st)) != 0] for m in se_setup.keys()}
    se_unload_agv = {agv: {job: {op: (solver.value(se_unload_agv[agv][job][op][0]), solver.value(se_unload_agv[agv][job][op][1]), f"{"".join([m_tmp * solver.value(history_agv[agv][job][op][1][m_tmp]) for m_tmp in machines.keys()]) if solver.value(history_agv[agv][job][op][0]) else "LU"}->{interval_unload_agv[agv][job][list(ini_set[job])[list(ini_set[job]).index(op) - 1]] if list(ini_set[job]).index(op) else f"LU"}") for op in se_unload_agv[agv][job].keys() if round(solver.value(se_unload_agv[agv][job][op][1]) - solver.value(se_unload_agv[agv][job][op][0])) != 0} for job in se_unload_agv[agv].keys()} for agv in se_unload_agv.keys()}
    se_load_agv = {agv: {job: {op: (solver.value(se_load_agv[agv][job][op][0]), solver.value(se_load_agv[agv][job][op][1]), f"{interval_load_agv[agv][job][list(ini_set[job])[list(ini_set[job]).index(op) - 1]] if list(ini_set[job]).index(op) else f"LU"}->{interval_load_agv[agv][job][op]}") for op in se_load_agv[agv][job].keys() if round(solver.value(se_load_agv[agv][job][op][1]) - solver.value(se_load_agv[agv][job][op][0])) != 0} for job in se_load_agv[agv].keys()} for agv in se_load_agv.keys()}
    return encoding(seq), solver.ObjectiveValue(), se_process, se_setup, se_load_agv, se_unload_agv

def mutation(process, setup, agv_move, ini_set, agv_info, pr):
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
    return decoding(process, setup, agv_move, ini_set, agv_info, (os_vector, ms_vector))

def crossover(process, setup, agv_move, ini_set, agv_info, pr1, pr2):
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

    tmp_set = {}
    for job in os_vector:
        if job not in tmp_set:
            tmp_set[job] = 0
    for point in points:
        tmp_set[os_vector[point]] += 1
    for l in range(len(os_vector_pair)):
        if tmp_set[os_vector_pair[l]] > 0:
            tmp_set[os_vector_pair[l]] -= 1
        else: points_pair.append(l)
    for i in range(len(os_vector)):
        if i in points:
            new_os_vector.append(os_vector[i])
            new_ms_vector.append(ms_vector[i])
        else:
            idx = points_pair.pop(0)
            new_os_vector.append(os_vector_pair[idx])
            new_ms_vector.append(ms_vector_pair[idx])

    return decoding(process, setup, agv_move, ini_set, agv_info, (new_os_vector, new_ms_vector))

def graph_gen(final):

    plt.plot([f"Gen{i+1}" for i in range(len(final))], final)

    plt.xticks(rotation=45, fontsize=5)
    plt.title("Makespan of FJSP")

    plt.xlabel("Gen")
    plt.ylabel("Tardiness")

    plt.show()

def graph_makespan(ini_set, machines, agv_info, best):
    seq, obj, se_process, se_setup, se_load_agv, se_unload_agv = best
    seq = correct_procedure(ini_set, seq[0], seq[1])
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
            ax.barh(m, setup_ing, left=st_setup, color='white', edgecolor='black')

    agv_load_list = {agv : sorted([(job, op) for job in se_load_agv[agv].keys() for op in se_load_agv[agv][job]], key=lambda sche:se_load_agv[agv][sche[0]][sche[1]][0]) for agv in agv_info}
    for agv in agv_info:
        print(agv, agv_load_list[agv])
    for agv in se_load_agv.keys():
        for job in se_load_agv[agv].keys():
            for op in se_load_agv[agv][job].keys():
                st, ed, attr = se_load_agv[agv][job][op]
                loading = ed - st

                if round(loading) != 0:
                    ax.barh(agv, loading, left=st, color='orange', edgecolor='black')
                    ax.text(st + loading / 2, agv, attr + f"\n{job}\n{list(ini_set[job])[list(ini_set[job]).index(op)-1] + "->" if list(ini_set[job]).index(op) else ""}{op}"+ f"\n({loading})" if agv != agv_info[0] else f"Special\n{job}", va='center', ha='center', fontsize=5)

    for agv in se_unload_agv.keys():
        for job in se_unload_agv[agv].keys():
            for op in se_unload_agv[agv][job]:
                st, ed, attr = se_unload_agv[agv][job][op]
                unloading = ed - st

                if round(unloading) != 0:
                    ax.barh(agv, unloading, left=st, color='white', edgecolor='black')
                    ax.text(st + unloading / 2, agv, attr + f"\n({unloading})", va='center', ha='center', fontsize=5)

    ax.set_xticks([i for i in range(int(obj) + 2)])
    ax.tick_params(axis='x', labelsize=5)
    ax.set_yticks(range(len(machines) + len(agv_info)))
    ax.set_yticklabels(machines + agv_info)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()

def fjsp_agv(process, setup, agv_move, ini_set, machines, agv_info):
    history = []
    ini_os = [job for job in ini_set.keys() for _ in range(len(ini_set[job].keys()))]
    pops = sorted([decoding(process, setup, agv_move, ini_set, agv_info, (rd.permutation(ini_os).tolist(), [])) for _ in range(params["pop_size"])], key=lambda case: case[1])
    for gen in range(1, params["num_of_gens"] + 1):
        offsprings = []

        mating_pool = [select_mp(pops) for _ in range(params["mating_pool"])]
        indices = list(range(params["mating_pool"]))
        for _ in range(len(mating_pool) // 2):
            pr1, pr2 = [indices.pop(rd.randint(len(indices))) for _ in range(2)]
            offsprings.append(crossover(process, setup, agv_move, ini_set, agv_info, mating_pool[pr1], mating_pool[pr2]) if rd.random() < 0.5 else mutation(process, setup, agv_move, ini_set, agv_info, mating_pool[pr1]))
        if pops[0][1] > offsprings[0][1]:
            pops = sorted(pops+offsprings, key=lambda case: case[1])[:params["pop_size"]]
        history.append(pops[0][1])
    graph_gen(history)
    graph_makespan(ini_set, machines, agv_info, pops[0])
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
        setattr(agv_move, f"{m1}{m2}", load_time)
        setattr(agv_move, f"{m1}{m2}unload", unload_time)
    fjsp_agv(process, setup, agv_move, ini_set, machines, agv_tmp[:len(agv_tmp) - 1])

def main():
    machines = [f"M{i}" for i in range(1, num_machines + 1)]
    agv = [f"AGV{i}" for i in range(0, num_AGV + 1)] + [[(m1, m2, rd.randint(1, max(2, (max_time // 3) + 1)), rd.randint(1, max(2, (max_time // 3) + 1))) if m1 != m2 else (m1, m2, 0, 0)  for m1 in machines + ["LU"] for m2 in machines + ["LU"]]]

    processes = {f"Job{j}": {f"Op{o + 1}": [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m)), rd.randint(1, max_time + 1)] for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types} for op1 in op_types}

    start(processes, setups, machines, agv)

if __name__ == "__main__":
    main()