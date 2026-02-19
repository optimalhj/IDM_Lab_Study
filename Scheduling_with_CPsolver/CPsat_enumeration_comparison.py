from ortools.sat.python import cp_model
from itertools import permutations
import time

Job_names = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'J10']
Process_times = [7, 3, 12, 5, 9, 4, 6, 11, 2, 8]
Due_dates = [22, 10, 25, 18, 30, 14, 28, 35, 8, 20]

N = 10

class Jobs:
    def __init__(self, name, process_time, due_date):
        self.name = name
        self.pt = process_time
        self.dd = due_date
def build():
    jobs = [Jobs(Job_names[i], Process_times[i], Due_dates[i]) for i in range(len(Job_names))]
    return jobs

def calculate_cp(case):
    ini_time = time.time()
    md = cp_model.CpModel()
    horizon = sum(job.pt for job in case)
    starts = {}
    ends = {}
    intervals = {}
    tds = {}
    for job in case:
        starts[job] = md.NewIntVar(0,horizon, name = "start_%s"%job.name)
        ends[job] = md.NewIntVar(0,horizon, name = "end_%s"%job.name)
        intervals[job] = md.NewIntervalVar(starts[job], job.pt, ends[job], name = "interval_%s"%job.name)
        tds[job] = md.NewIntVar(0,horizon, name = "tardiness_%s"%job.name)
    md.AddNoOverlap(intervals.values())
    for job in case:
        md.add(tds[job] >= ends[job] - job.dd)
    md.Minimize(sum(tds.values()))
    solver = cp_model.CpSolver()
    status = solver.Solve(md)
    if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        print("Total_Tardiness =", sum(solver.value(tds[job]) for job in case))
        for job in sorted(starts, key = lambda j : solver.value(starts[j])):
            print(job.name,"_ Start :",solver.value(starts[job]),"Process :", job.pt,"End :", solver.value(ends[job]), "Tardiness :", "%s - %s = %s"%(solver.value(ends[job]), job.dd, solver.value(tds[job])))
    return time.time() - ini_time

def calculate_permutation_sort(case):
    ini_time = time.time()
    cases = []
    for seq in permutations(case):
        each = {}
        start, end, total = 0, 0, 0
        for job in seq:
            end += job.pt
            each[job] = (start, end, max(0, end - job.dd))
            start = end
            total += each[job][2]
        cases.append((each, total))
    best, total_tardiness = sorted(cases, key = lambda j : j[1])[0]
    print("Total_Tardiness =", total_tardiness)
    for job in best:
        print(job.name, "_ Start :",best[job][0], "Process :", job.pt,"End :", best[job][1], "Tardiness :", "%s - %s = %s"%(best[job][1], job.dd, best[job][2]))
    return time.time() - ini_time

def calculate_permutation_comparison(case):
    ini_time = time.time()
    now, total_tardiness = 0, 0
    best = case
    for job in best:
        now += job.pt
        total_tardiness += max(0, now - job.dd)

    for seq in permutations(case):
        each = {}
        start,end, total = 0, 0, 0
        for job in seq:
            end += job.pt
            each[job] = (start, end, max(0, end - job.dd))
            start = end
            total += each[job][2]
        if total < total_tardiness: best, total_tardiness = each, total

    print("Total_Tardiness =", total_tardiness)
    for job in best:
        print(job.name, "_ Start :", best[job][0], "Process :", job.pt, "End :", best[job][1], "Tardiness : %s - %s = %s" % (best[job][1], job.dd, best[job][2]))
    return time.time() - ini_time

if __name__ == '__main__':
    ini_set = build()

    Result1_count, Result2_count, Result3_count = 0, 0, 0
    for _ in range(N):

        print("\nBased on Permutation_Sort")
        Result1 = calculate_permutation_sort(ini_set)
        print("Duration :", Result1)

        print("\nBased on Permutation_Comparison")
        Result2 = calculate_permutation_comparison(ini_set)
        print("Duration :", Result2)

        print("\nBased on CP sat")
        Result3 = calculate_cp(ini_set)
        print("Duration :", Result3)


        if Result1 <= Result2 and Result1 <= Result3:
            Result1_count += 1
        elif Result2 <= Result1 and Result2 <= Result3:
            Result2_count += 1
        else:
            Result3_count += 1
    print("\n\nFinal Result")
    print("Permutation_Sort_count =", Result1_count)
    print("Permutation_Comparison_count =", Result2_count)
    print("CP sat_count =", Result3_count)
