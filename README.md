# Elastically Scalable and Fault Tolerant Blockchain Transaction Processing

## (K8S + Spark + Kafka + MariaDB + MongoDB)


### <u>Overview</u>

This three-dimensional scaling web application provides an interface to a/many VPC-connected Ethereum node(s) (e.g. geth) which streams transactions from up to 75 peer nodes. The system holds a consistent transaction log of the past 6 months of Ethereum chain transactions using a distributed no-SQL Cassandra database, which can be used in efficient batch processing via Apache Spark.

A Kubernetes cluster is initialised and orchestrated using Fabric and boto3, utilising AWS's AutoScaling Groups (ASGs) to create a group of EC2 instances within a region-bounded ASG to ensure a **replication factor of 3** to ensure high availability (**HA**) through redundancies. The relevant images are pulled from the Docker.io container registry and initialised for the following node types (in this order): **database (transaction / web-metadata; **MariaDB / MongoDB resp.**)**, **web-facing (Flask)**, **streaming** (Ethereum node running API; e.g. geth) and **processor** (Kafka/Spark consumer) **nodes**. The client-facing nodes provide a web UI to connect user nodes to a Kafka Topic as a consumer. This Topic is streamed to processor nodes using Spark for processing, and the resulting file(s) are uploaded to MariaDB under the user / the cluster.



### <u>Deployment</u>

The deployment of this cluster and infrastructure is through Docker. The repo contains a Dockerfile which will launch a Python container - this container installs prerequisites (pip, "requirements.txt") and runs "start_ec2_autoscaling.sh", followed by "start_cluster.py" in CMD.

* Run and SSH into an EC2 instance or prepare your local machine

* Run the following commands to install and start Docker on your machine / an EC2 instance: 

  ``````
  $ sudo yum update 
  $ sudo yum install -y docker 
  $ sudo systemctl start docker 
  $ sudo systemctl enable docker 
  $ sudo usermod -aG docker ec2-user
  ``````

* Pull the Docker image from DockerHub:

  ```
  $ docker pull gg18045/ccbd-video-processor:1.0
  ```

* Configure the aws_access_key, aws_secret_access_key and aws_session_token environment variables in the ".env" file in the root directory (/app)

* Configure ssh_path and optionally (zookeeper_max_nodes, zookeeper_pref_nodes, zookeeper_min_nodes) in "config.yaml"

* Log into the container via an interactive terminal:

  ```
  $ docker exec -it redis-latest /bin/bash
  ```



#### Deploying a ```transaction-streamer``` node****

A **transaction-streamer** node uses a custom API to do one of three processes to send transaction data to the main cluster (the **database** and nodes through Kafka topics):

1. **Local Installation**: the script ```transaction_streamer.py``` runs on **transaction-streamer**; creates a web3 RPC pipe on the current machine.
2. **Remote Installation:** the script ```transaction_streamer.py``` runs on any machine and connects to the desired node machine via SSH, then creates a web3 RPC pipe on the connected machine. 
3. **Use Node API:** the script ```transaction_streamer.py``` runs on any machine and connects to the desired node machine via SSH, then tries to use the node's API depending on the **node_type** (default "geth")



To deploy a **transaction-streamer node**:

1. Copy the script and environment files - ``` transaction_streamer.py``` and ``` requirements-transaction-streamer.txt``` / ```environment-transaction-streamer.yml``` for **pip** / **anaconda** respectively.

2.  Activate the environment using:

   ```pip install -r requirements-transaction-streamer.txt``` for **pip**, or

   ```conda env create -n ENVIRONMENT_NAME -f environment-transaction-streamer.yml``` for **anaconda**.

3.  Then, run:

   ```sudo python transaction_streamer.py --addresses ADDRESSES_TO_MONITOR_ARRAY --pipeurl PIPE_URL [--OTHER_CLI_ARGUMENTS_HERE]``` where **PIPE_URL** is the path to the pipe:

   ``````
       if provider == "IPCProvider":
           w3 = Web3(Web3.IPCProvider(args.pipe_url)) #e.g. './path/to/geth.ipc'
       elif provider == "HTTPProvider":
           w3 = Web3(Web3.HTTPProvider(args.pipe_url)) #e.g. 'http://127.0.0.1:8545'
       elif provider == "WebsocketProvider":
           w3 = Web3(Web3.WebsocketProvider(args.pipe_url)) #e.g. 'wss://127.0.0.1:8546'
   ``````


The command-line arguments for  ```transaction_streamer.py``` are below. 

``````
    parser.add_argument("-p", "--pipeurl", dest="pipe_url", default="\\\\\.\\pipe\\geth.ipc", required=True,
                        help="IPC, HTTP or WebSocket pipe url used to create the web3 pipe; must be supplied")
    parser.add_argument("-a", "--addresses", nargs='+', required=True, dest="monitor_addresses", default=[],
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
``````

The default workflow is **1. Local Installation**.





### <u>Environments</u>

The environments for this system were created using **Anaconda** 2.2.0 using the command ```conda env export > environment.yml``` and were exported to **pip** using the command ```conda list -e > requirements.txt```. The ```.env``` filenames for each environment are given as **[ENV_FILENAME_PIP / ENV_FILENAME_CONDA]**.

### scalable-cloud-app

#### [requirements.txt    /    environment.yml]

The main cluster startup and deployment to spin up EC2 instances, autoscaling groups on AWS, the cluster API and the Kubernetes cluster.

| **library** | **version** | description                                    | **command**                                          |
| ----------- | ----------- | ---------------------------------------------- | ---------------------------------------------------- |
| kubernetes  | 24.2.0      | Kubernetes cluster deployment and maintenance  | ```conda install -c conda-forge python-kubernetes``` |
| fabric      | 2.6.0       | Executing ssh commands (in parallel) using SSH | ```conda install -c anaconda fabric```               |
| jinja2      | 3.0.3       | Template engine for cluster deployment         | ```conda install -c anaconda jinja2```               |
| pyyaml      | 6.0         | Reading and creating YAML files                | ```conda install -c conda-forge pyyaml```            |
| boto3       | 1.24.2      | Interaction with AWS services                  | ```conda install -c anaconda boto3```                |
| dotenv      | 0.20.0      | Get and set values in a ```.env``` file        | ```conda install -c conda-forge python-dotenv```     |



### transaction-streamer 

#### [requirements-transaction-streamer.txt    /    environment-transaction-streamer.yml]

The API which streams transactions to MariaDB from a hosted node or providers such as [**Infura**](https://infura.io/product/ethereum) and [**Alchemy**]().

| **library** | **version** | description                                                  | **command**                             |
| ----------- | ----------- | ------------------------------------------------------------ | --------------------------------------- |
| web3        | 24.2.0      | Web3 library for Python to stream transaction data from the blockchain. | ```conda install -c conda-forge web3``` |
| fabric      | 2.6.0       | Executing ssh commands (in parallel) using SSH               | ```conda install -c anaconda fabric```  |
| eth-tester  | 0.6.0b6     | Tools for testing Ethereum-based applications; testing connection to blockchain | ``` pip install eth-tester```           |
|             |             |                                                              |                                         |
|             |             |                                                              |                                         |
|             |             |                                                              |                                         |

