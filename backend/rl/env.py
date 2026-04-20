import numpy as np

class TrafficEnv:
    """
    Environment mapping perception metrics to states and rewards for the RL agent.
    """
    def __init__(self):
        # Actions: (FPS_Level, Confidence_Level)
        # FPS_Level: 0 (5 FPS), 1 (15 FPS), 2 (30 FPS)
        # Confidence_Level: 0 (0.25), 1 (0.45), 2 (0.65)
        self.action_space = [(f, c) for f in range(3) for c in range(3)]
        self.num_actions = len(self.action_space)
        
        # State: (Density_Level, Speed_Level)
        # Density: 0 (Low), 1 (Med), 2 (High)
        # Speed: 0 (Slow), 1 (Med), 2 (Fast)

    def get_state(self, density, avg_speed):
        """Discretize continuous metrics into state levels."""
        # Density levels
        if density < 0.1:
            d_lvl = 0
        elif density < 0.4:
            d_lvl = 1
        else:
            d_lvl = 2
            
        # Speed levels (normalized 0-1)
        if avg_speed < 0.3:
            s_lvl = 0
        elif avg_speed < 0.7:
            s_lvl = 1
        else:
            s_lvl = 2
            
        return (d_lvl, s_lvl)

    def calculate_reward(self, density, avg_speed, inference_time_ms, actual_fps, target_fps_lvl):
        """
        Calculate reward based on system goals.
        - Goal 1: Accuracy (Higher FPS and standard confidence when traffic is heavy).
        - Goal 2: Efficiency (Lower FPS when traffic is light).
        """
        reward = 0
        
        # Efficiency component: penalize high FPS when density is low
        if density < 0.1 and target_fps_lvl > 0:
            reward -= 5 * target_fps_lvl
        
        # Latency component: penalize high inference time
        if inference_time_ms > 100:
            reward -= 2
            
        # Accuracy component: reward high FPS when congestion is high
        if density > 0.4:
            if target_fps_lvl == 2:
                reward += 10
            elif target_fps_lvl == 1:
                reward += 2
            else:
                reward -= 10 # Very bad for safety/tracking
                
        # Stability reward: if speed is slow, we need consistent tracking
        if avg_speed < 0.3 and density > 0.2:
            if target_fps_lvl >= 1:
                reward += 5
        
        return reward

    def get_params_from_action(self, action_idx):
        fps_lvl, conf_lvl = self.action_space[action_idx]
        
        fps_map = {0: 5, 1: 15, 2: 30}
        conf_map = {0: 0.25, 1: 0.45, 2: 0.65}
        
        return {
            "fps": fps_map[fps_lvl],
            "confidence": conf_map[conf_lvl],
            "fps_lvl": fps_lvl,
            "conf_lvl": conf_lvl
        }
