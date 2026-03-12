from Initial_coding_set import setting
import Offspring_Evaluation_and_Generation
import Initial_Population

def start():
    ini_set, params = setting()
    original, initial_pop = Initial_Population.start(ini_set,
                                                     population_size=params["pop_size"],
                                                     ini_assign=params["ini_assign"],
                                                     ini_seq=params["ini_seq"])
    result = Offspring_Evaluation_and_Generation.start(original, initial_pop, ini_set, params["num_of_gens"], params["crossover"], params["pop_size"])
    for gen in result:
        print("Generation %s :"%gen, result[gen])
if __name__ == "__main__":
    start()