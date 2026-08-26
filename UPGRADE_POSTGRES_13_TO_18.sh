#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="docker_compose_production.yml"
ENV_FILE="database.env"
OLD_DATA_DIR="/opt/catcher/postgresql/data"
NEW_DATA_DIR="/opt/catcher/postgresql/18"
BACKUP_ROOT="/opt/catcher/postgresql-upgrade-backups"
NEW_IMAGE="postgres:18-trixie"
OLD_IMAGE="postgres:13-bookworm"
TEMP_CONTAINER="catcher-postgres18-upgrade"
ASSUME_YES=false
MODE="upgrade"
ROLLBACK_ARMED=false
RESTORE_FROM=""

# The checked-in Compose file targets PostgreSQL 18. During migration and any
# rollback, force Compose to describe the still-active PostgreSQL 13 service.
# These variables match the parameterized pgdatabase image and volume entries.
use_postgres13_compose() {
    export POSTGRES_IMAGE="$OLD_IMAGE"
    export POSTGRES_DATA_DIR="$OLD_DATA_DIR"
    export POSTGRES_CONTAINER_DATA_DIR="/var/lib/postgresql/data"
}

usage() {
    cat <<'EOF'
Usage: sudo ./UPGRADE_POSTGRES_13_TO_18.sh [options]

Migrates the Catcher PostgreSQL 13 database to PostgreSQL 18 using a compressed
PostgreSQL archive and a temporary PostgreSQL 18 container. The script does not edit
the Docker Compose file; it prints the required image and volume changes after
the restored database has been validated.

Options:
  -f, --compose-file FILE   Compose file to use (default: docker_compose_production.yml)
      --env-file FILE       PostgreSQL env file (default: database.env)
      --old-data-dir DIR    Existing PostgreSQL 13 data directory
      --new-data-dir DIR    New PostgreSQL 18 volume directory
      --backup-root DIR     Directory for database archives and migration records
      --new-image IMAGE     PostgreSQL 18 image (default: postgres:18-trixie)
      --status              Inspect containers and all PostgreSQL data copies
      --reset-failed        Restore a verified PostgreSQL 13 layout for another attempt
      --restore-from DIR    PostgreSQL 13 directory to use with --reset-failed
  -y, --yes                 Skip the typed confirmation
  -h, --help                Show this help

The existing PostgreSQL 13 directory is moved to a timestamped sibling and is
not deleted. On failure after that move, the script attempts to restore the old
directory and restart the PostgreSQL 13 service.

Run --status first after a failed attempt. --reset-failed never deletes a data
directory: incomplete PostgreSQL 18 data is renamed with a timestamp suffix.
EOF
}

log() {
    printf '[postgres-upgrade] %s\n' "$*"
}

fail() {
    printf '[postgres-upgrade] ERROR: %s\n' "$*" >&2
    if [[ "${ROLLBACK_ARMED:-false}" == true ]]; then
        rollback_on_error 1
    fi
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--compose-file)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --env-file)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            ENV_FILE="$2"
            shift 2
            ;;
        --old-data-dir)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            OLD_DATA_DIR="$2"
            shift 2
            ;;
        --new-data-dir)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            NEW_DATA_DIR="$2"
            shift 2
            ;;
        --backup-root)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            BACKUP_ROOT="$2"
            shift 2
            ;;
        --new-image)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            NEW_IMAGE="$2"
            shift 2
            ;;
        --status)
            MODE="status"
            shift
            ;;
        --reset-failed)
            MODE="reset"
            shift
            ;;
        --restore-from)
            [[ $# -ge 2 ]] || fail "$1 requires a value"
            RESTORE_FROM="$2"
            shift 2
            ;;
        -y|--yes)
            ASSUME_YES=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "Unknown argument: $1"
            ;;
    esac
done

pg_version_in() {
    local directory="$1"
    local version_file=""

    [[ -d "$directory" ]] || return 1
    if [[ -f "$directory/PG_VERSION" ]]; then
        version_file="$directory/PG_VERSION"
    else
        version_file="$(find "$directory" -maxdepth 4 -type f -name PG_VERSION -print -quit 2>/dev/null || true)"
    fi
    [[ -n "$version_file" ]] || return 1
    tr -d '[:space:]' < "$version_file"
}

directory_has_contents() {
    [[ -d "$1" ]] && [[ -n "$(find "$1" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]
}

compose_service_image() {
    docker compose -f "$COMPOSE_FILE" config 2>/dev/null | awk '
        /^  pgdatabase:$/ { in_service=1; next }
        in_service && /^  [^ ]/ { exit }
        in_service && /^    image:/ { print $2; exit }
    '
}

show_status() {
    local found=false
    local path=""
    local version=""
    local container_id=""
    local server_version=""
    local size=""
    local old_backup_found=false

    printf 'PostgreSQL upgrade status\n'
    printf '  Compose file: %s\n' "$COMPOSE_FILE"
    if [[ -f "$COMPOSE_FILE" ]]; then
        printf '  Compose image: %s\n' "$(compose_service_image || printf 'unknown')"
    else
        printf '  Compose image: unavailable (file not found)\n'
    fi

    printf '\nData directories:\n'
    for path in \
        "$OLD_DATA_DIR" \
        "${OLD_DATA_DIR}.postgres13-"* \
        "$NEW_DATA_DIR" \
        "${NEW_DATA_DIR}.failed-"* \
        "${NEW_DATA_DIR}.reset-"*; do
        [[ -e "$path" ]] || continue
        found=true
        [[ "$path" == "${OLD_DATA_DIR}.postgres13-"* ]] && old_backup_found=true
        version="$(pg_version_in "$path" 2>/dev/null || printf 'no PG_VERSION found')"
        size="$(du -sh "$path" 2>/dev/null | awk '{print $1}' || printf 'unknown')"
        printf '  %-62s PostgreSQL %-20s size=%s\n' "$path" "$version" "$size"
    done
    [[ "$found" == true ]] || printf '  No PostgreSQL data directories found.\n'

    printf '\nDatabase archives:\n'
    found=false
    if [[ -d "$BACKUP_ROOT" ]]; then
        while IFS= read -r path; do
            found=true
            printf '  %s\n' "$path"
        done < <(find "$BACKUP_ROOT" -maxdepth 2 -type f \
            \( -name '*-postgres13.dump' -o -name '*-postgres13.sql' \) -print 2>/dev/null | sort)
    fi
    [[ "$found" == true ]] || printf '  No database upgrade archives found.\n'

    printf '\nContainers:\n'
    if docker inspect "$TEMP_CONTAINER" >/dev/null 2>&1; then
        docker inspect "$TEMP_CONTAINER" --format \
            '  {{.Name}}: image={{.Config.Image}} state={{.State.Status}} exit={{.State.ExitCode}}'
        if [[ "$(docker inspect "$TEMP_CONTAINER" --format '{{.State.Status}}' 2>/dev/null)" == exited ]]; then
            printf '  Last PostgreSQL 18 log lines:\n'
            docker logs --tail 12 "$TEMP_CONTAINER" 2>&1 | sed 's/^/    /'
        fi
    else
        printf '  %s: absent\n' "$TEMP_CONTAINER"
    fi

    if [[ -f "$COMPOSE_FILE" ]]; then
        container_id="$(docker compose -f "$COMPOSE_FILE" ps -aq pgdatabase 2>/dev/null || true)"
        if [[ -n "$container_id" ]]; then
            docker inspect "$container_id" --format \
                '  pgdatabase: image={{.Config.Image}} state={{.State.Status}} exit={{.State.ExitCode}}'
            if [[ "$(docker inspect "$container_id" --format '{{.State.Running}}' 2>/dev/null)" == true ]]; then
                server_version="$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
                    sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version"' 2>/dev/null || true)"
                [[ -n "$server_version" ]] && printf '  Running PostgreSQL server: %s\n' "$server_version"
            fi
        else
            printf '  pgdatabase: absent\n'
        fi
    fi

    printf '\nInterpretation:\n'
    if [[ "$(pg_version_in "$OLD_DATA_DIR" 2>/dev/null || true)" == 13 ]]; then
        printf '  The normal data path contains PostgreSQL 13. The upgrade has not been committed.\n'
        if [[ "$old_backup_found" == true ]]; then
            printf '  WARNING: Another PostgreSQL 13 physical backup also exists. The normal path\n'
            printf '  may be a newly initialized empty cluster. Compare both before resetting, then\n'
            printf '  use --restore-from DIR to select the known-good source explicitly.\n'
        fi
        if directory_has_contents "$NEW_DATA_DIR"; then
            printf '  PostgreSQL 18 also has incomplete data that must be reset before retrying.\n'
        else
            printf '  The source layout is ready; PostgreSQL 13 must be running before retrying.\n'
        fi
    elif [[ "$(pg_version_in "$NEW_DATA_DIR" 2>/dev/null || true)" == 18 ]]; then
        printf '  PostgreSQL 18 data exists at the new path. Validate it before resetting anything.\n'
    else
        printf '  No active PostgreSQL 13 or 18 layout was identified. Do not move files manually.\n'
    fi
}

reset_failed_attempt() {
    local timestamp="$(date +%Y%m%d-%H%M%S)"
    local source_backup=""
    local source_version=""
    local compose_image=""
    local preserved_new="${NEW_DATA_DIR}.reset-${timestamp}"
    local candidate=""
    local active_old_preserved="${OLD_DATA_DIR}.reset-${timestamp}"
    local backup_count=0

    [[ -f "$COMPOSE_FILE" ]] || fail "Compose file not found: $COMPOSE_FILE"
    compose_image="$(compose_service_image)"
    [[ "$compose_image" =~ postgres:13([.-]|$) ]] || fail \
        "The pgdatabase Compose image is '$compose_image', not PostgreSQL 13. Change it back before resetting."

    if [[ -n "$RESTORE_FROM" ]]; then
        [[ -d "$RESTORE_FROM" ]] || fail "Requested restore directory not found: $RESTORE_FROM"
        [[ "$(pg_version_in "$RESTORE_FROM" 2>/dev/null || true)" == 13 ]] || fail \
            "Requested restore directory is not PostgreSQL 13 data: $RESTORE_FROM"
        source_backup="$RESTORE_FROM"
    else
        for candidate in "${OLD_DATA_DIR}.postgres13-"*; do
            [[ -d "$candidate" ]] || continue
            [[ "$(pg_version_in "$candidate" 2>/dev/null || true)" == 13 ]] || continue
            backup_count=$((backup_count + 1))
            if [[ -z "$source_backup" ]] || [[ "$candidate" > "$source_backup" ]]; then
                source_backup="$candidate"
            fi
        done

        source_version="$(pg_version_in "$OLD_DATA_DIR" 2>/dev/null || true)"
        if [[ "$source_version" == 13 ]] && (( backup_count > 0 )); then
            fail "Both $OLD_DATA_DIR and a PostgreSQL 13 physical backup exist. Compare them and rerun with --restore-from DIR"
        elif [[ "$source_version" == 13 ]]; then
            source_backup=""
            log "Verified PostgreSQL 13 at $OLD_DATA_DIR"
        elif [[ -e "$OLD_DATA_DIR" ]]; then
            fail "$OLD_DATA_DIR exists but is not PostgreSQL 13 data; rerun with a verified --restore-from DIR"
        else
            [[ -n "$source_backup" ]] || fail "No verified PostgreSQL 13 physical backup was found"
        fi
    fi

    docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1 || true
    docker compose -f "$COMPOSE_FILE" stop pgdatabase >/dev/null 2>&1 || true

    if [[ -n "$source_backup" ]]; then
        if [[ "$source_backup" != "$OLD_DATA_DIR" ]] && [[ -e "$OLD_DATA_DIR" ]]; then
            log "Preserving the current PostgreSQL 13 path at $active_old_preserved"
            mv "$OLD_DATA_DIR" "$active_old_preserved"
        fi
        log "Restoring PostgreSQL 13 data from $source_backup"
        if [[ "$source_backup" != "$OLD_DATA_DIR" ]]; then
            mv "$source_backup" "$OLD_DATA_DIR"
        fi
    fi

    if directory_has_contents "$NEW_DATA_DIR"; then
        log "Preserving incomplete PostgreSQL 18 data at $preserved_new"
        mv "$NEW_DATA_DIR" "$preserved_new"
    elif [[ -d "$NEW_DATA_DIR" ]]; then
        rmdir "$NEW_DATA_DIR"
    fi

    log "Starting PostgreSQL 13"
    docker compose -f "$COMPOSE_FILE" up -d pgdatabase
    for _ in $(seq 1 60); do
        if docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
            sh -c 'pg_isready -U "$POSTGRES_USER" -d postgres' >/dev/null 2>&1; then
            break
        fi
        sleep 2
    done
    source_version="$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
        sh -c 'psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version_num"' 2>/dev/null | cut -c1-2 || true)"
    [[ "$source_version" == 13 ]] || fail "PostgreSQL 13 did not start successfully; application services remain stopped"

    log "Reset completed. PostgreSQL 13 is running and the upgrade can be retried."
    show_status
}

[[ $EUID -eq 0 ]] || fail "Run this script with sudo so it can protect and move /opt/catcher data."
command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose is not available"
if [[ "$MODE" == status ]]; then
    show_status
    exit 0
fi
if [[ "$MODE" == reset ]]; then
    use_postgres13_compose
    reset_failed_attempt
    exit 0
fi
use_postgres13_compose
if command -v sha256sum >/dev/null 2>&1; then
    SHA256_COMMAND=(sha256sum)
elif command -v shasum >/dev/null 2>&1; then
    SHA256_COMMAND=(shasum -a 256)
else
    fail "Neither sha256sum nor shasum is installed"
fi
[[ -f "$COMPOSE_FILE" ]] || fail "Compose file not found: $COMPOSE_FILE"
[[ -f "$ENV_FILE" ]] || fail "Environment file not found: $ENV_FILE"
[[ -d "$OLD_DATA_DIR" ]] || fail "PostgreSQL 13 data directory not found: $OLD_DATA_DIR"
[[ -f "$OLD_DATA_DIR/PG_VERSION" ]] || fail "$OLD_DATA_DIR does not contain PG_VERSION"

SOURCE_DATA_MAJOR="$(tr -d '[:space:]' < "$OLD_DATA_DIR/PG_VERSION")"
[[ "$SOURCE_DATA_MAJOR" == "13" ]] || fail "Expected PostgreSQL 13 data, found PG_VERSION=$SOURCE_DATA_MAJOR"

if [[ -e "$NEW_DATA_DIR" ]] && [[ -n "$(find "$NEW_DATA_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    fail "New PostgreSQL directory is not empty: $NEW_DATA_DIR"
fi

SOURCE_CONTAINER_ID="$(docker compose -f "$COMPOSE_FILE" ps -q pgdatabase)"
[[ -n "$SOURCE_CONTAINER_ID" ]] || fail "The pgdatabase service is not running"

SOURCE_SERVER_MAJOR="$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
    psql -U "$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase printenv POSTGRES_USER)" \
    -d postgres -Atqc "SHOW server_version_num" | cut -c1-2)"
[[ "$SOURCE_SERVER_MAJOR" == "13" ]] || fail "Running server is not PostgreSQL 13 (version prefix: $SOURCE_SERVER_MAJOR)"

POSTGRES_USER="$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase printenv POSTGRES_USER | tr -d '\r\n')"
POSTGRES_DB="$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase printenv POSTGRES_DB | tr -d '\r\n')"
[[ -n "$POSTGRES_USER" ]] || fail "POSTGRES_USER is empty"
[[ -n "$POSTGRES_DB" ]] || fail "POSTGRES_DB is empty"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
SQL_DUMP="$BACKUP_DIR/${POSTGRES_DB}-postgres13.dump"
CHECKSUM_FILE="$SQL_DUMP.sha256"
POSTGRES18_INIT_LOG="$BACKUP_DIR/postgres18-init.log"
OLD_DATA_BACKUP="${OLD_DATA_DIR}.postgres13-${TIMESTAMP}"
FAILED_NEW_DATA="${NEW_DATA_DIR}.failed-${TIMESTAMP}"

DATA_KB="$(du -sk "$OLD_DATA_DIR" | awk '{print $1}')"

ALL_SERVICES=()
while IFS= read -r service; do
    ALL_SERVICES+=("$service")
done < <(docker compose -f "$COMPOSE_FILE" config --services)
APP_SERVICES=()
RUNNING_APP_SERVICES=()
for candidate in backend backendc worker worker_mon worker_kdm beat network-monitor; do
    for service in "${ALL_SERVICES[@]}"; do
        if [[ "$candidate" == "$service" ]]; then
            APP_SERVICES+=("$candidate")
            if [[ -n "$(docker compose -f "$COMPOSE_FILE" ps -q "$candidate" 2>/dev/null || true)" ]]; then
                RUNNING_APP_SERVICES+=("$candidate")
            fi
            break
        fi
    done
done

cat <<EOF

PostgreSQL upgrade plan
  Compose file:       $COMPOSE_FILE
  Database:           $POSTGRES_DB
  Database user:      $POSTGRES_USER
  Source data:        $OLD_DATA_DIR
  Physical rollback:  $OLD_DATA_BACKUP
  Database archive:   $SQL_DUMP
  PostgreSQL 18 data: $NEW_DATA_DIR
  New image:          $NEW_IMAGE

The application will remain stopped after a successful migration until the
Compose image and volume lines have been changed as printed at the end.
EOF

if [[ "$ASSUME_YES" != true ]]; then
    printf '\nType UPGRADE POSTGRES 13 TO 18 to continue: '
    read -r confirmation
    [[ "$confirmation" == "UPGRADE POSTGRES 13 TO 18" ]] || fail "Confirmation did not match; nothing was changed"
fi

MOVED_OLD_DATA=false
MIGRATION_COMPLETE=false

rollback_on_error() {
    local exit_code="${1:-1}"
    ROLLBACK_ARMED=false
    if [[ "$MIGRATION_COMPLETE" == true ]]; then
        return
    fi

    printf '\n[postgres-upgrade] Migration failed; attempting rollback.\n' >&2
    if docker inspect "$TEMP_CONTAINER" >/dev/null 2>&1 && [[ -n "${POSTGRES18_INIT_LOG:-}" ]]; then
        mkdir -p "$(dirname "$POSTGRES18_INIT_LOG")" 2>/dev/null || true
        docker logs "$TEMP_CONTAINER" > "$POSTGRES18_INIT_LOG" 2>&1 || true
        chmod 600 "$POSTGRES18_INIT_LOG" 2>/dev/null || true
        printf '[postgres-upgrade] PostgreSQL 18 logs preserved at %s\n' "$POSTGRES18_INIT_LOG" >&2
    fi
    docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1 || true

    if [[ "$MOVED_OLD_DATA" == true ]]; then
        if [[ -d "$NEW_DATA_DIR" ]]; then
            mv "$NEW_DATA_DIR" "$FAILED_NEW_DATA" || true
            printf '[postgres-upgrade] Incomplete PostgreSQL 18 data preserved at %s\n' "$FAILED_NEW_DATA" >&2
        fi
        if [[ ! -e "$OLD_DATA_DIR" ]] && [[ -d "$OLD_DATA_BACKUP" ]]; then
            mv "$OLD_DATA_BACKUP" "$OLD_DATA_DIR" || true
        fi
    fi

    docker compose -f "$COMPOSE_FILE" up -d pgdatabase >/dev/null 2>&1 || true
    if [[ ${#RUNNING_APP_SERVICES[@]} -gt 0 ]]; then
        docker compose -f "$COMPOSE_FILE" start "${RUNNING_APP_SERVICES[@]}" >/dev/null 2>&1 || true
    fi
    printf '[postgres-upgrade] PostgreSQL 13 rollback attempted. Inspect the services before retrying.\n' >&2
    exit "$exit_code"
}
ROLLBACK_ARMED=true
trap 'rollback_on_error $?' ERR
trap 'rollback_on_error 130' INT
trap 'rollback_on_error 143' TERM

log "Pulling $NEW_IMAGE before downtime begins"
docker pull "$NEW_IMAGE"

if [[ ${#APP_SERVICES[@]} -gt 0 ]]; then
    log "Stopping database-writing application services: ${APP_SERVICES[*]}"
    docker compose -f "$COMPOSE_FILE" stop "${APP_SERVICES[@]}"
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

SOURCE_TABLE_COUNT="$(docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema');")"

SOURCE_ROW_COUNTS="$BACKUP_DIR/source-table-row-counts.tsv"
TARGET_ROW_COUNTS="$BACKUP_DIR/target-table-row-counts.tsv"
ROW_COUNT_SQL="$BACKUP_DIR/table-row-counts.sql"

# Writers are stopped, so exact per-table counts provide a stable, much stronger
# restore check than comparing the number of schema objects alone.
docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
    "SELECT format('SELECT %L, count(*) FROM %I.%I;', table_schema || '.' || table_name, table_schema, table_name)
       FROM information_schema.tables
      WHERE table_type = 'BASE TABLE'
        AND table_schema NOT IN ('pg_catalog', 'information_schema')
      ORDER BY table_schema, table_name;" > "$ROW_COUNT_SQL"
[[ -s "$ROW_COUNT_SQL" ]] || fail "Could not generate the source table row-count query"
docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtF $'\t' < "$ROW_COUNT_SQL" > "$SOURCE_ROW_COUNTS"
chmod 600 "$ROW_COUNT_SQL" "$SOURCE_ROW_COUNTS"

log "Creating compressed PostgreSQL 13 archive at $SQL_DUMP"
docker compose -f "$COMPOSE_FILE" exec -T pgdatabase \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --format=custom --compress=6 --create --no-owner --no-privileges > "$SQL_DUMP"
chmod 600 "$SQL_DUMP"
[[ -s "$SQL_DUMP" ]] || fail "Database archive is empty"
docker compose -f "$COMPOSE_FILE" exec -T pgdatabase pg_restore --list < "$SQL_DUMP" >/dev/null
"${SHA256_COMMAND[@]}" "$SQL_DUMP" > "$CHECKSUM_FILE"

ARCHIVE_KB="$(du -k "$SQL_DUMP" | awk '{print $1}')"
AVAILABLE_KB="$(df -Pk "$(dirname "$OLD_DATA_DIR")" | awk 'NR==2 {print $4}')"
HEADROOM_KB=$((DATA_KB / 5))
(( HEADROOM_KB >= 1048576 )) || HEADROOM_KB=1048576
REQUIRED_KB=$((DATA_KB + HEADROOM_KB))
if (( AVAILABLE_KB < REQUIRED_KB )); then
    fail "Insufficient space after creating the compressed archive ($((ARCHIVE_KB / 1024)) MiB). Need approximately $((REQUIRED_KB / 1024)) MiB for PostgreSQL 18 and headroom, have $((AVAILABLE_KB / 1024)) MiB. Move --backup-root to another filesystem or free space, then retry."
fi
log "Space check passed: archive=$((ARCHIVE_KB / 1024)) MiB, available=$((AVAILABLE_KB / 1024)) MiB, target allowance=$((REQUIRED_KB / 1024)) MiB"

log "Stopping PostgreSQL 13"
docker compose -f "$COMPOSE_FILE" stop pgdatabase

log "Moving PostgreSQL 13 data to $OLD_DATA_BACKUP"
mv "$OLD_DATA_DIR" "$OLD_DATA_BACKUP"
MOVED_OLD_DATA=true

mkdir -p "$NEW_DATA_DIR"
# PostgreSQL 18 uses a versioned PGDATA below /var/lib/postgresql. The bind
# mount parent must remain traversable by the postgres user; PGDATA itself is
# initialized with restrictive permissions by the official image.
chmod 755 "$NEW_DATA_DIR"

docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1 || true
log "Starting temporary PostgreSQL 18 container"
docker run -d \
    --name "$TEMP_CONTAINER" \
    --shm-size 256m \
    --env-file "$ENV_FILE" \
    --mount "type=bind,src=$NEW_DATA_DIR,dst=/var/lib/postgresql" \
    "$NEW_IMAGE" >/dev/null

log "Waiting for PostgreSQL 18 to initialise"
ready=false
for _ in $(seq 1 90); do
    if docker exec "$TEMP_CONTAINER" pg_isready -U "$POSTGRES_USER" -d postgres >/dev/null 2>&1; then
        ready=true
        break
    fi
    if [[ "$(docker inspect "$TEMP_CONTAINER" --format '{{.State.Running}}' 2>/dev/null || true)" != true ]]; then
        fail "PostgreSQL 18 exited during initialization; inspect $POSTGRES18_INIT_LOG"
    fi
    sleep 2
done
[[ "$ready" == true ]] || fail "PostgreSQL 18 did not become ready within three minutes"

TARGET_SERVER_MAJOR="$(docker exec "$TEMP_CONTAINER" psql -U "$POSTGRES_USER" -d postgres -Atqc "SHOW server_version_num" | cut -c1-2)"
[[ "$TARGET_SERVER_MAJOR" == "18" ]] || fail "Temporary server is not PostgreSQL 18"

log "Removing the empty database created by the PostgreSQL 18 entrypoint"
docker exec "$TEMP_CONTAINER" \
    dropdb --if-exists --force -U "$POSTGRES_USER" "$POSTGRES_DB"

log "Restoring $POSTGRES_DB into PostgreSQL 18"
docker exec -i "$TEMP_CONTAINER" \
    pg_restore --exit-on-error --create \
    --no-owner --no-privileges -U "$POSTGRES_USER" -d postgres < "$SQL_DUMP"

TARGET_TABLE_COUNT="$(docker exec "$TEMP_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema');")"
[[ "$TARGET_TABLE_COUNT" == "$SOURCE_TABLE_COUNT" ]] || fail "Table-count validation failed: source=$SOURCE_TABLE_COUNT target=$TARGET_TABLE_COUNT"

docker exec -i "$TEMP_CONTAINER" \
    psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -AtF $'\t' < "$ROW_COUNT_SQL" > "$TARGET_ROW_COUNTS"
chmod 600 "$TARGET_ROW_COUNTS"
if ! cmp -s "$SOURCE_ROW_COUNTS" "$TARGET_ROW_COUNTS"; then
    diff -u "$SOURCE_ROW_COUNTS" "$TARGET_ROW_COUNTS" > "$BACKUP_DIR/table-row-count-mismatch.diff" || true
    chmod 600 "$BACKUP_DIR/table-row-count-mismatch.diff"
    fail "Per-table row-count validation failed; inspect $BACKUP_DIR/table-row-count-mismatch.diff"
fi

docker exec "$TEMP_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT 1" >/dev/null

log "Stopping temporary PostgreSQL 18 container"
docker stop -t 60 "$TEMP_CONTAINER" >/dev/null
docker rm "$TEMP_CONTAINER" >/dev/null

MIGRATION_COMPLETE=true
ROLLBACK_ARMED=false
trap - ERR INT TERM

cat <<EOF

PostgreSQL 18 migration completed and validated.

Backups retained:
  Database archive: $SQL_DUMP
  SHA-256:           $CHECKSUM_FILE
  PostgreSQL 13:     $OLD_DATA_BACKUP
  PostgreSQL 18:     $NEW_DATA_DIR
  Tables validated:  $TARGET_TABLE_COUNT
  Row counts:        $SOURCE_ROW_COUNTS

Edit $COMPOSE_FILE and change the pgdatabase service from:

  image: \${POSTGRES_IMAGE:-$OLD_IMAGE}
  volumes:
    - \${POSTGRES_DATA_DIR:-$OLD_DATA_DIR}:\${POSTGRES_CONTAINER_DATA_DIR:-/var/lib/postgresql/data}

to:

  image: \${POSTGRES_IMAGE:-$NEW_IMAGE}
  volumes:
    - \${POSTGRES_DATA_DIR:-$NEW_DATA_DIR}:\${POSTGRES_CONTAINER_DATA_DIR:-/var/lib/postgresql}

Then start and validate Catcher:

  docker compose -f $COMPOSE_FILE up -d pgdatabase
  docker compose -f $COMPOSE_FILE logs --tail=100 pgdatabase
  docker compose -f $COMPOSE_FILE run --rm backend python3 manage.py migrate
  docker compose -f $COMPOSE_FILE run --rm backend python3 manage.py check
  docker compose -f $COMPOSE_FILE up -d

Do not delete $OLD_DATA_BACKUP or $SQL_DUMP until the upgraded system has
completed operational testing and a fresh PostgreSQL 18 backup exists.

Rollback remains available by stopping Catcher and temporarily restoring:

  image: \${POSTGRES_IMAGE:-postgres:13-bookworm}
  volumes:
    - $OLD_DATA_BACKUP:/var/lib/postgresql/data/
EOF
