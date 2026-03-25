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
    '''
    for job_type in binary_space:
        print(job_type)
        for job in binary_space[job_type]:
            print("\t", job)
            for op in binary_space[job_type][job]:
                print("\t\t", op, ":", end=" ")
                for machine in binary_space[job_type][job][op]:
                    print(machine, ":", int(binary_space[job_type][job][op][machine].X) * getattr(origin, f"{job_type}{job}{op}{machine}"), end=" / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")
    for job_type in binary_space:
        print(job_type)
        for job in binary_space[job_type]:
            print("\t", job)
            for op in binary_space[job_type][job]:
                print("\t\t", op, ":", end=" ")
                for machine in binary_space[job_type][job][op]:
                    print(machine, ":", "(Start :", int(binary_space[job_type][job][op][machine][0].X), "End :", int(binary_space[job_type][job][op][machine][1].X), end=") / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")
    '''
    fig, ax = plt.subplots()
    colors_info = [(job_type, job) for job_type, job, _ in total_operation]
    for job_type in ini_set:
        for job in ini_set[job_type]["jobs"]:
            for operation in ini_set[job_type]["operations"]:
                for machine in machines:
                    if binary_space[job_type][job][operation][machine].X != 0:
                        start_info, end_info = [time_info.X for time_info in start_end_each_job[job_type][job][operation][machine]]
                        ax.barh(machine, end_info - start_info, left=start_info, color=plt.get_cmap('tab20', len(colors_info))(colors_info.index((job_type, job))), edgecolor='black')
                        ax.text((start_info + end_info) / 2, machine,f"{job_type}\n{job}\n{operation}\n({getattr(origin, f"{job_type}{job}{operation}{machine}")})", va='center', ha='center', color='black', fontsize=7)
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()
    return md.ObjVal

class Build:
    def __init__(self):
        pass
def start():
    """
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
    """

    built_parameter = {
        "Job_Type1" : {
            "Job1" : {
                'OP1': {'M1': 2, 'M2': 5, 'M3': 1, 'M4': 5, 'M5': 9}, 'OP2': {'M1': 9, 'M2': 2, 'M3': 9, 'M4': 5, 'M5': 2},
                'OP3': {'M1': 5, 'M2': 3, 'M3': 1, 'M4': 9, 'M5': 6}, 'OP4': {'M1': 5, 'M2': 5, 'M3': 1, 'M4': 6, 'M5': 3}},
            "Job2" : {
                'OP1': {'M1': 8, 'M2': 6, 'M3': 1, 'M4': 9, 'M5': 8}, 'OP2': {'M1': 4, 'M2': 6, 'M3': 3, 'M4': 5, 'M5': 1},
                'OP3': {'M1': 2, 'M2': 3, 'M3': 9, 'M4': 8, 'M5': 1}, 'OP4': {'M1': 3, 'M2': 3, 'M3': 6, 'M4': 4, 'M5': 7}},
            "Job3" : {
                'OP1': {'M1': 3, 'M2': 9, 'M3': 4, 'M4': 2, 'M5': 2}, 'OP2': {'M1': 8, 'M2': 4, 'M3': 2, 'M4': 6, 'M5': 9},
                'OP3': {'M1': 6, 'M2': 4, 'M3': 6, 'M4': 4, 'M5': 3}, 'OP4': {'M1': 6, 'M2': 6, 'M3': 5, 'M4': 7, 'M5': 3}}},
        "Job_Type2" : {
            "Job1" : {
                'OP1': {'M1': 2, 'M2': 1, 'M3': 4, 'M4': 7, 'M5': 9}, 'OP2': {'M1': 5, 'M2': 8, 'M3': 7, 'M4': 8, 'M5': 5},
                'OP3': {'M1': 6, 'M2': 8, 'M3': 6, 'M4': 2, 'M5': 2}, 'OP4': {'M1': 7, 'M2': 8, 'M3': 7, 'M4': 6, 'M5': 9}}},
        "Job_Type3" : {
            "Job1" : {
                'OP1': {'M1': 3, 'M2': 2, 'M3': 8, 'M4': 2, 'M5': 4}, 'OP2': {'M1': 3, 'M2': 6, 'M3': 1, 'M4': 5, 'M5': 2},
                'OP3': {'M1': 8, 'M2': 7, 'M3': 3, 'M4': 6, 'M5': 7}, 'OP4': {'M1': 1, 'M2': 3, 'M3': 5, 'M4': 7, 'M5': 2},
                'OP5': {'M1': 3, 'M2': 8, 'M3': 2, 'M4': 2, 'M5': 5}},
            "Job2" : {
                'OP1': {'M1': 6, 'M2': 2, 'M3': 2, 'M4': 6, 'M5': 5}, 'OP2': {'M1': 2, 'M2': 4, 'M3': 5, 'M4': 6, 'M5': 7},
                'OP3': {'M1': 8, 'M2': 5, 'M3': 2, 'M4': 8, 'M5': 9}, 'OP4': {'M1': 7, 'M2': 9, 'M3': 3, 'M4': 8, 'M5': 1},
                'OP5': {'M1': 5, 'M2': 8, 'M3': 6, 'M4': 8, 'M5': 6}}}}

    """
    built_parameter = {
        "Job_Type1" : {
            "Job1" : {
                'OP1': {'M1': 4, 'M2': 1, 'M3': 5, 'M4': 2, 'M5': 7}, 'OP2': {'M1': 2, 'M2': 2, 'M3': 8, 'M4': 6, 'M5': 9},
                'OP3': {'M1': 3, 'M2': 5, 'M3': 4, 'M4': 3, 'M5': 8}, 'OP4': {'M1': 3, 'M2': 6, 'M3': 7, 'M4': 4, 'M5': 2}},
	        "Job2" : {
                'OP1': {'M1': 8, 'M2': 1, 'M3': 3, 'M4': 8, 'M5': 4}, 'OP2': {'M1': 6, 'M2': 1, 'M3': 2, 'M4': 8, 'M5': 4},
                'OP3': {'M1': 9, 'M2': 7, 'M3': 5, 'M4': 6, 'M5': 3}, 'OP4': {'M1': 8, 'M2': 7, 'M3': 5, 'M4': 3, 'M5': 8}}},
        "Job_Type2" : {
	        "Job1" : {
                'OP1': {'M1': 7, 'M2': 6, 'M3': 9, 'M4': 7, 'M5': 5}, 'OP2': {'M1': 5, 'M2': 7, 'M3': 6, 'M4': 6, 'M5': 5},
                'OP3': {'M1': 7, 'M2': 8, 'M3': 3, 'M4': 5, 'M5': 1}, 'OP4': {'M1': 7, 'M2': 1, 'M3': 8, 'M4': 9, 'M5': 5}},
	        "Job2" : {
                'OP1': {'M1': 6, 'M2': 4, 'M3': 1, 'M4': 6, 'M5': 1}, 'OP2': {'M1': 1, 'M2': 8, 'M3': 8, 'M4': 1, 'M5': 5},
                'OP3': {'M1': 6, 'M2': 9, 'M3': 8, 'M4': 2, 'M5': 5}, 'OP4': {'M1': 6, 'M2': 4, 'M3': 5, 'M4': 9, 'M5': 8}},
	        "Job3" : {
                'OP1': {'M1': 6, 'M2': 2, 'M3': 6, 'M4': 8, 'M5': 2}, 'OP2': {'M1': 2, 'M2': 5, 'M3': 5, 'M4': 7, 'M5': 5},
                'OP3': {'M1': 1, 'M2': 5, 'M3': 3, 'M4': 7, 'M5': 4}, 'OP4': {'M1': 1, 'M2': 6, 'M3': 3, 'M4': 3, 'M5': 8}}},
        "Job_Type3" : {
            "Job1" : {
                'OP1': {'M1': 5, 'M2': 7, 'M3': 8, 'M4': 9, 'M5': 7}, 'OP2': {'M1': 6, 'M2': 8, 'M3': 4, 'M4': 9, 'M5': 7}},
	        "Job2" : {
                'OP1': {'M1': 8, 'M2': 9, 'M3': 1, 'M4': 1, 'M5': 5}, 'OP2': {'M1': 1, 'M2': 7, 'M3': 7, 'M4': 7, 'M5': 8}},
            "Job3" : {
                'OP1': {'M1': 8, 'M2': 7, 'M3': 1, 'M4': 2, 'M5': 3}, 'OP2': {'M1': 3, 'M2': 9, 'M3': 8, 'M4': 4, 'M5': 1}}}}
    """
    """
    built_parameter = {
        "Job_Type1" : {
            "Job1" : {
                'OP1': {'M1': 4, 'M2': 3, 'M3': 4, 'M4': 7, 'M5': 8}, 'OP2': {'M1': 9, 'M2': 4, 'M3': 4, 'M4': 2, 'M5': 6},
                'OP3': {'M1': 2, 'M2': 2, 'M3': 2, 'M4': 4, 'M5': 6}, 'OP4': {'M1': 6, 'M2': 5, 'M3': 7, 'M4': 8, 'M5': 5}},
            "Job2" : {
                'OP1': {'M1': 4, 'M2': 7, 'M3': 8, 'M4': 3, 'M5': 6}, 'OP2': {'M1': 4, 'M2': 4, 'M3': 1, 'M4': 3, 'M5': 8},
                'OP3': {'M1': 1, 'M2': 2, 'M3': 8, 'M4': 8, 'M5': 8}, 'OP4': {'M1': 4, 'M2': 6, 'M3': 8, 'M4': 7, 'M5': 9}},
            "Job3" : {
                'OP1': {'M1': 8, 'M2': 4, 'M3': 8, 'M4': 4, 'M5': 3}, 'OP2': {'M1': 2, 'M2': 2, 'M3': 2, 'M4': 6, 'M5': 6},
                'OP3': {'M1': 5, 'M2': 5, 'M3': 2, 'M4': 6, 'M5': 4}, 'OP4': {'M1': 6, 'M2': 8, 'M3': 3, 'M4': 3, 'M5': 3}}}}
    """
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
    good_seq = makespan(original, ini_set, machines)
    return good_seq

if __name__ == "__main__":
    print(start())