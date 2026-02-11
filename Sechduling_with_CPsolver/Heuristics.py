from ortools.sat.python import cp_model

# ---------------------------------- Initialization / Parameter ----------------------------------------

# Custom Job Set needed(same length of lists)
Job_names = ['J1', 'J2', 'J3', 'J4', 'J5']
Process_times = [3, 5, 2, 4, 3]
Due_dates = [12,8,4,15,10]

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

# ---------------------------------------------------------------------------

def solve_cp_sat(jobs):

    md = cp_model.CpModel()

    horizon = sum(job.processing_time for job in jobs)

    starts = {}
    ends = {}
    intervals = {}

    tds = {}

    for job in jobs:
        start = md.NewIntVar(0, horizon, "start_%s"%job.name)
        end = md.NewIntVar(0, horizon, "end_%s"%job.name)

        starts[job] = start
        ends[job] = end
        intervals[job] = md.NewIntervalVar(start,job.processing_time,end, "Interval_%s"%job.name)
        tds[job] = md.NewIntVar(0, horizon, "tardiness_%s"%job.name)

    md.AddNoOverlap(intervals.values())

    for job in jobs:
        md.add(tds[job] >= ends[job] - job.due)

    md.Minimize(sum(tds[job] for job in jobs))

    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    return solver, status, {"starts" : starts, "ends" : ends, "tds" : tds}

# ---------------------------------------------------------------------------

if __name__ == "__main__":

    ini_set = build(Job_names, Process_times, Due_dates)

    solver, status, results = solve_cp_sat(ini_set)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(solver.ObjectiveValue())

        assigned_jobs = []
        starts = results["starts"]
        ends = results["ends"]
        tds = results["tds"]

        for job in ini_set:
            assigned_jobs.append({"job" : job ,"start" : solver.value(starts[job]), "end" : solver.value(ends[job]), "duration" : job.processing_time, "td" : solver.value(tds[job])})
        assigned_jobs.sort(key=lambda job: job["start"])

        for job in assigned_jobs:
            print(job["job"].name, "__ start :", job["start"], "/ duration:", job["duration"], "/ end :", job["end"], "/ tardiness : %s - %s = %s" %(job["end"], job["job"].due, job["td"]))

    else:
        print("No solution")