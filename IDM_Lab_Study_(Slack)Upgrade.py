import pandas as pd

# 작업 순서 결정, 총 Tardiness 계산
def Slack(Times,Dues):
  
    now=0 ; total_tardiness=0 ; tardiness_dict={} ; sequence=[]

    j=0
    while j<len(Times):

        spt_dict = {}
        for job in Dues:
            spt_dict[job] = Dues[job] - now
        spt_min = min(spt_dict, key=spt_dict.get)

        now += Times[spt_min]
        tardiness_dict[spt_min] = max(now - Dues[spt_min],0)

        sequence.append(spt_min)

        Dues.pop(spt_min)

        j+=1

    for job in tardiness_dict:
        total_tardiness += tardiness_dict[job]

    return "%s : %s\n%s"%(sequence, total_tardiness , tardiness_dict)


# 작업의 종류, 시간, 납기일 수집
time_prod={}; due_dates={}
Jobs = pd.read_csv('Jobs_parameter.csv')
print(Jobs)

for Name in Jobs:
    if Name != 'Job':
        time_prod[Name]=Jobs.loc[0,Name]
        due_dates[Name]=Jobs.loc[1,Name]

print(Slack(time_prod,due_dates))