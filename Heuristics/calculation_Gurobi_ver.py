import gurobipy as gp
from gurobipy import GRB

def tardiness(seqs):
    md = gp.Model("Tardiness")

    # start time
    st = md.addVars(seqs, vtype = GRB.INTEGER)
    md.addConstrs(st[job] >= 0 for job in seqs)

    # end time
    et = md.addVars(seqs, vtype = GRB.INTEGER)
    md.addConstrs(et[job] >= 0 for job in seqs)

    # tardiness
    td = md.addVars(seqs, vtype = GRB.INTEGER)
    md.addConstrs(td[job] >= 0 for job in seqs)

    # First Job's start = 0
    md.addConstr(st[seqs[0]] == 0)

    # Start + process = End
    md.addConstrs(st[job] + job.processing_time == et[job] for job in seqs)

    # Job's end = Next Job's start
    md.addConstrs(et[seqs[job_sq]] == st[seqs[job_sq + 1]] for job_sq in range(len(seqs) - 1))

    # Tardiness >= 0 or Tardiness >= (End - Due)
    md.addConstrs(et[job] - job.due <= td[job] for job in seqs)

    md.setObjective(gp.quicksum(td[job] for job in seqs), GRB.MINIMIZE)
    md.optimize()
    '''
    for job in seqs:
        print(job.name,"/", "Start :", st[job].X, "Progress :", job.processing_time, "End :", et[job].X, "Due :", job.due, "--> Tardiness :", td[job].X)
    '''
    return seqs, round(md.ObjVal)

if __name__ == '__main__':
    print("tardiness")
