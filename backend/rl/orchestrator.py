import time
import logging
from rl.agent import QLearningAgent
from rl.env import TrafficEnv
from perception.detector import VehicleDetector
from perception.tracker import CentroidTracker

logger = logging.getLogger(__name__)

class AdaptiveTrafficOrchestrator:
    def __init__(self, detector: VehicleDetector, config):
        self.detector = detector
        self.config = config
        self.tracker = CentroidTracker()
        self.env = TrafficEnv()
        self.agent = QLearningAgent(state_size=9, action_size=9) # 9 states (3x3), 9 actions (3x3)
        
        self.current_action_idx = 4 # Start with Medium FPS, Medium Conf
        self.last_state = (0, 2) # (Low density, Fast speed)
        self.current_params = self.env.get_params_from_action(self.current_action_idx)
        
        self.step_counter = 0
        self.rl_active = True

    def process_frame(self, frame):
        """
        Process a single frame through RL-optimized detection.
        """
        # 1. Detect (using current RL-derived params)
        detection_result = self.detector.detect(
            frame, 
            confidence=self.current_params["confidence"],
            frame_interval=self.current_params["fps"] # Wait, interval is inverse of FPS in some sense
            # Actually detector.py uses interval (process 1 every N frames).
            # If Config.CCTV_FPS_SIM is 30, and interval is 2, it's 15 FPS.
        )
        
        # 2. Track
        boxes = detection_result.get("bounding_boxes", [])
        self.tracker.update(boxes)
        
        # 3. Get metrics
        density = detection_result.get("density_estimate", 0)
        avg_speed = self.tracker.get_avg_speed() / 100.0 # Normalize pixel speed roughly
        inference_time = detection_result.get("inference_time_ms", 0)
        
        # 4. RL Update Step (every N processed frames)
        if self.rl_active and self.step_counter % 30 == 0:
            current_state = self.env.get_state(density, avg_speed)
            
            # Calculate reward for the PREVIOUS action
            reward = self.env.calculate_reward(
                density, 
                avg_speed, 
                inference_time, 
                actual_fps=30 / self.current_params["fps"],
                target_fps_lvl=self.current_params["fps_lvl"]
            )
            
            # Learn
            self.agent.learn(self.last_state, self.current_action_idx, reward, current_state)
            
            # Choose next action
            self.current_action_idx = self.agent.choose_action(current_state)
            self.current_params = self.env.get_params_from_action(self.current_action_idx)
            self.last_state = current_state
            
            logger.info(f"RL Step | State: {current_state} | Action: {self.current_params} | Reward: {reward}")

        self.step_counter += 1
        
        return {
            "detections": detection_result,
            "tracker_count": len(self.tracker.objects),
            "avg_speed": round(avg_speed, 2),
            "rl_params": self.current_params,
            "rl_stats": {
                "epsilon": round(self.agent.epsilon, 4),
                "reward_history": [] # Could add history here
            }
        }
