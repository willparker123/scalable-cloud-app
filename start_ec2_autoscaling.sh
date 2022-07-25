#!/bin/bash
echo "Creating ec2 instances in AWS Autoscaling group..."
fab create-instance-autoscaling-group
fab waitfor-instances
sleep 20
echo "Prepare the droplets..."
fab getips-instances --type=all prepare-instances
echo "Configure the master..."
fab getips-instances --type=master prepare-master
echo "Configure the workers..."
fab getips-instances --type=slave prepare-slave
sleep 20
echo "Running a sanity check..."
fab getips-instances --type=master get-nodes