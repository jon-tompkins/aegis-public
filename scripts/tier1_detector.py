#!/usr/bin/env python3
"""
tier1_detector.py — Aegis Tier 1 (rule-based) screening prototype.

Implements the Tier 1 detection rules from docs/specs/hack-taxonomy.md.
These rules run in <10ms and flag transactions for WATCH or ESCALATE.

Usage:
    python3 tier1_detector.py --tx-hash 0x... --chain ethereum
    python3 tier1_detector.py --address 0x... --tvlamount 100000000 --validator-count 4
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from enum import IntEnum
from typing import Optional


class Flag(IntEnum):
    CLEAR = 0
    WATCH = 1
    ESCALATE = 2
    PAUSE = 3
    REJECT = 4


@dataclass
class DetectionResult:
    rule: str
    flag: Flag
    confidence_bp: int  # 0-10000 basis points
    description: str
    rule_id: str


@dataclass
class ScreeningResult:
    overall_flag: Flag
    max_confidence_bp: int
    detections: list[DetectionResult]
    block_number: Optional[int] = None
    block_timestamp: Optional[int] = None


# ─── Tier 1 Rules ────────────────────────────────────────────────────────────

def check_bridge_validator_count(
    validator_count: int,
    tvl_usd: float,
    chain: str = "ethereum"
) -> Optional[DetectionResult]:
    """
    Bridge validator count < 8 for TVL > $50M → WATCH
    Bridge validator count < 5 for any TVL → ESCALATE
    """
    if tvl_usd > 50_000_000:
        if validator_count < 5:
            return DetectionResult(
                rule="bridge_validator_count",
                flag=Flag.ESCALATE,
                confidence_bp=8500,
                description=f"Bridge has only {validator_count} validators for ${tvl_usd/1e6:.1f}M TVL — high concentration risk",
                rule_id="T1-001"
            )
        elif validator_count < 8:
            return DetectionResult(
                rule="bridge_validator_count",
                flag=Flag.WATCH,
                confidence_bp=6000,
                description=f"Bridge has only {validator_count} validators for ${tvl_usd/1e6:.1f}M TVL",
                rule_id="T1-001"
            )
    return None


def check_price_deviation(
    current_price: float,
    moving_average: float,
    lookback_hours: int = 24
) -> Optional[DetectionResult]:
    """
    Collateral price deviation > 20x 24h moving average → ESCALATE
    Collateral price deviation > 5x → WATCH
    """
    if moving_average <= 0:
        return None
    
    ratio = current_price / moving_average
    
    if ratio > 20:
        return DetectionResult(
            rule="price_deviation",
            flag=Flag.ESCALATE,
            confidence_bp=9000,
            description=f"Price {ratio:.1f}x higher than {lookback_hours}h moving average — likely oracle manipulation",
            rule_id="T1-002"
        )
    elif ratio > 5:
        return DetectionResult(
            rule="price_deviation",
            flag=Flag.WATCH,
            confidence_bp=5000,
            description=f"Price {ratio:.1f}x higher than {lookback_hours}h moving average",
            rule_id="T1-002"
        )
    return None


def check_large_mint_dex_exit(
    mint_amount_usd: float,
    has_dex_swap: bool,
    dex_destination: str,
    mint_token: str,
    tx_hash: str = ""
) -> Optional[DetectionResult]:
    """
    Single transaction mint + DEX exit → ESCALATE if > $1M stablecoin
    """
    if mint_amount_usd > 1_000_000 and has_dex_swap:
        return DetectionResult(
            rule="mint_dex_exit",
            flag=Flag.ESCALATE,
            confidence_bp=8000,
            description=f"${mint_amount_usd/1e6:.2f}M {mint_token} minted and swapped on DEX in same transaction",
            rule_id="T1-003"
        )
    elif mint_amount_usd > 100_000 and has_dex_swap:
        return DetectionResult(
            rule="mint_dex_exit",
            flag=Flag.WATCH,
            confidence_bp=5000,
            description=f"${mint_amount_usd/1e3:.0f}k {mint_token} minted + DEX swap — unusual pattern",
            rule_id="T1-003"
        )
    return None


def check_admin_key_sole_signer(
    is_admin_key_signing: bool,
    has_timelock: bool,
    contract_type: str
) -> Optional[DetectionResult]:
    """
    Admin key as sole signer with no timelock on bridge/lending protocol → WATCH
    """
    if is_admin_key_signing and not has_timelock and contract_type in ("bridge", "lending"):
        return DetectionResult(
            rule="admin_key_sole_signer",
            flag=Flag.WATCH,
            confidence_bp=7000,
            description=f"Admin key signing without timelock on {contract_type} contract",
            rule_id="T1-004"
        )
    return None


def check_whitelist_not_revoked(
    whitelist_entries: int,
    active_entries: int,
    last_rotation_hours: int
) -> Optional[DetectionResult]:
    """
    Bridge whitelist entries not revoked after use; unused entries after 30+ days → WATCH
    """
    unused = whitelist_entries - active_entries
    if unused > 0 and last_rotation_hours > 720:  # 30 days
        return DetectionResult(
            rule="whitelist_not_revoked",
            flag=Flag.WATCH,
            confidence_bp=7500,
            description=f"{unused} bridge whitelist entries unused for {last_rotation_hours//24} days — Ronin pattern",
            rule_id="T1-005"
        )
    return None


def check_flash_loan_multipool(
    pool_interactions: int,
    has_governance_action: bool,
    has_swap: bool
) -> Optional[DetectionResult]:
    """
    Single transaction with >3 DEX pools + governance action → WATCH
    Classic flash loan pattern
    """
    if pool_interactions > 3 and (has_governance_action or has_swap):
        return DetectionResult(
            rule="flash_loan_multipool",
            flag=Flag.WATCH,
            confidence_bp=6000,
            description=f"Single tx with {pool_interactions} pool interactions + governance/swap — possible flash loan attack",
            rule_id="T1-006"
        )
    return None


def check_phantom_deposit(
    bridge_deposit_declared_usd: float,
    bridge_deposit_actual_usd: float,
    tolerance_bp: int = 100
) -> Optional[DetectionResult]:
    """
    Bridge: declared deposit value != actual value (Qubit pattern).
    A discrepancy larger than `tolerance_bp` (default 1%) is almost always
    a phantom-deposit exploit.
    """
    if bridge_deposit_declared_usd <= 0:
        return None

    # If actual is effectively zero but declared is non-trivial, that's the
    # canonical Qubit attack shape.
    if bridge_deposit_actual_usd < 1 and bridge_deposit_declared_usd > 100:
        return DetectionResult(
            rule="phantom_deposit",
            flag=Flag.ESCALATE,
            confidence_bp=9500,
            description=(
                f"Bridge declared ${bridge_deposit_declared_usd:,.0f} deposit "
                f"but actual value ~${bridge_deposit_actual_usd:.2f} — Qubit pattern"
            ),
            rule_id="T1-007"
        )

    # General discrepancy check
    diff_bp = int(
        abs(bridge_deposit_declared_usd - bridge_deposit_actual_usd)
        / bridge_deposit_declared_usd * 10_000
    )
    if diff_bp > tolerance_bp:
        return DetectionResult(
            rule="phantom_deposit",
            flag=Flag.WATCH,
            confidence_bp=min(5000 + diff_bp, 9500),
            description=(
                f"Bridge deposit declared/actual differ by {diff_bp} bp "
                f"(${bridge_deposit_declared_usd:,.0f} vs ${bridge_deposit_actual_usd:,.0f})"
            ),
            rule_id="T1-007"
        )
    return None


def check_large_mint_from_eoa(
    mint_amount_usd: float,
    minter_is_contract: bool,
    has_mint_cap: bool,
    token: str = ""
) -> Optional[DetectionResult]:
    """
    Large token mint from an EOA (not a contract) with no mint cap.
    Captures Resolv-Labs / IoTeX patterns: key-compromised admin minting
    free tokens via a direct EOA call.
    """
    if minter_is_contract:
        return None

    if mint_amount_usd > 10_000_000 and not has_mint_cap:
        return DetectionResult(
            rule="large_mint_from_eoa",
            flag=Flag.ESCALATE,
            confidence_bp=9000,
            description=(
                f"${mint_amount_usd/1e6:.1f}M {token} minted from EOA with no mint cap — "
                "key-compromise shape"
            ),
            rule_id="T1-008"
        )
    if mint_amount_usd > 1_000_000 and not has_mint_cap:
        return DetectionResult(
            rule="large_mint_from_eoa",
            flag=Flag.WATCH,
            confidence_bp=7000,
            description=(
                f"${mint_amount_usd/1e3:.0f}k {token} minted from EOA with no mint cap"
            ),
            rule_id="T1-008"
        )
    return None


def check_privileged_cross_chain_relay(
    caller_is_cross_chain_relay: bool,
    target_is_privileged_data_contract: bool,
    selector_hex: str = ""
) -> Optional[DetectionResult]:
    """
    Cross-chain relay calling a privileged data contract (Poly Network pattern).
    Also flags known sighash-collision selectors.
    """
    # Selectors historically abused via hash collision on Poly Network.
    KNOWN_COLLISION_SELECTORS = {
        "f1121318",  # sighash-collision PoC
        "41973cd9",  # legacy cross-chain manager (Poly pattern family)
    }

    if caller_is_cross_chain_relay and target_is_privileged_data_contract:
        return DetectionResult(
            rule="privileged_cross_chain_relay",
            flag=Flag.ESCALATE,
            confidence_bp=9000,
            description=(
                "Cross-chain relay called a privileged data contract — Poly Network pattern"
            ),
            rule_id="T1-009"
        )

    if selector_hex.lower().lstrip("0x") in KNOWN_COLLISION_SELECTORS:
        return DetectionResult(
            rule="privileged_cross_chain_relay",
            flag=Flag.WATCH,
            confidence_bp=7500,
            description=f"Selector 0x{selector_hex} matches known collision pattern",
            rule_id="T1-009"
        )
    return None


def check_eoa_upgrade_or_param_change(
    is_upgrade_or_param_change: bool,
    signer_is_multisig: bool,
    has_timelock: bool,
    contract_type: str = ""
) -> Optional[DetectionResult]:
    """
    Contract upgrade or critical param change executed directly by an EOA
    with no multisig and no timelock. Strong admin-key-compromise indicator.
    """
    if not is_upgrade_or_param_change:
        return None
    if signer_is_multisig and has_timelock:
        return None

    severity = Flag.ESCALATE if (not signer_is_multisig and not has_timelock) else Flag.WATCH
    conf = 8500 if severity == Flag.ESCALATE else 6500
    return DetectionResult(
        rule="eoa_upgrade_or_param_change",
        flag=severity,
        confidence_bp=conf,
        description=(
            f"{contract_type or 'contract'} upgrade / param change — "
            f"multisig={signer_is_multisig}, timelock={has_timelock}"
        ),
        rule_id="T1-010"
    )


# ─── Main Screener ────────────────────────────────────────────────────────────

def screen(
    chain: str = "ethereum",
    tx_hash: str = "",
    # Bridge params
    validator_count: int = 0,
    tvl_usd: float = 0,
    whitelist_entries: int = 0,
    active_whitelist_entries: int = 0,
    last_whitelist_rotation_hours: int = 0,
    # Price params
    current_price: float = 0,
    price_ma24h: float = 0,
    # Transaction params
    mint_amount_usd: float = 0,
    mint_token: str = "",
    has_dex_swap: bool = False,
    dex_destination: str = "",
    pool_interactions: int = 0,
    has_governance_action: bool = False,
    # Contract params
    contract_type: str = "",
    is_admin_key_signing: bool = False,
    has_timelock: bool = False,
    # Phantom-deposit (T1-007)
    bridge_deposit_declared_usd: float = 0,
    bridge_deposit_actual_usd: float = 0,
    # Large mint from EOA (T1-008)
    minter_is_contract: bool = True,
    has_mint_cap: bool = True,
    # Cross-chain relay (T1-009)
    caller_is_cross_chain_relay: bool = False,
    target_is_privileged_data_contract: bool = False,
    selector_hex: str = "",
    # EOA upgrade / param change (T1-010)
    is_upgrade_or_param_change: bool = False,
    signer_is_multisig: bool = True,
) -> ScreeningResult:
    """
    Run all Tier 1 rules. Returns highest-flag result.
    """
    detections = []

    rules = [
        check_bridge_validator_count(validator_count, tvl_usd, chain),
        check_price_deviation(current_price, price_ma24h),
        check_large_mint_dex_exit(mint_amount_usd, has_dex_swap, dex_destination, mint_token, tx_hash),
        check_admin_key_sole_signer(is_admin_key_signing, has_timelock, contract_type),
        check_whitelist_not_revoked(whitelist_entries, active_whitelist_entries, last_whitelist_rotation_hours),
        check_flash_loan_multipool(pool_interactions, has_governance_action, has_dex_swap),
        check_phantom_deposit(bridge_deposit_declared_usd, bridge_deposit_actual_usd),
        check_large_mint_from_eoa(mint_amount_usd, minter_is_contract, has_mint_cap, mint_token),
        check_privileged_cross_chain_relay(
            caller_is_cross_chain_relay, target_is_privileged_data_contract, selector_hex
        ),
        check_eoa_upgrade_or_param_change(
            is_upgrade_or_param_change, signer_is_multisig, has_timelock, contract_type
        ),
    ]
    
    for r in rules:
        if r:
            detections.append(r)
    
    if not detections:
        return ScreeningResult(
            overall_flag=Flag.CLEAR,
            max_confidence_bp=0,
            detections=[]
        )
    
    # Return highest severity
    highest = max(detections, key=lambda d: (d.flag, d.confidence_bp))
    max_conf = max(d.confidence_bp for d in detections)
    
    return ScreeningResult(
        overall_flag=highest.flag,
        max_confidence_bp=max_conf,
        detections=detections
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis Tier 1 Screening Rules")
    parser.add_argument("--tx-hash", default="", help="Transaction hash")
    parser.add_argument("--chain", default="ethereum", help="Chain name")
    
    # Bridge args
    parser.add_argument("--validator-count", type=int, default=0)
    parser.add_argument("--tvl-usd", type=float, default=0)
    parser.add_argument("--whitelist-entries", type=int, default=0)
    parser.add_argument("--active-whitelist-entries", type=int, default=0)
    parser.add_argument("--last-whitelist-rotation-hours", type=int, default=0)
    
    # Price args
    parser.add_argument("--current-price", type=float, default=0)
    parser.add_argument("--price-ma24h", type=float, default=0)
    
    # TX args
    parser.add_argument("--mint-amount-usd", type=float, default=0)
    parser.add_argument("--mint-token", default="")
    parser.add_argument("--has-dex-swap", action="store_true")
    parser.add_argument("--dex-destination", default="")
    parser.add_argument("--pool-interactions", type=int, default=0)
    parser.add_argument("--has-governance-action", action="store_true")
    
    # Contract args
    parser.add_argument("--contract-type", default="")
    parser.add_argument("--is-admin-key-signing", action="store_true")
    parser.add_argument("--has-timelock", action="store_true")

    # Phantom-deposit (T1-007)
    parser.add_argument("--bridge-deposit-declared-usd", type=float, default=0)
    parser.add_argument("--bridge-deposit-actual-usd", type=float, default=0)

    # Large mint from EOA (T1-008)
    parser.add_argument("--minter-is-contract", action="store_true", default=True)
    parser.add_argument("--minter-is-eoa", dest="minter_is_contract", action="store_false")
    parser.add_argument("--has-mint-cap", action="store_true", default=True)
    parser.add_argument("--no-mint-cap", dest="has_mint_cap", action="store_false")

    # Cross-chain relay (T1-009)
    parser.add_argument("--caller-is-cross-chain-relay", action="store_true")
    parser.add_argument("--target-is-privileged-data-contract", action="store_true")
    parser.add_argument("--selector-hex", default="")

    # EOA upgrade / param change (T1-010)
    parser.add_argument("--is-upgrade-or-param-change", action="store_true")
    parser.add_argument("--signer-is-multisig", action="store_true", default=True)
    parser.add_argument("--signer-is-eoa", dest="signer_is_multisig", action="store_false")

    args = parser.parse_args()
    
    result = screen(
        chain=args.chain,
        tx_hash=args.tx_hash,
        validator_count=args.validator_count,
        tvl_usd=args.tvl_usd,
        whitelist_entries=args.whitelist_entries,
        active_whitelist_entries=args.active_whitelist_entries,
        last_whitelist_rotation_hours=args.last_whitelist_rotation_hours,
        current_price=args.current_price,
        price_ma24h=args.price_ma24h,
        mint_amount_usd=args.mint_amount_usd,
        mint_token=args.mint_token,
        has_dex_swap=args.has_dex_swap,
        dex_destination=args.dex_destination,
        pool_interactions=args.pool_interactions,
        has_governance_action=args.has_governance_action,
        contract_type=args.contract_type,
        is_admin_key_signing=args.is_admin_key_signing,
        has_timelock=args.has_timelock,
        bridge_deposit_declared_usd=args.bridge_deposit_declared_usd,
        bridge_deposit_actual_usd=args.bridge_deposit_actual_usd,
        minter_is_contract=args.minter_is_contract,
        has_mint_cap=args.has_mint_cap,
        caller_is_cross_chain_relay=args.caller_is_cross_chain_relay,
        target_is_privileged_data_contract=args.target_is_privileged_data_contract,
        selector_hex=args.selector_hex,
        is_upgrade_or_param_change=args.is_upgrade_or_param_change,
        signer_is_multisig=args.signer_is_multisig,
    )
    
    print(json.dumps({
        "tx_hash": args.tx_hash,
        "overall_flag": Flag(result.overall_flag).name,
        "max_confidence_bp": result.max_confidence_bp,
        "detections": [asdict(d) for d in result.detections]
    }, indent=2))
