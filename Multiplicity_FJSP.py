from numpy import random
import gurobipy as gp
from gurobipy import GRB

def makespan(origin, ini_set):

    machines = list(list(list(list(ini_set.values())[0].values())[0].values())[0])

    md = gp.Model()

    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()

    binary_space = md.addVars([(job_type, job, op, machine) for job_type in ini_set for job in ini_set[job_type] for op in ini_set[job_type][job] for machine in ini_set[job_type][job][op]] , vtype=GRB.BINARY)

    now_per_job = {}
    for job_type in ini_set:
        for job in ini_set[job_type]:
            now_per_job[(job_type, job)] = md.addVar(vtype=GRB.CONTINUOUS)
            md.addConstr(now_per_job[(job_type, job)] >= 0)
            for op in ini_set[job_type][job]:
                md.addConstr(sum(binary_space[(job_type, job, op, machine)] for machine in machines) == 1)

    now_per_machine = md.addVars(machines, vtype=GRB.CONTINUOUS)
    md.addConstrs(now_per_machine[machine] >= 0 for machine in machines)

    
    return binary_space

class Build:
    def __init__(self):
        pass

def start():
    job_types = [f"Job_Type{i+1}" for i in range(random.randint(1,5))]
    num_job_of_type ,num_op_of_type = {}, {}
    for job_type in job_types:
        num_job_of_type[job_type] = random.randint(1,4)
        num_op_of_type[job_type] = random.randint(2,6)
    machines = [f"M{i}" for i in range(1,6)]
    max_time = 9

    built_parameter = {job_type : {f"Job{i+1}" : {f"OP{j+1}" : {machine:random.randint(1,max_time+1) for machine in machines} for j in range(num_op_of_type[job_type])} for i in range(num_job_of_type[job_type])} for job_type in job_types}
    original = Build()

    '''
    for job_type in built_parameter:
        print(job_type)
        for job in built_parameter[job_type]:
            print("\t", end="")
            print(job)
            print("\t", end="")
            print(built_parameter[job_type][job])
        print()
    '''
    for job_type in built_parameter:
        for job in built_parameter[job_type]:
            for op in built_parameter[job_type][job]:
                for machine in built_parameter[job_type][job][op]:
                    setattr(original, f"{job_type}{job}{op}{machine}", built_parameter[job_type][job][op][machine])

    good_seq = makespan(original, built_parameter)
    return good_seq

if __name__ == "__main__":
    result = start()