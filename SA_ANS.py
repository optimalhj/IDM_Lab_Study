# For Random Processing_Time/Due_Date and Destruction
import numpy as np
import math
import itertools
from ortools.linear_solver import pywraplp

# Jobs to Class process / Randomly Building "Processing Time" and "Due Date"
class Jobs:
    def __init__(self):
        self.processing_time = np.random.randint(1,10)
        self.due = np.random.randint(1,4*Number_of_Jobs)
        self.rt_det = round(np.random.random(),3)
        self.rt_rep = round(np.random.random(),3)
        print("Processing Time :",self.processing_time, "/ Due Date :",self.due,"/ devastate :",self.rt_det,"/ replace :",self.rt_rep)

# For Cost Calculation, need to set parameters of the SOSP
def TC_Initialing(JBS):
    global Reps, muE, muR, muT, L, R, PB_j, aD_j, aU_j, D_j, M

    Reps = ["r%s" % (Q + 1) for Q in range(Number_of_Replaces)]

    muE = 50
    muR = 40
    muT = 70
    L = 50
    R = 110
    PB_j = {job: globals()[job].processing_time for job in JBS}
    aD_j = {job: globals()[job].rt_det for job in JBS}
    aU_j = {job: globals()[job].rt_rep for job in JBS}
    D_j = {job: globals()[job].due for job in JBS}
    M = 999999

def build():
    jobs = ["j%s"%(i+1) for i in range(Number_of_Jobs)]
    for job in jobs:
        print(job,end=" --> ")
        globals()[job] = Jobs()
    TC_Initialing(jobs)
    return jobs

# Calculating each job's tardiness and total tardiness
def tardiness(seqs):
    now,each_td = 0,{}
    for job in seqs:
        now += globals()[job].processing_time
        each_td[job] = max(now - globals()[job].due, 0)
    return each_td, sum(each_td.values())

# Calculating TC / Use every variable from TC_Initializing()
# Result is a just objective
def TC(Cand):
    Tasks = Cand + Reps

    solver = pywraplp.Solver.CreateSolver('SCIP')
    infinity = solver.infinity()

    x_r = {rep : solver.IntVar(0,1,'x_%s'%rep) for rep in Reps}
    y_kk = {(ini,fin) : solver.IntVar(0,1,'y_%s%s'%(ini,fin)) for ini,fin in itertools.permutations(Tasks,2)}

    a_j = {job: solver.NumVar(0, infinity, 'a_%s' % (job)) for job in Cand}
    l_j = {job: solver.NumVar(0, infinity, 'l_%s' % (job)) for job in Cand}
    p_j = {job: solver.NumVar(0, infinity, 'p_%s' % (job)) for job in Cand}
    t_j = {job: solver.NumVar(0, infinity, 't_%s' % (job)) for job in Cand}

    s_k = {task: solver.NumVar(0, infinity, 's_%s' % (task)) for task in Tasks}
    c_k = {task: solver.NumVar(0, infinity, 'c_%s' % (task)) for task in Tasks}

    solver.Add(x_r["r%s"%(len(Reps))] == 1)

    for job in Cand:
        solver.Add(y_kk[job,"r%s"%(len(Reps))] == 1)

    for job in Cand:
        for rep in Reps:
            solver.Add(s_k[rep] >= c_k[job] - M * x_r[rep])

    for job in Cand:
        solver.Add(t_j[job] >= c_k[job] - D_j[job])
        solver.Add(l_j[job] >= L)

    for job in Cand:
        for rep in range(len(Reps)-1):
            solver.Add(l_j[job] >= s_k["r%s"%(rep+2)] - c_k[job] - M * (1-y_kk["r%s"%(rep+1),job]+y_kk["r%s"%(rep+2),job]))

    for job in Cand:
        solver.Add(l_j[job] >= s_k["r1"] - M * (1-y_kk[job,"r1"]))

    for job in Cand:
        for rep in range(len(Reps)-1):
            solver.Add(a_j[job] >= s_k[job] - c_k["r%s"%(rep+1)] - M * (1-y_kk["r%s"%(rep+1),job] + y_kk["r%s"%(rep+2),job]))

    for job in Cand:
        solver.Add(a_j[job] >= s_k[job] - M * (1-y_kk[job,"r1"]))

    for ini,fin in itertools.combinations(Reps,2):
        solver.Add(y_kk[ini,fin] == 1)

    for ini,fin in itertools.permutations(Tasks,2):
        solver.Add(c_k[fin] <= s_k[ini] + M * y_kk[ini,fin])
        solver.Add(c_k[ini] <= s_k[fin] + M * (1-y_kk[ini,fin]))

    for rep in Reps:
        solver.Add(c_k[rep] == s_k[rep] + R * x_r[rep])

    for job in Cand:
        solver.Add(c_k[job] == s_k[job] + p_j[job])

    for job in Cand:
        solver.Add(p_j[job] >= PB_j[job] + aD_j[job] * a_j[job] - aU_j[job] * (L - l_j[job]))

    for job in Cand:
        solver.Add(p_j[job] >= PB_j[job])

    solver.Minimize(muE * sum(p_j[job] for job in Cand)
                  + muR * sum(x_r[rep] for rep in Reps)
                  + muT * sum(t_j[job] for job in Cand))
    solver.Solve()

    return round(solver.Objective().Value())

# Comparing each case with same jobs by comparing TC.
def best(cand):
    # Collecting every candidate's TC
    all_TC = []
    for case in range(len(cand)):
        all_TC.append(TC(cand[case]))
        print("Candidate %3s :" % (case+1), cand[case], "-->", all_TC[-1])
    min_TC = min(all_TC)

    # Choosing one case with the lowest Total Cost
    best_candidate = cand[all_TC.index(min_TC)]
    print("\n< Best case > : Candidate %d / %d\n"%(cand.index(best_candidate)+1, len(cand)), list(best_candidate),
          "\n<   TCost   > :", min_TC)
    return best_candidate,min_TC

# Local Search / If Nei ==1, Swap search    or    Nei == 2, Insert search
def localsearch(ini_seq,search):
    candidates = []
    for _ in range(search):
        ini_seq_tmp = ini_seq.copy()
        if Nei == 1:
            cvt = np.random.randint(len(ini_seq_tmp)-1)     # convert_index
            job = ini_seq_tmp.pop(cvt)
            ini_seq_tmp.insert(cvt+1,job)
            candidates.append(ini_seq_tmp)
        if Nei ==2 :
            dtt_job = ini_seq_tmp.pop(np.random.randint(len(ini_seq_tmp)))
            ini_seq_tmp.insert(np.random.randint(len(ini_seq_tmp)) + 1, dtt_job)
            candidates.append(ini_seq_tmp)
    return best(candidates)

# Iteration
# Comparing existing best sequence's Cost vs new candidate sequence's Cost. Lower one will survive.
def iteration(spt,spt_cost):
    each_sequence, total_cost = spt, spt_cost
    temperature = Temperature_Initial
    same_count = 0
    search = 1
    while temperature >= Temperature_Min and same_count <= SameCount_Max:
        iteration_compare = 0
        for Iteration in range(Iteration_Max):
            print("Best Jobs :", list(each_sequence))
            final_cost = localsearch(list(each_sequence),search)

            if final_cost[1] < total_cost:
                each_sequence, total_cost = final_cost
            else:
                if np.random.random() < math.e ** ((total_cost - final_cost[1]) / temperature):
                    each_sequence, total_cost = final_cost
                else:
                    iteration_compare += 1
                same_count += 1

            print("\n\n<<Iteration Result>>\n  Iteration  :  %s" % (Iteration + 1))
            print("New Sequence =", each_sequence)
            print("  New  Cost  = %s\n\n%s" % (total_cost, '-' * 100))

        temperature *= Temperature_K
        if iteration_compare >= Iteration_Max/2 and same_count < SameCount_Max:
            search += 1
        print("Temperature :", temperature, Temperature_Min)
        print(" Same Count :", same_count, SameCount_Max)
        print("   Search   :", search, "\n << New Period >>\n\n")
    return each_sequence, total_cost


# Initial Sequence : SPT
# Every Job Sequence is saved in List
# Jobs' attributes are saved as feature of the variable
def start(ini_jobs):
    SPT = sorted(ini_jobs, key = lambda job : globals()[job].processing_time)
    SPT_cost = TC(SPT)
    print("\nInitial  Sequence =", SPT)
    print("   Initial Cost   =", SPT_cost, "\n\n%s" % ("-" * 100))
    return iteration(SPT,SPT_cost)

# Number of Jobs, Replaces / Tasks = Jobs + Replaces
Number_of_Jobs = 20
Number_of_Replaces = 8

# SA Parameters / Able to modify values
Temperature_Initial = 50
Temperature_Min = 25
Temperature_K = 0.99
Iteration_Max = 20
SameCount_Max = 45698464
Search_Max = 5

# Neighborhood Type / (1) : Swap operator  (2) : Insert operator
Nei = 2

# SA_ANS
result = start(build())
print("<<<Final Result>>>")
print("Final  Each  Tardiness =", result[0])
print("Final Totals Tardiness =", result[1])