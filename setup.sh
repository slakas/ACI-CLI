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

#restart web shell
service shellinabox stop
service shellinabox start
