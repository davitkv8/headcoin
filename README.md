# Readme


**Requirement: Python 3.12 only.
Dependencies: No third-party packages. Everything uses Python stdlib.**

### What it is?
This project is a minimal, P2P blockchain that runs over UDP with rendezvous-based peer discovery.
- Peers (nodes) discover one another via a lightweight rendezvous server.
- Nodes exchange transactions and blocks via UDP (NO HTTP)
- Each node maintains a local blockchain with deterministic genesis, mempool, and PoW.


### How it works (high level)
1) Discovery (rendezvous)

- Nodes send a tiny UDP packet (“heartbeat”) to the rendezvous server.

- Server records last_seen per (ip, port), prunes stale peers after a timeout, and broadcasts PEERS (ip:port) lists.

2) Gossip (UDP)

- Nodes gossip transactions and blocks as single-packet JSON messages.

- Dedup: every transaction has a stable tx_id; nodes keep seen_tx_ids and skip retransmitting duplicates.

- No echo: nodes never re-send to the peer they just received from.

- TTL: each transaction gossip decrements a ttl so propagation naturally stops.

3) Blockchain core

- Deterministic GENESIS (same for all nodes) to avoid startup divergence.

- Mempool keyed by tx_id.

- Mining: coinbase (fixed reward) + mempool snapshot; PoW target = hash starts with "0000".

- Validation: previous-hash linkage + PoW check for all non-genesis blocks.

- Consensus: longest valid chain via replace_chain(); confirmed mempool txs are removed.

4) Sync & reorgs

- On startup, after getting peers, a node asks for a full chain (REQ_CHAIN → FULL_CHAIN) and adopts the longest valid one.

- If a received block doesn’t extend our tip, we request the sender’s full chain and attempt replacement.
