def tardiness(seqs):
    now = 0
    total_tardiness = 0
    for job in seqs:
        now += job.processing_time
        total_tardiness += max(0, now - job.due)
    return seqs, total_tardiness
