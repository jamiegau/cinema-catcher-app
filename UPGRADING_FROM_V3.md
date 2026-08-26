# Upgrading Cinema Catcher 3 to Cinema Catcher 4

This is a major, offline upgrade. Catcher 3 uses PostgreSQL 13 and Catcher 4
uses PostgreSQL 18 with a different data-volume layout. PostgreSQL data files
cannot be upgraded by pointing the PostgreSQL 18 container at the old directory.
The database must be dumped by PostgreSQL 13 and restored into a newly
initialised PostgreSQL 18 cluster.

The supplied [`UPGRADE_POSTGRES_13_TO_18.sh`](UPGRADE_POSTGRES_13_TO_18.sh)
performs that migration, validates every application table, and preserves the
old physical database for rollback.

## Critical rules

1. Schedule a maintenance window and stop external processes that can write to
   Catcher.
2. Do not copy the v4 `docker-compose.yml` over the v3 file before the database
   migration.
3. Do not run the v4 `update.sh` on a v3 installation.
4. Do not use `git reset --hard` as an upgrade procedure.
5. Do not run `docker system prune --all --volumes`; retain the v3 images and
   every rollback artifact until v4 has completed operational testing.
6. A rollback restores the data captured at the start of the maintenance
   window. It does not automatically merge changes made after v4 goes live.

## What changes

| Component | Catcher 3 | Catcher 4 |
| --- | --- | --- |
| Backend image | `jamiegau/catcher_backend:3.0` | `jamiegau/catcher_backend:4.0` |
| PostgreSQL | 13.x | 18.x (`postgres:18-trixie`) |
| PostgreSQL host path | `/opt/catcher/postgresql/data` | `/opt/catcher/postgresql/18` |
| PostgreSQL container mount | `/var/lib/postgresql/data` | `/var/lib/postgresql` |
| Redis | RedisTimeSeries image | Redis 8 Trixie |
| Web UI | AngularJS `/app/` interface | Svelte interface at `/` |
| Workers | General and status workers | General, status, and dedicated KDM delivery workers |
| Monitoring | Application polling | Isolated polling plus host network monitor |

The migration retains users, configuration, assets, targets, KDM history,
audit data and schedules stored in PostgreSQL. Content below
`/opt/catcher/storage` is not copied; it remains in place and is re-mounted by
the v4 containers.

## Tested upgrade record

This process was exercised on 26 August 2026 against a real Catcher 3.0 site:

- PostgreSQL 13.1 was migrated to PostgreSQL 18.6;
- 43 application tables were restored with exact per-table row-count matches;
- Django migrations increased from 96 to 115;
- Catcher 4.0.37 started successfully;
- the UI, version API, Daphne endpoint, PostgreSQL, Redis, FTP, aria2, and three
  Celery queues were checked; and
- both a v3 pre-upgrade backup and a checksummed v4 post-upgrade backup were
  retained.

The run exposed a deferred PostgreSQL foreign-key trigger issue in the v4
`ingest.0006_retention_constraints` migration. Current v4 images include the
correction. Do not use an older locally cached `catcher_backend:4.0` image;
always pull the published image immediately before migration.

## Phase 1: preparation

### 1. Confirm the installation and storage

The examples assume:

```text
Installation:     /opt/cinema-catcher-app
Persistent data:  /opt/catcher
PostgreSQL 13:    /opt/catcher/postgresql/data
Database env:     /opt/cinema-catcher-app/database.env
```

Inspect the host:

```bash
cd /opt/cinema-catcher-app
sudo docker compose ps --all
sudo docker compose images
df -h / /opt/catcher /opt/catcher/storage
sudo du -sh /opt/catcher/postgresql/data
sudo docker system df
```

Allow space for the v3 physical cluster, v4 physical cluster, compressed dump,
and at least 1 GB of additional headroom. Large databases need proportionally
more room.

### 2. Download the v4 installer without altering v3

Clone the current installation repository beside the live installation:

```bash
cd /opt
sudo git clone https://github.com/jamiegau/cinema-catcher-app.git \
  cinema-catcher-app-v4
```

If this helper clone already exists, update it and confirm that it contains this
guide and the upgrade script:

```bash
cd /opt/cinema-catcher-app-v4
sudo git pull --ff-only
sudo bash -n UPGRADE_POSTGRES_13_TO_18.sh
```

### 3. Start a root maintenance shell

Using one root shell avoids creating backup files owned by several different
users. Review every path before pressing Enter.

```bash
sudo bash
cd /opt/cinema-catcher-app
```

Commands below assume this root shell. Exit it after the upgrade.

### 4. Record the v3 baseline

Bring up only the old database if the stack is stopped, then verify PostgreSQL
13 and record the database state:

```bash
docker compose up -d pgdatabase

docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version"'

docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
  "SELECT count(*) FROM django_migrations"'

docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
  "SELECT pg_size_pretty(pg_database_size(current_database()))"'
```

Do not continue unless the running server reports PostgreSQL 13 and
`/opt/catcher/postgresql/data/PG_VERSION` contains `13`.

## Phase 2: create the rollback bundle

Create a new timestamped bundle for this attempt:

```bash
upgrade_stamp="$(date +%Y%m%d-%H%M%S)"
rollback_dir="/opt/catcher/upgrade-backups/$upgrade_stamp"

mkdir -p "$rollback_dir/service-data"
chmod 700 "$rollback_dir"

cp -a docker-compose.yml "$rollback_dir/"
cp -a .env "$rollback_dir/" 2>/dev/null || true
cp -a database.env "$rollback_dir/"
cp -a update.sh start.sh TAIL.sh "$rollback_dir/" 2>/dev/null || true

cp -a /opt/catcher/redis "$rollback_dir/service-data/"
cp -a /opt/catcher/aria2server "$rollback_dir/service-data/"
cp -a /opt/catcher/ftpserver "$rollback_dir/service-data/"

docker compose ps --all > "$rollback_dir/containers-before.txt"
docker compose images --format json > "$rollback_dir/images-before.json"
du -sh /opt/catcher/* > "$rollback_dir/data-sizes-before.txt"
git rev-parse HEAD > "$rollback_dir/git-head-before.txt" 2>/dev/null || true
```

If the local installation contains tracked changes, preserve a patch:

```bash
git status --short > "$rollback_dir/git-status-before.txt" 2>/dev/null || true
git diff > "$rollback_dir/local-installation.diff" 2>/dev/null || true
```

Check that the bundle contains the expected files before starting downtime:

```bash
find "$rollback_dir" -maxdepth 3 -type f -ls
```

## Phase 3: migrate PostgreSQL

Run the v4 migration script against the still-active v3 Compose file:

```bash
/opt/cinema-catcher-app-v4/UPGRADE_POSTGRES_13_TO_18.sh \
  --compose-file /opt/cinema-catcher-app/docker-compose.yml \
  --env-file /opt/cinema-catcher-app/database.env
```

The script prints all resolved paths and requires the exact confirmation:

```text
UPGRADE POSTGRES 13 TO 18
```

Before entering it, confirm that:

- source data is `/opt/catcher/postgresql/data`;
- PostgreSQL 18 data is `/opt/catcher/postgresql/18`;
- the archive is below `/opt/catcher/postgresql-upgrade-backups`; and
- the physical rollback path is a new timestamped sibling of the source.

The script then:

1. pulls `postgres:18-trixie` before downtime;
2. stops the v3 database-writing application services;
3. queries the exact row count for every application table;
4. creates a PostgreSQL custom-format dump;
5. verifies the dump can be read and writes its SHA-256 checksum;
6. checks free space;
7. stops PostgreSQL 13 and moves its physical data to
   `/opt/catcher/postgresql/data.postgres13-<timestamp>`;
8. initialises PostgreSQL 18 in `/opt/catcher/postgresql/18`;
9. restores the database;
10. compares the schema table count and every per-table row count; and
11. stops its temporary PostgreSQL 18 container after validation.

On success it prints the exact dump and physical rollback paths. Record them:

```bash
postgres13_dir=/opt/catcher/postgresql/data.postgres13-<database-upgrade-timestamp>
postgres13_dump=/opt/catcher/postgresql-upgrade-backups/<database-upgrade-timestamp>/catcher_db-postgres13.dump

printf '%s\n' "$postgres13_dir" > "$rollback_dir/postgres13-physical-path.txt"
printf '%s\n' "$postgres13_dump" > "$rollback_dir/postgres13-dump-path.txt"
```

Do not delete either artifact.

### If the database script fails

The script attempts to stop the temporary v4 database, restore the original v3
data path, restart PostgreSQL 13, and restart only application services that
were running before the attempt.

Do not immediately retry. Inspect first:

```bash
/opt/cinema-catcher-app-v4/UPGRADE_POSTGRES_13_TO_18.sh \
  --compose-file /opt/cinema-catcher-app/docker-compose.yml \
  --env-file /opt/cinema-catcher-app/database.env \
  --status

docker compose ps --all
docker compose logs --tail=150 pgdatabase
```

Incomplete PostgreSQL 18 directories and temporary-container logs are preserved
with failure timestamps. Use `--reset-failed` only after identifying the known
good PostgreSQL 13 directory. The reset command renames incomplete data instead
of deleting it.

## Phase 4: install Catcher 4

### 1. Replace installation files

If the live repository is clean, fast-forward it after the database migration:

```bash
cd /opt/cinema-catcher-app
git status --short
git pull --ff-only
```

If tracked files have local modifications, do not overwrite them blindly. Use
the patch saved in the rollback bundle, compare it with the v4 helper clone, and
carry forward only required site-specific changes. The new v4 Compose file and
scripts can be copied explicitly after that review:

```bash
cp /opt/cinema-catcher-app-v4/docker-compose.yml ./docker-compose.yml
cp /opt/cinema-catcher-app-v4/update.sh ./update.sh
cp /opt/cinema-catcher-app-v4/start.sh ./start.sh
cp /opt/cinema-catcher-app-v4/TAIL.sh ./TAIL.sh
chmod +x update.sh start.sh TAIL.sh
```

The site-specific `.env` and `database.env` from v3 must remain in place.

Validate before starting containers:

```bash
docker compose config --quiet
docker compose pull
```

Record the pulled image digests in the rollback bundle:

```bash
docker compose images --format json > "$rollback_dir/images-v4.json"
```

### 2. Start PostgreSQL 18 and Redis 8

```bash
docker compose up -d pgdatabase redis

docker compose exec -T pgdatabase pg_isready
docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version"'
docker compose exec -T redis redis-cli ping
```

Do not continue unless PostgreSQL reports 18 and Redis reports `PONG`.

### 3. Apply Catcher 4 migrations

Run migrations as explicit one-off containers while the web application and
workers remain stopped:

```bash
docker compose run --rm backend python3 ./manage.py migrate
docker compose run --rm backend python3 ./manage.py migrate --check
docker compose run --rm backend python3 ./manage.py check
docker compose run --rm backend python3 ./manage.py catcher_setup
```

`migrate --check` is silent on success. `check` should finish with:

```text
System check identified no issues (0 silenced).
```

If a migration fails, save the complete traceback. Do not repeatedly start the
full stack. Check the applied state with:

```bash
docker compose run --rm backend python3 ./manage.py showmigrations
```

### 4. Start the complete v4 stack

```bash
docker compose up -d
docker compose ps --all
```

All normal services should be `Up`; Samba should become healthy. NetBird is an
optional Compose profile and does not start unless explicitly requested:

```bash
docker compose --profile netbird up -d
```

## Phase 5: acceptance checks

### API and web services

```bash
curl -fsS -o /dev/null -w 'UI HTTP %{http_code}\n' http://127.0.0.1/
curl -fsS http://127.0.0.1/api/catcher/GetVersion/
curl -fsS -o /dev/null -w 'Daphne HTTP %{http_code}\n' \
  http://127.0.0.1:8001/api/catcher/GetVersion/
```

Expected results are HTTP 200 and a `4.x` version response.

### Application and database

```bash
docker compose exec -T backend python3 manage.py migrate --check
docker compose exec -T backend python3 manage.py check
docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
  "SELECT count(*) FROM django_migrations"'
```

### Background queues

```bash
docker compose exec -T worker \
  celery -A dcinenet_catcher inspect active_queues
```

Confirm the workers report their isolated queues:

- `worker`: `default`;
- `worker_mon`: `status_monitor`; and
- `worker_kdm`: `kdm_delivery`.

### FTP and aria2

```bash
timeout 3 bash -c 'exec 3<>/dev/tcp/127.0.0.1/21; head -1 <&3'

curl -fsS --max-time 5 \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"health","method":"aria2.getVersion"}' \
  http://127.0.0.1:16888/jsonrpc
```

### Browser workflow

Sign in with an existing user and verify:

1. Dashboard loads storage and recent asset information.
2. Media Assets can open an existing DCP and its CPL metadata.
3. Player Status connects its socket and updates an available player.
4. AutoKDM configuration, sources, targets, and KDM history are retained.
5. Playout Audit and Device Discovery retain their configuration.
6. Background Processes opens immediately and shows task progress.
7. The dark/light theme switch works.
8. Site-specific FTP, ingest, mail, player and reporting workflows succeed.

Review recent failures and restart counts after the stack has been running for
several minutes:

```bash
docker compose ps -q | xargs docker inspect \
  --format '{{.Name}} restart={{.RestartCount}} status={{.State.Status}}'

docker compose logs --since=10m 2>&1 |
  grep -Ei 'traceback|critical|segmentation|panic|fatal|internal server error' || true
```

## Phase 6: create the v4 recovery backup

After acceptance checks pass, create and verify a PostgreSQL 18 dump:

```bash
set -a
. /opt/cinema-catcher-app/database.env
set +a

post_upgrade_dir="$rollback_dir/post-upgrade"
mkdir -p "$post_upgrade_dir"
chmod 700 "$post_upgrade_dir"

docker compose exec -T pgdatabase \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc |
  tee "$post_upgrade_dir/catcher_db-postgres18.dump" >/dev/null

sha256sum "$post_upgrade_dir/catcher_db-postgres18.dump" |
  tee "$post_upgrade_dir/catcher_db-postgres18.dump.sha256"
sha256sum -c "$post_upgrade_dir/catcher_db-postgres18.dump.sha256"

docker compose exec -T pgdatabase pg_restore --list \
  < "$post_upgrade_dir/catcher_db-postgres18.dump" >/dev/null
```

Also capture the final container and image state:

```bash
docker compose ps --all --format json > "$rollback_dir/containers-v4-final.json"
docker compose images --format json > "$rollback_dir/images-v4-final.json"
```

Keep the v3 physical cluster, v3 logical dump, rollback bundle, old Compose
file, and old Docker images until the site owner accepts the upgrade and the
normal backup cycle has captured v4.

## Rolling back after a completed upgrade

Rollback returns Catcher to the start of the maintenance window. Stop operator
activity first. Set the exact paths printed by the upgrade script:

```bash
sudo bash
cd /opt/cinema-catcher-app

rollback_dir=/opt/catcher/upgrade-backups/<upgrade-timestamp>
postgres13_dir=/opt/catcher/postgresql/data.postgres13-<database-upgrade-timestamp>
rollback_stamp="$(date +%Y%m%d-%H%M%S)"

test -f "$rollback_dir/docker-compose.yml"
test "$(tr -d '[:space:]' < "$postgres13_dir/PG_VERSION")" = 13
```

Stop v4 and preserve its state without deleting it:

```bash
docker compose down

mv /opt/catcher/postgresql/18 \
  "/opt/catcher/postgresql/18.rolled-back-$rollback_stamp"

if [[ -e /opt/catcher/postgresql/data ]]; then
  printf 'STOP: /opt/catcher/postgresql/data already exists; inspect it first.\n' >&2
  exit 1
fi
cp -a "$postgres13_dir" /opt/catcher/postgresql/data
```

Restore the v3-compatible service data, preserving the v4 copies:

```bash
mv /opt/catcher/redis "/opt/catcher/redis.post-v4-$rollback_stamp"
cp -a "$rollback_dir/service-data/redis" /opt/catcher/redis

mv /opt/catcher/aria2server \
  "/opt/catcher/aria2server.post-v4-$rollback_stamp"
cp -a "$rollback_dir/service-data/aria2server" /opt/catcher/aria2server

mv /opt/catcher/ftpserver \
  "/opt/catcher/ftpserver.post-v4-$rollback_stamp"
cp -a "$rollback_dir/service-data/ftpserver" /opt/catcher/ftpserver
```

Restore the v3 installation configuration:

```bash
cp "$rollback_dir/docker-compose.yml" ./docker-compose.yml
cp "$rollback_dir/database.env" ./database.env
if [[ -f "$rollback_dir/.env" ]]; then
  cp "$rollback_dir/.env" ./.env
fi
```

Start only PostgreSQL 13 and Redis first:

```bash
docker compose up -d pgdatabase redis
docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version"'
docker compose exec -T redis redis-cli ping
```

Do not start the v3 application unless PostgreSQL reports 13. Then:

```bash
docker compose up -d
docker compose ps --all
```

Retain the preserved PostgreSQL 18 directory and its logical dump. Data created
after v4 cutover may need a separate recovery or reconciliation decision.

## Upgrade record template

Record the following for every site:

```text
Site:
Maintenance start/end:
Operator:
v3 Catcher version:
v3 PostgreSQL version:
v3 database size and migration count:
Rollback bundle:
PostgreSQL 13 physical snapshot:
PostgreSQL 13 logical dump and checksum:
v4 image digests:
v4 Catcher version:
v4 PostgreSQL version:
v4 migration count:
Per-table validation result:
Post-upgrade dump and checksum:
Acceptance checks completed:
Problems and resolutions:
Rollback deadline/retention decision:
```
