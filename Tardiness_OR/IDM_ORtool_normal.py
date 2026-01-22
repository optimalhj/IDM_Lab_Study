from ortools.linear_solver import pywraplp

md = pywraplp.Solver.CreateSolver('SCIP') # CBC(정수, 이진, 실수), GLOP(정수 X, only 실수)

x = md.IntVar(0, 20, 'x')
y = md.IntVar(0, 25, 'y')

md.Add(2 * x + y <= 50)

constraint1 = md.Constraint(-md.Infinity(), 150)
constraint1.SetCoefficient(x, 4)
constraint1.SetCoefficient(y, 6)

md.Maximize(5 * x + 3 * y)

status = md.Solve()

if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
    print('Optimal solution:', md.Objective().Value())
    print('x:', x.solution_value())
    print('y:', y.solution_value())
