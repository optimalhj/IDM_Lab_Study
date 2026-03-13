import gurobipy as gp
from gurobipy import GRB

model = gp.Model("example1")

variable = {var : model.addVar(vtype = GRB.BINARY, name = var) for var in ["x", "y", "z"]}

model.addConstr(variable["x"] + 2 * variable["y"] + 3 * variable["z"] <= 4, name = "constr1")
model.addConstr(variable["x"] + variable["y"] >= 1, name = "constr2")

model.setObjective(variable["x"] + variable["y"] + 2 * variable["z"], GRB.MAXIMIZE)

model.optimize()

print("-" * 50)
for var in variable:
    print(var,"=",variable[var].X)
print("Result =", model.getAttr("ObjVal"))