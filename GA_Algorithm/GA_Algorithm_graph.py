import time
import numpy as np
import matplotlib.pyplot as plt

from calculation_tardiness import tardiness

Time = 2
by = 0.125

plt_type = 1 # [0 : dot graph(scatter) , 1 : line graph(plot) , else -> default 1 convert]
if plt_type != 1 or plt_type != 0:
    plt_type = 1

params = {'MUT': 0.5, 'POP_SIZE' : 10, 'NUM_OFFSPRING' : 5}

# Jobs to Class process / "Name" as Attribute and Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self, name, processing_time, due):
        self.name = name
        self.processing_time = processing_time
        self.due = due
        print(self.name, "-->", "Processing Time :", self.processing_time, "/ Due Date :", self.due)

def build(names, times, dues):
    new_jobs = [Jobs(names[i], times[i], dues[i]) for i in range(len(names))]
    return new_jobs

# -------------------------IGA + SA_ANS------------------------------------

def data_collection(sequence, lap, tard):
    if not "%s"%(lap//by) in list(sequence.keys()):
        sequence["%s"%(lap//by)]=tard
    return sequence

def replacement_operator(population, offsprings):
    result_population = population + offsprings
    result_population.sort(key = lambda seq : tardiness(seq)[1])
    return result_population[0:params['POP_SIZE']]

def crossover_operator(mom_cho, dad_cho):
    indexes = sorted(np.random.choice([i for i in range(len(Job_names))], 2, replace = False))
    middle = mom_cho[indexes[0]:indexes[1]]
    left = [jb for jb in dad_cho if jb not in middle]
    return left[0:indexes[0]] + middle + left[indexes[0]:]

def selection_operator(population, sel):
    if sel == 0:   # fitness proportionate selection(roulette wheel selection)
        tardiness_for_apply = [tardiness(pop)[1] for pop in population]
        mom_ch,dad_ch = np.random.choice(range(params["POP_SIZE"]), size = 2, replace = False, p = [td / sum(tardiness_for_apply) for td in tardiness_for_apply])
        mom_ch, dad_ch = population[mom_ch], population[dad_ch]
    elif sel == 1:   # tournament selection
        mom_ch, dad_ch = [population[min(np.random.choice(range(params["POP_SIZE"]), size = max(2, params["POP_SIZE"]//3), replace = False))] for _ in range(2)]
        if mom_ch == dad_ch:
            mom_ch, dad_ch = selection_operator(population, sel = 99)
    elif sel == 2:   # elitist preserving selection
        mom_ch,dad_ch = population[0], population[1]
    else:
        mom_ch,dad_ch = population[0], population[np.random.randint(2,params["POP_SIZE"])]
    return mom_ch, dad_ch

def localsearch(ini_seq, search, nei):
    candidates = []
    for _ in range(search):
        ini_seq_tmp = ini_seq.copy()
        if nei:
            cvt = np.random.randint(len(ini_seq_tmp) - 1)
            ini_seq_tmp.insert(cvt + 1, ini_seq_tmp.pop(cvt))
            candidates.append(ini_seq_tmp)
        else:
            dtt_job = ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp)))
            ini_seq_tmp.insert(np.random.randint(len(ini_seq_tmp)) + 1, dtt_job)
            candidates.append(ini_seq_tmp)
    return candidates

def mutation_operator(chromosome, search = 1, rate = params['MUT']):
    if np.random.random() <= rate:
        return localsearch(chromosome, search, np.random.randint(2))
    else:
        return [chromosome]

def gen(ini_seq):
    each_sequence, total_tardiness = ini_seq
    population = [each_sequence]
    operation = mutation_operator(each_sequence, search = params['POP_SIZE'] - 1, rate = 1)
    population.extend(operation)
    population.sort(key = lambda seq : tardiness(seq)[1])
    ini_time = time.time()
    ga_result = {}
    lapse = time.time() - ini_time

    while lapse//by <= Time//by :
        offsprings = []
        for i in range(params["NUM_OFFSPRING"]):
            mom_ch, dad_ch = selection_operator(population, np.random.randint(4))
            offspring = mutation_operator(chromosome = crossover_operator(mom_ch, dad_ch))
            offsprings.extend(offspring)
        population_tmp = population.copy()
        population = replacement_operator(population,offsprings)

        result_td = tardiness(population[0])
        if result_td[1] < tardiness(population_tmp[0])[1] or population != population_tmp:
            each_sequence, total_tardiness = result_td

        ga_result = data_collection(ga_result, lapse, total_tardiness)
        lapse = time.time() - ini_time

    return ga_result

def meta_heuristic(*args):
    spt = sorted(args[0], key=lambda name: name.processing_time)
    if args[1]==2:
        return gen(tardiness(spt))

def GA(names):
    return meta_heuristic(names, 2, 2), "GA"

# ------------------------------ Graph -------------------------------------

def graph(result):
    if result[1] in ("SPT", "EDD", "SLACK"):
        x = [period for period in range(int(Time / by) + 1)]
        y = [result[0] for _ in range(int(Time / by) + 1)]
    else:
        x = [period for period in result[0]]
        y = [result[0][period] for period in result[0]]

    if plt_type:
        plt.plot(x, y, label=result[1])
    else:
        plt.scatter(x, y, label=result[1])
    return y,result[1]

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Custom Job Set needed(same length of lists)
    Job_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'J10']
    Process_times = [7, 3, 12, 5, 9, 4, 6, 11, 2, 8]
    Due_dates = [22, 10, 25, 18, 30, 14, 28, 35, 8, 20]

    ini_set = build(Job_names, Process_times, Due_dates)

    methods = [GA]
    for func in methods:
        results = func(ini_set)
        final = graph(results)
        print("Type :", final[1], "  /   Tardiness =",final[0][-1])

    plt.xticks(rotation=45, fontsize=5)
    plt.title("Tardiness and Time")
    plt.legend(ncol=2, fontsize=8, title="Heuristics")
    if by == 1:
        plt.xlabel("Time(second)")
    elif by == 60:
        plt.xlabel("Time(minute)")
    elif by == 3600:
        plt.xlabel("Time(hour)")
    else:
        plt.xlabel("Time(per %s seconds)"%by)
    plt.ylabel("Tardiness")

    plt.show()