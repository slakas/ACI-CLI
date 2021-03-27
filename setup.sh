#!/bin/bash

#create acicli user
USER='acicli'

useradd $USER
echo $USER:$USER"123"| chpasswd
# make home dir
mkhomedir_helper acicli
echo "user $USER added successfully!"

#run acicli after login
echo 'acicli' >> /home/acicli/.bashrc
echo 'exit' >> /home/acicli/.bashrc



#setup shellinabox
mv /etc/default/shellinabox /etc/default/shellinabox.old
echo 'SHELLINABOX_DAEMON_START=1' >> /etc/default/shellinabox
echo 'SHELLINABOX_PORT=443' >> /etc/default/shellinabox
echo "SHELLINABOX_USER=$USER" >> /etc/default/shellinabox
echo 'SHELLINABOX_ARGS="--no-beep"' >> /etc/default/shellinabox

cd /var/lib/shellinabox
#Genarte self-signed cert
openssl req -new -x509 -days 365 -nodes \
  -out /var/lib/shellinabox/certificate.pem \
  -keyout /var/lib/shellinabox/certificate.pem \
  -subj "/C=PL/ST=Mazowieckie/L=Warsaw/O=IT/CN=www.example.pl"


#restart web shell
service shellinabox stop
service shellinabox start

