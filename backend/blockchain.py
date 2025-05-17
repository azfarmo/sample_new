# backend/rl_agent/blockchain.py
import os
from web3 import Web3
from web3.middleware import geth_poa_middleware # For PoA networks like LUKSO Testnet
from dotenv import load_dotenv
import json

# ABIs (simplified, load full ABIs from files in a real app)
UP_ABI = json.loads('[{"inputs":[{"internalType":"bytes[]","name":"data","type":"bytes[]"}],"name":"setDataBatch","outputs":[],"stateMutability":"payable","type":"function"}, {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"getData","outputs":["bytes"],"stateMutability":"view","type":"function"}, {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]') # Add more as needed
LSP7_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"bool","name":"force","type":"bool"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"transfer","outputs":[],"stateMutability":"nonpayable","type":"function"}]') # Add more
LSP6_KEY_MANAGER_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"_address","type":"address"},{"internalType":"bytes4","name":"_functionSelector","type":"bytes4"},{"internalType":"bytes","name":"_data","type":"bytes"}],"name":"executeRelayCall","outputs":["bytes"],"stateMutability":"payable","type":"function"}, {"inputs":[{"internalType":"bytes[]","name":"keys","type":"bytes[]"},{"internalType":"bytes[]","name":"values","type":"bytes[]"}],"name":"setDataBatch","outputs":[],"stateMutability":"payable","type":"function"}]') # Add more as needed


load_dotenv()

class BlockchainService:
    def __init__(self):
        self.rpc_url = os.getenv("TESTNET_RPC_URL")
        self.agent_eoa_address = os.getenv("AGENT_EOA_ADDRESS")
        self.agent_eoa_private_key = os.getenv("AGENT_EOA_PRIVATE_KEY")
        self.thank_you_token_address = os.getenv("THANK_YOU_TOKEN_ADDRESS")
        # self.badge_nft_address = os.getenv("BADGE_NFT_ADDRESS") # If used
        self.chain_id = int(os.getenv("LUKSO_TESTNET_CHAIN_ID", 4201))

        if not all([self.rpc_url, self.agent_eoa_address, self.agent_eoa_private_key, self.thank_you_token_address]):
            raise ValueError("Missing blockchain config in .env for backend")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0) # Important for LUKSO Testnet

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to blockchain RPC")

        self.account = self.w3.eth.account.from_key(self.agent_eoa_private_key)
        assert self.account.address == self.agent_eoa_address, "Mismatch between agent EOA address and private key!"

    def get_up_owner(self, up_address: str) -> str:
        up_contract = self.w3.eth.contract(address=Web3.to_checksum_address(up_address), abi=UP_ABI)
        return up_contract.functions.owner().call() # This is the KeyManager address

    def _send_transaction(self, tx):
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx['nonce'] = nonce
        tx['gas'] = self.w3.eth.estimate_gas(tx) # Estimate gas
        tx['gasPrice'] = self.w3.eth.gas_price # Use current gas price
        tx['chainId'] = self.chain_id

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.agent_eoa_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    async def execute_via_key_manager(self, up_address: str, target_contract_address: str, encoded_payload: str):
        """
        Executes a call through the UP's KeyManager using the agent's EOA.
        Assumes agent EOA has 'EXECUTE_RELAY_CALL' or general 'CALL' permission set on KeyManager.
        Or, if KeyManager is the UP owner, uses execute function with proper ABI.
        """
        key_manager_address = self.get_up_owner(up_address)
        km_contract = self.w3.eth.contract(address=Web3.to_checksum_address(key_manager_address), abi=LSP6_KEY_MANAGER_ABI)

        # This example assumes the LSP6 execute function.
        # If using executeRelayCall, you need the relayCall ABI on KM and specific permission.
        # For setDataBatch on UP or transfer on Token:
        # The agent EOA was granted 'CALL' on KM for specific functions on other contracts,
        # OR 'SETDATA' on UP itself.
        # Here, we assume the agent will call functions on target contracts directly,
        # and the KM will allow these calls if the AGENT_EOA_ADDRESS has permissions.
        # More robustly, the agent EOA would call `execute(target, value, data)` on the KeyManager.

        # For this example, let's assume the KM allows direct calls from AGENT_EOA to specific functions
        # on the target_contract_address if permissions are set. This means the AGENT_EOA is
        # directly calling the target contract, and the KM doesn't need an `execute` call here.
        # The KeyManager's role is to *allow* the AGENT_EOA to make the call.

        # If the AGENT_EOA needs to execute a function *on the UP itself* (like setDataBatch),
        # it would call the UP's setDataBatch.
        if Web3.to_checksum_address(target_contract_address) == Web3.to_checksum_address(up_address):
            # This case is for calling a function on the UP itself (e.g. setDataBatch)
            up_contract_for_agent = self.w3.eth.contract(address=Web3.to_checksum_address(up_address), abi=UP_ABI)
            # Assume encoded_payload is for setDataBatch(bytes[] keys, bytes[] values)
            # This needs to be correctly unpacked or the function call built differently.
            # For simplicity, let's assume encoded_payload is the *entire* calldata for the target function
            # The function signature matching `encoded_payload` must exist on `target_contract_address`
            
            # Example: If encoded_payload is for setDataBatch on UP
            # tx_data = up_contract_for_agent.encodeABI(fn_name="setDataBatch", args=[keys, values])
            # This function needs refactoring to accept fn_name and args
            pass # This part needs more specific implementation based on the action.


        # If the agent is calling a function on ANOTHER contract (e.g., Token.transfer)
        # it calls that contract directly. The KeyManager's permission on AGENT_EOA allows this.
        # The tx 'from' will be AGENT_EOA_ADDRESS.
        # tx = {
        #     'to': Web3.to_checksum_address(target_contract_address),
        #     'value': 0,
        #     'data': encoded_payload, # This must be the full calldata for the target function
        #     'from': self.agent_eoa_address # Important: transaction is from agent
        # }
        # return self._send_transaction(tx)
        print(f"Simulating tx to {target_contract_address} with payload {encoded_payload}")
        return {"status": "simulated_success", "txHash": "0xsimulated"}


    async def make_post(self, up_address: str, post_content_cid: str):
        """
        Creates a simple post by setting LSP12IssuedAssets data on the UP.
        This requires the agent EOA to have SETDATA permission on the UP.
        """
        up_contract = self.w3.eth.contract(address=Web3.to_checksum_address(up_address), abi=UP_ABI)
        # This is a simplified example. Real LSP12 involves more keys.
        # You'd typically use lsp-utils or erc725.js to construct these payloads.
        # For a post, you might add an asset to LSP12IssuedAssets and link its metadata.
        # For now, let's simulate setting a generic "LastPostCID" key.
        # Schema for LSP3Profile: https://docs.lukso.tech/standards/universal-profile/lsp3-profile-metadata
        # Schema for LSP12IssuedAssets: https://docs.lukso.tech/standards/tokens/LSP12-Issued-Assets
        
        # Simplified: assume `setDataBatch` is called directly on UP by the agent.
        # Keys and values need to be constructed according to LSP standards.
        # For this example, let's imagine a very simple key for a post.
        # This requires lsp-utils or erc725.js for proper encoding.
        # Using erc725.js:
        # const lsp3ProfileData = erc725schema.encodeData([ ... ]);
        # For Python, you'd manually craft these or use a similar utility.
        # key = Web3.keccak(text="LSP3Profile") # This is not correct, use actual ERC725YDataKeys
        # For a simple text post, we might update a custom key or a simplified LSP12.
        
        # This is highly simplified and not LSP compliant for a "post".
        # A real implementation would use lsp-utils to generate the setDataBatch payload for LSP12.
        mock_key = Web3.keccak(text=f"MyProfilePost_{post_content_cid}")[:32] # Just an example
        mock_value = Web3.to_bytes(hexstr=post_content_cid) # Assuming CID is hex

        tx_data = up_contract.encodeABI(fn_name="setDataBatch", args=[[mock_key], [mock_value]])

        tx = {
            'to': Web3.to_checksum_address(up_address),
            'value': 0,
            'data': tx_data,
            'from': self.agent_eoa_address
        }
        print(f"Attempting to post to UP {up_address} via agent {self.agent_eoa_address}")
        return self._send_transaction(tx)


    async def send_thank_you_token(self, up_address_of_sender: str, to_address: str, amount: int):
        token_contract = self.w3.eth.contract(address=Web3.to_checksum_address(self.thank_you_token_address), abi=LSP7_ABI)
        
        # The agent EOA calls `transfer` on the token contract.
        # The `from` in the LSP7 transfer function is the UP of the user whose tokens are being sent.
        # The transaction itself is signed by and sent from the AGENT_EOA.
        # The KeyManager of `up_address_of_sender` must allow AGENT_EOA to make this call.
        tx_data = token_contract.encodeABI(
            fn_name="transfer",
            args=[
                Web3.to_checksum_address(up_address_of_sender), # from (the UP whose tokens are moved)
                Web3.to_checksum_address(to_address),           # to
                amount,                                         # amount
                True,                                           # force (allow sending to EOA)
                b''                                             # data
            ]
        )
        tx = {
            'to': Web3.to_checksum_address(self.thank_you_token_address),
            'value': 0,
            'data': tx_data,
            'from': self.agent_eoa_address # tx is initiated by agent
        }
        print(f"Attempting to send TYT from {up_address_of_sender} to {to_address} via agent {self.agent_eoa_address}")
        return self._send_transaction(tx)

    async def follow_profile(self, user_up_address: str, target_up_to_follow: str):
        # "Following" can be implemented in various ways on LUKSO.
        # 1. Update LSP3Profile with a custom "following" list (JSON array in a data key).
        # 2. Use a dedicated "SocialGraph" LSP contract.
        # For simplicity, let's assume updating a custom data key on the user's UP.
        # Key: keccak256("MyFollowingList")
        # Value: JSON string array of followed UP addresses, or a Link/Relay type if more complex.
        # This is similar to make_post, using setDataBatch on the user's UP.
        print(f"Simulating UP {user_up_address} following {target_up_to_follow}")
        # This would also use setDataBatch on the user_up_address, signed by agent_eoa_address
        # Similar to make_post, payload construction is key.
        return {"status": "simulated_follow_success", "txHash": "0xsimulated_follow"}

    async def get_profile_metrics(self, up_address: str):
        # This is a placeholder. In reality, you'd query an indexer (Blockscout, Subgraph, Subsquid)
        # or make multiple RPC calls to the UP to derive these metrics.
        # Example: Followers might be stored in a specific data key on LSP3Profile,
        # or derived from a Social Graph contract.
        # Posts: Count items in LSP12IssuedAssets.
        # Engagement: Much harder. Could be off-chain data or on-chain likes/comments if a standard exists.
        # For now, random data for simulation.
        import random
        return {
            "followers": random.randint(10, 1000),
            "posts_count": random.randint(5, 200),
            "engagement_rate": round(random.uniform(0.01, 0.15), 3) # e.g., likes per follower
        }

blockchain_service = BlockchainService()