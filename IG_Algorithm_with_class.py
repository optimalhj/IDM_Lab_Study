# For Random Processing_Time/Due_Date and Destruction
import numpy as np

# Jobs to Class process / Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self):
        self.processing_time = np.random.randint(1,10)
        self.due = np.random.randint(1,4*Number_of_Jobs)
        print("Processing Time :",self.processing_time, "/ Due Date :",self.due)

def build():
    jobs = ["Job%s"%(i+1) for i in range(Number_of_Jobs)]
    for job in jobs:
        print(job,end=" --> ")
        globals()[job] = Jobs()
    return jobs

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
    each_tardiness,total_tardiness = spt

    for k in range(Generation):
        final_tardiness = mutant(list(each_tardiness))
        if final_tardiness[1] < total_tardiness:
            each_tardiness,total_tardiness = final_tardiness
        print("\n\n<<Evolving Result>>\nGeneration : %s" % (k + 1))
        print("Evolved Sequence =", each_tardiness)
        print("Evolved Tardiness = %s\n\n%s" % (total_tardiness, '-' * 100))

    return each_tardiness, total_tardiness

# Initial Sequence : SPT
# Every Job Sequence is saved in List
# Jobs' attributes(processing time and due date) are saved as feature of the variable
def start(ini_jobs):
    spt = sorted(ini_jobs, key = lambda job : globals()[job].processing_time)
    spt_tardiness = tardiness(spt)
    print("\nInitial  Sequence =", spt_tardiness[0])
    print("Initial Tardiness =", spt_tardiness[1], "\n\n%s" % ("-" * 100))

    return evolve(spt_tardiness)

# Number of Jobs / Converting Jobs to Class
Number_of_Jobs = 12

# Amount of Evolving Process
Generation = 15

# IG(?) Process
result = start(build())
print("<<<Final Result>>>")
print("Final Sequence =", list(result[0]))
print("Final Each Tardiness =", result[0])
print("Final Totals Tardiness =", result[1])