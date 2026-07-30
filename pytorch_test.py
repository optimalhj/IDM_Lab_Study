import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from collections import deque

import random

class Qnet(nn.Module):
    def __init__(self):
        super(Qnet, self).__init__()
        self.layer1 = nn.Linear(6, 64)
        self.layer2 = nn.Linear(64, 32)
        self.layer3 = nn.Linear(32, 16)
        self.layer4 = nn.Linear(16, 4)
    def forward(self, x):
        x = self.layer1(x)
        x = F.relu(x)
        x = self.layer2(x)
        x = F.relu(x)
        x = self.layer3(x)
        x = F.relu(x)
        x = self.layer4(x)
        return x

class ReplayMemory:
    def __init__(self, max_len, sample_size):
        self.memory = deque(maxlen=max_len)
        self.sample_size = sample_size
    def add_buffer(self, buffer):
        self.memory.append(buffer)
    def sample(self):
        s_batch, a_batch, r_batch, s_prime_batch, done_batch = [], [], [], [], []
        for s, a, r, s_prime, done in random.sample(self.memory, min(len(self.memory), self.sample_size)):
            s_batch.append([s[0]/8] + [s[1]/5] + s[2:])
            a_batch.append([a])
            r_batch.append([r])
            s_prime_batch.append([s_prime[0]/8] + [s_prime[1]/5] + s_prime[2:])
            done_batch.append([done])
        return torch.tensor(s_batch, dtype=torch.float), torch.tensor(a_batch, dtype=torch.long), torch.tensor(r_batch, dtype=torch.float), torch.tensor(s_prime_batch, dtype=torch.float), torch.tensor(done_batch, dtype=torch.float)

def state(point):
    able = [1, 1, 1, 1]
    if point[0] == 1 or (point[0] == 4 and point[1] in [3,4,5]) or (point[0] == 7 and point[1] in [1,2,3]):
        able[0] -= 1
    if point[1] == 5 or (point[1] == 2 and point[0] == 3):
        able[1] -= 1
    if point[0] == 8 or (point[0] == 2 and point[1] in [3,4,5]) or (point[0] == 5 and point[1] in [1,2,3]):
        able[2] -= 1
    if point[1] == 1 or (point[1] == 4 and point[0] == 6):
        able[3] -= 1
    return point + able

def state_scaling(raw_state):
    return [raw_state[0]/8] + [raw_state[1]/5] + raw_state[2:]

def step(action, point):
    move_succeed = False
    if action == 0: # LEFT
        if point[0] == 1:
            pass
        elif point[0] == 4 and point[1] in [3,4,5]:
            pass
        elif point[0] == 7 and point[1] in [1,2,3]:
            pass
        else:
            point[0] -= 1
            move_succeed = True
    elif action == 1: # Up
        if point[1] == 5:
            pass
        elif point[1] == 2 and point[0] == 3:
            pass
        else:
            point[1] += 1
            move_succeed = True
    elif action == 2: # Right
        if point[0] == 8:
            pass
        elif point[0] == 2 and point[1] in [3,4,5]:
            pass
        elif point[0] == 5 and point[1] in [1,2,3]:
            pass
        else:
            point[0] += 1
            move_succeed = True
    else: # Down
        if point[1] == 1:
            pass
        elif point[1] == 4 and point[0] == 6:
            pass
        else:
            point[1] -= 1
            move_succeed = True
    return move_succeed
def start():
    coordinates = {x: {y: {0:0, 1:0, 2:0, 3:0} if x != 8 or y != 1 else "G" for y in range(1, 6)} for x in range(1, 9)}
    for y in range(3, 6): coordinates[3][y] = "N"
    for y in range(1, 4): coordinates[6][y] = "N"
    qnet, qnet_target = [Qnet() for _ in range(2)]
    qnet_target.load_state_dict(qnet.state_dict())
    qnet_target.eval()
    optimizer = optim.Adam(qnet.parameters(), lr=0.001)

    memory = ReplayMemory(max_len=2000, sample_size=150)
    epsilon = 1
    entire_count = {}
    for epoch in range(5000):
        entire_count[f"Trial {epoch + 1}"] = 0
        point, done = [1, 5], False
        while not done:
            state_list = state(point.copy())
            with torch.no_grad():
                action = qnet(torch.tensor(state_scaling(state_list), dtype=torch.float)).argmax().item() if random.random() > epsilon else random.randint(0, 3)
            move_succeed = step(action, point)
            state_prime_list = state(point.copy())

            done = (state_prime_list[0] == 8 and state_prime_list[1] == 1)

            if done:
                reward = 100
                coordinates[state_list[0]][state_list[1]][action] += 1
            elif move_succeed:
                reward = -1
                coordinates[state_list[0]][state_list[1]][action] += 1
            else: reward = -5
            memory.add_buffer((state_list, action, reward, state_prime_list, 1 if done else 0))
            if len(memory.memory) > 32:
                s_batch, a_batch, r_batch, s_prime_batch, done_batch = memory.sample()
                q_a = qnet(s_batch).gather(1, a_batch)
                with torch.no_grad():
                    max_q_prime = qnet_target(s_prime_batch).max(1)[0].unsqueeze(1)
                    target = r_batch + 0.9 * max_q_prime * (1 - done_batch)
                loss = F.smooth_l1_loss(q_a, target)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            entire_count[f"Trial {epoch + 1}"] += 1
            if entire_count[f"Trial {epoch + 1}"] >= 500:
                done = True
        epsilon *= 0.95

        if epoch % 5 == 0:
            qnet_target.load_state_dict(qnet.state_dict())
        # print(f"Trial {epoch + 1} :", entire_count[f"Trial {epoch + 1}"])

    movement = {0:"L", 1:"U", 2:"R", 3:"D"}
    for y in range(5, 0, -1):
        print(y, end=" : ")
        for x in range(1, 9):
            if len(coordinates[x][y]) != 1:
                action = max([0, 1, 2, 3], key=lambda direction:coordinates[x][y][direction])
                print(movement[action], end=" ")
            else:
                print(coordinates[x][y], end=" ")
        print()
    print("    " + " ".join([f"{i}" for i in range(1, 9)]))

    print("-" * 50)
    for y in range(5, 0, -1):
        print(y, end=" : ")
        for x in range(1, 9):
            if len(coordinates[x][y]) == 1:
                print(coordinates[x][y], end=" ")
            else:
                state_list = state([x, y])
                with torch.no_grad():
                    action = qnet(torch.tensor(state_scaling(state_list), dtype=torch.float)).argmax().item()
                print(movement[action], end=" ")
        print()
    print("    " + " ".join([f"{i}" for i in range(1, 9)]))
def main():
    start()
if __name__ == '__main__':
    main()