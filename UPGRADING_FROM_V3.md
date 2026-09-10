# Upgrading Cinema Catcher 3 to Cinema Catcher 4

This is a major, offline upgrade. Catcher 3 uses PostgreSQL 13 and Catcher 4
uses PostgreSQL 18 with a different data-volume layout. PostgreSQL data files
cannot be upgraded by pointing the PostgreSQL 18 container at the old directory.
The database must be dumped by PostgreSQL 13 and restored into a newly
initialised PostgreSQL 18 cluster.

The supplied [`UPGRADE_POSTGRES_13_TO_18.sh`](UPGRADE_POSTGRES_13_TO_18.sh)
performs that migration, validates every application table, and preserves the
old physical database for rollback.

**Cloning v4 and running the upgrade script without arguments is not enough.**
The script migrates PostgreSQL only; the application upgrade follows in Phase 4.
It must use the **original v3 Compose file and database credentials**, and the
old PostgreSQL service must be running when the dump is made. Its current
default, `docker_compose_production.yml`, is not the filename in this installer
repository. Always supply the explicit paths shown below.

Follow Phases 1–6 in order, one command block at a time. Do not paste the entire
page into a terminal. Stop at any error or unexpected result; do not skip a
failed check and continue. The commands assume Ubuntu, Bash, the Docker Compose
plugin (`docker compose`), and the standard paths below. If your paths or
PostgreSQL version differ, stop and adapt the plan before starting downtime.

- [Phase 1 — log in and prepare](#phase-1-log-in-and-prepare)
- [Phase 2 — stop v3, back up, and start only the old database](#phase-2-stop-v3-back-up-and-start-only-the-old-database)
- [Phase 3 — migrate PostgreSQL](#phase-3-migrate-postgresql)
- [Phase 4 — install Catcher 4](#phase-4-install-catcher-4)
- [Phase 5 — acceptance checks](#phase-5-acceptance-checks)
- [Phase 6 — create the v4 recovery backup](#phase-6-create-the-v4-recovery-backup)

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

On 10 September 2026, a separate stopped v3 installation was inspected and
prepared using the approach below: an intact PostgreSQL 13 cluster and site
configuration were cold-backed-up, the copy was compared with the source, and
only PostgreSQL 13 was restarted. The database responded successfully. This
confirmed the missing default Compose filename and stopped-database blockers;
it was **preflight validation, not a completed v4 migration**. Table and migration
counts vary between sites; record your own baseline rather than expecting the
historical counts above.

## Phase 1: log in and prepare

### 1. Log in from your computer

Replace `CATCHER_SERVER_IP` with your server's address, and `devbot` with your
SSH account if different. Use the site's actual password; this guide does not
publish or require a shared password.

```bash
ssh devbot@CATCHER_SERVER_IP
```

If SSH reports **REMOTE HOST IDENTIFICATION HAS CHANGED**, stop. Verify the new
key through a trusted local console or administrator before updating your saved
key. Do not disable host-key checking to get past the warning. At a trusted
server console, its ED25519 fingerprint can be displayed with:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Once logged in, open one root Bash shell and keep it for the remaining phases:

```bash
sudo bash
set -Eeuo pipefail
umask 077
cd /opt/cinema-catcher-app
hostname
pwd
```

`sudo` asks for your account's password. All later commands run **on the Catcher
server in this root shell**, not on your own computer. The error-stop settings
are deliberate: if a block fails and this shell exits, investigate before
opening another root shell. A failed upgrade is not a reason to rerun every
block blindly.

Do not perform downtime through a VPN container you are about to stop or
replace. Arrange LAN SSH, console access, or another independent route first.

### 2. Confirm the old installation and storage

These are the standard paths used throughout this walkthrough:

```text
Installation:     /opt/cinema-catcher-app
v4 helper clone:  /opt/cinema-catcher-app-v4
Persistent data:  /opt/catcher
PostgreSQL 13:    /opt/catcher/postgresql/data
Database env:     /opt/cinema-catcher-app/database.env
```

Inspect the host:

```bash
cd /opt/cinema-catcher-app
test -f docker-compose.yml
test -f database.env
test -f .env
docker compose version
docker compose config --quiet
docker compose ps --all
docker compose config --images
df -h / /opt/catcher /opt/catcher/storage
du -sh /opt/catcher/postgresql/data
docker system df
test "$(tr -d '[:space:]' < /opt/catcher/postgresql/data/PG_VERSION)" = 13
```

An empty `docker compose ps --all` is acceptable if the old stack was already
taken down. Do not run v4 `start.sh` or `update.sh` to recreate it. If `.env` is
missing, recover the old site's settings before continuing; do not substitute
the v4 example settings blindly.

Verify that the **old** Compose configuration uses PostgreSQL 13 and the
expected bind mount, without printing database passwords:

```bash
docker compose config --format json | python3 -c '
import json, sys
c = json.load(sys.stdin)
p = c["services"]["pgdatabase"]
print("Compose project:", c.get("name"))
print("Database image:", p["image"])
print("Database mounts:", p.get("volumes", []))
assert p["image"].startswith("postgres:13"), "STOP: not the old PostgreSQL 13 configuration"
assert any(v.get("type") == "bind" and v.get("source") == "/opt/catcher/postgresql/data"
           and v.get("target", "").rstrip("/") == "/var/lib/postgresql/data"
           for v in p.get("volumes", [])), "STOP: unexpected PostgreSQL data mount"
'
```

Allow room for the original v3 cluster, the additional cold copy in Phase 2,
the new v4 cluster, service-data backups, a compressed dump, downloaded images,
and at least 1 GB of additional database headroom. Verify the intended media
filesystem is mounted; `/opt/catcher/storage` itself is not copied by this guide.

### 3. Download or refresh the v4 helper clone

Run this block for either a first attempt or an existing helper clone. It does
**not** update the live v3 repository:

```bash
if [[ ! -e /opt/cinema-catcher-app-v4 ]]; then
  git clone https://github.com/jamiegau/cinema-catcher-app.git \
    /opt/cinema-catcher-app-v4
else
  test -d /opt/cinema-catcher-app-v4/.git
  test -z "$(git -C /opt/cinema-catcher-app-v4 status --porcelain)"
  git -C /opt/cinema-catcher-app-v4 pull --ff-only
fi
bash -n /opt/cinema-catcher-app-v4/UPGRADE_POSTGRES_13_TO_18.sh
```

If the helper is modified or its pull fails, stop and resolve that; do not reset
it destructively. Its lack of a site `.env` is normal. It is a source of scripts
and templates, **not the directory from which to start your site's services**.

Inspect any prior migration attempt before changing data:

```bash
bash /opt/cinema-catcher-app-v4/UPGRADE_POSTGRES_13_TO_18.sh \
  --compose-file /opt/cinema-catcher-app/docker-compose.yml \
  --env-file /opt/cinema-catcher-app/database.env \
  --status
```

For a first attempt, expect PostgreSQL 13 at the original path and no PostgreSQL
18 data. A missing/stopped `pgdatabase` container is handled in Phase 2. If
PostgreSQL 18 data or multiple PostgreSQL 13 copies exist, investigate the prior
attempt first; do not choose a copy by timestamp alone or delete any directories.

## Phase 2: stop v3, back up, and start only the old database

### 1. Save the installation configuration

Finish active ingests, transfers and other jobs, and stop external database
writers before the maintenance window. Review what will be stopped. The block
below excludes an optional `netbird` service, but independent access is still
required for the later cutover.

```bash
cd /opt/cinema-catcher-app
upgrade_stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p /opt/catcher/upgrade-backups
rollback_dir="$(mktemp -d "/opt/catcher/upgrade-backups/$upgrade_stamp-XXXXXX")"
mkdir "$rollback_dir/service-data"
chmod 700 "$rollback_dir"

cp -a docker-compose.yml database.env .env "$rollback_dir/"
for upgrade_file in update.sh start.sh TAIL.sh; do
  if [[ -f "$upgrade_file" ]]; then
    cp -a "$upgrade_file" "$rollback_dir/"
  fi
done
if [[ -d netbird-client-data ]]; then
  cp -a netbird-client-data "$rollback_dir/"
fi
git status --short > "$rollback_dir/git-status-before.txt"
git diff > "$rollback_dir/local-installation.diff"
git rev-parse HEAD > "$rollback_dir/git-head-before.txt"
docker compose ps --all > "$rollback_dir/containers-before.txt"
docker compose images --format json > "$rollback_dir/images-before.json"
printf 'Record this rollback directory: %s\n' "$rollback_dir"
```

Record that exact path outside this terminal. Backups contain credentials and
must remain private. Keep an off-host backup as well; a second directory on the
same disk is not protection against disk failure.

### 2. Stop the old services and take a verified cold backup

This also works when the stack was already stopped or removed with
`docker compose down`. Do **not** use `down --volumes` or prune anything.

```bash
mapfile -t upgrade_services < <(docker compose config --services | grep -vx netbird)
printf 'Stopping: %s\n' "${upgrade_services[*]}"
test "${#upgrade_services[@]}" -gt 0
docker compose stop "${upgrade_services[@]}"
test -z "$(docker compose ps --status running --services | grep -vx netbird || true)"
if pgrep -x postgres >/dev/null; then
  printf 'STOP: a PostgreSQL process is still running; investigate before copying data.\n' >&2
  exit 1
fi

cp -a /opt/catcher/postgresql/data "$rollback_dir/postgres13-cold"
diff -qr /opt/catcher/postgresql/data "$rollback_dir/postgres13-cold"
for upgrade_service in redis aria2server ftpserver; do
  cp -a "/opt/catcher/$upgrade_service" "$rollback_dir/service-data/"
done
du -sh "$rollback_dir"
printf 'Verified cold backup: %s\n' "$rollback_dir"
```

`diff -qr` must finish successfully with no differences. Do not make this copy
while PostgreSQL is running. The migration script will also create its own
logical dump and retain the original physical cluster later.

### 3. Start only PostgreSQL 13 and record the baseline

This is the step required if you previously shut down the whole stack:

```bash
cd /opt/cinema-catcher-app
docker compose up -d --no-deps pgdatabase
upgrade_db_ready=false
for upgrade_attempt in $(seq 1 60); do
  if docker compose exec -T pgdatabase \
    sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    upgrade_db_ready=true
    break
  fi
  sleep 2
done
test "$upgrade_db_ready" = true
docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At \
    -c "SHOW server_version" \
    -c "SELECT pg_size_pretty(pg_database_size(current_database()))" \
    -c "SELECT count(*) FROM django_migrations"' |
  tee "$rollback_dir/database-baseline.txt"
```

Expect a `13.x` server version, database size and migration count. Leave
PostgreSQL running; leave the application stopped. If readiness or the query
fails, stop and inspect `docker compose logs --tail=100 pgdatabase`.

If the SSH connection drops, open a root Bash shell again, restore the
error-stop settings and `cd /opt/cinema-catcher-app`. Restore `rollback_dir`
using the recorded path (`read -r -p 'Existing rollback directory: ' rollback_dir`),
then check `test -f "$rollback_dir/docker-compose.yml"` and run the Phase 1
`--status` command. Resume only after identifying the actual completed phase;
do not rerun the backup or migration against an unknown state.

## Phase 3: migrate PostgreSQL

Run the v4 migration script against the still-active v3 Compose file:

```bash
bash /opt/cinema-catcher-app-v4/UPGRADE_POSTGRES_13_TO_18.sh \
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
read -r -p 'Paste the printed PostgreSQL 13 physical rollback path: ' postgres13_dir
read -r -p 'Paste the printed PostgreSQL 13 database archive path: ' postgres13_dump
test "$(tr -d '[:space:]' < "$postgres13_dir/PG_VERSION")" = 13
test -s "$postgres13_dump"
sha256sum -c "$postgres13_dump.sha256"

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
bash /opt/cinema-catcher-app-v4/UPGRADE_POSTGRES_13_TO_18.sh \
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

Do this **only after** the database script says the migration completed and was
validated. All Compose commands continue to run from the original installation,
so the project name, site `.env`, database credentials and relative mounts stay
with the site. Do not start a second stack from `cinema-catcher-app-v4`.

Prepare a v4 Compose file for review and compare it with the old site file:

```bash
cd /opt/cinema-catcher-app
test -s "$rollback_dir/postgres13-physical-path.txt"
test -s "$rollback_dir/postgres13-dump-path.txt"
cp /opt/cinema-catcher-app-v4/docker-compose.yml \
  "$rollback_dir/docker-compose-v4.review.yml"
diff -u docker-compose.yml "$rollback_dir/docker-compose-v4.review.yml" || test "$?" -eq 1
```

**Review checkpoint:** carry required site-specific mounts, networking and
other deliberate customisations into the reviewed v4 file. Do not carry over
the old PostgreSQL mount/image or v3 application images. The saved
`local-installation.diff` identifies local tracked edits. If you cannot explain
a customisation, stop and ask before replacing the file. Use an editor if needed:

```bash
nano "$rollback_dir/docker-compose-v4.review.yml"
```

Once reviewed, install the files. This explicit-copy approach also works with
an old repository containing local changes; it does not reset or fast-forward
that repository. A later `git pull` may require those local changes to be merged.

```bash
cp "$rollback_dir/docker-compose-v4.review.yml" ./docker-compose.yml
for upgrade_file in update.sh start.sh TAIL.sh UPGRADE_POSTGRES_13_TO_18.sh; do
  cp "/opt/cinema-catcher-app-v4/$upgrade_file" "./$upgrade_file"
done
chmod +x update.sh start.sh TAIL.sh
cmp database.env "$rollback_dir/database.env"
test -f .env
```

Keep the site's existing `.env` and `database.env`; **do not copy** either from
the helper clone or replace `.env` with `.env.example`. Check the existing
`.env` against the helper's `.env.example`, adding any missing required values:
`CATCHER_HOSTNAME`, `LOCAL_TIMEZONE_NAME`, and
`EXPOSED_IP_PROJECTION_NETWORK`. Retain the actual site values, not the examples.
Do not publish these files. To edit:

```bash
nano .env
```

Validate before starting containers:

```bash
docker compose config --quiet
docker compose config --format json | python3 -c '
import json, sys
c = json.load(sys.stdin)
p = c["services"]["pgdatabase"]
print("Database image:", p["image"])
print("Database mounts:", p.get("volumes", []))
assert p["image"].startswith("postgres:18"), "STOP: PostgreSQL 18 image not selected"
assert any(v.get("type") == "bind" and v.get("source") == "/opt/catcher/postgresql/18"
           and v.get("target", "").rstrip("/") == "/var/lib/postgresql"
           for v in p.get("volumes", [])), "STOP: wrong PostgreSQL 18 mount"
assert c["services"]["backend"]["image"] == "jamiegau/catcher_backend:4.0", "STOP: wrong backend image"
'
docker compose pull
```

If a stale `POSTGRES_IMAGE`, `POSTGRES_DATA_DIR`, or
`POSTGRES_CONTAINER_DATA_DIR` override selects the old layout, correct that
override before continuing. The migration script sets its v3 overrides only
inside its own process; it does not update the parent shell or the site's files.

Record the pulled backend image, including its digest (the old containers may
still reference v3 images until recreated):

```bash
docker image inspect jamiegau/catcher_backend:4.0 \
  --format '{{.Id}} {{json .RepoDigests}}' > "$rollback_dir/backend-v4-image.txt"
```

### 2. Start PostgreSQL 18 and Redis 8

```bash
docker compose up -d --no-deps pgdatabase redis

docker compose exec -T pgdatabase pg_isready
docker compose exec -T pgdatabase \
  sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version"'
docker compose exec -T redis redis-cli ping
```

Do not continue unless PostgreSQL reports 18 and Redis reports `PONG`.
If either service is still starting, repeat the checks after a few seconds;
inspect `docker compose logs --tail=100 pgdatabase redis` if it does not become
ready. Do not proceed through a restart loop. In particular, do not delete the
old Redis dump to resolve a loading or permission error; its backup is needed
for rollback. See the [Redis diagnostics](README.md#troubleshooting) and seek
help if its saved data cannot be loaded by the new service.

### 3. Apply Catcher 4 migrations

Run migrations as explicit one-off containers while the web application and
workers remain stopped. Start aria2 explicitly because `catcher_setup` also
sets the transfer bandwidth limit. Previously queued downloads may resume;
this is why active work should be finished before the maintenance window.

```bash
docker compose up -d --no-deps aria2server
curl -fsS --max-time 10 \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"upgrade-check","method":"aria2.getVersion"}' \
  http://127.0.0.1:16888/jsonrpc
```

Expect a JSON `result` containing the aria2 version, not a JSON `error`. If it is
still starting, repeat that check before continuing. Then:

```bash
docker compose run --rm --no-deps backend python3 ./manage.py migrate
docker compose run --rm --no-deps backend python3 ./manage.py migrate --check
docker compose run --rm --no-deps backend python3 ./manage.py check
docker compose run --rm --no-deps backend python3 ./manage.py catcher_setup
```

`migrate --check` is silent on success. `check` should finish with:

```text
System check identified no issues (0 silenced).
```

If a migration fails, save the complete traceback. Do not repeatedly start the
full stack. Check the applied state with:

```bash
docker compose run --rm --no-deps backend python3 ./manage.py showmigrations
```

### 4. Start the complete v4 stack

```bash
docker compose up -d
docker compose ps --all
docker compose exec -T nginx nginx -t
docker compose exec -T nginx nginx -s reload
```

All normal services should be `Up`; Samba should become healthy. NetBird is an
optional Compose profile and does not start unless explicitly requested:

```bash
docker compose --profile netbird up -d
```

The nginx reload refreshes backend addresses after container replacement. If
the web page loads but `/api/` returns `502`, check backend health and the nginx
logs rather than assuming the application is working because its HTML loads.

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
post_upgrade_dir="$rollback_dir/post-upgrade"
mkdir -p "$post_upgrade_dir"
chmod 700 "$post_upgrade_dir"

docker compose exec -T pgdatabase \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "$post_upgrade_dir/catcher_db-postgres18.dump"
test -s "$post_upgrade_dir/catcher_db-postgres18.dump"

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

Exit the root maintenance shell and then the SSH session when finished:

```bash
exit
exit
```

## Common first-attempt errors

| Message or symptom | What to do |
| --- | --- |
| `Compose file not found: docker_compose_production.yml` | Run the Phase 3 command with **both absolute paths**. Do not rename the old Compose file to satisfy the default. |
| `The pgdatabase service is not running` | Complete the Phase 2 backup, then run `docker compose up -d --no-deps pgdatabase` from `/opt/cinema-catcher-app`, not the helper clone. |
| Permission denied for `/var/run/docker.sock` | Use the root maintenance shell (`sudo bash`). Do not loosen Docker socket permissions. |
| Missing `.env` or unset site variables in the helper clone | Do not run the site from the helper. Keep the old installation's settings and run Compose there. |
| PostgreSQL 18 directory is not empty | Use the explicit-path `--status` command and inspect prior attempts. Do not delete or reuse an unverified cluster. |
| Old database does not contain the expected data | Stop. Compare verified backups and database contents before any migration or reset. |
| SSH host key changed | Verify the fingerprint out of band. Do not disable host-key checking. |
| Root shell or SSH session exited after an error | Recover the recorded rollback path and inspect `--status` before deciding where to resume. |

## Rolling back after a completed upgrade

Rollback returns Catcher to the start of the maintenance window. Stop operator
activity first. Set the exact paths printed by the upgrade script:

```bash
sudo bash
set -Eeuo pipefail
umask 077
cd /opt/cinema-catcher-app

read -r -p 'Existing rollback bundle directory: ' rollback_dir
read -r -p 'Verified PostgreSQL 13 physical rollback directory: ' postgres13_dir
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
for upgrade_file in update.sh start.sh TAIL.sh; do
  if [[ -f "$rollback_dir/$upgrade_file" ]]; then
    cp -a "$rollback_dir/$upgrade_file" "./$upgrade_file"
  fi
done
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
