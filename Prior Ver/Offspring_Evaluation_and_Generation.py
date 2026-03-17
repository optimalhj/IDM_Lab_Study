import Makespan_Calculation
import Offspring_Generation

def start(origin, ini_pop, ini_set, gens, crossover, pop_size):
    generations, best_child, horizon = {}, 0, 9999999

    for gen in range(1, gens + 1):

        children = Offspring_Generation.start(origin, ini_pop, ini_set, crossover, pop_size)

        candidate = Makespan_Calculation.versus(origin, children)
        score_candidate = Makespan_Calculation.calculate(origin, candidate)

        if score_candidate < horizon:
            best_child = candidate
            horizon = score_candidate

        generations[gen] = horizon, best_child

        ini_pop = sorted(ini_pop + children, key=lambda case : Makespan_Calculation.calculate(origin, case))[0:pop_size]

    return generations