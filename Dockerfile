# VERSION 1.0
FROM slakas/acicli:latest

MAINTAINER Slawomir Kaszlikowski kaszlikowski.s@gmail.com

RUN apt-get update \
 && apt-get -y install git graphviz-dev pkg-config python python-pip vim-tiny \
 && cd /mnt \
 && git clone https://github.com/slakas/acicli.git\
 && cd acicli \
WORKDIR /mnt/acicli
CMD ["/bin/bash"]
