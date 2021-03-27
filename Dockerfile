# VERSION 1.0
FROM slakas/acicli:latest

MAINTAINER Slawomir Kaszlikowski kaszlikowski.s@gmail.com

RUN apt-get update \
 && apt-get -y install git graphviz-dev pkg-config python python-pip vim-tiny \
 && apt-get install openssl shellinabox \
 && cd /mnt \
 && git clone https://github.com/slakas/acicli.git\
 && cd acicli \
 && chmod +x acicli.sh \
 && cp acicli.sh /usr/bin/acicli\
 && bash setup.sh
EXPOSE 443
WORKDIR /mnt/acicli
CMD ["/bin/bash"]
