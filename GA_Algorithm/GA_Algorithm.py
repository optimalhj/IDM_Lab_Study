# ------ GA Programming -----
# 00000 00000부터 11111 11111까지 가장 큰 이진 정수를 GA로 찾기
# 탐색 중에 해집단의 해들이 일정 비율 동일하게 수렴하면 최적 해로 수렴했다고 판단하고 탐색을 종료하도록 설계
# ---------------------------

# 0 -> 0, 1-> 1, 10-> 2, 1101 -> 13

# ----- 제약사항 ------
# pandas 모듈 사용 금지
# random 모듈만 사용, 필요시 numpy 사용 가능
# [chromosome, fitness]로 구성된 list 타입의 해 사용: ["1010", 10]
# population 형태는 다음과 같이 list 타입으로 규정: [["1010", 10], ["0001", 1], ["0011", 3]]
# --------------------

import random

# ----- 수정 가능한 파라미터 -----

params = {'MUT': 0.5,  # 변이확률(%)
          'END' : 0.9,  # 설정한 비율만큼 chromosome이 수렴하면 탐색을 멈추게 하는 파라미터 (%)
          'POP_SIZE' : 10,  # population size 10 ~ 100
          'RANGE' : 10, # chromosome의 표현 범위, 만약 10이라면 00000 00000 ~ 11111 11111까지임
          'NUM_OFFSPRING' : 5} # 한 세대에 발생하는 자식 chromosome의 수
# 원하는 파라미터는 여기에 삽입할 것

# ------------------------------

class GA():
    def __init__(self, parameters):
        self.params = {}
        for key, value in parameters.items():
            self.params[key] = value



    def get_fitness(self, chromosome):
        fitness = 0
        for i in range(len(chromosome)):
            fitness += int(chromosome[i]) * (2 ** (self.params['RANGE'] - i - 1))
        return fitness

    def print_average_fitness(self, population):
        population_average_fitness = 0
        for pop in population:
            population_average_fitness += pop[1]
        population_average_fitness /= len(population)
        print("population 평균 fitness: {}".format(population_average_fitness))

    def sort_population(self, population):
        return population.sort(key = lambda pop : pop[1], reverse = True)

    def selection_operator(self, population):
        mom_ch = population[0]
        dad_ch = population[random.randint(a = 1, b = len(population) - 1)]

        return mom_ch, dad_ch

    def crossover_operator(self, mom_cho, dad_cho):
        indexes = sorted(random.sample([i for i in range(self.params['RANGE'])], random.randint(1, self.params['RANGE'])))
        offspring_cho = ""
        for idx in range(len(indexes)):
            if idx == 0:
                offspring_cho += str(mom_cho[0][0:indexes[idx]])
            else:
                offspring_cho += str(mom_cho[0][indexes[idx - 1]:indexes[idx]])
            mom_cho, dad_cho = dad_cho, mom_cho
        return offspring_cho + mom_cho[0][indexes[-1]:]

    def mutation_operator(self, chromosome):
        result_chromosome = ""
        for i in range(len(chromosome)):
            if random.random() <= self.params['MUT']:
                result_chromosome += str(1 - int(chromosome[i]))
            else:
                result_chromosome += chromosome[i]
        return result_chromosome, self.get_fitness(result_chromosome)

    def replacement_operator(self, population, offsprings):
        result_population = population + offsprings
        self.sort_population(result_population)
        return result_population[0:self.params['POP_SIZE']]

    # 해 탐색(GA) 함수
    def search(self):
        count = 0
        generation = 0  # 현재 세대 수
        population = [] # 해집단
        offsprings = [] # 자식해집단

        # 1. 초기화: 랜덤하게 해를 초기화
        for i in range(self.params["POP_SIZE"]):
            binary_num = ""
            for j in range(self.params['RANGE']):
                added = random.randint(0, 1)
                binary_num += str(added)
            deca_num = self.get_fitness(binary_num)
            population.append([binary_num, deca_num])
        self.sort_population(population)
        print("initialized population : \n", population, "\n\n")

        while 1:
            generation += 1
            for i in range(self.params["NUM_OFFSPRING"]):

                # 2. 선택 연산
                mom_ch, dad_ch = self.selection_operator(population)

                # 3. 교차 연산
                offspring = self.crossover_operator(mom_ch, dad_ch)

                # 4. 변이 연산
                offspring = self.mutation_operator(offspring)
                offsprings.append(offspring)

            # 5. 대치 연산
            population_tmp = population.copy()
            population = self.replacement_operator(population, offsprings)

            self.print_average_fitness(population) # population의 평균 fitness를 출력함으로써 수렴하는 모습을 보기 위한 기능

            # 6. 알고리즘 종료 조건 판단
            if population_tmp == population:
                count += 1
                if count / generation <= self.params['END']:
                    break

        # 최종적으로 얼마나 소요되었는지의 세대수, 수렴된 chromosome과 fitness를 출력
        print("탐색이 완료되었습니다. \t 최종 세대수: {},\t 최종 해: {},\t 최종 적합도: {}".format(generation, population[0][0], population[0][1]))


if __name__ == "__main__":
    ga = GA(params)
    ga.search()