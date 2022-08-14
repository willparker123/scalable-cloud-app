# Elastically Scalable and Fault Tolerant Video Stream Processing

## (K8S + Spark + Kafka + ZooKeeper)


### Overview

This is an elastically scalable, horizontally and vertically scaling and fault tolerant cloud application which utilises many components from AWS (S3 buckets, EC2 instances, Lambda and Autoscaling groups), as well as Kubernetes, ZooKeeper/Kafka, Spark, as well as Redis and Node to provide a web-app frontend/backend. 

The K8S cluster is initialised and orchestrated using fabric and boto3 to create EC2 instances on the back of an AWS Autoscaling Group Launch Template. The K8S cluster also deploys redis master and slave containers as well as node containers to provide a frontend. The frontend provides an interface to upload video files to an S3 bucket, where a Lambda function is triggered on upload to serialise the data into a bytestream forwarded to a Kafka Topic. This Topic is streamed to Spark for processing, and the resulting file(s) are uploaded to a seperate S3 bucket, with another Lambda function attached.



### Deployment

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