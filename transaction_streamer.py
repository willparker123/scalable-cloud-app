from argparse import ArgumentParser
from multiprocessing.sharedctypes import Value
from fabric import task, Connection
import logging
import sys
from web3 import Web3, EthereumTesterProvider
from web3.auto import w3

YOUR_PUBLIC_IP = "0.0.0.0"
YOUR_PRIVATE_IP = "0.0.0.0"
YOUR_IPS = (YOUR_PUBLIC_IP, YOUR_PRIVATE_IP)

main_host = YOUR_IPS

class Transaction(object):
    def __init__(self, tx):
        """
        {
            'blockHash': HexBytes('HASH'), 
            'blockNumber': 12345678, 
            'from': 'ADDR', 
            'gas': 350000, 
            'gasPrice': 25524367634, 
            'hash': HexBytes('HASH'), 
            'input': '0x', 
            'nonce': 6123469, 
            'to': 'ADDR', 
            'transactionIndex': 0, 
            'value': 45584000000000000, 
            'type': '0x0', 
            'chainId': '0x1', 
            'v': 38, 
            'r': HexBytes('HASH'), 
            's': HexBytes('HASH')
        }
        """
        self.block_hash = tx["blockHash"]
        self.block_number = tx["blockNumber"]
        self.to_addr = tx["to"]
        self.from_addr = tx["from"]
        self.gas = tx["gas"]
        self.gas_price = tx["gasPrice"]
        self.nonce = tx["nonce"]
        self.value = tx["value"]
        self.type = tx["type"]
        self.chainId = tx["chainId"]
        self.vrs = (tx["v"], tx["r"], tx["s"])
        self.transaction_index = tx["transactionIndex"]
        
def format_addresses(web3_, addresses):
    return list(map(lambda x: web3_.toChecksumAddress(x), addresses))

def send_tx_to_cluster(logger, tx, log_send=False):
    if log_send:
        logger.info(f"Sending transaction (TX) to cluster: {tx['transactionIndex']}")
    return Transaction(tx)

def send_txs_to_cluster(logger, txs):
    if len(txs) < 1:
        logger.info(f"No TXs to send.")
        return []
    else:
        logger.info(f"Sending {len(txs)} transactions (TXs) to cluster...")
        transactions = [send_tx_to_cluster(logger, tx) for tx in txs]
        return transactions

def create_web3_pipe(logger, args, filter_address=False):
    provider = args.provider
    logger.info(f"Trying to connect to Web3...")
    web3_ = None
    try:
        web3_ = Web3(EthereumTesterProvider())
    except:
        raise ValueError("Error: cannot connect to Web3")
    if not web3_.isConnected():
        raise ValueError("Error: cannot connect to Web3")
    if provider not in {"IPCProvider", "HTTPProvider", "WebsocketProvider"}:
        raise ValueError(f"Error: provider '{provider}' not one of 'IPCProvider', 'HTTPProvider' or 'WebsocketProvider'")
    if provider == "IPCProvider":
        web3_ = Web3(Web3.IPCProvider(args.pipe_url)) #e.g. './path/to/geth.ipc'
    elif provider == "HTTPProvider":
        web3_ = Web3(Web3.HTTPProvider(args.pipe_url)) #e.g. 'http://127.0.0.1:8545'
    elif provider == "WebsocketProvider":
        web3_ = Web3(Web3.WebsocketProvider(args.pipe_url)) #e.g. 'wss://127.0.0.1:8546'
    else:
        raise ValueError(f"Error: provider '{provider}' not one of 'IPCProvider', 'HTTPProvider' or 'WebsocketProvider'")
    if web3_ is not None:
        logger.info(f"Connected to Web3 successfully.")
    else:
        raise ValueError("Error: cannot connect to Web3")

    #latest_block = w3.eth.get_block('latest')
    transaction_hashes = []
    temp_transactions = []
    restart_bool = False
    while not restart_bool:
        logger.info(f"Getting latest Block while monitoring address(es) {args.monitor_addresses}...")
        pending_block = web3_.eth.getBlock(block_identifier='pending', full_transactions=True)
        pending_transactions = pending_block['transactions']
        
        latestblock_filter = web3_.eth.filter({'fromBlock': 'latest', 'toBlock': 'pending'})
        if filter_address:
            latestblock_filter = web3_.eth.filter({'fromBlock': 'latest', 'toBlock': 'pending', 'address': format_addresses(web3_, args.monitor_addresses)})
        #pending_transactions_filtered = latestblock_filter.get_new_entries()
        #logger.info("Waiting for latest block hashes...")
        while True:
            #transaction_hashes = web3_.eth.getFilterChanges(latestblock_filter.filter_id)
            pending_block = web3_.eth.getBlock(block_identifier='pending', full_transactions=True)
            new_pending = [x for x in pending_block['transactions'] if x not in pending_transactions]
            logger.info(f"New pending transactions: {len(new_pending)}")
            pending_transactions.extend(new_pending)
            #new_transaction_hashes = [web3_.eth.getTransaction(h) for h in new_pending]
            new_transaction_hashes = new_pending
            transaction_hashes.extend(new_transaction_hashes)
            send_txs_to_cluster(logger, new_transaction_hashes)
        #logger.info("Waiting for latest block hashes...")
        #while len(pending_transactions) < 1:
            #logger.info("tick")
            #transaction_hashes = web3_.eth.getFilterChanges(latestblock_filter.filter_id)
        #temp_transactions = [web3_.eth.getTransaction(h['transactionHash']) for h in transaction_hashes]
        #logger.info(f"Captured {len(transaction_hashes)} transaction_hashes from block")
        #logger.info(f"Captured TXs: {temp_transactions}")
        #for tx in temp_transactions:
        #    logger.info(f"Sending TX: {tx} to cluster")
        #    send_txs_to_cluster(logger, pending_transactions)
        
    
    
@task
def create_web3_pipe_remote(c, logger, args):
    #TODO githubaddr = get_githubaddr()
    githubaddr = "https://github.com/ccdb-uob/stream_event_generator"
    logger.info(f"Pulling from GitHub on {c.host} from address '{githubaddr}'")
    #TODO
    #c.sudo("apt-get update")
    logger.info(f"Creating environment for '{githubaddr}' on {c.host}")
    #TODO
    logger.info(f"Running '{githubaddr}' on {c.host}")
    #TODO
    
@task
def connect(user, host):
    con = Connection(f"{user}@{host}")
    return con

@task
def setup_ssh(logger, args, host, run_script=True):
    pipe = None
    c = connect(args.user, host)
    # RUNS THIS SCRIPT ON THE MACHINE OVER SSH TO CREATE PIPE
    if run_script:
        logger.info(f"Running 'transaction_streamer.py' on {c.host} with arguments:")
        logger.info(f"{args}")
        pipe = create_web3_pipe_remote(c, logger, args)
    else:
        #TODO node_type = get_node_type() WITH CHECKS AGAINST valid_node_types
        node_type = 'geth'
        logger.info(f"Creating web3 RPC pipe on {c.host}; node implementation is '{node_type}'")
        #TODO USES NODE API OVER SSH CONNECTION FROM WEB UI FOR {node_type} TO CREATE PIPE
        #c.sudo("apt-get update")
    return pipe

def main(args, parser, logger, host):
    pipe = None
    # ONLY IF --connect_via_ssh AND --user ARE SUPPLIED TO CLI
    #
    # USE API ON NODE (E.G. geth)  || OR ||  RUN SCRIPT VIA SSH
    if args.connect_via_ssh:
        if args.user is None:
            parser.error("--connect_via_ssh requires --user.")
        
        if args.use_node_api:
            pipe = setup_ssh(logger, args, host, run_script=False)
        else:
            pipe = setup_ssh(logger, args, host, run_script=True)
    else:
        # *********************
        # RUN SCRIPT LOCALLY        [DEFAULT]
        # *********************
        pipe = create_web3_pipe(logger, args, filter_address=len(args.monitor_addresses) < 1)
    if pipe is None:
        raise ValueError("Error: broken pipe or ssh connection; failed to make web3 RPC pipe")

if __name__ == "__main__":
    # use loggers right from the start, rather than 'print'
    logger = logging.getLogger(__name__)
    # this will log boto output to std out
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    
    parser = ArgumentParser()
    parser.add_argument("-p", "--pipeurl", dest="pipe_url", required=True,
                        help="IPC, HTTP or WebSocket pipe url used to create the web3 pipe; must be supplied")
    parser.add_argument("-a", "--addresses", nargs='+', required=False, dest="monitor_addresses", default=[],
                        help="the addresses used in the 'address' field in web3.eth.filter")
    parser.add_argument("-u", "--publicip", dest="ip_public", default=YOUR_PUBLIC_IP,
                        help="public IP address for the hosted Node")
    parser.add_argument("-v", "--privateip", dest="ip_private", default=YOUR_PRIVATE_IP,
                        help="private IP address for the hosted Node")
    parser.add_argument("-s", "--ssh",
                        action="store_true", dest="connect_via_ssh", default=False,
                        help="connect to the node via ssh - requires '-u / --user'")
    parser.add_argument("-P", "--provider", dest="provider", default="IPCProvider",
                        help="type of provider to use - must be 'IPCProvider', 'HTTPProvider' or 'WebsocketProvider'")
    parser.add_argument("-A", "--useapi",
                        action="store_true", dest="use_node_api", default=False,
                        help="when connected to the node via ssh, use the node's api")
    parser.add_argument("-U", "--user", dest="user", default=None,
                        help="the user for the ssh connection - requires '-u / --user'")
    args = parser.parse_args()
    if args.pipe_url is None:
        raise ValueError("Error: -p / --pipeurl must be supplied")
    if len(args.monitor_addresses) < 1:
        logger.warning("-a / --addresses is empty; monitor_addresses=[]")
    if args.provider not in {'IPCProvider', 'HTTPProvider', 'WebsocketProvider'}:
        raise ValueError("Error: -P / --provider must be one of 'IPCProvider', 'HTTPProvider' or 'WebsocketProvider'")
    
    main_host = (args.ip_public, args.ip_private)
    main(args, parser, logger, main_host)