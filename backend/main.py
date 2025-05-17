# backend/rl_agent/main.py
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import os

from .model import load_rl_model, train_rl_model # .model refers to model.py
from .environment import SocialEnv # .environment refers to environment.py
from .blockchain import blockchain_service, UP_ABI, LSP7_ABI # .blockchain refers to blockchain.py
from web3 import Web3 # For encoding data for execution

# Load the RL model globally on startup
# The SocialEnv instance passed here is more for structural compatibility if needed by load.
# The actual interactions for recommendations will use observations passed in requests.
# We need a UP address for the SocialEnv instance if it's used by the model internally.
# However, for `predict`, we typically pass an observation array directly.
# For now, let's not pass an env to load_rl_model or pass a dummy one.
# The `load_rl_model` function was updated to handle this.
POLICY_PATH = "backend/policy/dqn_social_policy.zip"
rl_model = load_rl_model(POLICY_PATH) # Loads or initializes a new model

app = FastAPI(
    title="Autonomous Profile Agent RL Backend",
    description="Provides action recommendations and executes them for LUKSO Universal Profiles.",
    version="0.1.0"
)

# This global SocialEnv instance is problematic if it holds state for a *specific* UP.
# For stateless prediction based on input observation, it's okay.
# Or, create env on-the-fly if UP context is needed for prediction beyond observation.
# For now, let's assume observation is sufficient.
# social_env = SocialEnv(up_address="0x...some_default_or_dynamic_up") # Needs careful handling for multi-user

class ActionRequest(BaseModel):
    up_address: str
    # Observations should match the environment's observation space
    followers: float # Actual count
    posts_count: float # Actual count
    engagement_rate: float # Actual rate (e.g., 0.05 for 5%)
    # Add any other metrics your SocialEnv uses

class ExecuteActionRequest(BaseModel):
    up_address: str
    action_id: int # 0=post, 1=follow, 2=reward
    # Optional parameters for actions
    target_address: str = None # For follow or reward
    post_content_cid: str = None # For post
    reward_amount_wei: int = None # For reward (LSP7 uses uint256 for amount)

@app.on_event("startup")
async def startup_event():
    if not os.path.exists(POLICY_PATH) and os.getenv("TRAIN_MODEL_ON_STARTUP", "false").lower() == "true":
        print("No policy found, and TRAIN_MODEL_ON_STARTUP is true. Training a new model...")
        try:
            # This is a blocking call if train_rl_model is not fully async
            # Consider running training as a separate process or background task.
            # For simplicity in example, direct call.
            # For SB3, training is CPU-bound and sync, so running in thread executor if FastAPI is async.
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: asyncio.run(train_rl_model(total_timesteps=10000))) # Small train for startup
            global rl_model # Reload the newly trained model
            rl_model = load_rl_model(POLICY_PATH)
        except Exception as e:
            print(f"Error during startup model training: {e}")
            # Fallback to an untrained model structure if training fails
            if rl_model is None:
                 # Initialize a basic model structure if load_rl_model didn't handle it
                from stable_baselines3 import DQN
                from .model import SimplifiedSocialEnv # Use the sync env for this
                temp_env = SimplifiedSocialEnv(up_address="0x0")
                rl_model = DQN("MlpPolicy", temp_env)
                print("Initialized a default untrained model due to training/loading failure.")


@app.post("/recommend-action")
async def recommend_action(req: ActionRequest):
    # Normalize observations similar to how SocialEnv does it
    # These max values should be consistent with SocialEnv's definition
    # Consider creating a utility in SocialEnv for normalization.
    temp_env = SocialEnv(up_address=req.up_address) # Create a temp env for normalization constants
    
    obs_normalized = np.array([
        req.followers / temp_env.max_followers,
        req.posts_count / temp_env.max_posts,
        req.engagement_rate / temp_env.max_engagement_rate,
    ], dtype=np.float32)
    obs_normalized = np.clip(obs_normalized, 0, 1)

    if rl_model is None:
        # Fallback: return a random action or a default if model isn't loaded
        print("Warning: RL model not loaded. Returning random action.")
        return {"action_id": int(np.random.choice([0,1,2])), "action_name": "Random (Model Unloaded)", "recommendation_confidence": 0.0}

    action_id_array, _states = rl_model.predict(obs_normalized, deterministic=True)
    action_id = int(action_id_array.item()) # Get single int from numpy array

    action_map = {0: "Make Post", 1: "Follow Profile", 2: "Reward Follower"}
    action_name = action_map.get(action_id, "Unknown Action")

    return {"action_id": action_id, "action_name": action_name, "recommendation_confidence": 1.0} # Confidence is placeholder

@app.post("/execute-action")
async def execute_agent_action(req: ExecuteActionRequest):
    if not blockchain_service.agent_eoa_private_key:
        raise HTTPException(status_code=500, detail="Agent EOA private key not configured for execution.")

    try:
        tx_receipt = None
        if req.action_id == 0: # Make Post
            if not req.post_content_cid:
                raise HTTPException(status_code=400, detail="post_content_cid required for posting.")
            print(f"Agent executing 'Make Post' for UP: {req.up_address}, CID: {req.post_content_cid}")
            tx_receipt = await blockchain_service.make_post(req.up_address, req.post_content_cid)

        elif req.action_id == 1: # Follow Profile
            if not req.target_address:
                raise HTTPException(status_code=400, detail="target_address required for follow.")
            print(f"Agent executing 'Follow Profile' for UP: {req.up_address}, Target: {req.target_address}")
            tx_receipt = await blockchain_service.follow_profile(req.up_address, req.target_address)

        elif req.action_id == 2: # Reward Follower
            if not req.target_address or req.reward_amount_wei is None:
                raise HTTPException(status_code=400, detail="target_address and reward_amount_wei required for reward.")
            print(f"Agent executing 'Reward Follower' for UP: {req.up_address}, Target: {req.target_address}, Amount: {req.reward_amount_wei}")
            tx_receipt = await blockchain_service.send_thank_you_token(req.up_address, req.target_address, req.reward_amount_wei)
        else:
            raise HTTPException(status_code=400, detail="Invalid action_id.")

        return {"status": "success", "action_id": req.action_id, "details": tx_receipt}

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Blockchain connection error: {e}")
    except ValueError as e: # Catch contract errors, insufficient funds etc.
        # This will catch `assert`s from web3.py if a tx would fail (e.g. insufficient balance for agent EOA gas)
        # Actual on-chain reverts need to be parsed from receipt if tx goes through but reverts.
        raise HTTPException(status_code=400, detail=f"Blockchain interaction error: {str(e)}")
    except Exception as e:
        print(f"Unhandled error during action execution: {e}") # Log for debugging
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# To run (from backend directory): uvicorn rl_agent.main:app --host 0.0.0.0 --port 8000 --reload