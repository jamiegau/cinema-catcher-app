#!/bin/bash
source ./local.env.sh
docker compose down &&
docker compose pull &&
docker compose run backend python3 ./manage.py migrate &&
docker compose run backend python3 ./manage.py catcher_setup &&
docker compose up -d &&
docker image prune -a -f
