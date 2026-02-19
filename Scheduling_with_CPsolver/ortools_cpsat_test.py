from ortools.sat.python import cp_model

def main():
    # 1. 모델 생성
    model = cp_model.CpModel()

    # 2. 데이터 정의 (Job ID: 소요 시간)
    # 예: Job 0은 3시간, Job 1은 2시간...
    jobs_data = [
        {'id': 0, 'duration': 3},
        {'id': 1, 'duration': 5},
        {'id': 2, 'duration': 2},
        {'id': 3, 'duration': 4},
        {'id': 4, 'duration': 3},
    ]

    # Horizon 계산 (모든 작업 시간의 합 = 스케줄이 가능한 최대 길이)
    horizon = sum(job['duration'] for job in jobs_data)

    # 3. 변수 생성
    # 각 작업의 start, end, interval 변수를 저장할 딕셔너리
    starts = {}
    ends = {}
    intervals = {}

    for job in jobs_data:
        duration = job['duration']
        job_id = job['id']
        name_suffix = f'_job{job_id}'

        # Start 변수: 0부터 horizon 사이의 값을 가짐
        start_var = model.NewIntVar(0, horizon, 'start' + name_suffix)

        # End 변수: 0부터 horizon 사이의 값을 가짐
        end_var = model.NewIntVar(0, horizon, 'end' + name_suffix)

        # Interval 변수: start, duration, end를 묶음
        # (중요) 이 변수가 스케줄링의 핵심 객체입니다.
        interval_var = model.NewIntervalVar(start_var, duration, end_var, 'interval' + name_suffix)

        starts[job_id] = start_var
        ends[job_id] = end_var
        intervals[job_id] = interval_var

    # 4. 제약 조건 추가: 싱글 머신 제약 (No Overlap)
    # 리스트에 있는 모든 interval 변수들은 시간이 겹치면 안 됨
    model.AddNoOverlap(intervals.values())

    # 5. 목적 함수: Makespan (전체 완료 시간) 최소화
    # 모든 작업의 끝나는 시간(end_var) 중 가장 큰 값(max)을 최소화(minimize)
    makespan = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(makespan, ends.values()) # makespan = max(ends)
    model.Minimize(makespan)

    # 6. 솔버 실행
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # 7. 결과 출력
    if status == cp_model.OPTIMAL or status == cp_model.FEATIBLE:
        print(f'Objective Value (Makespan): {solver.ObjectiveValue()}')
        print('-' * 40)

        # 시작 시간 순서대로 정렬하여 출력
        assigned_jobs = []
        for job_id in starts:
            start_time = solver.Value(starts[job_id])
            assigned_jobs.append((job_id, start_time, jobs_data[job_id]['duration']))

        assigned_jobs.sort(key=lambda x: x[1])

        for job in assigned_jobs:
            job_id, start, duration = job
            print(f"Job {job_id}: Start={start}, End={start + duration} (Duration: {duration})")
    else:
        print("No solution found.")

if __name__ == '__main__':
    main()
