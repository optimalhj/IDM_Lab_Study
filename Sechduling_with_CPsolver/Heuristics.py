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

    def cp_assign(self, var_start, var_end, var_td):
        self.start = var_start
        self.end = var_end
        self.td = var_td

def build(names, times, dues):
    new_jobs = [Jobs(names[i], times[i], dues[i]) for i in range(len(names))]
    return new_jobs

# ---------------------------------------------------------------------------
def solve_cp_sat(jobs):

    md = cp_model.CpModel()

    horizon = sum(job.processing_time for job in jobs)
    intervals = {}

    for job in jobs:
        job.cp_assign(md.NewIntVar(0, horizon, "start_%s"%job.name), md.NewIntVar(0, horizon, "end_%s"%job.name), md.NewIntVar(0, horizon, "tardiness_%s"%job.name))
        intervals[job] = md.NewIntervalVar(job.start,job.processing_time,job.end, "Interval_%s"%job.name)

    md.AddNoOverlap(intervals.values())

    for job in jobs:
        md.add(job.td >= job.end - job.due)

    md.Minimize(sum(job.td for job in jobs))

    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    return solver, status

# ---------------------------------------------------------------------------

if __name__ == "__main__":

    ini_set = build(Job_names, Process_times, Due_dates)
    solver, status = solve_cp_sat(ini_set)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        assigned_jobs = [{"job" : job ,"start" : solver.value(job.start), "end" : solver.value(job.end), "duration" : job.processing_time, "td" : solver.value(job.td)} for job in ini_set]
        assigned_jobs.sort(key=lambda job: job["start"])

        print("\nResult :", solver.ObjectiveValue())
        for job in assigned_jobs:
            print(job["job"].name, "__ start :", job["start"], "/ duration:", job["duration"], "/ end :", job["end"], "/ tardiness : %s - %s = %s" %(job["end"], job["job"].due, job["td"]))

    else:
        print("No solution")