from ortools.sat.python import cp_model

def simple_sat_program():

    model = cp_model.CpModel()

    x = model.NewIntVar(0, 2, 'x')
    y = model.NewIntVar(0, 2, 'y')
    z = model.NewIntVar(0, 2, 'z')

    model.Add(x != y)

    model.Maximize(x + y + z)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # status가 Optimal이거나 Feasible 한 게 있다면
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print('x = %i' % solver.Value(x))
        print('y = %i' % solver.Value(y))
        print('z = %i' % solver.Value(z))
        print('Solution =', solver.ObjectiveValue())
    else:
        print('No solution found.')
if __name__ == '__main__':
    simple_sat_program()