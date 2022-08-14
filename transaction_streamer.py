from argparse import ArgumentParser
from multiprocessing.sharedctypes import Value
from fabric import task, Connection
import logging
import sys
from web3 import Web3, EthereumTesterProvider

YOUR_PUBLIC_IP = "192.168.0.0"
YOUR_PRIVATE_IP = "0.0.0.0"
YOUR_IPS = (YOUR_PUBLIC_IP, YOUR_PRIVATE_IP)

host = YOUR_IPS

class Transaction(object):
    def __init__(self):
        self.to_addr = "a"

def send_tx_to_cluster(logger, tx):
    (addr_from, adrr_to, value, gas_price, gas, max_priority_fee_per_gas, max_fee_per_gas, nonce, type_) = tx
    logger.info(f"Sending transaction (TX) to cluster: {tx}")
    return tx

def send_txs_to_cluster(logger, txs):
    return txs

def create_web3_pipe(logger, args, provider="IPCProvider"):
    logger.info(f"Trying to connect to Web3...")
    w3 = None
    try:
        w3 = Web3(EthereumTesterProvider())
    except:
        raise ValueError("Error: cannot connect to Web3")
    if not w3.isConnected():
        raise ValueError("Error: cannot connect to Web3")
    if provider not in {"IPCProvider", "HTTPProvider", "WebsocketProvider"}:
        raise ValueError(f"Error: provider '{provider}' not one of 'IPCProvider', 'HTTPProvider' or 'WebsocketProvider'")
    if provider == "IPCProvider":
        w3 = Web3(Web3.IPCProvider(args.pipe_url)) #e.g. './path/to/geth.ipc'
    elif provider == "HTTPProvider":
        w3 = Web3(Web3.HTTPProvider(args.pipe_url)) #e.g. 'http://127.0.0.1:8545'
    elif provider == "WebsocketProvider":
        w3 = Web3(Web3.WebsocketProvider(args.pipe_url)) #e.g. 'wss://127.0.0.1:8546'
    else:
        raise ValueError(f"Error: provider '{provider}' not one of 'IPCProvider', 'HTTPProvider' or 'WebsocketProvider'")
    if w3 is not None:
        logger.info(f"Connected to Web successfully.")
    else:
        raise ValueError("Error: cannot connect to Web3")

    #latest_block = w3.eth.get_block('latest')
    
    while True:
        logger.info("G")
        #pending_block = w3.eth.getBlock(block_identifier='pending', full_transactions=True)
        #pending_transactions = pending_block['transactions']
        latestblock_filter = w3.eth.filter({'fromBlock': 'latest', 'toBlock': 'pending'})#, 'address': 'MY ADDRESS'
        #pending_transactions_filtered = latestblock_filter.get_new_entries()
        
        transaction_hashes = w3.eth.getFilterChanges(latestblock_filter.filter_id)
        transactions = [w3.eth.getTransaction(h) for h in transaction_hashes]
        for tx in transactions:
            send_tx_to_cluster(tx)
        #send_txs_to_cluster(logger, pending_transactions)
    
    
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
def setup_ssh(logger, args, run_script=True):
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

def main(args, parser, logger, host=None):
    pipe = None
    # ONLY IF --connect_via_ssh AND --user ARE SUPPLIED TO CLI
    #
    # USE API ON NODE (E.G. geth)  || OR ||  RUN SCRIPT VIA SSH
    if args.connect_via_ssh:
        if args.user is None:
            parser.error("--connect_via_ssh requires --user.")
        
        if args.use_node_api:
            pipe = setup_ssh(logger, args, run_script=False)
        else:
            pipe = setup_ssh(logger, args, run_script=True)
    else:
        # *********************
        # RUN SCRIPT LOCALLY        [DEFAULT]
        # *********************
        pipe = create_web3_pipe(logger, args)
    if pipe is None:
        raise ValueError("Error: broken pipe or ssh connection; failed to make web3 RPC pipe")

if __name__ == "__main__":
    # use loggers right from the start, rather than 'print'
    logger = logging.getLogger(__name__)
    # this will log boto output to std out
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    
    parser = ArgumentParser()
    parser.add_argument("-p", "--pipeurl", dest="pipe_url", default="\\\\\.\\pipe\\geth.ipc",
                        help="IPC, HTTP or WebSocket pipe url used to create the web3 pipe; must be supplied")
    parser.add_argument("-u", "--publicip", dest="ip_public", default=YOUR_PUBLIC_IP,
                        help="public IP address for the hosted Node")
    parser.add_argument("-v", "--privateip", dest="ip_private", default=YOUR_PRIVATE_IP,
                        help="private IP address for the hosted Node")
    parser.add_argument("-s", "--ssh",
                        action="store_true", dest="connect_via_ssh", default=False,
                        help="connect to the node via ssh - requires '-u / --user'")
    parser.add_argument("-a", "--useapi",
                        action="store_true", dest="use_node_api", default=False,
                        help="when connected to the node via ssh, use the node's api")
    parser.add_argument("-U", "--user", dest="user", default=None,
                        help="the user for the ssh connection - requires '-u / --user'")
    args = parser.parse_args()
    if args.pipe_url is None:
        raise ValueError("Error: -p / --pipeurl must be supplied")
    
    host = (args.ip_public, args.ip_private)
    if host[0] == YOUR_PUBLIC_IP and host[1] == YOUR_PRIVATE_IP:
        main(args, parser, logger)
    else:
        main(args, parser, logger, host)