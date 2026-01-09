import numbers
import time, math
import numpy as np
import matplotlib.pyplot as plt
from calculation_Gurobi_ver import tardiness

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

def best(cases):
    all_case = [tardiness(case) for case in cases]
    best_case = cases[[case[1] for case in all_case].index(min([case[1] for case in all_case]))]
    return best_case

def candidate(ini_seq):
    ini_seq_tmp = ini_seq.copy()
    dtt_jobs = [ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp))) for _ in
                range(np.random.randint(1, len(ini_seq_tmp)))]
    for con_jobs in dtt_jobs:
        every_case = []
        for j in range(len(ini_seq_tmp) + 1):
            ini_seq_tmp.insert(j, con_jobs)
            every_case.append(tuple(ini_seq_tmp))
            ini_seq_tmp.pop(j)
        ini_seq_tmp = list(best(every_case))
    return tardiness(ini_seq_tmp)

def evolve(ini_seq):
    each_tardiness, total_tardiness = ini_seq
    iga_result = {}
    ini_time = time.time()
    lapse = time.time() - ini_time
    while lapse//by <= Time//by:
        final_tardiness = candidate(list(each_tardiness))
        if final_tardiness[1] < total_tardiness:
            each_tardiness, total_tardiness = final_tardiness
        iga_result = data_collection(iga_result, lapse, total_tardiness)
        lapse = time.time() - ini_time
    return iga_result

def localsearch(ini_seq, search, nei):
    candidates = []
    for _ in range(search):
        ini_seq_tmp = ini_seq.copy()
        if nei:
            cvt = np.random.randint(len(ini_seq_tmp) - 1)
            job = ini_seq_tmp.pop(cvt)
            ini_seq_tmp.insert(cvt + 1, job)
            candidates.append(ini_seq_tmp)
        else:
            dtt_job = ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp)))
            ini_seq_tmp.insert(np.random.randint(len(ini_seq_tmp)) + 1, dtt_job)
            candidates.append(ini_seq_tmp)
    ini_seq_tmp = list(best(candidates))
    return tardiness(ini_seq_tmp)

def iteration(ini_seq, nei):
    # SA Parameters / Able to modify values
    temperature_initial = 50
    temperature_k = 0.99
    iteration_max = 20
    search_max = 5

    ini_time = time.time()

    each_sequence, total_tardiness = ini_seq
    temperature = temperature_initial
    same_count = 0
    search = 1

    sa_ans_result = {}
    lapse = time.time() - ini_time
    while lapse//by <= Time//by :
        iteration_compare = 0

        for _ in range(iteration_max):
            final_tardiness = localsearch(list(each_sequence), search, nei)

            if final_tardiness[1] < total_tardiness:
                each_sequence, total_tardiness = final_tardiness
            else:
                if np.random.random() < math.e ** ((total_tardiness - final_tardiness[1]) / temperature):
                    each_sequence, total_tardiness = final_tardiness
                else:
                    iteration_compare += 1
                same_count += 1
        temperature *= temperature_k
        if iteration_compare >= iteration_max / 2 and search < search_max:
            search += 1
        sa_ans_result=data_collection(sa_ans_result,lapse,total_tardiness)
        lapse = time.time() - ini_time
    return sa_ans_result

def meta_heuristic(*args):
    spt = sorted(args[0], key=lambda name: name.processing_time)
    if args[1]:
        return evolve(tardiness(spt))
    else:
        return iteration(tardiness(spt), args[2])

def IGA(names):
    return meta_heuristic(names, 1), "IGA"

def SA_ANS_Swap(names):
    return meta_heuristic(names, 0, 1), "SA_ANS_Swap"

def SA_ANS_Insert(names):
    return meta_heuristic(names, 0, 0), "SA_ANS_Insert"

# ------------------------------ Graph -------------------------------------

def graph(result):
    if isinstance(result[0], numbers.Integral):
        x = [period for period in range(int(Time / by) + 1)]
        y = [result[0] for _ in range(int(Time / by) + 1)]
        if plt_type:
            plt.plot(x, y, label=result[1])
        else:
            plt.scatter(x, y, label=result[1])
        return y,result[1]

    elif isinstance(result[0], dict):
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


    ini_set = build(Job_names, Process_times, Due_dates)

    Time = 2
    by = 0.125

    plt_type = 1 # [0 : dot graph(scatter) , 1 : line graph(plot) , else -> default 1 convert]
    if plt_type != 1 or plt_type != 0:
        plt_type = 1

    methods = [IGA, SA_ANS_Swap]
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
