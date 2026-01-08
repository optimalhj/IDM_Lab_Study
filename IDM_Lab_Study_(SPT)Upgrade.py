import pandas as pd

# 작업 순서 결정, 총 Tardiness 계산

def SPT(Times,Dues):

    now=0 ; total_tardiness=0 ; tardiness_dict={} ; sequence=[]

    for job in sorted(Times.items(), key=lambda item:item[1]):
    
        now += job[1]
    
        tardiness_dict[job[0]]=max(now-Dues[job[0]],0)
    
        total_tardiness += tardiness_dict[job[0]]
    
        sequence.append(job[0])

    return "%s : %s\n%s"%(sequence, total_tardiness , tardiness_dict)

# 작업의 종류, 시간, 납기일 수집
time_prod={}; due_dates={}
Jobs = pd.read_csv('Jobs_parameter.csv')
print(Jobs)

for Name in Jobs:
    if Name != 'Job':
        time_prod[Name]=Jobs.loc[0,Name]
        due_dates[Name]=Jobs.loc[1,Name]

print(SPT(time_prod,due_dates))