"""
Solidity Expert Skill for OpenHands - MAIN for EVM / PulseChain development
Ειδικός σε ανάπτυξη, audit, testing, gas optimization, security και deployment
smart contracts σε Ethereum και PulseChain (hard fork του Ethereum).

Υποστηρίζει:
- ERC20/721/1155, Vesting, Staking, Governance, Upgradeable (UUPS)
- PulseChain specifics: PLS native, PulseX DEX, chainId 369, lower fees
- Full project scaffolding (contract + tests + deployment scripts)
"""

from logger import log
import re
from typing import Literal

Chain = Literal["ethereum", "pulsechain"]

class SolidityExpert:
    def __init__(self):
        self.common_vulns = [
            "reentrancy", "integer overflow/underflow", "unchecked external calls",
            "access control", "front-running", "oracle manipulation", "flash loan attacks",
            "delegatecall", "selfdestruct", "tx.origin"
        ]
        self.pulsechain_notes = """
PULSECHAIN SPECIFICS (when target_chain="pulsechain"):
- Native token is PLS (not ETH) for gas payments
- Chain ID: 369
- Use PulseX for DEX interactions (similar to Uniswap but on PulseChain)
- Much lower fees than Ethereum mainnet
- Some precompiles and opcodes behave slightly differently
- Popular contracts often deployed at same addresses as Ethereum but verify
- For DeFi: check PulseX factory/router addresses
"""

    def write_solidity_contract(
        self, 
        task: str, 
        standards: list = None, 
        target_chain: Chain = "ethereum"
    ) -> str:
        """Γράφει ή επεκτείνει Solidity contract με υποστήριξη PulseChain."""
        log.info(f"Solidity Expert: Writing contract for task: {task} (chain={target_chain})")
        
        standards = standards or ["ERC20", "Ownable", "ReentrancyGuard"]
        native = "PLS" if target_chain == "pulsechain" else "ETH"
        dex = "PulseX" if target_chain == "pulsechain" else "Uniswap"
        
        base_code = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/// @title {self._extract_title(task)}
/// @notice {task}
/// @dev Generated for {target_chain.upper()} (EVM compatible)
/// @dev Native gas token: {native} | Preferred DEX: {dex}
contract {self._extract_contract_name(task)} is ERC20, Ownable, ReentrancyGuard, Pausable {{
    
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10**18;
    uint256 public constant VESTING_DURATION = 365 days;
    
    mapping(address => uint256) public vestedAmount;
    mapping(address => uint256) public vestingStart;
    
    constructor() ERC20("{self._extract_title(task)}", "TKN") Ownable(msg.sender) {{
        _mint(msg.sender, MAX_SUPPLY);
    }}
    
    // ========== VESTING (common in team/investor allocations) ==========
    function vestTokens(address beneficiary, uint256 amount) external onlyOwner {{
        require(vestedAmount[beneficiary] == 0, "Already vested");
        vestedAmount[beneficiary] = amount;
        vestingStart[beneficiary] = block.timestamp;
        _transfer(msg.sender, address(this), amount);
    }}
    
    function releaseVested() external nonReentrant {{
        uint256 vested = vestedAmount[msg.sender];
        require(vested > 0, "No vesting");
        
        uint256 elapsed = block.timestamp - vestingStart[msg.sender];
        uint256 releasable = (vested * elapsed) / VESTING_DURATION;
        releasable = releasable > vested ? vested : releasable;
        
        vestedAmount[msg.sender] -= releasable;
        _transfer(address(this), msg.sender, releasable);
    }}
    
    // ========== Custom logic based on task: {task} ==========
    function customFunction() external nonReentrant whenNotPaused {{
        // TODO: Implement business logic for: {task}
        // PulseChain tip: Use PLS for any native value transfers
    }}
    
    function pause() external onlyOwner {{ _pause(); }}
    function unpause() external onlyOwner {{ _unpause(); }}
}}
"""
        if target_chain == "pulsechain":
            base_code += self.pulsechain_notes
        
        print(f"🔷 Solidity Expert: Contract generated for {target_chain} with vesting + security patterns")
        return base_code

    def write_vesting_contract(self, task: str, target_chain: Chain = "ethereum") -> str:
        """Dedicated vesting contract (team, advisors, investors)."""
        log.info("Solidity Expert: Generating Vesting contract")
        native = "PLS" if target_chain == "pulsechain" else "ETH"
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// @title Vesting for {task} on {target_chain}
contract TokenVesting is Ownable, ReentrancyGuard {{
    IERC20 public immutable token;
    uint256 public constant VESTING_DURATION = 365 days;
    
    struct VestingSchedule {{
        uint256 totalAmount;
        uint256 released;
        uint256 start;
    }}
    
    mapping(address => VestingSchedule) public vestings;
    
    constructor(address _token) Ownable(msg.sender) {{
        token = IERC20(_token);
    }}
    
    function createVesting(address beneficiary, uint256 amount) external onlyOwner {{
        require(vestings[beneficiary].totalAmount == 0, "Already vested");
        vestings[beneficiary] = VestingSchedule(amount, 0, block.timestamp);
        token.transferFrom(msg.sender, address(this), amount);
    }}
    
    function release() external nonReentrant {{
        VestingSchedule storage schedule = vestings[msg.sender];
        uint256 vested = _vestedAmount(schedule);
        uint256 releasable = vested - schedule.released;
        require(releasable > 0, "Nothing to release");
        
        schedule.released += releasable;
        token.transfer(msg.sender, releasable);
    }}
    
    function _vestedAmount(VestingSchedule memory schedule) internal view returns (uint256) {{
        if (block.timestamp >= schedule.start + VESTING_DURATION) {{
            return schedule.totalAmount;
        }}
        return (schedule.totalAmount * (block.timestamp - schedule.start)) / VESTING_DURATION;
    }}
}}
"""

    def write_staking_contract(self, task: str, target_chain: Chain = "ethereum") -> str:
        """Staking / Farming contract with rewards."""
        log.info("Solidity Expert: Generating Staking contract")
        native = "PLS" if target_chain == "pulsechain" else "ETH"
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// @title Staking for {task} on {target_chain}
/// @dev Rewards in {native} or separate reward token. Low fees on PulseChain.
contract SimpleStaking is Ownable, ReentrancyGuard {{
    IERC20 public stakingToken;
    uint256 public rewardRate = 100; // adjustable
    
    mapping(address => uint256) public staked;
    mapping(address => uint256) public rewards;
    mapping(address => uint256) public lastUpdate;
    
    constructor(address _stakingToken) Ownable(msg.sender) {{
        stakingToken = IERC20(_stakingToken);
    }}
    
    function stake(uint256 amount) external nonReentrant {{
        _updateReward(msg.sender);
        stakingToken.transferFrom(msg.sender, address(this), amount);
        staked[msg.sender] += amount;
    }}
    
    function withdraw(uint256 amount) external nonReentrant {{
        _updateReward(msg.sender);
        staked[msg.sender] -= amount;
        stakingToken.transfer(msg.sender, amount);
    }}
    
    function claimReward() external nonReentrant {{
        _updateReward(msg.sender);
        uint256 reward = rewards[msg.sender];
        rewards[msg.sender] = 0;
        payable(msg.sender).transfer(reward); // or reward token
    }}
    
    function _updateReward(address account) internal {{
        if (staked[account] > 0) {{
            uint256 time = block.timestamp - lastUpdate[account];
            rewards[account] += (staked[account] * rewardRate * time) / 1e18;
        }}
        lastUpdate[account] = block.timestamp;
    }}
}}
"""

    def write_upgradeable_contract(self, task: str, target_chain: Chain = "ethereum") -> str:
        """Upgradeable contract using UUPS pattern (recommended for long-term)."""
        log.info("Solidity Expert: Generating Upgradeable (UUPS) contract")
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

/// @title Upgradeable {task} for {target_chain}
contract UpgradeableToken is Initializable, ERC20Upgradeable, OwnableUpgradeable, UUPSUpgradeable {{
    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {{
        _disableInitializers();
    }}
    
    function initialize() initializer public {{
        __ERC20_init("Token", "TKN");
        __Ownable_init(msg.sender);
        __UUPSUpgradeable_init();
        _mint(msg.sender, 1_000_000_000 * 10**18);
    }}
    
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {{}}
}}
"""

    def write_governance_contract(self, task: str, target_chain: Chain = "ethereum") -> str:
        """Governance token with voting (ERC20Votes)."""
        log.info("Solidity Expert: Generating Governance contract")
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title Governance Token for {task} on {target_chain}
contract GovernanceToken is ERC20, ERC20Votes, Ownable {{
    constructor() ERC20("GovToken", "GOV") Ownable(msg.sender) {{
        _mint(msg.sender, 1_000_000 * 10**18);
    }}
    
    // The rest of the ERC20Votes boilerplate (checkpoints etc.)
    function _update(address from, address to, uint256 value) internal override(ERC20, ERC20Votes) {{
        super._update(from, to, value);
    }}
    
    function nonces(address owner) public view override returns (uint256) {{
        return super.nonces(owner);
    }}
}}
"""

    def audit_solidity(self, code: str, target_chain: Chain = "ethereum") -> str:
        """Πλήρες security + chain-specific audit."""
        log.info(f"Solidity Expert: Running audit (chain={target_chain})")
        
        findings = []
        code_lower = code.lower()

        # NO SCORE. This used to start at 10.0 and only come down for two
        # substring tests, so it answered "Score: 10.0/10, Findings: (none)" for
        # a contract with reentrancy AND an unprotected drainAll() — and for an
        # empty string, and for a line of Python. The orchestrator then
        # substituted this for the real reviewer output. A number nobody
        # computed is worse than no number: it is read as a verdict.
        if not code.strip():
            return "❌ Δεν δόθηκε κώδικας — δεν έγινε κανένας έλεγχος."
        if "pragma solidity" not in code_lower and "contract " not in code_lower:
            return ("❌ Αυτό δεν μοιάζει με Solidity — δεν έγινε έλεγχος. "
                    "Ο έλεγχος αναγνωρίζει μόνο συμβόλαια Solidity.")

        # Common EVM checks. Heuristics, not an audit — see the header below.
        if "tx.origin" in code_lower:
            findings.append("❌ CRITICAL: Use of tx.origin")
        # State written AFTER an external call is the reentrancy shape. Checking
        # for "require" anywhere in the FILE disarmed this entirely: the
        # vulnerable contract contained require(ok) two lines later.
        for m in re.finditer(r"\.call\{[^}]*\}\(|\.call\(", code_lower):
            tail = code_lower[m.end():m.end() + 400]
            if re.search(r"\w+\s*\[[^\]]*\]\s*=|\w+\s*=\s*0\s*;", tail):
                findings.append("❌ CRITICAL: state updated AFTER an external "
                                "call — reentrancy shape")
                break
        if re.search(r"\.call\{|\.call\(", code_lower) and                 not re.search(r"nonreentrant|reentrancyguard", code_lower):
            findings.append("⚠️ HIGH: external call with no reentrancy guard")
        # Value-moving functions with no access control at all.
        for m in re.finditer(r"function\s+(\w+)[^{]*\{", code):
            head = m.group(0)
            body = code[m.end():m.end() + 500]
            moves = re.search(r"\.transfer\(|\.send\(|\.call\{", body)
            guarded = re.search(r"onlyowner|require\s*\(\s*msg\.sender|modifier",
                                head.lower() + body.lower())
            if moves and not guarded:
                findings.append(f"❌ CRITICAL: {m.group(1)}() moves funds with "
                                f"no access control")
        
        # PulseChain specific
        if target_chain == "pulsechain":
            if "block.timestamp" in code_lower:
                findings.append("ℹ️ PulseChain: block.timestamp is still manipulable but less issue due to lower fees")
            findings.append("✅ PulseChain: Remember gas is paid in PLS, much cheaper")
        
        if "reentrancyguard" in code_lower:
            findings.append("✅ Good: ReentrancyGuard used")
        
        audit = f"""
🔐 SOLIDITY ΠΡΟ-ΕΛΕΓΧΟΣ ({target_chain.upper()})
⚠️ Αυτό ΔΕΝ είναι audit. Είναι ένας ρηχός έλεγχος με regex, που πιάνει μόνο
   γνωστά μοτίβα. Η απουσία ευρημάτων ΔΕΝ σημαίνει ότι ο κώδικας είναι ασφαλής.

Ευρήματα ({len(findings)}):
{chr(10).join(findings) if findings else "  (κανένα από τα μοτίβα που ξέρει να ψάχνει)"}

PulseChain Notes (if applicable):
- Deploy on chainId 369
- Use PulseX router for swaps
- Test with small PLS amounts first
- Many Ethereum tools (Hardhat, Foundry) work with --network pulsechain

Recommended: Slither, MythX, manual review + formal verification for high value.
"""
        print(audit)
        return audit

    def write_tests(self, contract_code: str, target_chain: Chain = "ethereum") -> str:
        """Foundry tests with chain awareness."""
        log.info("Solidity Expert: Generating tests")
        native_symbol = "PLS" if target_chain == "pulsechain" else "ETH"
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

contract ContractTest is Test {{
    // Deploy on {target_chain}
    function setUp() public {{
        vm.deal(msg.sender, 1000 ether); // works for both ETH and PLS
    }}
    
    function test_{native_symbol}_NativeHandling() public {{
        // Test native token handling for {target_chain}
    }}
}}
"""

    def generate_full_project(self, task: str, target_chain: Chain = "ethereum") -> dict:
        """Παράγει ολόκληρο project scaffold (contract + tests + deploy script)."""
        log.info(f"Solidity Expert: Generating FULL project for {target_chain}")
        
        contract = self.write_solidity_contract(task, target_chain=target_chain)
        tests = self.write_tests(contract, target_chain=target_chain)
        audit = self.audit_solidity(contract, target_chain=target_chain)
        
        deploy_script = f"""// Hardhat/Foundry deploy script for {target_chain}
const {{ ethers }} = require("hardhat");

async function main() {{
  const Contract = await ethers.getContractFactory("YourContract");
  const contract = await Contract.deploy();
  await contract.deployed();
  console.log("Deployed to:", contract.address);
  console.log("Network:", "{target_chain}");
}}
"""
        
        return {
            "contract": contract,
            "tests": tests,
            "audit": audit,
            "deploy": deploy_script,
            "chain": target_chain,
            "notes": "Use foundry or hardhat. For PulseChain configure RPC to a PulseChain node."
        }

    def _extract_contract_name(self, task: str) -> str:
        words = re.findall(r'\b[A-Z][a-zA-Z0-9]*\b', task)
        return words[0] if words else "CustomToken"

    def _extract_title(self, task: str) -> str:
        return task.split()[0].upper() if task else "TOKEN"

    def write_advanced_defi_pattern(self, pattern: str, task: str, target_chain: Chain = "ethereum") -> str:
        """Advanced DeFi patterns: flashloan, liquidity provision, simple lending, yield farming stub."""
        log.info(f"Solidity Expert: Advanced DeFi pattern {pattern} for {task}")
        native = "PLS" if target_chain == "pulsechain" else "ETH"
        dex = "PulseX" if target_chain == "pulsechain" else "Uniswap"
        
        if "flash" in pattern.lower():
            return f"""// Advanced Flash Loan for {task} on {target_chain}
// Perfect for arbitrage on {dex}. Very cheap on PulseChain.
contract FlashLoan{self._extract_contract_name(task)} {{
    // Implement IERC3156FlashBorrower
    // Borrow {native}, do logic, repay + fee
}}
"""
        elif "liquidity" in pattern.lower() or "pool" in pattern.lower():
            return f"""// Liquidity Pool / AMM for {task} on {target_chain}
// Pair with {dex} factory. Provide {native} + token liquidity.
"""
        elif "lending" in pattern.lower():
            return f"""// Simple Lending Pool stub for {task} on {target_chain}
// Collateral, borrow, interest. Market data can set rates.
"""
        else:
            return f"// Custom advanced DeFi: {pattern} for {task} on {target_chain}\n// Integrate market data via tool_hub for dynamic parameters."

# Register as the main expert for OpenHands Solidity/PulseChain work
solidity_expert = SolidityExpert()
