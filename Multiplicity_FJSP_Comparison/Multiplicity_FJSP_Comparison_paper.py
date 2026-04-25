from numpy import random as rd
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt
import time

def makespan(duration, setup, ini_set, machines):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    calculating_start = time.time()
    md = gp.Model(env=env)

    x, y, se, total_operation, big_m = {}, {}, {}, [], 0
    for job_type in ini_set:
        x[job_type], y[job_type], se[job_type] = {}, {}, {}
        for job in ini_set[job_type]["jobs"]:
            x[job_type][job], y[job_type][job], se[job_type][job] = {}, {}, {}
            for op in ini_set[job_type]["ops"]:
                x[job_type][job][op], y[job_type][job][op] = {}, {}
                se[job_type][job][op] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                total_operation.append((job_type, job, op))
                big_m += getattr(duration, f"{job_type}{op}")
                for m in machines:
                    x[job_type][job][op][m], y[job_type][job][op][m] = [md.addVar(vtype=GRB.BINARY) for _ in range(2)]
                md.addConstr(sum(x[job_type][job][op].values()) == 1)
                if op != list(ini_set[job_type]["ops"])[0]:
                    md.addConstr(se[job_type][job][op][0] >= se[job_type][job][list(ini_set[job_type]["ops"])[list(ini_set[job_type]["ops"]).index(op)-1]][1])

    z = {operation1 : {operation2 : md.addVar(vtype=GRB.BINARY) for operation2 in total_operation} for operation1 in total_operation}

    for operation1 in total_operation:
        job_type1, job1, op1 = operation1
        for m in machines:
            if m in ini_set[job_type1]['ops'][op1]:
                md.addConstr(se[job_type1][job1][op1][1] >= se[job_type1][job1][op1][0] + getattr(duration, f"{job_type1}{op1}") - big_m * (1 - y[job_type1][job1][op1][m]))
            else:
                md.addConstr(x[job_type1][job1][op1][m] == 0)
            md.addConstr(x[job_type1][job1][op1][m] >= y[job_type1][job1][op1][m])
        for operation2 in total_operation:
            if operation1 != operation2:
                job_type2, job2, op2 = operation2
                for m in set(ini_set[job_type1]['ops'][op1]) & set(ini_set[job_type2]['ops'][op2]):
                    md.addConstr(se[job_type2][job2][op2][0] >= se[job_type1][job1][op1][1] - big_m * (3 - z[operation1][operation2] + y[job_type2][job2][op2][m] - x[job_type1][job1][op1][m] - x[job_type2][job2][op2][m]))
                    md.addConstr(se[job_type1][job1][op1][0] <= se[job_type2][job2][op2][0] + big_m * (2 - y[job_type1][job1][op1][m] - x[job_type2][job2][op2][m]))
                for m in ini_set[job_type2]['ops'][op2]:
                    md.addConstr(z[operation1][operation2] <= big_m * (1 - y[job_type2][job2][op2][m]))
                    md.addConstr(x[job_type1][job1][op1][m] - x[job_type2][job2][op2][m] <= 1 - z[operation1][operation2])
                    md.addConstr(x[job_type2][job2][op2][m] - x[job_type1][job1][op1][m] <= 1 - z[operation1][operation2])
                    md.addConstr(se[job_type2][job2][op2][1] >= se[job_type2][job2][op2][0] + getattr(duration,f"{job_type2}{op2}") + getattr(setup, f"{job_type1}{op1}{job_type2}{op2}") - big_m * (2 - x[job_type2][job2][op2][m] + y[job_type2][job2][op2][m] -z[operation1][operation2]))
        md.addConstr(gp.quicksum(z[operation1][operation2] for operation2 in total_operation if operation1 != operation2) <= 1)

    for operation2 in total_operation:
        job_type2, job2, op2 = operation2
        for m in ini_set[job_type2]['ops'][op2]:
            z_tmp = md.addVar(vtype=GRB.CONTINUOUS)
            md.addConstr(z_tmp == gp.quicksum(z[operation1][operation2] for operation1 in total_operation if operation2 != operation1))
            md.addConstr(z_tmp <= 1 + big_m * (1 - x[job_type2][job2][op2][m] + y[job_type2][job2][op2][m]))
            md.addConstr(z_tmp >= 1 - big_m * (1 - x[job_type2][job2][op2][m] + y[job_type2][job2][op2][m]))

    md.addConstrs(gp.quicksum(y[job_type][job][op][m] for job_type, job, op in total_operation) == 1 for m in machines)

    c_max= md.addVar(vtype=GRB.CONTINUOUS)
    md.addGenConstrMax(c_max, [se[job_type][job][op][1] for job_type, job, op in total_operation])
    md.setObjective(c_max, GRB.MINIMIZE)
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
                    if m in ini_set[job_type]["ops"][op] and round(x[job_type][job][op][m].X) != 0:
                        end_info, duration_info = se[job_type][job][op][1].X, getattr(duration, f"{job_type}{op}")
                        ax.barh(m, duration_info, left=end_info - duration_info, color=plt.get_cmap('tab20', len(colors_info))(colors_info.index((job_type, job))), edgecolor='black')
                        ax.text(end_info - duration_info / 2, m,f"{job_type}\n{job}\n{op}\n{m}\n({duration_info})", va='center', ha='center', color='black', fontsize=7)
                        final_seq.append((job_type, job, op, m))
    final_seq.sort(key=lambda attr: se[attr[0]][attr[1]][attr[2]][1].X - getattr(duration, f"{attr[0]}{attr[2]}"))

    final_setup = {}
    for m in machines:
        setup_tmp = [oper for oper in final_seq if oper[3] == m]
        final_setup[m] = []
        for i in range(len(setup_tmp) - 1):
            i_oper, j_oper = setup_tmp[i], setup_tmp[i + 1]
            setup_time = getattr(setup, f"{i_oper[0]}{i_oper[2]}{j_oper[0]}{j_oper[2]}")
            if setup_time != 0:
                ax.barh(m, setup_time, left=se[j_oper[0]][j_oper[1]][j_oper[2]][1].X - getattr(duration, f"{j_oper[0]}{j_oper[2]}") - setup_time, color='black', edgecolor='black')
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

    # Parameter Input
    num_job_types = 2
    max_num_job = 3
    max_num_op = 3
    num_machines = 3
    max_time = 6
    max_setup_time = max(max_time//2, 1)

    machines = [f"M{i}" for i in range(1, num_machines + 1)]
    durations = {job_type : {"jobs" : [f"Job{j+1}" for j in range(rd.randint(2, max_num_job + 1))],
                             "ops"  : {f"Op{o+1}":
                                           [sorted(rd.choice(machines, size=rd.randint(1, len(machines)), replace=False), key=lambda m:machines.index(m)),
                                            rd.randint(2, max_num_op + 1)]
                                       for o in range(rd.randint(1, max_num_op + 1))}}
                 for job_type in [f"Job_Type{i + 1}" for i in range(rd.randint(2, num_job_types + 1))]}

    every_op = [(job_type, op) for job_type in durations.keys() for op in durations[job_type][list(durations[job_type])[1]]]
    setups = {op1 : {op2 : 0 if op1[0] == op2[0] else rd.randint(1, max_setup_time + 1) for op2 in every_op} for op1 in every_op}

    start(durations, setups, machines)

if __name__ == "__main__":
    main()