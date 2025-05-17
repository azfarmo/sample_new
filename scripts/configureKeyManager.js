// scripts/configureKeyManager.js
import { ethers } from 'ethers';
import { ERC725, ERC725__factory } from '@erc725/erc725.js';
import { LSP6KeyManager__factory, UniversalProfile__factory } from '@lukso/lsp-smart-contracts';
import LSP6Schema from '@erc725/erc725.js/schemas/LSP6KeyManager.json';
import 'dotenv/config'; // To load .env variables

const {
    TESTNET_RPC_URL,
    DEPLOYER_PRIVATE_KEY,
    TARGET_UP_ADDRESS,
    AGENT_EOA_ADDRESS,
    THANK_YOU_TOKEN_ADDRESS, // Make sure this is deployed and address is in .env
    BADGE_NFT_ADDRESS,       // Make sure this is deployed and address is in .env
} = process.env;

if (!DEPLOYER_PRIVATE_KEY || !TARGET_UP_ADDRESS || !AGENT_EOA_ADDRESS || !TESTNET_RPC_URL || !THANK_YOU_TOKEN_ADDRESS) {
    console.error("Missing required environment variables!");
    process.exit(1);
}

async function configureKeyManager() {
    const provider = new ethers.JsonRpcProvider(TESTNET_RPC_URL);
    const deployerWallet = new ethers.Wallet(DEPLOYER_PRIVATE_KEY, provider);

    console.log(`Configuring KeyManager for UP: ${TARGET_UP_ADDRESS}`);
    console.log(`Granting permissions to Agent EOA: ${AGENT_EOA_ADDRESS}`);

    const up = UniversalProfile__factory.connect(TARGET_UP_ADDRESS, deployerWallet);
    const keyManagerAddress = await up.owner(); // In UPs, owner() is the KeyManager
    const keyManager = LSP6KeyManager__factory.connect(keyManagerAddress, deployerWallet);

    // --- Define Permissions for the Agent EOA ---
    // 1. Permission to call `setDataBatch` on the Universal Profile itself
    //    This allows creating posts (LSP12), updating profile (LSP3), following (custom key)
    const upPermissions = ERC725.encodePermissions({
        SETDATA: true, // General setData permission
        CALL: true,    // Needed if posts involve contract interactions beyond simple setData
    });

    // 2. Permission to call `transfer` on the ThankYouToken (LSP7)
    const tokenTransferSelector = ethers.Interface.getAbiCoder().decode(
        ['bytes4'],
        ethers.id('transfer(address,address,uint256,bool,bytes)').slice(0, 10)
    )[0];

    const lsp7Permissions = ERC725.encodePermissions({
        CALL: true, // To call transfer on the token contract
    });

    // (Optional) 3. Permission to call `transfer` on the BadgeNFT (LSP8)
    const nftTransferSelector = ethers.Interface.getAbiCoder().decode(
        ['bytes4'],
        ethers.id('transfer(address,address,bytes32,bool,bytes)').slice(0, 10)
    )[0];

    const lsp8Permissions = ERC725.encodePermissions({
        CALL: true, // To call transfer on the NFT contract
    });

    // --- Construct the KeyManager setDataBatch payload ---
    // ERC725.js utility to encode keys and values for KeyManager
    const erc725 = new ERC725(LSP6Schema, keyManagerAddress, provider, {});

    const permissionData = erc725.encodeData([
        // Grant general UP permissions to Agent
        {
            keyName: 'AddressPermissions:Permissions:<address>',
            dynamicKeyParts: AGENT_EOA_ADDRESS,
            value: upPermissions,
        },
        // Grant specific CALL permission for ThankYouToken.transfer
        {
            keyName: 'AddressPermissions:AllowedCalls:<address>',
            dynamicKeyParts: AGENT_EOA_ADDRESS,
            value: [
                {
                    address: THANK_YOU_TOKEN_ADDRESS,
                    interfaceId: '0x00000000', // No specific interface ID, function selector is enough
                    permissionType: '0x0000000000000000000000000000000000000000000000000000000000000001', // CALL
                    allowedFunctions: [tokenTransferSelector], //bytes4[]
                },
                 // (Optional) Add BadgeNFT transfer permission
                 ...(BADGE_NFT_ADDRESS ? [{
                    address: BADGE_NFT_ADDRESS,
                    interfaceId: '0x00000000',
                    permissionType: '0x0000000000000000000000000000000000000000000000000000000000000001', // CALL
                    allowedFunctions: [nftTransferSelector],
                }] : [])
            ],
        },
    ]);

    console.log("Proposing permissions...");
    try {
        const tx = await keyManager.connect(deployerWallet).setDataBatch(permissionData.keys, permissionData.values);
        await tx.wait();
        console.log('Permissions successfully set for agent EOA:');
        console.log(`  - Target UP: ${TARGET_UP_ADDRESS}`);
        console.log(`  - Agent EOA: ${AGENT_EOA_ADDRESS}`);
        console.log(`  - ThankYouToken: ${THANK_YOU_TOKEN_ADDRESS}`);
        if (BADGE_NFT_ADDRESS) console.log(`  - BadgeNFT: ${BADGE_NFT_ADDRESS}`);
        console.log(`  - Transaction hash: ${tx.hash}`);
    } catch (error) {
        console.error("Error setting permissions:", error);
    }
}

configureKeyManager().catch(console.error);