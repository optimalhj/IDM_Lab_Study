import time
import numpy as np
import matplotlib.pyplot as plt
import Tardiness_Code_Other, Tardiness_Gurobi, Tardiness_ORtools, Tardiness_CPsat

# ---------------------------------- Initialization / Parameter ----------------------------------------

# Custom Job Set needed(same length of lists)
Job_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'J10', 'J11', 'J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'J18', 'J19', 'J20',
             'J21', 'J22', 'J23', 'J24', 'J25', 'J26', 'J27', 'J28', 'J29', 'J30', 'J31', 'J32', 'J33', 'J34', 'J35', 'J36', 'J37', 'J38', 'J39', 'J40',
             'J41', 'J42', 'J43', 'J44', 'J45', 'J46', 'J47', 'J48', 'J49', 'J50', 'J51', 'J52', 'J53', 'J54', 'J55', 'J56', 'J57', 'J58', 'J59', 'J60',
             'J61', 'J62', 'J63', 'J64', 'J65', 'J66', 'J67', 'J68', 'J69', 'J70', 'J71', 'J72', 'J73', 'J74', 'J75', 'J76', 'J77', 'J78', 'J79', 'J80',
             'J81', 'J82', 'J83', 'J84', 'J85', 'J86', 'J87', 'J88', 'J89', 'J90', 'J91', 'J92', 'J93', 'J94', 'J95', 'J96', 'J97', 'J98', 'J99', 'J100']
Process_times = [3, 4, 6, 9, 2, 3, 6, 2, 7, 7, 5, 6, 4, 8, 9, 6, 5, 7, 3, 5,
                 9, 9, 1, 8, 2, 2, 7, 8, 9, 2, 4, 3, 8, 8, 1, 4, 9, 3, 9, 9,
                 7, 9, 3, 4, 8, 7, 2, 5, 9, 2, 1, 8, 1, 8, 8, 6, 8, 2, 5, 2,
                 5, 5, 2, 3, 6, 8, 2, 9, 4, 1, 6, 1, 2, 9, 1, 1, 7, 4, 5, 9,
                 3, 5, 6, 9, 8, 1, 8, 2, 5, 3, 2, 9, 3, 3, 3, 8, 3, 1, 2, 2]
Due_dates = [304, 143, 343, 218, 373, 260, 362, 387, 344, 204, 60, 225, 178, 324, 381, 348, 201, 337, 71, 381,
             251, 186, 317, 202, 265, 324, 369, 10, 190, 84, 365, 46, 194, 155, 280, 14, 238, 276, 320, 9,
             53, 376, 207, 194, 242, 217, 183, 200, 283, 230, 253, 206, 66, 197, 82, 19, 260, 283, 230, 39,
             216, 320, 127, 63, 328, 66, 55, 304, 177, 261, 308, 61, 105, 110, 189, 278, 355, 61, 260, 308,
             399, 336, 347, 241, 26, 292, 392, 58, 52, 2, 333, 343, 239, 179, 22, 154, 176, 161, 126, 304]

Time = 1800
by = 60

plt_type = 0 # [0 : dot graph(scatter) , 1 : line graph(plot) , else -> default 1 convert]
if plt_type != 1 or plt_type != 0:
    plt_type = 1

params = {'MUT': 0.5, 'POP_SIZE' : 10, 'NUM_OFFSPRING' : 5}

# ------------------------------------------------------------------------------------------------------

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

# Calculating each job's tardiness and total tardiness
def tardiness(seqs):
    if td_type == "Code":
        now, total_tardiness = 0, 0
        for job in seqs:
            now += job.processing_time
            total_tardiness += max(now - job.due, 0)
        return seqs, total_tardiness
    elif td_type == "Code_Other":
        return Tardiness_Code_Other.tardiness(seqs)
    elif td_type == "Gurobi":
        return Tardiness_Gurobi.tardiness(seqs)
    elif td_type == "ORLP":
        return Tardiness_ORtools.tardiness(seqs)
    else:
        return Tardiness_CPsat.tardiness(seqs)

# ------------------------- For every meta Heuristic ----------------------------------

def data_collection(seq, lap, tard):
    if not "%s"%(lap//by) in list(seq.keys()):
        seq["%s"%(lap//by)]=tard
    return seq

def localsearch(ini_seq, search, nei):
    nei = 1
    candidates = []
    for _ in range(search):
        ini_seq_tmp = ini_seq.copy()
        if nei:
            cvt = np.random.randint(len(ini_seq_tmp) - 1)
            ini_seq_tmp.insert(cvt + 1, ini_seq_tmp.pop(cvt))
        else:
            dtt_job = ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp)))
            ini_seq_tmp.insert(np.random.randint(len(ini_seq_tmp)) + 1, dtt_job)
        candidates.append(ini_seq_tmp)
    return candidates

# -------------------------------- GA ----------------------------------------

def replacement_operator(population, offsprings):
    result_population = population + offsprings
    result_population.sort(key = lambda seq : tardiness(seq)[1])
    return result_population[0:params['POP_SIZE']]

def crossover_operator(mom_cho, dad_cho):
    indexes = sorted(np.random.choice([i for i in range(len(Job_names))], 2, replace = False))
    middle = mom_cho[indexes[0]:indexes[1]]
    left = [jb for jb in dad_cho if jb not in middle]
    return left[0:indexes[0]] + middle + left[indexes[0]:]

def selection_operator(population):
    mom_ch = population[0]
    dad_ch = population[np.random.randint(1, len(population))]
    return mom_ch, dad_ch

def mutation_operator(chromosome, search = 1, rate = params['MUT']):
    if np.random.random() <= rate:
        return localsearch(chromosome, search, np.random.randint(2))
    else:
        return [chromosome]

def start_ga(ini_seq):
    sequence, total_tardiness = ini_seq
    population = [sequence]
    operation = mutation_operator(sequence, search = params['POP_SIZE'] - 1, rate = 1)
    population.extend(operation)
    population.sort(key = lambda seq : tardiness(seq)[1])

    ga_result = {}

    count = 0
    ini_time = time.time()
    lapse = time.time() - ini_time
    while lapse//by <= Time//by :
        count += 1
        offsprings = []
        for i in range(params["NUM_OFFSPRING"]):
            mom_ch, dad_ch = selection_operator(population)
            offspring = mutation_operator(chromosome = crossover_operator(mom_ch, dad_ch))
            offsprings.extend(offspring)
        population_tmp = population.copy()
        population = replacement_operator(population,offsprings)

        final_tardiness = tardiness(population[0])
        if final_tardiness[1] < tardiness(population_tmp[0])[1] or population != population_tmp:
            sequence, total_tardiness = final_tardiness

        ga_result = data_collection(ga_result, lapse, total_tardiness)
        lapse = time.time() - ini_time

    return sequence, ga_result, count

def meta_heuristic(*args):
    spt = sorted(args[0], key=lambda name: name.processing_time)
    if args[1] == 2:
        return start_ga(tardiness(spt))
    else:
        return "Will ADD"

def GA(names):
    return meta_heuristic(names, 2), "GA"

# -------------------------- Drawing Graph ---------------------------------

def graph(result):
    if result[1] in ("SPT", "EDD", "SLACK"):
        x = [period for period in range(int(Time / by) + 1)]
        y = [result[0][1] for _ in range(int(Time / by) + 1)]
        td = result[0][1]
    else:
        x = [period for period in result[0][1]]
        y = [result[0][1][period] for period in result[0][1]]
        td = y[-1]

    if plt_type:
        plt.plot(x, y, label="%s-%s" %(result[1], td_type))
    else:
        plt.scatter(x, y,label="%s-%s" %(result[1], td_type))
    return td

def final_graph():
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

# ---------------------------------------------------------------------------

if __name__ == "__main__":

    ini_set = build(Job_names, Process_times, Due_dates)

    methods = [GA]
    td_types = ["Gurobi","Code", "Code_Other", "ORLP", "ORCP"]
    for func in methods:
        for td_type in td_types:
            results = func(ini_set)
            Tardiness = graph(results)
            print("Type :", results[1], "-", td_type, "  /   Tardiness =", Tardiness, "  /   Count =", results[0][2])
            print("Sequence :", end = "")
            for job in results[0][0]:
                print(job.name, end = " ")
            print()

    final_graph()