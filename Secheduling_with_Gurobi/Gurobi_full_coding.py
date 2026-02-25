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

    md=gp.Model("scheduling")
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

    '''
    seq = {job1 : {job2 : md.addVar(vtype = GRB.BINARY) for job2 in ini if job2 != job1} for job1 in ini}
    md.addConstrs(seq[job1][job2] + seq[job2][job1] == 1 for job2 in ini for job1 in ini if job1 != job2)
    '''

    '''
    seq = {}
    for job1 in ini:
        seq[job1] = {}
        for job2 in ini+["final"]:
            if job2 == job1:
                continue
            else :
                seq[job1][job2] = md.addVar(vtype = GRB.BINARY)
    md.addConstr(gp.quicksum(seq[job1]["final"] for job1 in ini) == 1)
    '''

    '''
    md.addConstrs(seq[job1][job2] + seq[job2][job1] == 1 for job2 in ini for job1 in ini if job1 != job2)
    '''

    '''
    for job1 in ini:
        for job2 in ini:
            if job2 != job1:
                md.addConstr((starts[job1] + job1.processing_time) - starts[job2] <= horizon * (1 - seq[job1][job2]))
                md.addConstr((starts[job2] + job2.processing_time) - starts[job1] <= horizon * seq[job1][job2])
    '''

    td = {}
    for job in ini:
        td[job] = md.addVar(0, horizon, vtype = GRB.INTEGER)
        md.addConstr(td[job] >= starts[job] + job.processing_time - job.due)

    md.setObjective(sum(td[job] for job in ini), GRB.MINIMIZE)

    md.setParam('OutputFlag', 0)
    md.optimize()

    for job in sorted(ini, key = lambda jb : starts[jb].X):
        print(job.name,
              " _ 시작 :", abs(starts[job].X),
              "/ 기간 :", job.processing_time,
              "/ 끝 :", starts[job].X + job.processing_time,
              "/ Td : %s - %s = %s"%(abs(starts[job].X), job.processing_time, abs(td[job].X))
              )
    print("Total : %i"%md.ObjVal)

if __name__ == "__main__":
    ini_set = build(Job_names, Process_times, Due_dates)
    start_scheduling(ini_set)



