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
# Download first: a registry/network failure must not take a working site down.
docker compose pull

# Remove the entire stack, including nginx. Merely stopping the backend leaves
# nginx holding upstream IP addresses from before the containers were replaced.
# Never use --volumes: the database and other persistent data must survive.
echo 'Stopping and removing the Compose stack. Persistent data will be retained.'
trap 'status=$?; echo "Update failed (exit $status). The stack may be stopped or only partially running. Resolve the error and rerun update.sh; do not bypass failed migrations with start.sh." >&2; exit "$status"' ERR
docker compose down --remove-orphans --timeout 60

docker compose up -d pgdatabase redis

# PostgreSQL startup/recovery can outlast container creation after a full down.
database_ready=false
for ((attempt = 1; attempt <= 30; attempt++)); do
    if docker compose exec -T pgdatabase sh -c 'pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; then
        database_ready=true
        break
    fi
    sleep 2
done
if [[ "$database_ready" != true ]]; then
    echo 'PostgreSQL did not become ready. Inspect docker compose logs pgdatabase, then rerun update.sh.' >&2
    exit 1
fi

# Only the database/cache and these short-lived migration containers may run
# during the upgrade; do not implicitly start backend dependencies such as aria2.
docker compose run --rm --no-deps backend python3 ./manage.py migrate
docker compose run --rm --no-deps backend python3 ./manage.py migrate --check
docker compose run --rm --no-deps backend python3 ./manage.py check
docker compose run --rm --no-deps backend python3 ./manage.py catcher_setup
docker compose up -d
trap - ERR

# A guided upgrade records exact old image IDs for rollback. Some can become
# dangling after a pull, so do not prune while that recovery state is retained.
if [[ -f .catcher-upgrade/state.json ]]; then
    echo 'Keeping old images for the saved v3 upgrade rollback.'
else
    docker image prune --force
fi

docker compose ps --all
