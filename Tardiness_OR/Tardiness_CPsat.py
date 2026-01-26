from ortools.sat.python import cp_model

def tardiness(seqs):
    md = cp_model.CpModel()

    horizon = sum(jb.processing_time for jb in seqs)

    # start time
    st = {jb: md.NewIntVar(0, horizon, f"st_{jb.name}") for jb in seqs}

    # end time
    et = {jb: md.NewIntVar(0, horizon, f"et_{jb.name}") for jb in seqs}

    # tardiness
    td = {jb: md.NewIntVar(0, horizon, f"td_{jb.name}") for jb in seqs}

    # First Job's start = 0
    md.Add(st[seqs[0]] == 0)

    # Start + process = End
    for jb in seqs:
        md.Add(st[jb] + jb.processing_time <= et[jb])

    # Job's end = Next Job's start
    for i in range(len(seqs) - 1):
        md.Add(st[seqs[i + 1]] >= et[seqs[i]])

    # Tardiness = 0 or Tardiness = (End - Due)
    for jb in seqs:
        md.Add(td[jb] >= et[jb] - jb.due)

    md.Minimize(sum(td[jb] for jb in seqs))

    solver = cp_model.CpSolver()
    status = solver.Solve(md)

    return status, seqs, solver.ObjectiveValue()



class Jobs:
    def __init__(self, name, pt, dd):
        self.name = name
        self.processing_time = pt
        self.due = dd


def build(names, times, dates):
    return [Jobs(names[i], times[i], dates[i]) for i in range(len(names))]


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
    ini_set.sort(key = lambda jb: jb.processing_time)
    result = tardiness(ini_set)

    if result[0] in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for job in result[1]:
            print(job.name, "/", job.processing_time, ",", job.due)
        print("Total tardiness =", result[2])
    else:
        print("No solution found")
