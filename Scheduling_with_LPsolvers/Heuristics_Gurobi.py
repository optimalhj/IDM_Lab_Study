import gurobipy as gp
from gurobipy import GRB

Job_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'J10']
Process_times = [7, 3, 12, 5, 9, 4, 6, 11, 2, 8]
Due_dates = [22, 10, 25, 18, 30, 14, 28, 35, 8, 20]

# Jobs to Class process / "Name" as Attribute and Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self, name, processing_time, due):
        self.name = name
        self.processing_time = processing_time
        self.due = due
        print(self.name, "-->", "Processing Time :", self.processing_time, "/ Due Date :", self.due)

def build(names, times, dues):
    new_jobs = [Jobs(names[i], times[i], dues[i]) for i in range(len(names))]
    return new_jobs

def start_scheduling(ini):

    md=gp.Model()
    horizon = sum(job.due for job in ini)

    starts = md.addVars(ini, lb=0, ub=horizon, vtype=GRB.INTEGER)
    seq = {}
    n = len(ini)
    for i in range(n):
        seq[ini[i]] = {}
        for j in range(i+1, n):
            seq[ini[i]][ini[j]] = md.addVar(vtype = GRB.BINARY)
            md.addConstr(starts[ini[i]] + ini[i].processing_time - starts[ini[j]] <= horizon * (1 - seq[ini[i]][ini[j]]))
            md.addConstr(starts[ini[j]] + ini[j].processing_time - starts[ini[i]] <= horizon * seq[ini[i]][ini[j]])

    td = {}
    for job in ini:
        td[job] = md.addVar(0, horizon, vtype = GRB.INTEGER)
        md.addConstr(td[job] >= starts[job] + job.processing_time - job.due)

    md.setObjective(sum(td.values()), GRB.MINIMIZE)

    md.setParam('OutputFlag', 0)
    md.optimize()

    for job in sorted(ini, key = lambda jb : starts[jb].X):
        print(job.name,
              " _ 시작 : %i"%starts[job].X,
              "/ 기간 :", job.processing_time,
              "/ 끝 : %i"%(starts[job].X + job.processing_time),
              "/ Td : %i - %s = %i"%(starts[job].X + job.processing_time, job.due, td[job].X)
              )
    print("Total : %i"%md.ObjVal)

if __name__ == "__main__":
    ini_set = build(Job_names, Process_times, Due_dates)
    start_scheduling(ini_set)



