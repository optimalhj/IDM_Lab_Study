from numpy import random as rd
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt
import numpy as np
import time

def makespan(duration, setup, ini_set, machines):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    calculating_start = time.time()
    md = gp.Model(env=env)

    binary_space, start_end, seq_m, total_operation = {}, {}, {}, {m : [] for m in machines}

    for job_type in ini_set:
        binary_space[job_type] = {}
        start_end[job_type] = {}

        for job in ini_set[job_type]["jobs"]:
            binary_space[job_type][job] = {}
            start_end[job_type][job] = {}

            for op in ini_set[job_type]["ops"]:
                binary_space[job_type][job][op] = {}
                start_end[job_type][job][op] = {}

                for m in ini_set[job_type]["ops"][op]:
                    total_operation[m].append((job_type, job, op))
                    binary_space[job_type][job][op][m] = md.addVar(vtype=GRB.BINARY)
                    start_end[job_type][job][op][m] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstr(start_end[job_type][job][op][m][0] >= 0)
                    md.addConstr(start_end[job_type][job][op][m][1] == start_end[job_type][job][op][m][0] + getattr(duration, f"{job_type}{op}") * binary_space[job_type][job][op][m])

                    if op != list(ini_set[job_type]["ops"])[0]:
                        max_prior_operation = md.addVar(vtype=GRB.CONTINUOUS)
                        md.addGenConstrMax(max_prior_operation, [se[1] for se in start_end[job_type][job][list(ini_set[job_type]["ops"])[list(ini_set[job_type]["ops"]).index(op) - 1]].values()])
                        md.addConstr(start_end[job_type][job][op][m][0] >= max_prior_operation)

                md.addConstr(sum(binary_space[job_type][job][op].values()) == 1)

    for m in machines:

        for i in range(len(total_operation[m])):
            ith = total_operation[m][i]
            seq_m[ith] = {}
            for j in range(i + 1, len(total_operation[m])):
                jth = total_operation[m][j]
                seq_m[ith][jth] = md.addVar(vtype=GRB.BINARY)
                both_work = md.addVar(vtype=GRB.BINARY)
                md.addGenConstrMin(both_work, [binary_space[ith[0]][ith[1]][ith[2]][m], binary_space[jth[0]][jth[1]][jth[2]][m]])
                md.addGenConstrIndicator(seq_m[ith][jth], True, start_end[ith[0]][ith[1]][ith[2]][m][1] + getattr(setup, f"{ith[0]}{ith[2]}{jth[0]}{jth[2]}") * both_work <= start_end[jth[0]][jth[1]][jth[2]][m][0])
                md.addGenConstrIndicator(seq_m[ith][jth], False, start_end[jth[0]][jth[1]][jth[2]][m][1] + getattr(setup, f"{jth[0]}{jth[2]}{ith[0]}{ith[2]}") * both_work <= start_end[ith[0]][ith[1]][ith[2]][m][0])

    z = md.addVar(vtype=GRB.CONTINUOUS)
    md.addGenConstrMax(z, [start_end[job_type][job][op][m][1] for job_type in start_end for job in start_end[job_type] for op in start_end[job_type][job] for m in start_end[job_type][job][op]])
    md.setObjective(z, GRB.MINIMIZE)
    md.optimize()
    calculating_end = time.time()

    final_seq, colors_info = [], []
    _, ax = plt.subplots()
    for job_type in ini_set:
        for job in ini_set[job_type]["jobs"]:
            colors_info.append((job_type, job))
    for m in machines:
        ax.barh(m, 0, left=0)
        for job_type in ini_set:
            for job in ini_set[job_type]["jobs"]:
                for op in ini_set[job_type]["ops"]:
                    if m in ini_set[job_type]["ops"][op] and round(binary_space[job_type][job][op][m].X) != 0:
                        start_info, end_info = [time_info.X for time_info in start_end[job_type][job][op][m]]
                        ax.barh(m, end_info - start_info, left=start_info, color=plt.get_cmap('tab20', len(colors_info))(colors_info.index((job_type, job))), edgecolor='black')
                        ax.text((start_info + end_info) / 2, m,f"{job_type}\n{job}\n{op}\n{m}\n({getattr(duration, f"{job_type}{op}")})", va='center', ha='center', color='black', fontsize=7)
                        final_seq.append((job_type, job, op, m))
    final_seq.sort(key=lambda attr: start_end[attr[0]][attr[1]][attr[2]][attr[3]][0].X)
    final_setup = {}
    for m in machines:
        setup_tmp = [oper for oper in final_seq if oper[3] == m]
        final_setup[m] = []
        for i in range(len(setup_tmp) - 1):
            i_oper = setup_tmp[i]
            j_oper = setup_tmp[i + 1]
            setup_time = getattr(setup, f"{i_oper[0]}{i_oper[2]}{j_oper[0]}{j_oper[2]}")
            if setup_time != 0:
                ax.barh(m, setup_time, left=start_end[j_oper[0]][j_oper[1]][j_oper[2]][j_oper[3]][0].X - setup_time, color='black', edgecolor='black')
                final_setup[m].append((i_oper[0:3], j_oper[0:3], setup_time))
    ax.set_xlim(0, round(md.ObjVal))
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()
    return round(md.ObjVal), final_seq, final_setup, calculating_end - calculating_start

class Duration:
    def __init__(self):
        pass
class SetUp:
    def __init__(self):
        pass
def start(durations, setups, machines_tmp):
    duration, setup, ini_set, machines = Duration(), SetUp(), {}, []
    for job_type in durations.keys():
        ini_set[job_type] = {"jobs": durations[job_type]["jobs"], "ops": {}}

        for op in durations[job_type]["ops"]:
            ini_set[job_type]["ops"][op] = durations[job_type]["ops"][op][0]
            setattr(duration, f"{job_type}{op}", durations[job_type]["ops"][op][1])
            for m in durations[job_type]["ops"][op][0]:
                if m not in machines:
                    machines.append(m)
    machines.sort(key=lambda machine : machines_tmp.index(machine))

    for job_type1 in ini_set:
        for op1 in ini_set[job_type1]["ops"]:
            for job_type2 in ini_set:
                for op2 in ini_set[job_type2]["ops"]:
                    setattr(setup, f"{job_type1}{op1}{job_type2}{op2}", setups[(job_type1, op1)][(job_type2, op2)])
    result_obj, result_seq, result_setup, calculating_time = makespan(duration, setup, ini_set, machines)

    return result_obj, calculating_time

def main():

    durations = {'Job_Type1': {'jobs': ['Job1', 'Job2', 'Job3'],
                               'ops': {'Op1': [[np.str_('M1'), np.str_('M2')], 3], 'Op2': [[np.str_('M3')], 3]}},
                 'Job_Type2': {'jobs': ['Job1', 'Job2'], 'ops': {'Op1': [[np.str_('M2'), np.str_('M3')], 2]}}}
    setups = {('Job_Type1', 'Op1'): {('Job_Type1', 'Op1'): 0, ('Job_Type1', 'Op2'): 0, ('Job_Type2', 'Op1'): 2},
              ('Job_Type1', 'Op2'): {('Job_Type1', 'Op1'): 0, ('Job_Type1', 'Op2'): 0, ('Job_Type2', 'Op1'): 2},
              ('Job_Type2', 'Op1'): {('Job_Type1', 'Op1'): 2, ('Job_Type1', 'Op2'): 3, ('Job_Type2', 'Op1'): 0}}
    machines = ['M1', 'M2', 'M3']

    start(durations, setups, machines)

if __name__ == "__main__":
    main()