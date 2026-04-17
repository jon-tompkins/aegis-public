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
    )
    
    print(json.dumps({
        "tx_hash": args.tx_hash,
        "overall_flag": Flag(result.overall_flag).name,
        "max_confidence_bp": result.max_confidence_bp,
        "detections": [asdict(d) for d in result.detections]
    }, indent=2))
