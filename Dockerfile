# syntax=docker/dockerfile:1
FROM python:latest
RUN mkdir /app
COPY . /app
WORKDIR /app
LABEL Maintainer="gg18045.scalable-cloud-app"
RUN /usr/local/bin/python -m pip install --upgrade pip
EXPOSE 80
CMD ["sudo lsmod | grep br_netfilter"]
RUN pip install -r requirements.txt
CMD [ "python", "./start_cluster.py"]