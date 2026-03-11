import Makespan_Calculation
import Initial_Population
import Population_Selection
from Initial_coding_set import setting
from numpy import random

def pox(mom_cho, dad_cho):
    indexes = sorted(random.choice([i for i in range(len(mom_cho))], 2, replace=False))
    middle = mom_cho[indexes[0]:indexes[1]]
    left = [jb for jb in dad_cho if jb not in middle]
    return left[0:indexes[0]] + middle + left[indexes[0]:]

def assignment(mom_cho,dad_cho):
    return mom_cho,dad_cho
def pps(mom_cho,dad_cho):
    return mom_cho,dad_cho
def mutation(mom_cho,dad_cho):
    return mom_cho,dad_cho
def intelligent_mutation(mom_cho,dad_cho):
    return mom_cho,dad_cho

def start(mom_cho, dad_cho, rates):
    way_operator = random.choice([i for i in range(len(rates))], size=1, p=rates)
    print(way_operator)

    if way_operator == 0:
        offspring = pox(mom_cho, dad_cho)
    elif way_operator == 1:
        offspring = assignment(mom_cho,dad_cho)
    elif way_operator == 2:
        offspring = pps(mom_cho,dad_cho)
    elif way_operator == 3:
        offspring = mutation(mom_cho,dad_cho)
    elif way_operator == 4:
        offspring = intelligent_mutation(mom_cho,dad_cho)
    else: # Do not reach
        offspring = 0
    return offspring

if __name__ == "__main__":
    Ini_Job_Set, params = setting()
    Original, Initial_Pop = Initial_Population.start(Ini_Job_Set,
                                        population_size = params["pop_size"],
                                        ini_assign = params["ini_assign"],
                                        ini_seq = params["ini_seq"])
    mother, father = Population_Selection.start(Original, Initial_Pop)
    print(Makespan_Calculation.calculate(Original, mother), mother)
    print(Makespan_Calculation.calculate(Original, father), father)

    result = start(mother, father, params["crossover"])
    print("자손 생성", result)


