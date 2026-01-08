# For random extraction
import numpy as np

# Calculating each job's tardiness and total tardiness
def tardiness(seqs):
    now,each_td = 0,{}
    for jobs in seqs:
        now += jobs[1]
        each_td[jobs[0]] = max(now - jobs[2], 0)
    return seqs, each_td, sum(each_td.values())

# Comparing each case with same jobs by comparing tardiness.
def best(every):
    # Collecting all case's tardiness
    all_case = []
    for case in range(len(every)):
        all_case.append(tardiness(every[case]))
        print("Case %s :" % (case+1), all_case[len(all_case)-1][1], "-->", all_case[len(all_case)-1][2])

    # Choosing one case with the lowest tardiness
    best_case = all_case[[case[2] for case in all_case].index(min([case[2] for case in all_case]))]
    print("\n<Best case> : Case %d / %d\n"%(all_case.index(best_case)+1, len(all_case)), list(best_case[1]), "\n<Tardiness> :", best_case[2])
    return best_case[0]

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
        print("\n\n<Constructing %s>" % con_jobs[0])
        every_case = []
        for j in range(len(ini_seq_tmp) + 1):
            ini_seq_tmp.insert(j, con_jobs)
            every_case.append(tuple(ini_seq_tmp))
            ini_seq_tmp.pop(j)
        ini_seq_tmp = list(best(every_case))

    return tardiness(ini_seq_tmp)

# Comparing each sequence's total tardiness. Lower one will survive.
def evolve(spt):
    attribute,printing_seq,total_tardiness = spt

    for k in range(Generation):
        final_attribute = mutant(attribute)
        if final_attribute[2] < total_tardiness:
            attribute,printing_seq,total_tardiness = final_attribute
        print("\n\n<<Evolving Result>>\nGeneration : %s" % (k + 1))
        print("Evolved Sequence =", printing_seq)
        print("Evolved Tardiness = %s\n\n%s" % (total_tardiness, '-' * 100))

    return printing_seq, total_tardiness

# Initial Sequence : SPT
# Every Job_Attribute is saved and Calculated with below group of attributes
# ['Job Name',Producing Time(Int),Due Date(Int)]
def start(dic):
    spt = [[job[0], job[1][0], job[1][1]] for job in sorted(dic.items(), key=lambda jobs: jobs[1][0])]
    spt_attribute = tardiness(spt)
    print("\n")
    print("Initial Sequence =", spt_attribute[1])
    print("Initial Tardiness =", spt_attribute[2], "\n\n%s" % ("-" * 100))

    return evolve(spt_attribute)

# Jobs input // "Must" Write same amount of attribute in each list
Names = ["J1","J2","J3","J4","J5","J6","J7","J8","J9","J10","J11","J12","J13","J14","J15","J16","J17","J18","J19","J20","J21","J22","J23","J24","J25","J26","J27","J28","J29","J30"]  # Job Name
Times = [9,5,7,4,11,3,8,6,2,10,5,7,6,4,8,9,3,2,12,5,4,6,7,3,9,2,5,6,8,10]  # Producing Time
Dues  = [27,22,41,16,45,19,33,28,15,38,30,24,20,18,26,43,17,14,50,21,25,29,31,23,37,13,19,34,36,40]  # Due Date
Generation = 20  # Amount of Evolving Process
Dict = dict(zip(Names,zip(Times,Dues)))

result = start(Dict)
print("<<<Final Result>>>")
print("Final Sequence =", list(result[0]))
print("Final Each Tardiness =", result[0])
print("Final Totals Tardiness =", result[1])