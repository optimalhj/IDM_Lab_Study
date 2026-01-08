import gurobipy as gp
from gurobipy import GRB

index = ["호준",4,2,6,"정우"]

md = gp.Model("1")

x1 = md.addVars(index,vtype = GRB.CONTINUOUS, name="x1")
x2 = md.addVar(vtype = GRB.CONTINUOUS, name="x2")
md.addConstr(x2 >= 0)

md.addConstrs(3 * x1[i] + 4 * x2 <= 12 for i in index)
md.addConstrs(5 * x1[i] + 3 * x2 == 15 for i in index)


md.setObjective(x2, GRB.MAXIMIZE)
md.optimize()

if md.status == GRB.OPTIMAL:
    print(x2.X)
    print(md.objVal)

else:
    print("No solution")
