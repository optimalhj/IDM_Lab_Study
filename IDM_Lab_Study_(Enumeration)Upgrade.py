import itertools    # 순열 툴을 위한 라이브러리 삽입
import pandas as pd

# 작업 순서 결정, 총 Tardiness 계산
def Enumeration(Times,Dues):

    tardiness_dict = {}
    for sequence in list(itertools.permutations(Times.keys())):
        now = 0 ;  total_tardiness = 0

        for job in sequence:

            now += Times[job]

            tardiness = max(now-Dues[job],0)

            total_tardiness += tardiness

        tardiness_dict[sequence]=total_tardiness

    enumeration_lists_min = min(tardiness_dict, key=tardiness_dict.get)

    return "%s , %s\n%s"%(enumeration_lists_min, tardiness_dict[enumeration_lists_min] , tardiness_dict)


# 작업의 종류, 시간, 납기일 수집
time_prod={}; due_dates={}
Jobs = pd.read_csv('Jobs_parameter.csv')
print(Jobs)

for Name in Jobs:
    if Name != 'Job':
        time_prod[Name]=Jobs.loc[0,Name]
        due_dates[Name]=Jobs.loc[1,Name]

print(Enumeration(time_prod,due_dates))