# ACI CLI
> Custom command line tool for Cisco ACI
<hr>

## Description

The program works similarly to the Cisco CLI. It connects using the REST API to the APIC to get the data. It's based on ACI Toolkit https://github.com/datacenter/acitoolkit

## Installation
It's easy to qucick run and test the program. Use Dockerfile to create an image and run the container

`docker build -t youruser:acicli .`	

`docker run -dit --name acicli -p 8080:443 youruser:acicli /bin/bash`

## How to use
### Option 1
 Use docker exec to use acicli shell<br />
 > ` docker exec -it acicli acicli `

### Option 2:
 Use browser to connect to acicli shell via shellinabox<br />
 > `https://127.0.0.1:8080/`<br />
 default user: `acicli`<br />
 default password: `aclicli123`
