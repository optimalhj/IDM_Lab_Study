# For Random Processing_Time/Due_Date and Destruction
import numpy as np
import time

# Jobs to Class process / Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self,processing_time,due):
        self.processing_time = processing_time
        self.due = due
        print(self.processing_time, self.due,end="  /  ")

def build(j,p,d):
    for num in range(len(j)):
        print(j[num], ":",end=" ")
        globals()[j[num]] = Jobs(p[num],d[num])
    return j

# Calculating each job's tardiness and total tardiness
def tardiness(seqs):
    now,each_td = 0,{}
    for job in seqs:
        now += globals()[job].processing_time
        each_td[job] = max(now - globals()[job].due, 0)
    return each_td, sum(each_td.values())

# Comparing each case with same jobs by comparing tardiness.
def best(every):
    # Collecting all case's tardiness
    all_case = []
    for case in range(len(every)):
        all_case.append(tardiness(every[case]))
        print("Case %s :" % (case+1), all_case[-1][0], "-->", all_case[-1][1])

    # Choosing one case with the lowest tardiness
    best_case = all_case[[case[1] for case in all_case].index(min([case[1] for case in all_case]))]
    print("\n<Best case> : Case %d / %d\n"%(all_case.index(best_case)+1, len(all_case)), list(best_case[0]), "\n<Tardiness> :", best_case[1])
    return list(best_case[0])

# Destruction and Construction
def mutant(ini_seq):

    print("Original Jobs :", ini_seq)
    # Destruction : Randomly extrude job
    ini_seq_tmp = ini_seq.copy()
    dtt_jobs = [ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp))) for _ in range(np.random.randint(1, len(ini_seq_tmp)))]
    print("  Left  Jobs  :", ini_seq_tmp)
    print("Extruded Jobs :", dtt_jobs)

    # Construction : Considering every case
    for con_jobs in dtt_jobs:
        print("\n\n<Constructing %s>" % con_jobs)
        every_case = []
        for j in range(len(ini_seq_tmp) + 1):
            ini_seq_tmp.insert(j, con_jobs)
            every_case.append(tuple(ini_seq_tmp))
            ini_seq_tmp.pop(j)
        ini_seq_tmp = best(every_case)

    return tardiness(ini_seq_tmp)

# Comparing each sequence's total tardiness. Lower one will survive.
def evolve(spt):
    time_ini = time.time()

    each_tardiness,total_tardiness = spt

    for k in range(Generation):
        final_tardiness = mutant(list(each_tardiness))
        if final_tardiness[1] < total_tardiness:
            each_tardiness,total_tardiness = final_tardiness
        print("\n\n<<Evolving Result>>\nGeneration : %s" % (k + 1))
        print("Evolved Sequence =", each_tardiness)
        print("Evolved Tardiness = %s\n\n%s" % (total_tardiness, '-' * 100))

        time_fin = time.time()
        if time_fin - time_ini >= 1800:
            print("Entire time :", time_fin - time_ini)
            return each_tardiness, total_tardiness
    print("Entire time :",time.time()-time_ini)
    return each_tardiness, total_tardiness

# Initial Sequence : SPT
# Every Job Sequence is saved in List
# Jobs' attributes(processing time and due date) are saved as feature of the variable
def start(ini_seq):
    spt = sorted(ini_seq, key = lambda job : globals()[job].processing_time)
    spt_tardiness = tardiness(spt)
    print("\n Initial Sequence =", spt_tardiness[0])
    print("Initial Tardiness =", spt_tardiness[1], "\n\n%s" % ("-" * 100))

    return evolve(spt_tardiness)

# Number of Jobs / Converting Jobs to Class
Job_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'J10', 'J11', 'J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'J18', 'J19', 'J20', 'J21', 'J22', 'J23', 'J24', 'J25', 'J26', 'J27', 'J28', 'J29', 'J30', 'J31', 'J32', 'J33', 'J34', 'J35', 'J36', 'J37', 'J38', 'J39', 'J40', 'J41', 'J42', 'J43', 'J44', 'J45', 'J46', 'J47', 'J48', 'J49', 'J50', 'J51', 'J52', 'J53', 'J54', 'J55', 'J56', 'J57', 'J58', 'J59', 'J60', 'J61', 'J62', 'J63', 'J64', 'J65', 'J66', 'J67', 'J68', 'J69', 'J70', 'J71', 'J72', 'J73', 'J74', 'J75', 'J76', 'J77', 'J78', 'J79', 'J80', 'J81', 'J82', 'J83', 'J84', 'J85', 'J86', 'J87', 'J88', 'J89', 'J90', 'J91', 'J92', 'J93', 'J94', 'J95', 'J96', 'J97', 'J98', 'J99', 'J100']
Process_times = [3, 4, 6, 9, 2, 3, 6, 2, 7, 7, 5, 6, 4, 8, 9, 6, 5, 7, 3, 5, 9, 9, 1, 8, 2, 2, 7, 8, 9, 2, 4, 3, 8, 8, 1, 4, 9, 3, 9, 9, 7, 9, 3, 4, 8, 7, 2, 5, 9, 2, 1, 8, 1, 8, 8, 6, 8, 2, 5, 2, 5, 5, 2, 3, 6, 8, 2, 9, 4, 1, 6, 1, 2, 9, 1, 1, 7, 4, 5, 9, 3, 5, 6, 9, 8, 1, 8, 2, 5, 3, 2, 9, 3, 3, 3, 8, 3, 1, 2, 2]
Due_dates = [304, 143, 343, 218, 373, 260, 362, 387, 344, 204, 60, 225, 178, 324, 381, 348, 201, 337, 71, 381, 251, 186, 317, 202, 265, 324, 369, 10, 190, 84, 365, 46, 194, 155, 280, 14, 238, 276, 320, 9, 53, 376, 207, 194, 242, 217, 183, 200, 283, 230, 253, 206, 66, 197, 82, 19, 260, 283, 230, 39, 216, 320, 127, 63, 328, 66, 55, 304, 177, 261, 308, 61, 105, 110, 189, 278, 355, 61, 260, 308, 399, 336, 347, 241, 26, 292, 392, 58, 52, 2, 333, 343, 239, 179, 22, 154, 176, 161, 126, 304]

# Amount of Evolving Process
Generation = 1

# IG Algorithm Process
result = start(build(Job_names,Process_times,Due_dates))
print("<<<Final Result>>>")
print("Final Sequence =", list(result[0]))
print("Final Each Tardiness =", result[0])
print("Final Totals Tardiness =", result[1])