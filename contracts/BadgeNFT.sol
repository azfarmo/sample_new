// contracts/BadgeNFT.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19; // Use a more recent compiler version

import "@lukso/lsp-smart-contracts/contracts/LSP8IdentifiableDigitalAsset/LSP8IdentifiableDigitalAsset.sol";

contract BadgeNFT is LSP8IdentifiableDigitalAsset {
    constructor(
        string memory name_,
        string memory symbol_,
        address owner_ // UP address of the creator/owner
    ) LSP8IdentifiableDigitalAsset(name_, symbol_, owner_) {}

    // Optional: Add a mint function if you want the agent or UP owner to mint new badges
    // Ensure it's appropriately permissioned (e.g., only owner or a controller)
    function mint(address to, bytes32 tokenId, bool force, bytes memory data) external {
        // Add access control: e.g., require(msg.sender == owner() || /* agent has permission */, "Not authorized to mint");
        _mint(to, tokenId, force, data);
    }
}