import json
import datetime
import hashlib
from data_types import BlockType, TransactionType


BLOCK_REWARD = 50.0  # TOY


def _hash_dict(obj: dict | BlockType | TransactionType) -> str:
    """Hashes dict object."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


# Initial block - GENESIS.
GENESIS: BlockType = {
    "index": 1,
    "timestamp": "2025-01-01T00:00:00Z",
    "nonce": 1,
    "previous_hash": "0",
    "transactions": [],
}


class Blockchain:
    """
    Minimal, P2P-friendly blockchain core with a deterministic genesis block,
    PoW, a mempool, and longest-valid-chain replacement.
    """

    def __init__(self):
        self.chain: list[BlockType] = [GENESIS]
        self.mempool: dict[str, TransactionType] = {}

    def hash_block(self, block: BlockType) -> str:
        """Hashes block."""
        return _hash_dict(block)

    def _build_block(self, nonce: int, previous_hash: str, txs: list[TransactionType]) -> BlockType:
        """Builds a single block resource."""
        return {
            "index": len(self.chain) + 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "nonce": nonce,
            "previous_hash": previous_hash,
            "transactions": txs,
        }

    def get_latest_block(self) -> BlockType:
        """Gets latest block from chain."""
        return self.chain[-1]

    def mine_block(self, miner_address: str) -> BlockType:
        """
        Mine a block, or in other words - proof of work.

        btw, this method is responsible for building a new valid block and updating chain with it.
        """
        prev_hash = self.hash_block(self.get_latest_block())

        coinbase_tx: TransactionType = {
            "tx_id": f"coinbase-{len(self.chain)+1}",
            "sender": "COINBASE",
            "receiver": miner_address,
            "amount": BLOCK_REWARD,
            "type": "coinbase",
        }

        txs = [coinbase_tx] + list(self.mempool.values())

        block = self._build_block(nonce=1, previous_hash=prev_hash, txs=txs)
        while not self.hash_block(block).startswith("0000"):
            block["nonce"] += 1

        self.chain.append(block)
        self._remove_confirmed_from_mempool(block["transactions"])
        return block

    def is_chain_valid(self, chain: list[BlockType] | None = None) -> bool:
        """Validates full chain object."""

        chain = chain or self.chain
        if not chain or chain[0] != GENESIS:
            return False

        for i in range(1, len(chain)):
            prev, curr = chain[i-1], chain[i]
            if not _hash_dict(curr).startswith("0000") or curr["previous_hash"] != _hash_dict(prev):
                return False

        return True

    def validate_and_add_block(self, block: BlockType) -> bool:
        """Validates a single block resource, adds to chain if it's valid."""
        last = self.get_latest_block()
        if not self.hash_block(block).startswith("0000") or block["previous_hash"] != self.hash_block(last):
            return False

        self.chain.append(block)
        self._remove_confirmed_from_mempool(block["transactions"])
        return True

    def replace_chain(self, new_chain: list[BlockType]) -> bool:
        """Replaces full chain."""
        if not self.is_chain_valid(new_chain) or len(new_chain) <= len(self.chain):
            return False

        self.chain = [b for b in new_chain]
        confirmed_ids = {
            tx["tx_id"]
            for blk in self.chain
            for tx in blk["transactions"]
            if tx["type"] == "regular"
        }
        self.mempool = {tid: tx for tid, tx in self.mempool.items() if tid not in confirmed_ids}
        return True

    def add_transaction(self, tx: TransactionType) -> tuple[bool, TransactionType]:
        """
        Adds new transaction to mempool.
        :param tx: Transaction to add.
        :return: tuple -> (added, tx)

        added=True if new tx added to mempool; else False.
        """

        # Just minimal validation for transaction's amount
        try:
            amt = float(tx["amount"])
        except Exception as e:
            print(e)
            return False, tx

        if amt <= 0:
            return False, tx

        if not tx.get("sender") or not tx.get("receiver") or not tx.get("tx_id"):
            return False, tx

        if tx.get("type") not in ("regular", "coinbase"):
            return False, tx

        tx_id = tx["tx_id"]
        if tx_id in self.mempool:
            return False, self.mempool[tx_id]

        if tx["type"] == "coinbase":
            return False, tx

        self.mempool[tx_id] = tx
        return True, tx

    def _remove_confirmed_from_mempool(self, confirmed_txs: list[TransactionType]) -> None:
        """Removes confirmed transactions from mempool."""

        for t in confirmed_txs:
            if t["type"] == "regular":
                self.mempool.pop(t["tx_id"], None)
