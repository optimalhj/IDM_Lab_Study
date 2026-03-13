import gurobipy as gp
from gurobipy import GRB
from numpy import random as rand

model = gp.Model("example3")

N = rand.randint(1,1001)
W = rand.randint(1,10001)
print("N =", N, "type")
print("W =", W, "ton")

jewels={}
for jewel in ["N%s"%(i + 1) for i in range(N)]:
    jewels[jewel] = {"W" : rand.randint(low = 1, high = W + 1),
                     "P" : rand.randint(low = 1,high = 10000),
                     "Num" : model.addVar(vtype = GRB.INTEGER, name = jewel)}
    print(jewel,":", "W =",jewels[jewel]["W"], "P =",jewels[jewel]["P"])


model.addConstr(gp.quicksum(jewels[jewel]["W"] * jewels[jewel]["Num"] for jewel in jewels) <= W, name = "Weight")
model.setObjective(sum(jewels[jewel]["P"] * jewels[jewel]["Num"] for jewel in jewels), GRB.MAXIMIZE)

model.optimize()

print("-" * 50)

for jewel in jewels:
    if jewels[jewel]["Num"].X != 0:
        price_per_jewel = jewels[jewel]["P"] * jewels[jewel]["Num"].X
        print(jewel,":",jewels[jewel]["P"],"$/ea x", jewels[jewel]["Num"].X,"ea =", price_per_jewel, "$")
print("Total price:", model.getAttr("ObjVal"))

print("-" * 50)

weight_sum =0
for jewel in jewels:
    if jewels[jewel]["Num"].X != 0:
        weight_per_jewel = jewels[jewel]["W"] * jewels[jewel]["Num"].X
        print(jewel, ":", jewels[jewel]["W"], "ton/ea x", jewels[jewel]["Num"].X, "ea =", weight_per_jewel, "ton")
        weight_sum += weight_per_jewel
print("Total weight:", weight_sum)