def calculate(origin, operations):
    machines, jobs = {}, {}
    for operation in operations:
        machines[operation[0]] = 0
        jobs[operation[1]] = 0
    for operation in operations:
        start_of_operation = max(machines[operation[0]], jobs[operation[1]])
        machines[operation[0]] = start_of_operation + getattr(origin, "%s%s%s"%(operation[0], operation[1], operation[2]))
        jobs[operation[1]] = start_of_operation + getattr(origin, "%s%s%s"%(operation[0], operation[1], operation[2]))
    return max(machines.values())

def versus(origin, cases):
    makespans = [calculate(origin, case) for case in cases]
    return cases[makespans.index(min(makespans))]