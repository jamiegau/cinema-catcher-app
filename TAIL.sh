#!/usr/bin/env bash

set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Pass an optional service name, for example: ./TAIL.sh backend
docker compose logs --follow --tail=50 "$@"
