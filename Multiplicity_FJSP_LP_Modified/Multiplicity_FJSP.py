from numpy import random
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

def makespan(origin, ini_set, machines):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    binary_space, start_end_each_job, seq_machine, total_operation = {}, {}, {}, []

    for job_type in ini_set:
        binary_space[job_type] = {}
        start_end_each_job[job_type] = {}

        for job in ini_set[job_type]["jobs"]:
            binary_space[job_type][job] = {}
            start_end_each_job[job_type][job] = {}

            for op in ini_set[job_type]["operations"]:
                binary_space[job_type][job][op] = {}
                start_end_each_job[job_type][job][op] = {}
                if (job_type, job, op) not in total_operation:
                    total_operation.append((job_type, job, op))
                for machine in machines:
                    binary_space[job_type][job][op][machine] = md.addVar(vtype=GRB.BINARY)
                    start_end_each_job[job_type][job][op][machine] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstr(start_end_each_job[job_type][job][op][machine][0] >= 0)
                    md.addConstr(start_end_each_job[job_type][job][op][machine][1] == start_end_each_job[job_type][job][op][machine][0] + getattr(origin, f"{job_type}{job}{op}{machine}") * binary_space[job_type][job][op][machine])

                    if op != ini_set[job_type]["operations"][0]:
                        max_prior_operation = md.addVar(vtype=GRB.CONTINUOUS)
                        md.addGenConstrMax(max_prior_operation, [start_end[1] for start_end in start_end_each_job[job_type][job][ini_set[job_type]["operations"][ini_set[job_type]["operations"].index(op) - 1]].values()])
                        md.addConstr(start_end_each_job[job_type][job][op][machine][0] >= max_prior_operation)

                md.addConstr(sum(binary_space[job_type][job][op].values()) == 1)

    for machine in machines:

        for i in range(len(total_operation)):
            ith_op = total_operation[i]
            seq_machine[ith_op] = {}

            for j in range(i + 1, len(total_operation)):
                jth_op = total_operation[j]
                seq_machine[ith_op][jth_op] = md.addVar(vtype=GRB.BINARY)
                md.addGenConstrIndicator(seq_machine[ith_op][jth_op], True, start_end_each_job[ith_op[0]][ith_op[1]][ith_op[2]][machine][1] <= start_end_each_job[jth_op[0]][jth_op[1]][jth_op[2]][machine][0])
                md.addGenConstrIndicator(seq_machine[ith_op][jth_op], False, start_end_each_job[jth_op[0]][jth_op[1]][jth_op[2]][machine][1] <= start_end_each_job[ith_op[0]][ith_op[1]][ith_op[2]][machine][0])

    z = md.addVar(vtype=GRB.CONTINUOUS)
    md.addGenConstrMax(z, [start_end_each_job[job_type][job][operation][machine][1] for job_type in ini_set for job in ini_set[job_type]["jobs"] for operation in ini_set[job_type]["operations"] for machine in machines])
    md.setObjective(z, GRB.MINIMIZE)
    md.optimize()

    for job_type in ini_set:
        print(job_type)
        for job in ini_set[job_type]["jobs"]:
            print("\t", job)
            for op in ini_set[job_type]["operations"]:
                print("\t\t", op, ":", end=" ")
                for machine in machines:
                    print(machine, ":", int(binary_space[job_type][job][op][machine].X) * getattr(origin, f"{job_type}{job}{op}{machine}"), end=" / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")
    for job_type in ini_set:
        print(job_type)
        for job in ini_set[job_type]["jobs"]:
            print("\t", job)
            for op in ini_set[job_type]["operations"]:
                print("\t\t", op, ":", end=" ")
                for machine in machines:
                    print(machine, ":", "(Start :", int(start_end_each_job[job_type][job][op][machine][0].X), "End :", int(start_end_each_job[job_type][job][op][machine][1].X), end=") / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")

    for_print, colors_info = [], []
    fig, ax = plt.subplots()
    for job_type, job, _ in total_operation:
        if (job_type, job) not in colors_info:
            colors_info.append((job_type, job))
    for machine in machines:
        ax.barh(machine, 0, left=0)
        for job_type in ini_set:
            for job in ini_set[job_type]["jobs"]:
                for op in ini_set[job_type]["operations"]:
                    if round(binary_space[job_type][job][op][machine].X) != 0:
                        start_info, end_info = [time_info.X for time_info in start_end_each_job[job_type][job][op][machine]]
                        ax.barh(machine, end_info - start_info, left=start_info, color=plt.get_cmap('tab20', len(colors_info))(colors_info.index((job_type, job))), edgecolor='black')
                        ax.text((start_info + end_info) / 2, machine,f"{job_type}\n{job}\n{op}\n({getattr(origin, f"{job_type}{job}{op}{machine}")})", va='center', ha='center', color='black', fontsize=7)
                        for_print.append((job_type, job, op, machine))
    for_print.sort(key=lambda attr:start_end_each_job[attr[0]][attr[1]][attr[2]][attr[3]][0].X)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()
    return md.ObjVal, for_print

class Build:
    def __init__(self):
        pass
def main():

    # Parameter Input
    the_number_of_job_types = 3
    the_maximal_number_of_job = 3
    the_maximal_number_of_operation = 5
    the_number_of_machines = 5
    max_time = 9

    job_types = [f"Job_Type{i+1}" for i in range(random.randint(1,the_number_of_job_types + 1))]
    num_job_of_type ,num_op_of_type = {}, {}
    for job_type in job_types:
        num_job_of_type[job_type] = random.randint(1,the_maximal_number_of_job + 1)
        num_op_of_type[job_type] = random.randint(2,the_maximal_number_of_operation + 1)
    machines = [f"M{i}" for i in range(1,the_number_of_machines + 1)]

    built_parameter = {job_type : {f"Job{i+1}" : {f"OP{j+1}" : {machine:random.randint(1,max_time+1) for machine in machines} for j in range(num_op_of_type[job_type])} for i in range(num_job_of_type[job_type])} for job_type in job_types}

    for job_type in built_parameter.keys():
        print(job_type)
        for job in built_parameter[job_type]:
            print("\t", end="")
            print(job)
            print("\t", end="")
            print(built_parameter[job_type][job])
        print()
    print("-----------------------------------------------------------------------------------------------------")

    original, ini_set, machines = Build(), {}, []

    for job_type in built_parameter:
        ini_set[job_type] = {"jobs" : [], "operations" : []}
        for job in built_parameter[job_type]:
            ini_set[job_type]["jobs"].append(job)
            for op in built_parameter[job_type][job]:
                if op not in ini_set[job_type]["operations"]:
                    ini_set[job_type]["operations"].append(op)
                for machine in built_parameter[job_type][job][op]:
                    setattr(original, f"{job_type}{job}{op}{machine}", built_parameter[job_type][job][op][machine])
                    if machine not in machines:
                        machines.append(machine)
    result_obj, result_seq = makespan(original, ini_set, machines)
    print("Total Makespan :", result_obj)
    print("Seq :\n", result_seq)

if __name__ == "__main__":
    main()