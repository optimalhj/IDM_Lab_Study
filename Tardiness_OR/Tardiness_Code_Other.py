def tardiness(seqs):
    now, total_tardiness = 0, 0
    for job in seqs:
        now += job.processing_time
        total_tardiness += max(now - job.due, 0)
    return seqs, total_tardiness

if __name__ == '__main__':
    print("tardiness")