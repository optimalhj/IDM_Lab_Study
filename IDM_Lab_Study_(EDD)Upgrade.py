import pandas as pd

def EDD(Times,Dues):

    now=0 ; total_tardiness=0 ; tardiness_dict={} ; sequence=[]

    for job in sorted(Dues.items(), key=lambda item:item[1]):
    
        now += Times[job[0]]
    
        tardiness_dict[job[0]]=max(now-job[1],0)
    
        total_tardiness += tardiness_dict[job[0]]
    
        sequence.append(job[0])

    return "%s : %s\n%s"%(sequence, total_tardiness , tardiness_dict)


time_prod={}; due_dates={}
Jobs = pd.read_csv('Jobs_parameter.csv')
print(Jobs)

for Name in Jobs:
    if Name != 'Job':
        time_prod[Name]=Jobs.loc[0,Name]
        due_dates[Name]=Jobs.loc[1,Name]

print(EDD(time_prod,due_dates))