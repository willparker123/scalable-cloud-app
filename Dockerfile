# syntax=docker/dockerfile:1
FROM python:latest
RUN mkdir /app
COPY . /app
WORKDIR /app
LABEL Maintainer="gg18045.ccbd-video-processor"
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install -r requirements.txt
CMD [ "sh", "./start_ec2_autoscaling.sh"]
CMD [ "python", "./start_cluster.py"]