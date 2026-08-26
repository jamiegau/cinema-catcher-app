#!/usr/bin/env bash

set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

docker compose config --quiet
docker compose up -d
docker compose ps --all
