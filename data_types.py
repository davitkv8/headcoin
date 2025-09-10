"""Common types shared between modules."""
from typing import TypedDict


class TransactionType(TypedDict):
    """Single transaction resource."""
    tx_id: str
    sender: str
    receiver: str
    amount: float
    type: str


class BlockType(TypedDict):
    """Single block resource."""
    index: int
    timestamp: str
    nonce: int
    previous_hash: str
    transactions: list[TransactionType]
