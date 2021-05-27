#!/bin/bash
# Used to monitor the output of the docker containers.
# can specify the container to watch, of if no argument, get output of all containers.
docker-compose logs -f --tail="10" $1
