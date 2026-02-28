from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model
import gurobipy as gp
from gurobipy import GRB
from numpy import random
from matplotlib import pyplot as plt
from time import time

Num_Jobs = 5

plt_type = 1

class Jobs:
    def __init__(self, name, processing_time, due):
        self.name = name
        self.processing_time = processing_time
        self.due = due
        print(self.name, "-->", "Processing Time :", self.processing_time, "/ Due Date :", self.due)

def build(names, times, dues):
    return [Jobs(names[i], times[i], dues[i]) for i in range(len(names))]

def graph(types):
    x = [i for i in range(1, Num_Jobs + 1)]
    for way in types:
        y = types[way]
        if plt_type:
            plt.plot(x, y, label = way)
        else:
            plt.scatter(x, y, label = way)

    plt.xticks(rotation=45, fontsize=5)
    plt.title("Duration and Number of Jobs (The lower is better)")
    plt.legend(fontsize=8, title="Solvers")

    plt.xlabel("Number of Jobs")
    plt.ylabel("Duration")

    plt.show()

def or_lp(ini):
    n = len(ini)

    ini_time = time()

    md = pywraplp.Solver.CreateSolver('SCIP')

    starts, td = {}, {}
    for job in ini:
        starts[job] = md.IntVar(0, horizon, name = "Start_%s"%job.name)
        td[job] = md.IntVar(0, horizon, name="Td_%s" % job.name)
        md.Add(td[job] >= starts[job] + job.processing_time - job.due)

    seq = {}
    for i in range(n):
        seq[ini[i]] = {}
        for j in range(i+1, n):
            seq[ini[i]][ini[j]] = md.IntVar(0, 1, name = "Sequence_%s_%s"%(ini[i].name, ini[j].name))
            md.Add(starts[ini[i]] + ini[i].processing_time - starts[ini[j]] <= horizon * (1 - seq[ini[i]][ini[j]]))
            md.Add(starts[ini[j]] + ini[j].processing_time - starts[ini[i]] <= horizon * seq[ini[i]][ini[j]])

    md.Minimize(sum(td.values()))
    solver = md.Solve()

    duration = time() - ini_time
    if solver in [md.OPTIMAL, md.FEASIBLE]:
        print("ORtools LP Passed :", md.Objective().Value(), "Duration :", duration, "sec")
        return duration
    else:
        print("ORtools LP Failed")
        return 0

def gp_lp(ini):
    n = len(ini)
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()

    ini_time = time()

    md = gp.Model(env = env)

    starts, td = {}, {}
    for job in ini:
        starts[job] = md.addVar(0, horizon, vtype=GRB.INTEGER)
        td[job] = md.addVar(0, horizon, vtype=GRB.INTEGER)
        md.addConstr(td[job] >= starts[job] + job.processing_time - job.due)

    seq = {}
    for i in range(n):
        seq[ini[i]] = {}
        for j in range(i+1, n):
            seq[ini[i]][ini[j]] = md.addVar(vtype = GRB.BINARY)
            md.addConstr(starts[ini[i]] + ini[i].processing_time - starts[ini[j]] <= horizon * (1 - seq[ini[i]][ini[j]]))
            md.addConstr(starts[ini[j]] + ini[j].processing_time - starts[ini[i]] <= horizon * seq[ini[i]][ini[j]])

    md.setObjective(sum(td.values()), GRB.MINIMIZE)
    md.optimize()

    duration = time() - ini_time
    if md.status in [GRB.OPTIMAL, GRB.SUBOPTIMAL]:
        print("Gurobi Passed :", md.ObjVal, "Duration :", duration, "sec")
        return duration
    else:
        print("Gurobi Failed")
        return 0


def or_cp(ini):

    ini_time = time()

    md = cp_model.CpModel()

    starts, intervals, td = {}, {}, {}
    for job in ini:
        starts[job] = md.NewIntVar(0, horizon, "start_%s"%job.name)
        intervals[job] = md.NewIntervalVar(starts[job],job.processing_time,md.NewIntVar(0, horizon, "end_%s" % job.name), "Interval_%s"%job.name)
        td[job] = md.NewIntVar(0, horizon, "td_%s" % job.name)
        md.Add(td[job] >= starts[job] + job.processing_time - job.due)
    md.AddNoOverlap(intervals.values())

    md.Minimize(sum(td.values()))

    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    duration = time() - ini_time
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("ORtools CP Passed :", solver.ObjectiveValue(), "Duration :", duration, "sec")
        return duration
    else:
        print("ORtools CP Failed")
        return 0

def start():
    global horizon

    func = [
        # (or_lp, "OR LP"),
        (gp_lp,"GP LP"),
        (or_cp,"OR CP")]
    ways = {way[1] : [] for way in func}

    for num_jobs in range(1, Num_Jobs + 1):
        print()

        Job_names, Process_times, Due_dates = [], [], []
        for num_job in range(num_jobs):
            Job_names.append('J%d' % (num_job + 1))
            Process_times.append(random.randint(1, 10))
            Due_dates.append(random.randint(1, 4 * (num_job + 1)))
        horizon = sum(Process_times)

        ini_set = build(Job_names, Process_times, Due_dates)
        for fnc, way in func:
            ways[way].append(fnc(ini_set))

    graph(ways)

if __name__ == "__main__":
    start()