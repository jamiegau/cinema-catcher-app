#!/usr/bin/env bash

set -Eeuo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ -f /opt/catcher/postgresql/data/PG_VERSION ]] &&
   [[ "$(tr -d '[:space:]' < /opt/catcher/postgresql/data/PG_VERSION)" == "13" ]]; then
    cat >&2 <<'EOF'
This is a Catcher v3 / PostgreSQL 13 installation.

Do not use update.sh for the v3 to v4 upgrade. Follow UPGRADING_FROM_V3.md so
the database is backed up and migrated to PostgreSQL 18 with rollback support.
EOF
    exit 1
fi

docker compose config --quiet
docker compose pull

# Stop every database-writing application process before applying migrations.
docker compose stop \
    backend backendc worker worker_mon worker_kdm beat network-monitor

docker compose up -d pgdatabase redis
docker compose run --rm backend python3 ./manage.py migrate
docker compose run --rm backend python3 ./manage.py migrate --check
docker compose run --rm backend python3 ./manage.py check
docker compose run --rm backend python3 ./manage.py catcher_setup
docker compose up -d

# A guided upgrade records exact old image IDs for rollback. Some can become
# dangling after a pull, so do not prune while that recovery state is retained.
if [[ -f .catcher-upgrade/state.json ]]; then
    echo 'Keeping old images for the saved v3 upgrade rollback.'
else
    docker image prune --force
fi

docker compose ps --all
