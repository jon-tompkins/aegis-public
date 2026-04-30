"""Arweave audit trail — uploader interface + outbox-driven writer task.

The hot path (rule-hit → sign → DB insert → WS broadcast) does not block
on Arweave. After the row lands in `flags` with `arweave_tx_id IS NULL`,
the writer task drains the outbox queue (which is the
`ix_flags_arweave_pending` partial index, not a separate table) and
publishes each canonical body to Arweave via an `ArweaveUploader`.

See `docs/specs/arweave-flag-storage.md` for the full design.
"""

from .uploader import ArweaveUploader, DryRunUploader, Tag, build_flag_tags
from .writer import ArweaveWriter

__all__ = [
    "ArweaveUploader",
    "ArweaveWriter",
    "DryRunUploader",
    "Tag",
    "build_flag_tags",
]
