from Initial_coding_set import setting
import Initial_Population
import Makespan_Calculation
import Offspring_Generation
import Offspring_Evaluation_and_Generation

def start(gens, origin):
    generations = []
    for _ in range(gens):
        sorted_offsprings = Offspring_Evaluation.start(origin, Offspring_Generation.start(Original, Initial_Pop, Ini_Set, params["crossover"], params["pop_size"]))
        generations.append((sorted_offsprings, Makespan_Calculation.calculate(origin, sorted_offsprings[0])))
    return generations

if __name__ == "__main__":
    Ini_Set, params = setting()
    Original, Initial_Pop = Initial_Population.start(Ini_Set,
                                                     population_size=params["pop_size"],
                                                     ini_assign=params["ini_assign"],
                                                     ini_seq=params["ini_seq"])
