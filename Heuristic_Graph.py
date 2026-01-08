import time,math
import numpy as np
from multiprocessing import Pool
import matplotlib.pyplot as plt

# Jobs to Class process / "Name" as Attribute and Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self,name,processing_time,due):
        self.name = name
        self.processing_time = processing_time
        self.due = due
        print(self.name,"-->", "Processing Time :",self.processing_time, "/ Due Date :",self.due)

def build(names,times,dues):
    new_jobs = [Jobs(names[i],times[i],dues[i]) for i in range(len(names))]
    return new_jobs

# Calculating each job's tardiness and total tardiness
def tardiness(seqs):
    now,each_td = 0,{}
    for job in seqs:
        now += job.processing_time
        each_td[job] = max(now - job.due, 0)
    return list(each_td), sum(each_td.values())

#-----------------------------SPT-----------------------------------------

def SPT(names):
    ini_time = time.time()
    spt = sorted(names, key = lambda name : name.processing_time)
    SPT_result,duration = tardiness(spt)[1],time.time() - ini_time
    return duration, SPT_result

#-----------------------------EDD-----------------------------------------

def EDD(names):
    ini_time = time.time()
    edd = sorted(names, key = lambda name : name.due)
    EDD_result,duration = tardiness(edd)[1],time.time() - ini_time
    return duration, EDD_result

#----------------------------SLACK----------------------------------------

def SLACK(names):
    names_tmp = names.copy()
    now = 0
    slack = []
    ini_time = time.time()
    for _ in range(len(names_tmp)):
        each_slack = {}
        for job in names_tmp:
            each_slack[job] = job.due - now
        chosen_job = min(each_slack, key = each_slack.get)
        names_tmp.remove(chosen_job)
        slack.append(chosen_job)
    SLACK_result, duration = tardiness(slack)[1], time.time() - ini_time
    return duration, SLACK_result

#-------------------------IGA + SA_ANS------------------------------------

def best(cands):
    all_case = [tardiness(case) for case in cands]
    best_case = cands[[case[1] for case in all_case].index(min([case[1] for case in all_case]))]
    return best_case

def candidate(ini_seq):
    ini_seq_tmp = ini_seq.copy()
    dtt_jobs = [ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp))) for _ in range(np.random.randint(1, len(ini_seq_tmp)))]
    for con_jobs in dtt_jobs:
        every_case = []
        for j in range(len(ini_seq_tmp) + 1):
            ini_seq_tmp.insert(j, con_jobs)
            every_case.append(tuple(ini_seq_tmp))
            ini_seq_tmp.pop(j)
        ini_seq_tmp = list(best(every_case))
    return tardiness(ini_seq_tmp)

def evolve(ini_seq):
    each_tardiness,total_tardiness = ini_seq
    ini_time = time.time()
    for k in range(50):
        final_tardiness = candidate(list(each_tardiness))
        if final_tardiness[1] < total_tardiness:
            each_tardiness,total_tardiness = final_tardiness
    IGA_result, duration = total_tardiness, time.time() - ini_time
    return duration, IGA_result

def localsearch(ini_seq,search,nei):
    candidates = []
    for _ in range(search):
        ini_seq_tmp = ini_seq.copy()
        if nei:
            cvt = np.random.randint(len(ini_seq_tmp)-1)
            job = ini_seq_tmp.pop(cvt)
            ini_seq_tmp.insert(cvt+1,job)
            candidates.append(ini_seq_tmp)
        else:
            dtt_job = ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp)))
            ini_seq_tmp.insert(np.random.randint(len(ini_seq_tmp)) + 1, dtt_job)
            candidates.append(ini_seq_tmp)
        ini_seq_tmp = list(best(candidates))
    return tardiness(ini_seq_tmp)

def iteration(ini_seq,nei):
    # SA Parameters / Able to modify values
    Temperature_Initial = 50
    Temperature_Min = 25
    Temperature_K = 0.99
    Iteration_Max = 20
    SameCount_Max = 45698464
    Search_Max = 5

    ini_time = time.time()

    each_sequence, total_tardiness = ini_seq
    temperature = Temperature_Initial
    SameCount = 0
    Search = 1

    while temperature >= Temperature_Min and SameCount <= SameCount_Max:
        iteration_compare = 0
        for _ in range(Iteration_Max):
            final_tardiness = localsearch(list(each_sequence),Search,nei)

            if final_tardiness[1] < total_tardiness:
                each_sequence, total_tardiness = final_tardiness
            else:
                if np.random.random() < math.e ** ((total_tardiness - final_tardiness[1]) / temperature):
                    each_sequence, total_tardiness = final_tardiness
                else:
                    iteration_compare += 1
                SameCount += 1
        temperature *= Temperature_K
        if iteration_compare >= Iteration_Max/2 and Search < Search_Max:
            Search += 1

    SA_ANS_result, duration = total_tardiness, time.time() - ini_time
    return duration, SA_ANS_result

def meta_heuristic(*args):
    spt = sorted(args[0], key = lambda name : name.processing_time)
    if args[1]: return evolve(tardiness(spt))
    else: return iteration(tardiness(spt),args[2])

def IGA(names):
    return meta_heuristic(names,1)

def SA_ANS_Swap(names):
    return meta_heuristic(names,0,1)

def SA_ANS_Insert(names):
    return meta_heuristic(names,0,0)

def run_N_times(args):
    func, jobs = args
    return [func(jobs) for _ in range(Num)]

# ---------------------------------------------------------------------------

Num = 5

if __name__ == "__main__":
    Job_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'J10', 'J11', 'J12', 'J13', 'J14', 'J15', 'J16',
                 'J17', 'J18', 'J19', 'J20', 'J21', 'J22', 'J23', 'J24', 'J25', 'J26', 'J27', 'J28', 'J29', 'J30',
                 'J31', 'J32', 'J33', 'J34', 'J35', 'J36', 'J37', 'J38', 'J39', 'J40', 'J41', 'J42', 'J43', 'J44',
                 'J45', 'J46', 'J47', 'J48', 'J49', 'J50', 'J51', 'J52', 'J53', 'J54', 'J55', 'J56', 'J57', 'J58',
                 'J59', 'J60', 'J61', 'J62', 'J63', 'J64', 'J65', 'J66', 'J67', 'J68', 'J69', 'J70', 'J71', 'J72',
                 'J73', 'J74', 'J75', 'J76', 'J77', 'J78', 'J79', 'J80', 'J81', 'J82', 'J83', 'J84', 'J85', 'J86',
                 'J87', 'J88', 'J89', 'J90', 'J91', 'J92', 'J93', 'J94', 'J95', 'J96', 'J97', 'J98', 'J99', 'J100']
    Process_times = [3, 4, 6, 9, 2, 3, 6, 2, 7, 7, 5, 6, 4, 8, 9, 6, 5, 7, 3, 5, 9, 9, 1, 8, 2, 2, 7, 8, 9, 2, 4, 3, 8,
                     8, 1, 4, 9, 3, 9, 9, 7, 9, 3, 4, 8, 7, 2, 5, 9, 2, 1, 8, 1, 8, 8, 6, 8, 2, 5, 2, 5, 5, 2, 3, 6, 8,
                     2, 9, 4, 1, 6, 1, 2, 9, 1, 1, 7, 4, 5, 9, 3, 5, 6, 9, 8, 1, 8, 2, 5, 3, 2, 9, 3, 3, 3, 8, 3, 1, 2,
                     2]
    Due_dates = [304, 143, 343, 218, 373, 260, 362, 387, 344, 204, 60, 225, 178, 324, 381, 348, 201, 337, 71, 381, 251,
                 186, 317, 202, 265, 324, 369, 10, 190, 84, 365, 46, 194, 155, 280, 14, 238, 276, 320, 9, 53, 376, 207,
                 194, 242, 217, 183, 200, 283, 230, 253, 206, 66, 197, 82, 19, 260, 283, 230, 39, 216, 320, 127, 63,
                 328, 66, 55, 304, 177, 261, 308, 61, 105, 110, 189, 278, 355, 61, 260, 308, 399, 336, 347, 241, 26,
                 292, 392, 58, 52, 2, 333, 343, 239, 179, 22, 154, 176, 161, 126, 304]
    
    ini_set = build(Job_names, Process_times, Due_dates) # 공통 패러미터

    funcs = [SPT, EDD, SLACK, IGA, SA_ANS_Swap, SA_ANS_Insert]
    tasks = [(func, ini_set) for func in funcs]

    with Pool(processes=len(funcs)) as pool:
        results = pool.map(run_N_times, tasks)

    SPT_lists, EDD_lists, SLACK_lists, IGA_lists, SA_ANS_Swap_lists, SA_ANS_Insert_lists = results

    print("SPT :", SPT_lists)
    print("EDD :", EDD_lists)
    print("SLACK :", SLACK_lists)
    print("IGA :", IGA_lists)
    print("SA_ANS_Swap :", SA_ANS_Swap_lists)
    print("SA_ANS_Insert :", SA_ANS_Insert_lists)

    x_spt = [jobs[0] for jobs in SPT_lists]
    y_spt = [jobs[1] for jobs in SPT_lists]

    x_edd = [jobs[0] for jobs in EDD_lists]
    y_edd = [jobs[1] for jobs in EDD_lists]

    x_slack = [jobs[0] for jobs in SLACK_lists]
    y_slack = [jobs[1] for jobs in SLACK_lists]

    x_iga = [jobs[0] for jobs in IGA_lists]
    y_iga = [jobs[1] for jobs in IGA_lists]

    x_sa_ans_swap = [jobs[0] for jobs in SA_ANS_Swap_lists]
    y_sa_ans_swap = [jobs[1] for jobs in SA_ANS_Swap_lists]

    x_sa_ans_insert = [jobs[0] for jobs in SA_ANS_Insert_lists]
    y_sa_ans_insert = [jobs[1] for jobs in SA_ANS_Insert_lists]

    plt.scatter(x_spt, y_spt, color='red', label='SPT')
    plt.scatter(x_edd, y_edd, color='blue', label='EDD')
    plt.scatter(x_slack, y_slack, color='purple', label='SLACK')
    plt.scatter(x_iga, y_iga, color='green', label='IGA')
    plt.scatter(x_sa_ans_swap, y_sa_ans_swap, color='yellow', label='SA_ANS_Swap')
    plt.scatter(x_sa_ans_insert, y_sa_ans_insert, color='Brown', label='SA_ANS_Insert')

    plt.title("Tardiness and Time")
    plt.legend(['SPT','EDD','SLACK','IGA','SA_ANS_Swap','SA_ANS_Insert'], ncol = 2, fontsize = 8, title = "Heuristics")
    plt.xlabel("Time")
    plt.ylabel("Tardiness")

    plt.xlim([0,max(x_iga+x_sa_ans_swap+x_sa_ans_insert)])
    plt.ylim([min(y_iga+y_sa_ans_swap+y_sa_ans_insert+y_slack),max(y_spt+y_edd+y_slack)])
    plt.show()