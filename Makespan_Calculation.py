from Initial_coding_set import setting
import Initial_Population


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

if __name__ == "__main__":

    Ini_Job_Set, params = setting()
    Original, Initial_Pop = Initial_Population.start(Ini_Job_Set, population_size=params["pop_size"],
                                        ini_assign=params["ini_assign"], ini_seq=params["ini_seq"])

    result = versus(Original, Initial_Pop)
    print(result)