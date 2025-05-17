# backend/rl_agent/environment.py
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random
from .blockchain import blockchain_service # Assuming blockchain.py is in the same directory

class SocialEnv(gym.Env):
    metadata = {'render_modes': ['human'], 'render_fps': 30}

    def __init__(self, up_address: str):
        super().__init__()
        self.up_address = up_address
        self.action_history_limit = 10 # Remember last N actions to avoid repetition
        self.action_history = []

        # Observation space: [followers_normalized, posts_count_normalized, engagement_rate_normalized, time_since_last_post_norm, ... potentially more features]
        # Normalize values roughly between 0 and 1. Max values are estimates.
        self.max_followers = 10000
        self.max_posts = 1000
        self.max_engagement_rate = 0.5 # e.g. 50%
        self.max_time_since_last_action = 7*24*60 # 1 week in minutes, or steps

        # Add features for recent action types to discourage spamming the same action
        # One-hot encoding for last N actions (e.g., 3 actions * 3 types = 9 features)
        # For simplicity now, let's stick to basic metrics.
        self.observation_space = spaces.Box(low=0, high=1, shape=(3,), dtype=np.float32)

        # Action space:
        # 0: Make a generic post (e.g., "Feeling good today!")
        # 1: Follow a suggested profile (for now, pick a random known profile or a hardcoded one)
        # 2: Reward an active follower (for now, pick a random known profile or hardcoded one with TYT)
        self.action_space = spaces.Discrete(3)

        self.current_step = 0
        self.max_steps_per_episode = 100 # An episode ends after N actions

        # Initial state (will be fetched in reset)
        self.state = np.zeros(self.observation_space.shape, dtype=np.float32)


    async def _get_observation(self):
        # In a real scenario, fetch from blockchain_service or an indexer
        # metrics = await blockchain_service.get_profile_metrics(self.up_address) # async call
        # For now, simulate metrics based on previous actions or random
        # This needs to be synchronous for stable_baselines3 or use an async wrapper for the env

        # SIMULATED: For stable_baselines3, this needs to be synchronous.
        # We'll use placeholder logic. In a real app, the env might need to run in its own async loop
        # and provide observations synchronously when polled by the agent.
        
        # Placeholder: slightly improve metrics if certain actions were taken
        # This is where the core simulation logic for training would go if not using live data.
        # For a live agent, this would fetch real data.
        
        # For now, let's use random data for a non-training 'live' agent and assume metrics are passed in.
        # During training, this would be more sophisticated.
        # Let's assume the `step` and `reset` methods will update a self.metrics dictionary
        # For this example, we'll just generate random metrics.
        
        # This function will be called by `reset` and `step`
        # For now, let's assume self.metrics is populated by some external process or simulation
        if not hasattr(self, 'simulated_metrics'):
             self.simulated_metrics = {
                "followers": random.randint(10, self.max_followers // 2),
                "posts_count": random.randint(5, self.max_posts // 2),
                "engagement_rate": round(random.uniform(0.01, self.max_engagement_rate / 2), 3)
            }

        obs = np.array([
            self.simulated_metrics["followers"] / self.max_followers,
            self.simulated_metrics["posts_count"] / self.max_posts,
            self.simulated_metrics["engagement_rate"] / self.max_engagement_rate,
        ], dtype=np.float32)
        return np.clip(obs, 0, 1) # Ensure values are within bounds

    async def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.action_history = []
        # Fetch initial metrics for the UP (or use simulation)
        self.simulated_metrics = await blockchain_service.get_profile_metrics(self.up_address) # Initial fetch
        self.state = await self._get_observation()
        return self.state, {} # obs, info

    async def step(self, action: int):
        self.current_step += 1
        terminated = False
        truncated = False
        reward = 0
        
        # Store action to discourage repetition if needed
        self.action_history.append(action)
        if len(self.action_history) > self.action_history_limit:
            self.action_history.pop(0)

        # --- SIMULATE ACTION EFFECT & CALCULATE REWARD ---
        # This is the core of the RL environment's dynamics.
        # For a real agent, you'd execute the action on-chain and then observe the new state.
        # For training, you'd simulate this.
        
        # Placeholder target addresses for follow/reward
        placeholder_target_up = "0xSomeOtherUserProfileAddress" # Replace with actual or dynamically chosen
        placeholder_amount_tyt = 1 * (10**18) # 1 TYT token (assuming 18 decimals)

        action_cost = 0.05 # Small cost for any action (e.g. gas)

        if action == 0: # Make a post
            # print(f"Env: Simulating action 'Make Post' for {self.up_address}")
            # In a real agent: await blockchain_service.make_post(self.up_address, "ipfs://some_content_cid")
            self.simulated_metrics["posts_count"] += 1
            # Reward: Small positive for posting, larger if it leads to engagement
            reward += 0.1 + (random.uniform(0, 0.2) if self.simulated_metrics["engagement_rate"] > 0.05 else 0)
        elif action == 1: # Follow a profile
            # print(f"Env: Simulating action 'Follow Profile' {placeholder_target_up} for {self.up_address}")
            # In a real agent: await blockchain_service.follow_profile(self.up_address, placeholder_target_up)
            # Reward: Small positive, larger if it leads to follow-back or network growth
            reward += 0.05 + (random.uniform(0, 0.15) if random.random() < 0.2 else 0) # 20% chance of positive interaction
            self.simulated_metrics["followers"] += random.randint(0,1) # Small chance of immediate follower gain
        elif action == 2: # Reward an active follower
            # print(f"Env: Simulating action 'Reward Follower' {placeholder_target_up} for {self.up_address}")
            # In a real agent: await blockchain_service.send_thank_you_token(self.up_address, placeholder_target_up, placeholder_amount_tyt)
            # Reward: Neutral base, positive if it boosts overall engagement or follower loyalty
            reward += 0.0 + (random.uniform(0.1, 0.3) if self.simulated_metrics["engagement_rate"] > 0.03 else -0.05)
            self.simulated_metrics["engagement_rate"] *= random.uniform(1.0, 1.05) # Slight engagement boost
        
        # Discourage spamming the same action (example)
        if len(self.action_history) >=3 and len(set(self.action_history[-3:])) == 1:
            reward -= 0.1 

        reward -= action_cost # Apply action cost

        # Simulate slight organic changes to metrics
        self.simulated_metrics["followers"] += random.randint(-1, 2) # Organic growth/loss
        self.simulated_metrics["followers"] = max(0, self.simulated_metrics["followers"])
        self.simulated_metrics["engagement_rate"] *= random.uniform(0.98, 1.02) # Fluctuation
        self.simulated_metrics["engagement_rate"] = np.clip(self.simulated_metrics["engagement_rate"], 0, self.max_engagement_rate)


        # Update observation
        next_obs = await self._get_observation()
        self.state = next_obs

        if self.current_step >= self.max_steps_per_episode:
            truncated = True # Episode ends due to time limit

        # print(f"Step {self.current_step}: Action {action}, Reward {reward:.2f}, Next Obs: {next_obs}")
        return next_obs, reward, terminated, truncated, {} # obs, reward, terminated, truncated, info

    def render(self):
        # For now, no specific rendering
        pass

    def close(self):
        pass