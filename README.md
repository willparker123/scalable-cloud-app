# Elastically Scalable and Fault Tolerant Blockchain Transaction Processing

## (K8S + Spark + Kafka + Cassandra + MongoDB)


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

### <u>Environments</u>

The environments for this system were created using Anaconda 2.2.0 and were exported to **pip** using the command ```conda list -e > requirements_{environment_name}.txt```

### scalable-cloud-app

The main cluster startup and deployment to spin up EC2 instances, autoscaling groups on AWS, the cluster API and the Kubernetes cluster.

| **library** | **version** | description                                    | **command**                                          |
| ----------- | ----------- | ---------------------------------------------- | ---------------------------------------------------- |
| kubernetes  | 24.2.0      | Kubernetes cluster deployment and maintenance  | ```conda install -c conda-forge python-kubernetes``` |
| fabric      | 2.6.0       | Executing ssh commands (in parallel) using SSH | ```conda install -c anaconda fabric```               |
| jinja2      | 3.0.3       | Template engine for cluster deployment         | ```conda install -c anaconda jinja2```               |
| pyyaml      | 6.0         | Reading and creating YAML files                | ```conda install -c conda-forge pyyaml```            |
| boto3       | 1.24.2      | Interaction with AWS services                  | ```conda install -c anaconda boto3```                |
| dotenv      | 0.20.0      | Get and set values in a ```.env``` file        | ```conda install -c conda-forge python-dotenv```     |
