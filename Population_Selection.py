import Initial_Population
import Makespan_Calculation
from Initial_coding_set import setting
from numpy import random

def binary_tournament(origin, ini_pop):
    indices = [i for i in range(len(ini_pop))]
    candidates = []
    while len(indices) > 0:
        if len(indices) < 2:
            candidates.append(indices)
            break
        else:
            candidates.append([indices.pop(random.randint(len(indices))) for _ in range(2)])
    new_candidates = [Makespan_Calculation.versus(origin, [ini_pop[idx] for idx in candidate]) for candidate in candidates]

    if len(new_candidates) > 2:
        return binary_tournament(origin, new_candidates)
    else:
        return new_candidates

def n_size_tournament(origin, ini_pop):
    indices = [i for i in range(len(ini_pop))]
    candidates = []
    while len(indices) > 0:
        if len(indices) >= 3:
            n_size = random.randint(2, len(indices))
        else:
            n_size = len(indices)

        if len(indices) < n_size:
            candidates.append(indices)
            break
        else:
            candidates.append([indices.pop(random.randint(len(indices))) for _ in range(n_size)])
    new_candidates = [Makespan_Calculation.versus(origin, [ini_pop[idx] for idx in candidate]) for candidate in
                      candidates]

    if len(new_candidates) == 2:
        return new_candidates
    else:
        return n_size_tournament(origin, new_candidates)

def linear_ranking(origin, ini_pop):
    tmp = sorted(ini_pop, key = lambda case : Makespan_Calculation.calculate(origin, case))
    idx1, idx2 = random.choice([i for i in range(0, len(ini_pop))], size = 2, replace = False, p = [2 * i / (len(ini_pop) * (len(ini_pop) + 1)) for i in range(1, len(ini_pop) + 1)])
    return tmp[idx1], tmp[idx2]

def start(origin, ini_pop):

    way = random.randint(3)
    if way == 0: # Binary tournament
        return binary_tournament(origin, ini_pop)
    elif way == 1: # n-Size tournament
        return n_size_tournament(origin, ini_pop)
    elif way == 2:  # Linear ranking
        return linear_ranking(origin, ini_pop)
    else:  # Do not reach
        return 0

if __name__ == "__main__":
    Ini_Job_Set, params = setting()
    Original, Initial_Pop = Initial_Population.start(Ini_Job_Set, population_size=params["pop_size"],
                                        ini_assign=params["ini_assign"], ini_seq=params["ini_seq"])
    mother, father = start(Original, Initial_Pop)
    print(Makespan_Calculation.calculate(Original, mother), mother)
    print(Makespan_Calculation.calculate(Original, father), father)