# backend/rl_agent/model.py
import os
import gymnasium as gym
from stable_baselines3 import DQN
from stable_baselines3.common.env_util import make_vec_env
from .environment import SocialEnv # Assuming SocialEnv is in environment.py

MODEL_PATH = "backend/policy/dqn_social_policy.zip"
# Critical: The SocialEnv needs a UP address. For training, this could be a dummy or test UP.
# For a real agent, it's the user's UP.
# This implies that a model might need to be fine-tuned per user, or a generic model used.
# For simplicity, let's assume a generic model trained on a representative environment.
DUMMY_UP_FOR_TRAINING = "0x0000000000000000000000000000000000000000" # Placeholder

async def train_rl_model(total_timesteps=10000, save_path=MODEL_PATH):
    print(f"Training RL model for {total_timesteps} timesteps...")
    # Create the environment. For SB3, it needs to be a sync env.
    # SocialEnv itself is async due to blockchain calls. This is a mismatch.
    # For training, you'd typically:
    # 1. Create a fully SIMULATED SocialEnv that doesn't make real async calls.
    # 2. Or use a wrapper that handles the async nature if SB3 supports it (not typically).
    # For this example, we'll assume SocialEnv's async parts are placeholders
    # and it can run "synchronously enough" for a basic training loop.
    # THIS IS A MAJOR SIMPLIFICATION FOR THE EXAMPLE.
    # A real async env with SB3 often requires custom loops or libraries like `sb3-contrib`.

    # If SocialEnv has async methods like reset/step, make_vec_env might not work directly.
    # For now, assuming they can be called and awaited in a simplified loop or adapted.
    
    # To make it runnable with SB3 which expects sync envs,
    # we'd need to adapt SocialEnv or use a sync version for training.
    # Let's proceed with a conceptual training step, acknowledging this limitation.
    
    # Create a lambda that instantiates the environment
    # This is tricky because SocialEnv constructor takes an arg and reset/step are async
    # We need a synchronous wrapper or a synchronous version of SocialEnv for SB3.
    
    # For the sake of a runnable example, let's assume a simplified sync SocialEnv for training.
    # This would mean `_get_observation` and `step`'s blockchain calls are fully mocked/simulated.
    
    # --- Simplified Sync Env for Training (conceptual) ---
    class SimplifiedSocialEnv(SocialEnv): # Inherit and override async methods
        def __init__(self, up_address: str):
            super().__init__(up_address)
            # No async blockchain calls here, all simulated
            print("Using SimplifiedSocialEnv for training (all actions/observations are simulated synchronously)")

        # Override async methods to be sync and use pure simulation
        def _get_sync_observation(self): # Renamed to avoid clash and indicate sync
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
            return np.clip(obs, 0, 1)

        def reset(self, seed=None, options=None): # Sync override
            super().reset(seed=seed) # Calls gym.Env.reset
            self.current_step = 0
            self.action_history = []
            self.simulated_metrics = { # Initial simulated metrics
                "followers": random.randint(10, self.max_followers // 2),
                "posts_count": random.randint(5, self.max_posts // 2),
                "engagement_rate": round(random.uniform(0.01, self.max_engagement_rate / 2), 3)
            }
            self.state = self._get_sync_observation()
            return self.state, {}

        def step(self, action: int): # Sync override
            # Call the async step logic but ensure it's effectively sync for simulation
            # This is where you'd put the pure simulation logic from the async step.
            # For brevity, copying parts of the async step's simulation logic:
            self.current_step += 1
            terminated = False
            truncated = False
            reward = 0
            action_cost = 0.05

            if action == 0: # Make a post
                self.simulated_metrics["posts_count"] += 1
                reward += 0.1 + (random.uniform(0, 0.2) if self.simulated_metrics["engagement_rate"] > 0.05 else 0)
            elif action == 1: # Follow
                reward += 0.05 + (random.uniform(0, 0.15) if random.random() < 0.2 else 0)
                self.simulated_metrics["followers"] += random.randint(0,1)
            elif action == 2: # Reward
                reward += 0.0 + (random.uniform(0.1, 0.3) if self.simulated_metrics["engagement_rate"] > 0.03 else -0.05)
                self.simulated_metrics["engagement_rate"] *= random.uniform(1.0, 1.05)
            
            reward -= action_cost
            self.simulated_metrics["followers"] = max(0, self.simulated_metrics["followers"] + random.randint(-1, 2))
            self.simulated_metrics["engagement_rate"] = np.clip(self.simulated_metrics["engagement_rate"] * random.uniform(0.98, 1.02), 0, self.max_engagement_rate)

            next_obs = self._get_sync_observation()
            self.state = next_obs
            if self.current_step >= self.max_steps_per_episode:
                truncated = True
            return next_obs, reward, terminated, truncated, {}
    # --- End of Simplified Sync Env ---

    env_lambda = lambda: SimplifiedSocialEnv(up_address=DUMMY_UP_FOR_TRAINING)
    vec_env = make_vec_env(env_lambda, n_envs=1) # Use the lambda to create env

    model = DQN('MlpPolicy', vec_env, verbose=1,
                learning_rate=1e-4,
                buffer_size=50000,
                learning_starts=1000,
                batch_size=32,
                tau=1.0,
                gamma=0.99,
                train_freq=4,
                gradient_steps=1,
                exploration_fraction=0.1,
                exploration_final_eps=0.05,
                tensorboard_log="./dqn_social_tensorboard/")
    
    model.learn(total_timesteps=total_timesteps, log_interval=4)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save(save_path)
    print(f"Model trained and saved to {save_path}")
    vec_env.close()
    return model

def load_rl_model(load_path=MODEL_PATH, env_up_address:str = None):
    if not os.path.exists(load_path):
        print(f"No pre-trained model found at {load_path}. Consider training one first.")
        # Fallback: create a new untrained model or return None
        # For now, let's try to train a tiny one if not found
        print("Attempting to train a new basic model...")
        # This requires the SocialEnv to be usable synchronously for SB3
        # The `train_rl_model` above uses a SimplifiedSocialEnv
        # We need an env instance for DQN.load() if custom_objects or env is not saved with model
        # Create a dummy env for loading, actual env for inference will be different
        temp_env_for_loading = SimplifiedSocialEnv(up_address=DUMMY_UP_FOR_TRAINING) # Use the sync version
        model = DQN('MlpPolicy', temp_env_for_loading, verbose=0)
        # No actual training, just initializing a structure
        print("Initialized a new, untrained model structure.")
        return model

    print(f"Loading model from {load_path}")
    # When loading, you might need to pass the environment or custom objects
    # if they were not saved with the model or if you're using a custom policy.
    # For standard models, often the path is enough.
    # If the environment for inference is different (e.g. uses live data),
    # you'd typically set the env after loading or use model.predict with new obs.
    # The env passed to DQN.load is mostly for structure validation if not fully saved.
    
    # For inference, we'll use the real SocialEnv (async). SB3 predict is sync.
    # This means the observation for `model.predict` must be obtained synchronously.
    # The FastAPI endpoint will get observation, then call predict.
    # So, the env passed to `DQN.load` can be a placeholder if needed.
    temp_env_for_loading = SimplifiedSocialEnv(up_address=env_up_address or DUMMY_UP_FOR_TRAINING)
    model = DQN.load(load_path, env=temp_env_for_loading)
    print("Model loaded successfully.")
    return model

# Example usage (run this file directly to train)
if __name__ == "__main__":
    import asyncio
    # To train, you would run: python -m backend.rl_agent.model
    # Ensure SocialEnv can be instantiated and run by SB3 (i.e., it's effectively synchronous or wrapped)
    asyncio.run(train_rl_model(total_timesteps=20000)) # Small number for quick test