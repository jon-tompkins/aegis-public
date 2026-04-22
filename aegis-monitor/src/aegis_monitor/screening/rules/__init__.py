"""Tier 1 detectors. Each rule lives in its own module."""

from .approve_to_eoa import ApproveToEoaRule
from .fresh_approval_new_contract import FreshApprovalNewContractRule
from .transfer_from import TransferFromUnauthorizedRule
from .unlimited_approval import UnlimitedApprovalRule

__all__ = [
    "ApproveToEoaRule",
    "FreshApprovalNewContractRule",
    "TransferFromUnauthorizedRule",
    "UnlimitedApprovalRule",
]
