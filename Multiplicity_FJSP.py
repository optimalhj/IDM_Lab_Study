from numpy import random
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

def makespan(origin, ini_set):
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    md = gp.Model(env=env)

    binary_space, start_end_per_machine, start_end_per_each_job, seq_machine, horizon= {}, {}, {}, {}, 0

    for job_type in ini_set:
        binary_space[job_type] = {}
        start_end_per_each_job[job_type] = {}

        for job in ini_set[job_type]:
            binary_space[job_type][job] = {}
            start_end_per_each_job[job_type][job] = {}

            for op in ini_set[job_type][job]:
                binary_space[job_type][job][op] = {}
                start_end_per_each_job[job_type][job][op] = {}

                for machine in ini_set[job_type][job][op]:
                    binary_space[job_type][job][op][machine] = md.addVar(vtype=GRB.BINARY)
                    start_end_per_each_job[job_type][job][op][machine] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstr(start_end_per_each_job[job_type][job][op][machine][0] >= 0)
                    md.addConstr(start_end_per_each_job[job_type][job][op][machine][1] == start_end_per_each_job[job_type][job][op][machine][0] + getattr(origin, f"{job_type}{job}{op}{machine}") * binary_space[job_type][job][op][machine])
                    start_end_per_machine[machine] = {}
                    horizon += getattr(origin, f"{job_type}{job}{op}{machine}")

                md.addConstr(sum(binary_space[job_type][job][op].values()) == 1)

    for job_type in start_end_per_each_job:
        for job in start_end_per_each_job[job_type]:
            for op in start_end_per_each_job[job_type][job]:
                for machine in binary_space[job_type][job][op]:
                    start_end_per_machine[machine][(job_type, job, op)] = [md.addVar(vtype=GRB.CONTINUOUS) for _ in range(2)]
                    md.addConstrs(start_end_per_each_job[job_type][job][op][machine][i] == start_end_per_machine[machine][(job_type, job, op)][i] for i in range(2))
                    md.addConstr(start_end_per_machine[machine][(job_type, job, op)][0] >= 0)
                    md.addConstr(start_end_per_machine[machine][(job_type, job, op)][1] == start_end_per_machine[machine][(job_type, job, op)][0] + getattr(origin, f"{job_type}{job}{op}{machine}") * binary_space[job_type][job][op][machine])

                if op != list(start_end_per_each_job[job_type][job])[len(start_end_per_each_job[job_type][job]) - 1]:
                    tmp_var = md.addVar(vtype=GRB.CONTINUOUS)
                    md.addGenConstrMax(tmp_var, [start_end_per_each_job[job_type][job][op][start_and_end][1] for start_and_end in start_end_per_each_job[job_type][job][op]])
                    md.addConstrs(start_end_per_each_job[job_type][job][list(start_end_per_each_job[job_type][job])[list(start_end_per_each_job[job_type][job]).index(op) + 1]][machine][0] >= tmp_var for machine in start_end_per_each_job[job_type][job][op])

    for machine in start_end_per_machine:
        n = len(start_end_per_machine[machine])
        for i in range(n):
            seq_machine[list(start_end_per_machine[machine])[i]] = {}
            for j in range(i + 1, n):
                seq_machine[list(start_end_per_machine[machine])[i]][list(start_end_per_machine[machine])[j]] = md.addVar(vtype=GRB.BINARY)
                md.addConstr(start_end_per_machine[machine][list(start_end_per_machine[machine])[i]][1] - start_end_per_machine[machine][list(start_end_per_machine[machine])[j]][0] <= horizon * (1 - seq_machine[list(start_end_per_machine[machine])[i]][list(start_end_per_machine[machine])[j]]))
                md.addConstr(start_end_per_machine[machine][list(start_end_per_machine[machine])[j]][1] - start_end_per_machine[machine][list(start_end_per_machine[machine])[i]][0] <= horizon * seq_machine[list(start_end_per_machine[machine])[i]][list(start_end_per_machine[machine])[j]])

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

    operations_per_machines = {machine : [] for machine in start_end_per_machine}
    assigned_job = []
    for machine in start_end_per_machine:
        for operation in start_end_per_machine[machine]:
            job_type, job, op = operation
            if binary_space[job_type][job][op][machine].X != 0:
                operations_per_machines[machine].append(operation)
            if (job_type, job) not in assigned_job:
                assigned_job.append((job_type, job))

    colors = plt.get_cmap('tab20', len(assigned_job))
    fig, ax = plt.subplots()
    for machine in operations_per_machines:
        for operation in operations_per_machines[machine]:
            job_type, job, op = operation
            start_info, end_info = [time_info.X for time_info in start_end_per_each_job[job_type][job][op][machine]]
            ax.barh(machine, end_info-start_info, left=start_info, color=colors(assigned_job.index((job_type, job))), edgecolor='black')
            ax.text(start_info + (end_info - start_info) / 2, machine, f"{job_type}\n{job}\n{op}\n({getattr(origin, f"{job_type}{job}{op}{machine}")})", va='center', ha='center', color='black', fontsize=7)
    ax.set_yticks(range(len(operations_per_machines)))
    ax.set_yticklabels(list(operations_per_machines))
    ax.set_xlabel("Time")
    ax.set_title("Makespan_Result")
    plt.tight_layout()
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
    original = Build()

    for job_type in built_parameter:
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