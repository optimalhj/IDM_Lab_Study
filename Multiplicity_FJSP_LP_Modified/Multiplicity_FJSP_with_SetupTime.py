from numpy import random as rd
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

def makespan(duration, setup, ini_set, machines):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    binary_space, start_end, seq_m, total_operation = {}, {}, {}, []

    for job_type in ini_set:
        binary_space[job_type] = {}
        start_end[job_type] = {}

        for job in ini_set[job_type]["jobs"]:
            binary_space[job_type][job] = {}
            start_end[job_type][job] = {}

            for op in ini_set[job_type]["ops"]:
                binary_space[job_type][job][op] = {}
                start_end[job_type][job][op] = {}
                total_operation.append((job_type, job, op))

                for m in machines:
                    binary_space[job_type][job][op][m] = md.addVar(vtype=GRB.BINARY)
                    start_end[job_type][job][op][m] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstr(start_end[job_type][job][op][m][0] >= 0)
                    md.addConstr(start_end[job_type][job][op][m][1] == start_end[job_type][job][op][m][0] + getattr(duration, f"{job_type}{job}{op}{m}") * binary_space[job_type][job][op][m])

                    if op != ini_set[job_type]["ops"][0]:
                        max_prior_operation = md.addVar(vtype=GRB.CONTINUOUS)
                        md.addGenConstrMax(max_prior_operation, [se[1] for se in start_end[job_type][job][ini_set[job_type]["ops"][ini_set[job_type]["ops"].index(op) - 1]].values()])
                        md.addConstr(start_end[job_type][job][op][m][0] >= max_prior_operation)

                md.addConstr(sum(binary_space[job_type][job][op].values()) == 1)

    for m in machines:

        for i in range(len(total_operation)):
            ith = total_operation[i]
            seq_m[ith] = {}
            for j in range(i + 1, len(total_operation)):
                jth = total_operation[j]
                seq_m[ith][jth] = md.addVar(vtype=GRB.BINARY)
                both_work = md.addVar(vtype=GRB.BINARY)
                md.addGenConstrMin(both_work, [binary_space[ith[0]][ith[1]][ith[2]][m], binary_space[jth[0]][jth[1]][jth[2]][m]])
                md.addGenConstrIndicator(seq_m[ith][jth], True, start_end[ith[0]][ith[1]][ith[2]][m][1] + getattr(setup, f"{m}{ith[0]}{ith[2]}{jth[0]}{jth[2]}") * both_work <= start_end[jth[0]][jth[1]][jth[2]][m][0])
                md.addGenConstrIndicator(seq_m[ith][jth], False, start_end[jth[0]][jth[1]][jth[2]][m][1] + getattr(setup, f"{m}{jth[0]}{jth[2]}{ith[0]}{ith[2]}") * both_work <= start_end[ith[0]][ith[1]][ith[2]][m][0])

    z = md.addVar(vtype=GRB.CONTINUOUS)
    md.addGenConstrMax(z, [start_end[job_type][job][operation][machine][1] for job_type in ini_set for job in ini_set[job_type]["jobs"] for operation in ini_set[job_type]["ops"] for machine in machines])
    md.setObjective(z, GRB.MINIMIZE)
    md.optimize()
    '''
    for job_type in ini_set:
        print(job_type)
        for job in ini_set[job_type]["jobs"]:
            print("\t", job)
            for op in ini_set[job_type]["ops"]:
                print("\t\t", op, ":", end=" ")
                for m in machines:
                    print(m, ":", int(binary_space[job_type][job][op][m].X) * getattr(duration, f"{job_type}{job}{op}{m}"), end=" / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")
    for job_type in ini_set:
        print(job_type)
        for job in ini_set[job_type]["jobs"]:
            print("\t", job)
            for op in ini_set[job_type]["ops"]:
                print("\t\t", op, ":", end=" ")
                for m in machines:
                    print(m, ":", "(Start :", int(start_end[job_type][job][op][m][0].X), "End :", int(start_end[job_type][job][op][m][1].X), end=") / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")
    '''
    final_seq = []
    fig, ax = plt.subplots()
    colors_info = []
    for job_type in ini_set:
        for job in ini_set[job_type]["jobs"]:
            colors_info.append((job_type, job))
    for m in machines:
        ax.barh(m, 0, left=0)
        for job_type in ini_set:
            for job in ini_set[job_type]["jobs"]:
                for op in ini_set[job_type]["ops"]:
                    if round(binary_space[job_type][job][op][m].X) != 0:
                        start_info, end_info = [time_info.X for time_info in start_end[job_type][job][op][m]]
                        ax.barh(m, end_info - start_info, left=start_info, color=plt.get_cmap('tab20', len(colors_info))(colors_info.index((job_type, job))), edgecolor='black')
                        ax.text((start_info + end_info) / 2, m,f"{job_type}\n{job}\n{op}\n({getattr(duration, f"{job_type}{job}{op}{m}")})", va='center', ha='center', color='black', fontsize=7)
                        final_seq.append((job_type, job, op, m))
    final_seq.sort(key=lambda attr: start_end[attr[0]][attr[1]][attr[2]][attr[3]][0].X)
    final_setup = {}
    for m in machines:
        setup_tmp = [oper for oper in final_seq if oper[3] == m]
        final_setup[m] = []
        for i in range(len(setup_tmp) - 1):
            i_oper = setup_tmp[i]
            j_oper = setup_tmp[i + 1]
            setup_time = getattr(setup, f"{m}{i_oper[0]}{i_oper[2]}{j_oper[0]}{j_oper[2]}")
            if setup_time != 0:
                ax.barh(m, setup_time, left=start_end[j_oper[0]][j_oper[1]][j_oper[2]][j_oper[3]][0].X - setup_time, color='black', edgecolor='black')
                final_setup[m].append((i_oper[0:3], j_oper[0:3], setup_time))

    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()
    return md.ObjVal, final_seq, final_setup

class Duration:
    def __init__(self):
        pass
class SetUp:
    def __init__(self):
        pass
def start(durations, setups):
    duration, setup, ini_set, machines = Duration(), SetUp(), {}, []

    for job_type in durations.keys():
        ini_set[job_type] = {"jobs": [], "ops": []}
        for job in durations[job_type]:
            ini_set[job_type]["jobs"].append(job)
            for op in durations[job_type][job]:
                if op not in ini_set[job_type]["ops"]:
                    ini_set[job_type]["ops"].append(op)
                for m in durations[job_type][job][op]:
                    setattr(duration, f"{job_type}{job}{op}{m}", durations[job_type][job][op][m])
                    if m not in machines:
                        machines.append(m)
    for m in machines:
        for job_type1 in ini_set:
            for op1 in ini_set[job_type1]["ops"]:
                for job_type2 in ini_set:
                    for op2 in ini_set[job_type2]["ops"]:
                        setattr(setup, f"{m}{job_type1}{op1}{job_type2}{op2}", setups[m][(job_type1, op1)][(job_type2, op2)])
    result_obj, result_seq, result_setup = makespan(duration, setup, ini_set, machines)
    print("Total Makespan :", result_obj)
    print("Seq :\n", result_seq)
    print("Setups:\n", result_setup)

def main():

    # Parameter Input
    num_job_types = 3
    max_num_job = 3
    max_num_op = 3
    num_machines = 3
    max_time = 9
    max_setup_time = max(max_time//2, 1)

    job_types = [f"Job_Type{i + 1}" for i in range(rd.randint(1, num_job_types + 1))]
    num_job_of_type, num_op_of_type = {}, {}
    for job_type in job_types:
        num_job_of_type[job_type] = rd.randint(1, max_num_job + 1)
        num_op_of_type[job_type] = rd.randint(2, max_num_op + 1)
    machines = [f"M{i}" for i in range(1, num_machines + 1)]

    durations = {}
    for job_type in job_types:
        durations[job_type] = {}
        for i in range(num_job_of_type[job_type]):
            durations[job_type][f"Job{i + 1}"] = {}
            for j in range(num_op_of_type[job_type]):
                durations[job_type][f"Job{i + 1}"][f"OP{j + 1}"] = {}
                for m in machines:
                    durations[job_type][f"Job{i + 1}"][f"OP{j + 1}"][m] = rd.randint(1, max_time + 1)

    setups = {}
    every_op = [(job_type, op) for job_type in job_types for op in durations[job_type][list(durations[job_type])[0]]]
    for m in machines:
        setups[m] = {}
        for op1 in every_op:
            setups[m][op1] = {}
            for op2 in every_op:

                if op1[0] == op2[0]:
                    setups[m][op1][op2] = 0
                else:
                    setups[m][op1][op2] = rd.randint(1, max_setup_time + 1)

    for job_type in durations.keys():
        print(job_type)
        for job in durations[job_type]:
            print("\t", end="")
            print(job)
            print("\t", end="")
            print(durations[job_type][job])
        print()
    print("-----------------------------------------------------------------------------------------------------")

    start(durations, setups)

if __name__ == "__main__":
    main()