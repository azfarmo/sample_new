// scripts/deploy.js
import { ethers } from 'hardhat'; // If using Hardhat
// Or: import { ethers } from 'ethers'; if using plain ethers with a provider
import fs from 'fs';
import path from 'path';
import 'dotenv/config';

const { DEPLOYER_PRIVATE_KEY, TARGET_UP_ADDRESS, TESTNET_RPC_URL } = process.env;

async function main() {
    if (!DEPLOYER_PRIVATE_KEY || !TARGET_UP_ADDRESS || !TESTNET_RPC_URL) {
        console.error("Missing DEPLOYER_PRIVATE_KEY, TARGET_UP_ADDRESS or TESTNET_RPC_URL in .env");
        process.exit(1);
    }

    const provider = new ethers.JsonRpcProvider(TESTNET_RPC_URL);
    const deployerWallet = new ethers.Wallet(DEPLOYER_PRIVATE_KEY, provider);
    console.log(`Deploying contracts with account: ${deployerWallet.address}`);

    const ThankYouTokenFactory = await ethers.getContractFactory("ThankYouToken", deployerWallet);
    const thankYouToken = await ThankYouTokenFactory.deploy("ThankYou Token", "TYT", TARGET_UP_ADDRESS, false);
    await thankYouToken.waitForDeployment();
    const tyTokenAddress = await thankYouToken.getAddress();
    console.log("ThankYouToken deployed to:", tyTokenAddress);

    const BadgeNFTFactory = await ethers.getContractFactory("BadgeNFT", deployerWallet);
    const badgeNFT = await BadgeNFTFactory.deploy("Engagement Badge", "EBDG", TARGET_UP_ADDRESS);
    await badgeNFT.waitForDeployment();
    const badgeNftAddress = await badgeNFT.getAddress();
    console.log("BadgeNFT deployed to:", badgeNftAddress);

    // Update .env file or a config file
    const envPath = path.resolve(__dirname, '../.env');
    let envContent = fs.readFileSync(envPath, { encoding: 'utf8' });
    envContent = envContent.replace(/THANK_YOU_TOKEN_ADDRESS=.*/g, `THANK_YOU_TOKEN_ADDRESS=${tyTokenAddress}`);
    envContent = envContent.replace(/BADGE_NFT_ADDRESS=.*/g, `BADGE_NFT_ADDRESS=${badgeNftAddress}`);
    fs.writeFileSync(envPath, envContent);
    console.log(".env file updated with new contract addresses.");

    // For frontend consumption, also update REACT_APP_ prefixed vars
    envContent = envContent.replace(/REACT_APP_THANK_YOU_TOKEN_ADDRESS=.*/g, `REACT_APP_THANK_YOU_TOKEN_ADDRESS=${tyTokenAddress}`);
    envContent = envContent.replace(/REACT_APP_BADGE_NFT_ADDRESS=.*/g, `REACT_APP_BADGE_NFT_ADDRESS=${badgeNftAddress}`);
    fs.writeFileSync(envPath, envContent);
    console.log(".env file updated with REACT_APP_ prefixed contract addresses.");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});