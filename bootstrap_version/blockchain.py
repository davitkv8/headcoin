import sys
import datetime
import hashlib
import json
import requests

from typing import TypedDict
from uuid import uuid4
from urllib.parse import urlparse

from flask import Flask, jsonify, request


class TransactionType(TypedDict):
    """Single transaction resource."""

    sender: str
    receiver: str
    amount: str | float


class BlockType(TypedDict):
    """Single block resource."""

    index: str | int
    timestamp: str
    nonce: int
    previous_hash: str
    transactions: list[TransactionType]


class Blockchain:

    def __init__(self):
        self.chain: list[BlockType] = []
        self.transactions: list[TransactionType] = []
        self.nodes = set([])

        initial_block = self.build_block(nonce=1, previous_block_hash="0")
        self.chain.append(initial_block)
        self.transactions = []

    def build_block(self, nonce: int, previous_block_hash: str) -> BlockType:
        """Build block object."""
        block: BlockType = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'nonce': nonce,
            'previous_hash': previous_block_hash,
            'transactions': self.transactions,
        }

        return block


    def get_latest_block(self) -> BlockType:
        """Gets the latest block from the chain."""
        return self.chain[-1]


    def mine_block(self) -> BlockType:
        """Mine block."""

        previous_block = self.get_latest_block()
        previous_block_hash = self.hash_block(previous_block)

        new_block: BlockType = self.build_block(nonce=1, previous_block_hash=previous_block_hash)
        while True:
            new_block_hash = self.hash_block(new_block)
            if new_block_hash.startswith('0000'):
                break

            new_block['nonce'] += 1

        self.chain.append(new_block)
        self.transactions = []

        return new_block

    def hash_block(self, block: BlockType) -> str:
        """Hashes block resource."""

        encoded_block = json.dumps(block, sort_keys = True).encode()

        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain: list[BlockType] | None = None) -> bool:
        """Checking full chain validity."""

        chain = chain or self.chain
        previous_index = 0
        current_index = 1

        while current_index < len(chain):
            previous_block: BlockType = chain[previous_index]
            current_block: BlockType = chain[current_index]

            # Checking if current block correctly points to previous block's hash.
            if current_block['previous_hash'] != self.hash_block(previous_block):
                return False


            # Checking if current block's hash is valid.
            if not self.hash_block(current_block).startswith('0000'):
                return False

            previous_index = current_index
            current_index += 1

        return True

    def add_transaction(self, sender, receiver, amount):
        """Add new transaction."""
        self.transactions.append({
                'sender': sender,
                'receiver': receiver,
                'amount': amount,
            })

        latest_block = self.get_latest_block()
        return latest_block['index'] + 1

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def replace_chain(self):
        """Tracks whole network and updates chain."""
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)

        for node in network:
            response = requests.get(f'http://{node}/get-chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.is_chain_valid(chain):
                    longest_chain = chain
                    max_length = length

        if longest_chain:
            self.chain = longest_chain
            return True

        return False



app = Flask(__name__)

node_address = str(uuid4()).replace('-', '')

blockchain = Blockchain()


@app.route('/mine-block', methods = ['GET'])
def mine_block():
    """Mines a block."""
    blockchain.add_transaction(node_address, user, 1)
    block = blockchain.mine_block()
    response = {
        'message': 'Congratulations, you just mined a block!',
        **block,
    }
    return jsonify(response), 200


@app.route('/get-chain', methods = ['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/is-valid', methods = ['GET'])
def is_valid():
    """Checks blockchain validity."""

    if blockchain.is_chain_valid():
        response = {'message': 'All good. The Blockchain is valid.'}
    else:
        response = {'message': 'Houston, we have a problem. The Blockchain is not valid.'}

    return jsonify(response), 200

@app.route('/add-transaction', methods = ['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = {'sender', 'receiver', 'amount'}

    if len(transaction_keys) != len(json) or not all(key in json for key in transaction_keys):
        return 'Invalid data provided!', 400

    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {
        "message": f"This transaction will be added to Block {index}"
    }

    return jsonify(response, 201)

@app.route('/connect-node', methods = ['POST'])
def connect_node():
    json = request.get_json()
    nodes = json["nodes"]
    if nodes is None:
        return "No node", 400

    for node in nodes:
        blockchain.add_node(node)

    response = {
        "message": "All the nodes are now connected",
        "total_nodes": list(blockchain.nodes),
    }

    return jsonify(response), 201

@app.route('/replace-chain', methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {"message": "The chain was replaced by the longest one."}
    else:
        response = {"message": "All good. the chain in the longest one."}

    response["actual_chain"] = blockchain.chain

    return jsonify(response), 200


if __name__ == "__main__":
    port = None
    user = None

    for arg in sys.argv:
        if "--port" in arg:
            port = arg.split("=")[1]

        if "--user" in arg:
            user = arg.split("=")[1]

    if port is None:
        raise Exception("Port must be specified")

    if user is None:
        raise Exception("User must be specified")

    app.run(host="0.0.0.0", port=int(port))
