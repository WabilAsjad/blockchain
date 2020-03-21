from lib import Block
from flask import Flask
from flask import request
from flask import render_template, redirect
import datetime
from hashlib import sha256
import json


class Block:
    """Create new block object."""

    def __init__(self, index, transactions, time_stamp, previous_hash):
        """
        Constructor for the Block class.
        :param index: Unique ID for block.
        :param transactions: List of transactions.
        :param previous_hash: Unique hash of previous block.
        :param time_stamp: Time of creation of block.
        """
        self.index = index
        self.time_stamp = datetime.datetime.now()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.generate_hash()

    def compute_hash(self):
        """Returns the hash of a block instance
        by converting it to JSON format.
        """
        block_header = str(self.time_stamp) + str(self.transactions) + str(self.previous_hash) + str(self.nonce)
        block_hash = sha256(block_header.encode())
        return str(block_hash.hexdigest())


# Testing
def test_contents(block):
    print("index:", self.index)
    print("timestamp:", self.time_stamp)
    print("transactions:", self.transactions)
    print("current hash:", self.generate_hash())
    print("previous hash:", self.previous_hash)


class Blockchain:
    # set difficulty of Proof of Work algorithm
    difficulty = 2

    def __init__(self):
        self.chain = []
        self.unconfirmed_transactions = []
        self.genesis_block()
        self.previous_block = self.chain[len(self.chain) - 1].hash

    def genesis_block(self):
        """
        Creates genesis block and appends it to chain. The block has
        index 0, previous_hash as 0, and a valid given hash.
        """
        transactions = {}
        genesis_block = Block(0, [], datetime.datetime.now(), "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the blockchain, after
        verifying that it is valid through proof of work, and
        checking if the previous_hash is valid.
        :param block
        :param proof of block
        :return:
        """
        previous_block_hash = self.last_block.hash

        # verify if block is valid
        if previous_block_hash != block.previous_hash:
            return False
        if not self.is_valid(block, proof):
            return False

        proof = block.previous_hash
        self.chain.append(block)
        return True

    def is_valid(self, block, block_hash):
        """Check if block_hash is a valid hash and
        meets the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

    def proof_of_work(self, block):
        """Function that attempts different values of nonce to get a
        hash that meets the difficulty criteria."""
        proof = block.compute_hash()
        while proof[:difficulty] != '0' * Blockchain.difficulty:
            block.nonce += 1
            proof = block.compute_hash()
        # reset nonce
        block.nonce = 0
        return proof

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    def interface(self):
        """Serves as an interface to add pending transactions to blockchain
        by adding them to block and verifying Proof of Work algorithm.
        """

        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=datetime.datetime.now(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)

        # reset unconfirmed transactions
        self.unconfirmed_transactions = []
        return new_block.index

    def check_chain_validity(cls, chain):
        """
        A helper method to check if the entire blockchain is valid.
        """
        result = True
        previous_hash = "0"

        # Iterate through every block
        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid(block, block.hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result


def consensus():
    """
    Our simple consensus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global blockchain

    longest_chain = None
    current_len = len(blockchain.chain)

    for node in participants:
        response = requests.get('{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            # Longer valid chain found!
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


# Initialize Flask app
application = Flask(__name__)

blockchain = Blockchain()


# Declare endpoint for our application to submit transactions to


@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "content"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    tx_data["timestamp"] = datetime.datetime.now()

    blockchain.add_new_transaction(tx_data)

    return "Success", 201


# Get copy of node's current blockchain
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data})


# Mine any unconfirmed transactions
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    return "Block #{} is mined.".format(result)


@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


# Contains the host addresses of other participating members of the network
participants = set()


# Endpoint to add new participants to the network
@app.route('/register_node', methods=['POST'])
def register_new_participants():
    # The host address to the participant node
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the participants list
    participants.add(node_address)

    # Return the blockchain to the newly registered node so that it can sync
    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the remote node specified in the
    request, and sync the blockchain as well with the remote node.
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global participants
        # update chain and the participants
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        participants.update(response.json()['participants'])
        return "Registration successful", 200
    else:
        # If error is encountered, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    blockchain = Blockchain()
    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"])
        proof = block_data['hash']
        if idx > 0:
            added = blockchain.add_block(block, proof)
            if not added:
                raise Exception("The chain dump is tampered!!")
        else:  # the block is a genesis block, no verification needed
            blockchain.chain.append(block)
    return blockchain


# endpoint to add a block mined by someone else to
# the node's chain. The node first verifies the block
# and then adds it to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


def announce_new_block(block):
    """
    Announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for participant in participants:
        url = "{}add_block".format(participant)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))


@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


app.run(debug=True, port=8000)