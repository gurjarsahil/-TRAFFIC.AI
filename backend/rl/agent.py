import numpy as np
import random
import json
import os

class QLearningAgent:
    def __init__(self, state_size, action_size, learning_rate=0.1, discount_factor=0.9, epsilon=1.0, epsilon_decay=0.995):
        self.state_size = state_size
        self.action_size = action_size
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = 0.01
        self.q_table = {}

    def _get_q_values(self, state):
        if state not in self.q_table:
            self.q_table[state] = np.zeros(self.action_size)
        return self.q_table[state]

    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        
        q_values = self._get_q_values(state)
        return np.argmax(q_values)

    def learn(self, state, action, reward, next_state):
        current_q = self._get_q_values(state)[action]
        max_next_q = np.max(self._get_q_values(next_state))
        
        # Q-Learning update rule
        new_q = current_q + self.lr * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state][action] = new_q
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save(self, filepath):
        # Convert state keys to string for JSON serialization
        data = {
            "q_table": {str(k): v.tolist() for k, v in self.q_table.items()},
            "epsilon": self.epsilon
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)

    def load(self, filepath):
        if not os.path.exists(filepath):
            return
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.q_table = {eval(k): np.array(v) for k, v in data["q_table"].items()}
            self.epsilon = data["epsilon"]
