from Initial_coding_set import setting
import Initial_Population
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

if __name__ == "__main__":
    Ini_Set, params = setting()
    Original, Initial_Pop = Initial_Population.start(Ini_Set,
                                                     population_size=params["pop_size"],
                                                     ini_assign=params["ini_assign"],
                                                     ini_seq=params["ini_seq"])
    result = start(Original, Initial_Pop, Ini_Set, params["num_of_gens"], params["crossover"], params["pop_size"])
    for child in result:
        print(result[child])