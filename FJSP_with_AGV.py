# import numpy as np
from numpy import random as rd
from ortools.sat.python import cp_model
import matplotlib.pyplot as plt

num_job, max_num_op, num_machines, num_AGV, max_time = 3, 3, 3, 3, 5
params = {"pop_size":10, "num_of_gens": 5, "s_max": 2}

def correct_procedure(ini_set, agv_info, os_vector, ms_vector, vs_vector):
    seq, info_op = os_vector.copy(), {job: {op: 0 for op in ini_set[job]} for job in ini_set.keys()}
    for l in range(len(seq)):
        job = seq[l]
        op = min(ini_set[job], key=lambda op: info_op[job][op])
        info_op[job][op] += 1
        m = ms_vector[l] if len(ms_vector) else str(rd.choice(ini_set[job][op]))
        agv = vs_vector[l] if len(vs_vector) else str(rd.choice(agv_info[1:]))

        final_same_machine_info = ("none_job", "none_op", "none_m", "none_agv")
        for sche in seq[l-1::-1]:
            if sche[2] == m:
                final_same_machine_info = sche
                break
        prior_op = list(ini_set[job])[list(ini_set[job]).index(op) - 1]
        if final_same_machine_info[0] == job and final_same_machine_info[1] == prior_op and final_same_machine_info[2] == m:
            agv = agv_info[0]

        seq[l] = (job, op, m, agv)
    # for vector in seq:
    #     print(vector)
    return seq

def encoding(seq):
    os_vector, ms_vector, vs_vector = [], [], []
    for job, _, m, agv in seq:
        os_vector.append(job)
        ms_vector.append(m)
        vs_vector.append(agv)
    return os_vector, ms_vector, vs_vector

def decoding(process, setup, agv_move, ini_set, agv_info, vectors):
    se_process, interval = {}, {}
    seq = correct_procedure(ini_set, agv_info, vectors[0], vectors[1], vectors[2])
    horizon = num_job * max_num_op * max_time
    md = cp_model.CpModel()
    for job in ini_set.keys():
        se_process[job], interval[job] = {}, {}
        for l in range(len(ini_set[job])):
            op = list(ini_set[job])[l]
            se_process[job][op] = [md.new_int_var(0, horizon, f'{job}{op}') for _ in range(2)]
            interval[job][op] = md.new_interval_var(se_process[job][op][0], getattr(process, f"{job}{op}"), se_process[job][op][1], f'{job}{op}')
            if l >= 1: md.add(se_process[job][list(ini_set[job])[l-1]][1] <= se_process[job][op][0])
        md.add_no_overlap(interval[job].values())

    machines, se_setup, interval_setup = {}, {}, {}
    for job, op, m, agv in seq:
        if m not in machines:
            machines[m] = []
            se_setup[m] = []
            interval_setup[m] = []
        machines[m].append((job, op))

    for m in machines.keys():
        for l in range(1, len(machines[m])):
            job1, op1 = machines[m][l-1]
            job2, op2 = machines[m][l]
            md.add(se_process[job1][op1][1] <= se_process[job2][op2][0])
            if getattr(setup, f"{job1}{op1}{job2}{op2}"):
                se_setup[m].append([md.new_int_var(0, horizon, f'{job1}{op1}_{job2}{op2}') for _ in range(2)])
                idx = len(se_setup[m]) - 1
                interval_setup[m].append(md.new_interval_var(se_setup[m][idx][0], getattr(setup, f"{job1}{op1}{job2}{op2}"), se_setup[m][idx][1], f'{job1}{op1}_{job2}{op2}'))
                md.add(se_setup[m][idx][1] == se_process[job2][op2][0])
        md.add_no_overlap(interval_setup[m] + [interval[job][op] for job, op in machines[m]])
    md.add_cumulative([l for m in interval_setup.keys() for l in interval_setup[m]], [1 for m in interval_setup.keys() for _ in interval_setup[m]], params["s_max"])

    agvs, se_agv, interval_agv = {}, {}, {}
    for agv in agv_info:
        agvs[agv] = []
        se_agv[agv] = []
        interval_agv[agv] = []
    for job, op, m, agv in seq:
        agvs[agv].append((job, op, m))

    for agv in agv_info:
        if agv == agv_info[0]:
            for l in range(len(agvs[agv])):
                job, op, m = agvs[agv][l]
                se_agv[agv].append([md.new_int_var(0, horizon, f"{job}{op}") for _ in range(2)] + [f"{(job, m)}"])
                interval_agv[agv].append(md.new_interval_var(se_agv[agv][l][0], 2, se_agv[agv][l][1], se_agv[agv][l][2]))
                md.add(se_agv[agv][l][0] + se_agv[agv][l][1] == 2 * se_process[job][op][0])
        else:
            for l in range(len(agvs[agv])):
                job, op, m = agvs[agv][l]
                if l == 0:
                    se_agv[agv].append([md.new_int_var(0, horizon, f"{job}{op}") for _ in range(2)] + [f"First/({job}, {op}, {m})"])
                    interval_agv[agv].append(md.new_interval_var(se_agv[agv][l][0], getattr(agv_move, f"LU{m}"), se_agv[agv][l][1],se_agv[agv][l][2]))
                else:
                    prior_job, prior_op, prior_m = agvs[agv][l - 1]
                    if op != list(ini_set[job])[0]:


                        if prior_job == job: # Loading Situation
                            se_agv[agv].append([md.new_int_var(0, horizon, f"{job}{op}") for _ in range(2)] + [f"Loaded/({prior_job}, {prior_op}, {prior_m})/({job}, {op}, {m})"])
                            interval_agv[agv].append(md.new_interval_var(se_agv[agv][l][0], getattr(agv_move, f"{prior_m}{m}load"), se_agv[agv][l][1], se_agv[agv][l][2]))
                            md.add(se_process[prior_job][prior_op][1] <= se_agv[agv][l][0])

                        else: # Unloading Situation
                            se_agv[agv].append([md.new_int_var(0, horizon, f"{job}{op}") for _ in range(2)] + [f"UnLoaded/({prior_job}, {prior_op}, {prior_m})/({job}, {op}, {m})"])
                            interval_agv[agv].append(md.new_interval_var(se_agv[agv][l][0], getattr(agv_move, f"{prior_m}{m}unload"), se_agv[agv][l][1], se_agv[agv][l][2]))
                            md.add(se_process[prior_job][prior_op][0] <= se_agv[agv][l][0])

                    else:
                        se_agv[agv].append([md.new_int_var(0, horizon, f"{job}{op}") for _ in range(2)] + [f"Comeback/({prior_job}, {prior_op}, {prior_m})/({job}, {op}, {m})"])
                        interval_agv[agv].append(md.new_interval_var(se_agv[agv][l][0], getattr(agv_move, f"LU{prior_m}") + getattr(agv_move, f"LU{m}"), se_agv[agv][l][1], se_agv[agv][l][2]))
                        md.add(se_process[prior_job][prior_op][0] <= se_agv[agv][l][0])
                    md.add(se_agv[agv][l - 1][1] <= se_agv[agv][l][0])
                md.add(se_agv[agv][l][1] <= se_process[job][op][0])

            md.add_no_overlap(interval_agv[agv])

    obj = md.new_int_var(0, horizon, "c_max")
    md.add_max_equality(obj, [se_process[job][op][1] for job in ini_set.keys() for op in ini_set[job]])
    md.minimize(obj)
    solver = cp_model.CpSolver()
    solver.Solve(md)

    se_agv = {agv : [(solver.value(st), solver.value(ed), attr) for st, ed, attr in se_agv[agv]] for agv in se_agv.keys()}
    return encoding(seq), solver.ObjectiveValue(), {job : {op : [solver.value(time) for time in se_process[job][op]] for op in se_process[job].keys()} for job in se_process.keys()}, {m:[(solver.value(st), solver.value(ed)) for st, ed in se_setup[m]] for m in se_setup.keys()}, se_agv

def graph_makespan(ini_set, machines, agv_info, best):
    seq, obj, se_process, se_setup, se_agv = best
    seq = correct_procedure(ini_set, agv_info, seq[0], seq[1], seq[2])
    _, ax = plt.subplots()
    s_job = list(ini_set.keys())
    for m in machines + agv_info:
        ax.barh(m, 0, left=0)
    for l in range(len(seq)):
        job, op, m, _ = seq[l]
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
        for st, ed, attr in se_agv[agv]:
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
    pops1, pops2 = [sorted([decoding(process, setup, agv_move, ini_set, agv_info, (rd.permutation(ini_os).tolist(), [], [])) for _ in range(params["pop_size"])], key=lambda case:case[1]) for _ in range(2)]
    for pop in sorted(pops1, key=lambda case:case[1]):
        print(pop[1], pop[0], pop[2:])
    graph_makespan(ini_set, machines, agv_info, pops1[0])
    for gen in range(1, params["num_of_gens"] + 1):
        break

    return 0

class Process:
    def __init__(self): pass
class SetUp:
    def __init__(self): pass
class AGVMove:
    def __init__(self): pass
class AGVUnLoaded:
    def __init__(self): pass
def start(processes, setups, machines_tmp, agv_tmp):
    process, setup, ini_set, agv_move, machines = Process(), SetUp(), {}, AGVMove(),[]
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

    processes = {f"Job{j + 1}": {f"Op{o + 1}": [sorted(rd.choice(machines, size=rd.randint(2, len(machines)), replace=False).tolist(), key=lambda m: machines.index(m)), rd.randint(1, max_time + 1)] for o in range(rd.randint(1, max_num_op + 1))} for j in range(1, num_job + 1)}

    op_types = [(job, op) for job in processes.keys() for op in processes[job].keys()]
    setups = {op1: {op2: 0 if op1[0] == op2[0] else rd.randint(1, max(max_time // 2, 1) + 1) for op2 in op_types}
              for op1 in op_types}

    start(processes, setups, machines, agv)

if __name__ == "__main__":
    main()