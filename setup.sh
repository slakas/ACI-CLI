#!/bin/bash

#create acicli user
USER='acicli'

useradd $USER
echo $USER:$USER"123"| chpasswd
echo "user $USER added successfully!"

#setup shellinabox
mv /etc/default/shellinabox /etc/default/shellinabox.old
echo 'SHELLINABOX_DAEMON_START=1' >> /etc/default/shellinabox
echo 'SHELLINABOX_PORT=443' >> /etc/default/shellinabox
echo "SHELLINABOX_USER=$USER" >> /etc/default/shellinabox
echo 'SHELLINABOX_ARGS="--no-beep"' >> /etc/default/shellinabox

cd /var/lib/shellinabox
#Genarte self-signed cert
#Required
domain='com'
commonname='acicli'

#Change to your company details
country=PL
state=Mazowieckie
locality=Warsaw
organization=acicli.net
organizationalunit=IT
email=admin@acicli.net

#Optional
password=aciclipassword

echo "Generating key request for $domain"

#Generate a key
openssl genrsa -des3 -passout pass:$password -out $domain.key 2048 -noout

#Remove passphrase from the key. Comment the line out to keep the passphrase
echo "Removing passphrase from key"
openssl rsa -in $domain.key -passin pass:$password -out $domain.key

#Create the request
echo "Creating CSR"
openssl req -new -key $domain.key -out $domain.csr -passin pass:$password \
    -subj "/C=$country/ST=$state/L=$locality/O=$organization/OU=$organizationalunit/CN=$commonname/emailAddress=$email"


#restart web shell
service shellinabox stop
service shellinabox start

