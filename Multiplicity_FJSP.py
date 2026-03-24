from numpy import random
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

def makespan(origin, ini_set):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    binary_space, start_end_per_machine, start_end_per_each_job, seq_machine, colors_info = {}, {}, {}, {}, []

    for job_type in ini_set:
        binary_space[job_type] = {}
        start_end_per_each_job[job_type] = {}

        for job in ini_set[job_type]:
            binary_space[job_type][job] = {}
            start_end_per_each_job[job_type][job] = {}
            if (job_type, job) not in colors_info:
                colors_info.append((job_type, job))

            for op in ini_set[job_type][job]:
                binary_space[job_type][job][op] = {}
                start_end_per_each_job[job_type][job][op] = {}

                for machine in ini_set[job_type][job][op]:
                    binary_space[job_type][job][op][machine] = md.addVar(vtype=GRB.BINARY)
                    start_end_per_each_job[job_type][job][op][machine] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstr(start_end_per_each_job[job_type][job][op][machine][0] >= 0)
                    md.addConstr(start_end_per_each_job[job_type][job][op][machine][1] == start_end_per_each_job[job_type][job][op][machine][0] + getattr(origin, f"{job_type}{job}{op}{machine}") * binary_space[job_type][job][op][machine])
                    start_end_per_machine[machine] = {}

                md.addConstr(sum(binary_space[job_type][job][op].values()) == 1)

    for job_type in start_end_per_each_job:
        for job in start_end_per_each_job[job_type]:
            for op in start_end_per_each_job[job_type][job]:

                for machine in start_end_per_each_job[job_type][job][op]:
                    start_end_per_machine[machine][(job_type, job, op)] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstrs(start_end_per_each_job[job_type][job][op][machine][i] == start_end_per_machine[machine][(job_type, job, op)][i] for i in range(2))

                    if op != list(start_end_per_each_job[job_type][job])[0]:
                        tmp_var = md.addVar(vtype=GRB.CONTINUOUS)
                        md.addGenConstrMax(tmp_var, [start_end_per_each_job[job_type][job][list(start_end_per_each_job[job_type][job])[list(start_end_per_each_job[job_type][job]).index(op) - 1]][start_and_end][1] for start_and_end in start_end_per_each_job[job_type][job][op]])
                        md.addConstr(start_end_per_each_job[job_type][job][op][machine][0] >= tmp_var)

    for machine in start_end_per_machine:
        n = len(start_end_per_machine[machine])
        for i in range(n):
            seq_machine[list(start_end_per_machine[machine])[i]] = {}
            for j in range(i + 1, n):
                seq_machine[list(start_end_per_machine[machine])[i]][list(start_end_per_machine[machine])[j]] = md.addVar(vtype=GRB.BINARY)
                md.addGenConstrIndicator(seq_machine[list(start_end_per_machine[machine])[i]][list(start_end_per_machine[machine])[j]], True, start_end_per_machine[machine][list(start_end_per_machine[machine])[i]][1] <= start_end_per_machine[machine][list(start_end_per_machine[machine])[j]][0])
                md.addGenConstrIndicator(seq_machine[list(start_end_per_machine[machine])[i]][list(start_end_per_machine[machine])[j]], False, start_end_per_machine[machine][list(start_end_per_machine[machine])[j]][1] <= start_end_per_machine[machine][list(start_end_per_machine[machine])[i]][0])

    z = md.addVar(vtype=GRB.CONTINUOUS)
    md.addGenConstrMax(z, [start_end_per_machine[machine][operation][1] for machine in start_end_per_machine for operation in start_end_per_machine[machine]])
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
    for job_type in start_end_per_each_job:
        print(job_type)
        for job in start_end_per_each_job[job_type]:
            print("\t", job)
            for op in start_end_per_each_job[job_type][job]:
                print("\t\t", op, ":", end=" ")
                for machine in start_end_per_each_job[job_type][job][op]:
                    print(machine, ":", "(Start :", int(start_end_per_each_job[job_type][job][op][machine][0].X), "End :", int(start_end_per_each_job[job_type][job][op][machine][1].X), end=") / ")
                print()
    print("-----------------------------------------------------------------------------------------------------")
    '''
    fig, ax = plt.subplots()
    for machine in start_end_per_machine:
        for operation in start_end_per_machine[machine]:
            job_type, job, op = operation
            if binary_space[job_type][job][op][machine].X != 0:
                start_info, end_info = [time_info.X for time_info in start_end_per_each_job[job_type][job][op][machine]]
                ax.barh(machine, end_info - start_info, left=start_info, color=plt.get_cmap('tab20', len(colors_info))(colors_info.index((job_type, job))), edgecolor='black')
                ax.text((start_info + end_info) / 2, machine,f"{job_type}\n{job}\n{op}\n({getattr(origin, f"{job_type}{job}{op}{machine}")})", va='center', ha='center', color='black', fontsize=7)
    ax.set_yticks(range(len(start_end_per_machine)))
    ax.set_yticklabels(list(start_end_per_machine))
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.show()
    return md.ObjVal

class Build:
    def __init__(self):
        pass
def start():

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
    original = Build()

    for job_type in built_parameter.keys():
        print(job_type)
        for job in built_parameter[job_type]:
            print("\t", end="")
            print(job)
            print("\t", end="")
            print(built_parameter[job_type][job])
        print()
    print("-----------------------------------------------------------------------------------------------------")
    for job_type in built_parameter:
        for job in built_parameter[job_type]:
            for op in built_parameter[job_type][job]:
                for machine in built_parameter[job_type][job][op]:
                    setattr(original, f"{job_type}{job}{op}{machine}", built_parameter[job_type][job][op][machine])

    good_seq = makespan(original, built_parameter)
    return good_seq

if __name__ == "__main__":
    print(start())