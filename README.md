# ACI CLI
`A custom command line tool for Cisco ACI`

The program works similarly to the Cisco CLI. It connects using the REST API to the APIC to get the data.

## How to run
It's easy to qucick run and test the program. Use Dockerfile to create an image and run the container

`docker build -t youruser:acicli .`
`docker run -dit --name acicli_dev -p 8080:443 youruser:acicli /bin/bash`

