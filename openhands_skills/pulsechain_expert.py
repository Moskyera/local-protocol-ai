"""
PulseChain Expert Skill for OpenHands
Dedicated expert for PulseChain (Ethereum hard fork).
Handles PLS-specific logic, PulseX DEX, deployment, known contracts, and differences from Ethereum.
Works together with solidity_expert for full EVM + PulseChain smart contract development.
"""

from logger import log
from openhands_skills.solidity_expert import solidity_expert

PULSECHAIN_KNOWN = {
    "chain_id": 369,
    "native": "PLS",
    "dex": "PulseX",
    "router": "0x98bf93ebf5c380C0e6Ae8e192A7e2AE08edAcc02",  # Example PulseX router (verify on explorer)
    "factory": "0x1715a3E4A142d8b6981311089951aD5e1b0e9e2",  # Example
    "notes": """
PULSECHAIN SPECIFICS:
- Gas paid in PLS (much cheaper than ETH)
- Use PulseX for liquidity/swaps (similar interface to Uniswap V2)
- Many Ethereum contracts have PulseChain deployments at similar or same addresses - always verify
- No certain Ethereum precompiles or slight differences in behavior
- Excellent for high-volume DeFi due to low fees
- For token launches: consider PLS liquidity pools on PulseX
"""
}

class PulseChainExpert:
    def __init__(self):
        self.chain = "pulsechain"

    def generate_pulsechain_contract(self, task: str) -> str:
        """Generate contract optimized for PulseChain using solidity_expert under the hood."""
        log.info("PulseChain Expert: Generating PulseChain-optimized contract")
        base = solidity_expert.write_solidity_contract(task, target_chain="pulsechain")
        # Add PulseChain specific header/notes
        header = f"""// PULSECHAIN OPTIMIZED
// Chain ID: {PULSECHAIN_KNOWN['chain_id']}
// Native: {PULSECHAIN_KNOWN['native']}
// DEX: {PULSECHAIN_KNOWN['dex']}
// Router: {PULSECHAIN_KNOWN['router']}
{PULSECHAIN_KNOWN['notes']}
"""
        return header + base

    def get_pulsechain_deployment_script(self, contract_name: str) -> str:
        """Hardhat/Foundry script tailored for PulseChain."""
        log.info("PulseChain Expert: Generating deployment script")
        return f"""// PulseChain deployment script for {contract_name}
// Use with: npx hardhat run scripts/deploy.js --network pulsechain
const {{ ethers }} = require("hardhat");

async function main() {{
  console.log("Deploying to PulseChain (chainId 369)...");
  const Contract = await ethers.getContractFactory("{contract_name}");
  const contract = await Contract.deploy();
  await contract.deployed();
  console.log("{contract_name} deployed to:", contract.address);
  console.log("Verify on PulseChain explorer and add liquidity on PulseX");
}}

main().catch((error) => {{
  console.error(error);
  process.exitCode = 1;
}});
"""

    def audit_for_pulsechain(self, code: str) -> str:
        """Run audit with PulseChain-specific checks."""
        log.info("PulseChain Expert: PulseChain-specific audit")
        base_audit = solidity_expert.audit_solidity(code, target_chain="pulsechain")
        extra = """
PULSECHAIN-SPECIFIC AUDIT NOTES:
- Ensure no hard-coded ETH amounts or Ethereum-specific assumptions
- Liquidity on PulseX: use correct factory/router addresses
- Test with very small PLS amounts (fees are tiny)
- Watch for any Ethereum-only precompile usage
- PLS is the native - treat it like ETH in value transfers
"""
        return base_audit + extra

    def suggest_tokenomics_with_market(self, token_name: str, market_data: dict = None) -> str:
        """Suggest tokenomics informed by market data (integrates with tool_hub if available)."""
        log.info("PulseChain Expert: Generating tokenomics suggestions")
        market_info = ""
        if market_data:
            market_info = f"\nMarket context used: {market_data}\n"
        
        return f"""Tokenomics suggestion for {token_name} on PulseChain:
- Total Supply: 1B (common for new launches)
- Liquidity: 10-20% on PulseX (use PLS pair)
- Team/Investors: 15-20% with 1-year vesting (use the vesting contract)
- Marketing: 5-10%
- Rewards/Staking: 20-30% (use staking contract)
- Community/Airdrop: 10-15%
{market_info}
PulseChain advantage: Low fees allow for more frequent small transactions and farming.
Always DYOR and consider current market conditions.
"""

# Register
pulsechain_expert = PulseChainExpert()
