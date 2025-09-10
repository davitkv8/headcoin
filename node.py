import socket
import threading
import json
import uuid
from enum import Enum
from typing import Any, cast
from data_types import TransactionType, BlockType
from blockchain_core import Blockchain


class CommandEnum(Enum):
    CHAIN = 'CHAIN'
    MEMPOOL = 'MEMPOOL'
    MINE = 'MINE'
    TX = 'TX'


RENDEZVOUS = ('127.0.0.1', 55555)


class Node:
    """
    UDP-based P2P blockchain node with rendezvous-driven peer discovery, gossip
    propagation for transactions and blocks, and startup/full reorg syncing.
    """

    def __init__(self):
        self.blockchain = Blockchain()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 0))
        self.port = self.sock.getsockname()[1]
        self.address = str(uuid.uuid4()).replace('-', '')
        self.peers: list[tuple[str, int]] = []
        self.seen_tx_ids: set[str] = set()

        print(f"My address: {self.address}  UDP:{self.port}")

    def connect(self):
        """Registers/connects current node to rendezvous. sets separate thread for main listener."""
        self.sock.sendto(b'0', RENDEZVOUS)
        threading.Thread(target=self.listen, daemon=True).start()
        self.repl()

    def _send(self, msg: dict[str, Any], peer: tuple[str, int]) -> None:
        """Sends message to specific peer."""
        self.sock.sendto(json.dumps(msg).encode(), peer)

    def _broadcast(self, msg: dict[str, Any], except_peer: tuple[str, int] | None = None) -> None:
        """Broadcasts message all over the P2P network."""
        raw = json.dumps(msg).encode()
        for peer in self.peers:
            if except_peer and peer == except_peer:
                continue
            self.sock.sendto(raw, peer)

    def _request_full_chain_from(self, peer: tuple[str, int]) -> None:
        """Requests full chain from specific peer of P2P network."""
        self._send({"type": "REQ_CHAIN"}, peer)

    def _startup_sync(self):
        """Synchronization for newly registered nodes. It's used to pull the chain from already existing nodes."""
        if self.peers:
            self._request_full_chain_from(self.peers[0])

    def listen(self):
        """Main listener method. Usage: usually, all the nodes are processing its listener in a separate thread."""
        while True:
            data, addr = self.sock.recvfrom(65536)
            msg = data.decode()

            # peers list from rendezvous
            if msg.startswith("PEERS"):
                _, *peer_addresses = msg.split()

                new_peers = []
                for s in peer_addresses:
                    ip, port = s.split(":")
                    peer = (ip, int(port))
                    if peer != ("127.0.0.1", self.port) and peer not in self.peers:
                        new_peers.append(peer)

                if new_peers:
                    self.peers.extend(new_peers)
                    print("Updated peers:", self.peers)
                    self._startup_sync()

                continue

            try:
                payload = json.loads(msg)

                if payload["type"] == "new_transaction":
                    tx = cast(TransactionType, payload["tx"])
                    tx_id = tx["tx_id"]
                    ttl = int(payload.get("ttl", 4))

                    if not tx_id or tx_id in self.seen_tx_ids:
                        continue

                    self.seen_tx_ids.add(tx_id)
                    added, _ = self.blockchain.add_transaction(tx)
                    if added:
                        print(f"💸 TX added to mempool: {tx}")

                    if ttl > 0:
                        self._broadcast({"type": "new_transaction", "tx": tx, "ttl": ttl - 1}, except_peer=addr)

                elif payload["type"] == "new_block":
                    block = cast(BlockType, payload["block"])
                    if self.blockchain.validate_and_add_block(block):
                        print(f"\n📦 Added block {block['index']} (txs={len(block['transactions'])}) || {block}")
                    else:
                        self._request_full_chain_from(addr)

                elif payload["type"] == "REQ_CHAIN":
                    self._send({"type": "FULL_CHAIN", "chain": self.blockchain.chain}, addr)

                elif payload["type"] == "FULL_CHAIN":
                    remote = payload["chain"]
                    if self.blockchain.replace_chain(remote):
                        print(f"\n🔁 Chain replaced. Height={len(self.blockchain.chain)}")

            except Exception as e:
                print("Decode error:", e)

    def repl(self):
        """Print loop..."""
        while True:
            cmd = input("--> ").strip()
            if not cmd:
                continue
            head, *rest = cmd.split()

            if head.upper() == CommandEnum.CHAIN.value:
                print(json.dumps(self.blockchain.chain, indent=2))

            elif head.upper() == CommandEnum.MEMPOOL.value:
                print(json.dumps(list(self.blockchain.mempool.values()), indent=2))

            elif head.upper() == CommandEnum.MINE.value:
                blk = self.blockchain.mine_block(self.address)
                print(f"⛏️  Mined block {blk['index']} (txs={len(blk['transactions'])})")
                self._broadcast({"type": "new_block", "block": blk})

            elif head.upper() == CommandEnum.TX.value:
                # TX <receiver> <amount>  (sender is me)
                if len(rest) != 2:
                    print("Usage: TX <receiver> <amount>")
                    continue

                receiver, amount = rest
                tx: TransactionType = {
                    "tx_id": uuid.uuid4().hex,
                    "sender": self.address,
                    "receiver": receiver,
                    "amount": float(amount),
                    "type": "regular",
                }
                added, _ = self.blockchain.add_transaction(tx)

                if added:
                    self.seen_tx_ids.add(tx["tx_id"])
                    self._broadcast({"type": "new_transaction", "tx": tx, "ttl": 4})
                    print(f"✅ TX accepted & broadcast: {tx}")
                else:
                    print("TX rejected or duplicate")

            else:
                print("Commands: CHAIN, MEMPOOL, MINE, TX <receiver> <amount>")

if __name__ == "__main__":
    Node().connect()
