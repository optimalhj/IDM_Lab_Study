import gurobipy as gp
from gurobipy import GRB
import pandas as pd

dt = pd.read_csv("quiz5_set.csv")

md = gp.Model()

machine_A_times, machine_B_times = [], []
for i in range(len(dt)):
    machine_A_times.append(md.addVar(vtype = GRB.BINARY, name = f"machine_A_{i+1}"))
    machine_B_times.append(md.addVar(vtype = GRB.BINARY, name = f"machine_B_{i+1}"))
    md.addConstr(machine_A_times[i] + machine_B_times[i] == 1)

md.setObjective(gp.quicksum(machine_A_times[i] * dt.loc[i,"Machine A"] + machine_B_times[i] * dt.loc[i,"Machine B"] for i in range(len(dt))), GRB.MINIMIZE)
md.optimize()

print(md.ObjVal)
for A in machine_A_times:
    print(A.X, end=" ")
print()
for B in machine_B_times:
    print(B.X, end=" ")
print()
