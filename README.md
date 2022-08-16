# Elastically Scalable and Fault Tolerant Blockchain Transaction Processing

## (K8S + Spark + Kafka + MariaDB + MongoDB)


### <u>Overview</u>

This three-dimensional scaling web application provides a web login and interface to a/many HTTPS, WebSocket or IPC-connected Ethereum node(s) (e.g. geth) which stream transactions using Web3 from peer nodes to the cluster; they are referred to as **(transaction) streaming nodes**. The system holds a consistent transaction log of previously-streamed chain transactions using a distributed no-SQL MariaDB database, which can be used in efficient parallel batch processing via Apache Spark, which occurs on **processor nodes**.

A Kubernetes cluster is initialised and orchestrated using Fabric and boto3, utilising AWS's AutoScaling Groups (ASGs) to create a group of EC2 instances within a region-bounded ASG to ensure a **replication factor of 3** to ensure high availability (**HA**) through redundancies. The relevant images are pulled from the Docker.io container registry and initialised for the following node types (in this order): **database (transaction / web-metadata; **MariaDB / MongoDB resp.**)**, **web-facing (Flask)**, **streaming** (Ethereum node running API; e.g. geth) and **processor** (Kafka/Spark consumer) **nodes**. The client-facing nodes provide a web UI to connect user nodes to a Kafka Topic as a consumer. This Topic is streamed to processor nodes using Spark for processing, and the resulting file(s) are uploaded to MariaDB under the user / the cluster.



### <u>Deployment</u>

The deployment of this cluster and infrastructure is through Docker. The repo contains a Dockerfile which will launch a Python container - this container installs prerequisites (pip, "requirements.txt") and clones the **[repository of this project](https://github.com/willparker123/scalable-cloud-app)**. Afterwards, ``start_cluster.py`` can be ran to begin deployment from the VM where the Docker image is installed.

Before the following instructions, please [sign up](https://docs.aws.amazon.com/powershell/latest/userguide/pstools-appendix-sign-up.html) to AWS or log into the AWS console and generate an [**access and secret access key**](https://aws.amazon.com/blogs/security/wheres-my-secret-access-key/) as well as a [**authentication public key**](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/getstarted-keypair.html) (``'aws_key.pem'`` by default or  CLI arg ``args.aws_pem_path``)

* Run and SSH into an EC2 instance or prepare your local machine (e.g. using a VM)

* Run the following commands to install and start Docker on your machine / an EC2 instance: 

  ``````
  $ sudo yum update 
  $ sudo yum install -y docker 
  $ sudo systemctl start docker 
  $ sudo systemctl enable docker 
  $ sudo usermod -aG docker ec2-user
  ``````

* Pull the Docker image from DockerHub, create the image and run a copy of the container **or** create locally :

  ```
  $ docker pull gg18045/scalable-cloud-app:1.0
  $ docker build -t gg18045/scalable-cloud-app:1.0 .
  $ docker run -d -p 80:80 gg18045/scalable-cloud-app:1.0
  
  $ cd ./PATH_TO_DOCKERFILE
  $ docker build -t scalable-cloud-app .
  $ docker run -d -p 80:80 scalable-cloud-app
  ```

* Configure the aws_access_key, aws_secret_access_key and aws_session_token environment variables in the ".env" file in the root directory (/app).

* Configure the configuration file ``config.yml`` and other environment variables to include host ``<public_ip>:<private_ip>`` pairs if you wish to use EC2 instances created before deployment. 

  Note: pair **1.2.3.4:5.6.7.8** is used to indicate a fresh startup (default **hosts**).

* Log into the container via an interactive terminal and run the ``start_cluster.py`` script to begin cluster deployment:

  ```
  $ docker exec -it <CONTAINER_NAME> /bin/bash
  ```

* Configure the aws_access_key, aws_secret_access_key and aws_session_token environment variables in the ".env" file in the root directory (/app).

* Run the deployment Python script ``start_cluster.py`` with the following CLI arguments:

      parser.add_argument("-k", "--awskeypath", dest="aws_pem_path", default="aws_key.pem", required=False,
                              help="Path to the ssh publickey generate")
          
      
      *** Due to lack of development time, there are currently no more CLI arguments for start_cluster.py: however it will still run ***



#### Deploying a ```transaction-streamer``` node****

A **transaction-streamer** node uses a custom API to do one of three processes to send transaction data (all pending transactions after the current block has been mined) to the main cluster (the **database** and **worker nodes** through Kafka topics):

1. **Local Installation**: the script ```transaction_streamer.py``` runs on **transaction-streamer**; creates a web3 RPC pipe on the current machine.
2. **Remote Installation:** the script ```transaction_streamer.py``` runs on any machine and connects to the desired node machine via SSH, then creates a web3 RPC pipe on the connected machine. 
3. **Use node provider's API:** the script ```transaction_streamer.py``` runs on any machine and connects to the desired node machine via SSH, then tries to use the node's API depending on the **node_type** (default "geth") to get transactions.



To deploy a **transaction-streamer node**:

1. Copy the script and environment files - ``` transaction_streamer.py``` and ``` requirements-transaction-streamer.txt``` / ```environment-transaction-streamer.yml``` for **pip** / **anaconda** respectively.

2.  Create the environment using the below commands, and activate the environment:

   ```pip install -r requirements-transaction-streamer.txt``` for **pip**, or

   ```conda env create -n ENVIRONMENT_NAME -f environment-transaction-streamer.yml``` for **anaconda**.

3.  Then, run:

   ```sudo python transaction_streamer.py --addresses ADDRESSES_TO_MONITOR --pipeurl PIPE_URL [--OTHER_CLI_ARGUMENTS_HERE]``` where **PIPE_URL** is the path to the pipe and **ADDRESSES_TO_MONITOR** is an array of wallet addresses to watch transactions from

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

The default workflow is **1. Local Installation**. For example, using **3. Use node provider's API** and **Alchemy** as a node provider:

```python transaction_streamer.py -a WALLET_ADDRESS1 [WALLET_ADDRESS2 ...] -p https://eth-mainnet.g.alchemy.com/v2/API_KEY -P HTTPProvider``` where **WALLET_ADDRESS** is the address of the wallet(s) to monitor and **API_KEY** is the API key from the node provider.



### <u>Environments</u>

The environments for this system were created using **Anaconda** 2.2.0 using the command ```conda env export > environment.yml``` and were exported to **pip** using the command ```conda list -e > requirements.txt```. The ```.env``` filenames for each environment are given as **[ENV_FILENAME_PIP / ENV_FILENAME_CONDA]**.

### scalable-cloud-app

#### [requirements.txt    /    environment.yml]

The main cluster startup and deployment to spin up EC2 instances, autoscaling groups on AWS, the cluster API and the Kubernetes cluster.

| **library**  | **version** | description                                    | **command**                                          |
| ------------ | ----------- | ---------------------------------------------- | ---------------------------------------------------- |
| kubernetes   | 24.2.0      | Kubernetes cluster deployment and maintenance  | ```conda install -c conda-forge python-kubernetes``` |
| fabric3      | 2.6.0       | Executing ssh commands (in parallel) using SSH | ```conda install -c anaconda fabric```               |
| jinja2       | 3.0.3       | Template engine for cluster deployment         | ```conda install -c anaconda jinja2```               |
| pyyaml       | 6.0         | Reading and creating YAML files                | ```conda install -c conda-forge pyyaml```            |
| boto3        | 1.24.2      | Interaction with AWS services                  | ```conda install -c anaconda boto3```                |
| dotenv       | 0.20.0      | Get and set values in a ```.env``` file        | ```conda install -c conda-forge python-dotenv```     |
| kafka-python |             |                                                |                                                      |
| pyspark      |             |                                                |                                                      |



### transaction-streamer 

#### [requirements-transaction-streamer.txt    /    environment-transaction-streamer.yml]

The API which streams transactions to MariaDB from a hosted node or providers such as [**Infura**](https://infura.io/product/ethereum) and [**Alchemy**]().

| **library** | **version** | description                                                  | **command**                                 |
| ----------- | ----------- | ------------------------------------------------------------ | ------------------------------------------- |
| web3        | 24.2.0      | Web3 library for Python to stream transaction data from the blockchain. | ```conda install -c conda-forge web3```     |
| fabric3     | 2.6.0       | Executing ssh commands (in parallel) using SSH               | ```conda install -c anaconda fabric```      |
| eth-tester  | 0.6.0b6     | Tools for testing Ethereum-based applications; testing connection to blockchain | ``` pip install eth-tester```               |
| websockets  | 10.3        | Websocket connections to stream data from web3               | ``conda install -c conda-forge websockets`` |
| asyncio     | 3.4.1       | Starting asynchronous processes for request handling over websocket | ``conda install -c mutirri asyncio``        |

