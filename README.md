🚀 About Engage Agents

🌟 Project Overview

AI Agents on LUKSO for Creator Engagement

📈 Key Features





RL-Driven Action Recommendations





Agents analyze on-chain metrics (followers, posts count, engagement rate) to suggest optimal next moves (post, follow, reward).



Uses a DQN-based policy trained via Stable Baselines3 on a custom SocialEnv gym environment .



On-Chain Execution via KeyManager





Agent EOA holds fine-grained permissions on the creator’s UP through LSP6 KeyManager, enabling it to call setData (for posts) and token/NFT transfers autonomously .



Custom Engagement Assets





ThankYouToken (LSP7 fungible token) for micro-rewards.



BadgeNFT (LSP8 NFT) to issue achievement badges.



Deployed and owned by the creator’s UP, ensuring transparency and full on-chain provenance .



Real-Time Feedback Loop





After each action, agents fetch updated metrics on-chain to adjust strategy, ensuring continuous optimization of engagement.



Modular & Extensible





New actions or reward types (e.g., content stamping, DAO votes) can be added by extending the SocialEnv and smart contracts.

📦 Tech Stack





Frontend: React.js & Next.js (TypeScript), using @lukso/up-provider for one-click UP wallet connection, ethers.js & ERC725.js for interacting with UP data, and axios for HTTP calls.



Backend: Python · FastAPI handles REST endpoints (/recommend-action, /execute-action) . RL logic implemented with Stable Baselines3 & Gymnasium. Web3 interactions via web3.py.



Database / Storage:





Policy Storage: RL policy artifacts (DQN zip files) saved to disk under backend/policy/.



Logging: TensorBoard logs for training metrics; no on-chain metric caching, guaranteeing live data freshness.



APIs & Integrations:





LUKSO Testnet RPC for blockchain reads/writes.



IPFS/CID storage for post content.



Hardhat/Ethers for contract deployment scripts.



Environment variables managed via .env (e.g., RPC URLs, private keys).

🛠️ How It Works





Profile Connection & Permissioning





Creator connects their UP via the frontend.



Backend runs configureKeyManager.js to grant the agent EOA SETDATA and CALL permissions (including token/NFT transfers) on the target UP .



Metric Collection





Agent queries on-chain metrics (followers, posts count, engagement rate) through blockchain_service.



Action Recommendation





FastAPI /recommend-action endpoint normalizes metrics, calls the DQN policy to select the best action (post/follow/reward) configureKeyManagerdeploy.



Execution





Upon user approval (or fully automated), /execute-action sends the transaction: posting via setData, following via UP call, or transferring TYT tokens/NFT badges mainconfigureKeyManager.



Feedback Loop





After execution, updated metrics are fetched to retrain or refine the policy over time.

📌 Technicals





RL Environment (SocialEnv) simulates or executes on-chain actions, with observation space normalized to [0,1] for followers/posts/engagement and discrete action space of size 3 mainmain.



DQN Hyperparameters: learning rate 1e-4, buffer size 50k, batch size 32, γ = 0.99, exploration ε decay to 0.05.



Smart Contracts:





LSP7DigitalAsset (ThankYouToken.sol) for fungible thank-you tokens.



LSP8IdentifiableDigitalAsset (BadgeNFT.sol) for unique badges, with an open mint function for future expansion.



Permission Encoding: Uses ERC725’s encodePermissions and encodeData utilities to batch configure keys and allowed function selectors on LSP6 environmentconfigureKeyManager

✅ Why Your Submission?





Seamless AI + Blockchain Fusion: First on LUKSO to combine on-chain Universal Profiles with RL agents for real-time engagement.



True Decentralization: Agents operate purely via blockchain permissions—no custodial servers or off-chain middlemen.



Custom Tokenomics: Unique LSP7 tokens and LSP8 badges directly reward community participation.



Scalable & Extensible: Modular env and contract design allows adding new action types and reward mechanics without overhauling core logic.

📅 Project Future





Personalized Policies: Fine-tune RL models per creator niche or audience segment.



Generative Content: Integrate GPT-based content drafts for posts.



Cross-Chain Support: Extend to Ethereum & Polygon via UP bridging.



Engagement Analytics Dashboard: Real-time charts and predictions powered by agent logs and on-chain data.



Marketplace Integration: Allow creators to sell engagement packages or premium badges

🤝 Team & Contributions





🧑‍💻 Azfar Mohamed: Lead Developer



📊 Arnav Nikam: Product Manager/Strategy
