// contracts/ThankYouToken.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19; // Use a more recent compiler version

import "@lukso/lsp-smart-contracts/contracts/LSP7DigitalAsset/LSP7DigitalAsset.sol";

contract ThankYouToken is LSP7DigitalAsset {
    constructor(
        string memory name_,
        string memory symbol_,
        address owner_, // UP address of the creator/owner
        bool isNFT_ // Should be false for LSP7
    ) LSP7DigitalAsset(name_, symbol_, owner_, isNFT_) {}
}