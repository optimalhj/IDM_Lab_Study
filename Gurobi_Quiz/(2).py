import gurobipy as gp
from gurobipy import GRB

model = gp.Model("example2")

variable = {var : model.addVar(vtype = GRB.CONTINUOUS, name = var) for var in ["x", "y"]}

model.addConstr(variable["x"] - variable["y"] <= 4, name = "constr1")
model.addConstr(variable["x"] + variable["y"] <= 4, name = "constr2")
model.addConstr(-0.25 * variable["x"] + variable["y"] <= 1 , name = "constr3")

model.setObjective(variable["y"], GRB.MAXIMIZE)

model.optimize()

print("-" * 50)
for var in variable:
    print(var,"=",variable[var].X)
print("Result =", model.getAttr("ObjVal"))