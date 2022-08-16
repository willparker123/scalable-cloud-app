import sys
import time
import logging
import yaml
import logging
from fabric import Connection, task
import os
from kubernetes import client, config
from dotenv import load_dotenv, dotenv_values
from cluster_handler import Cluster
from argparse import ArgumentParser

"""
hosts:
  52.90.32.232: 172.31.89.137
  3.86.104.131: 172.31.89.30
  54.89.180.182: 172.31.90.131
"""


def main(logger, config_env, args, user=None):
    if user is not None:
        main_cluster = Cluster(config_path='config.yml', aws_pem_path='aws_key.pem', logger=logger, config_env=config_env, user=user)
    else:
        main_cluster = Cluster(config_path='config.yml', aws_pem_path='aws_key.pem', logger=logger, config_env=config_env)
    main_cluster.start_cluster()

if __name__ == "__main__":
    # use loggers right from the start, rather than 'print'
    logger = logging.getLogger(__name__)
    # this will log boto output to std out
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    load_dotenv()
    config_env = dotenv_values(".env")
    
    parser = ArgumentParser()
    parser.add_argument("-k", "--awskeypath", dest="aws_pem_path", default="aws_key.pem", required=False,
                        help="Path to the ssh publickey generated on AWS for EC2 connections")
    args = parser.parse_args()
    
    main(logger, config_env, args)