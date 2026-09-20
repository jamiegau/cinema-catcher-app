# Upgrade Catcher 3 to Catcher 4 with one command

You do **not** need a second `cinema-catcher-app-v4` checkout, manual Compose
editing, or a sequence of database commands. Download the entry-point script
into your **existing v3 installation** and let it coordinate the upgrade.

## Before starting

- Finish downloads, ingests and other jobs. Arrange a maintenance window and
  stop any external process writing to the database. Queued transfers may
  resume when the transfer service starts during setup.
- Keep a current **off-host backup**. The script's local copies cannot protect
  against a failed system disk.
- Use LAN SSH or a console. Do not depend solely on a remote-access container.
  The script leaves NetBird running, but independent access is still important.
- Requirements: Linux, sudo, Python 3, Git, curl, Docker Engine and the Compose
  plugin (`docker compose`). Standard Ubuntu utilities including `pgrep`, `cp`,
  `diff`, `du`, `df` and SHA-256 tools must be installed.
- Keep the original v3 `docker-compose.yml`, `.env`, and `database.env` in place.
  Do not run `git pull`, replace Compose, or run `update.sh` first.

## Log in, then download and run

From your computer (replace the address and SSH account):

```bash
ssh devbot@CATCHER_SERVER_IP
```

On that server, enter the **existing** installation directory. Use its actual
path: it may be `~/git/cinema-catcher-app` or `/opt/cinema-catcher-app`.

```bash
cd ~/git/cinema-catcher-app
```

Then this is the **single upgrade command**:

```bash
sudo curl --fail --location --proto '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/jamiegau/cinema-catcher-app/main/UPGRADE_TO_V4.sh \
  -o UPGRADE_TO_V4.sh && sudo bash UPGRADE_TO_V4.sh
```

The download must succeed before the script runs. It is saved as a file rather
than piped into a root shell. You can inspect it before running by doing the
download and `sudo bash` portions separately.

Review the detected installation and project, then type **`UPGRADE TO V4`**
when prompted. Stay connected and allow the operation to finish. Downloading
images and copying a large database can take time; progress stages are printed
and detailed command output is kept in the private log path displayed by the
script. A v3 stack that is already stopped is supported.

Optional preflight only, once downloaded:

```bash
sudo bash UPGRADE_TO_V4.sh --check
```

This downloads the release and validates the configuration without stopping
services, pulling application images or modifying database data.

## What the script handles

1. Fetches the v4 helpers and templates together from one Git commit into a
   temporary directory. It does not reset or overwrite your Git checkout.
2. Validates the v3 database path, Compose project, site configuration and
   supported customizations. An exclusive lock prevents concurrent upgrades.
3. Saves the original configuration and exact old image IDs, prepares the new
   Compose configuration, and pulls v4 images **before downtime**.
4. Checks available disk space, disables automatic restart of the old managed
   containers, and stops the stack except NetBird.
5. Makes and compares a cold PostgreSQL 13 copy and snapshots Redis, FTP and
   aria2 data. The media library is not copied, moved or deleted.
6. Starts only PostgreSQL 13, creates a checksummed database archive, restores
   it into PostgreSQL 18, and verifies table counts and exact per-table row
   counts. The original PostgreSQL 13 files are retained separately.
7. Installs v4 Compose and helper scripts in the original directory, retaining
   the project name, site credentials, ports, and supported custom mounts.
8. Starts PostgreSQL 18/Redis, applies and checks Django migrations, runs Catcher
   setup, and verifies existing password hashes remain unchanged. Setup may
   create its standard default accounts if they were previously missing;
   review and secure the user list after upgrade.
9. Takes a checksummed PostgreSQL 18 backup, starts the v4 services, checks that
   they are running, and tests the version API through nginx.

`.env` and `database.env` are **not** replaced with release defaults. The new
`docker-compose.yml` uses expanded JSON, which is valid Compose/YAML syntax,
to retain the reviewed site values. It includes resolved environment settings
and may contain credentials, so it is written with root-only permissions.
Changing `.env` alone will not change values already expanded in that file;
edit the relevant site Compose values deliberately for later configuration changes.

Application setup preserves existing login passwords; it does not change them
to `admin/admin`. Sign in using the site's existing account.

## If the script stops or SSH disconnects

Do **not** start the full stack, delete database directories, flush Redis or
rerun the database helper blindly. Check the recorded stage:

```bash
sudo bash UPGRADE_TO_V4.sh --status
```

The output identifies the recovery directory below
`/opt/catcher/upgrade-backups/`. Its `upgrade.log` contains detailed output and
may contain sensitive site information; do not publish it unredacted.

- Before the database migration starts (`prepared`, `stopping-v3`, or
  `cold-backup-verified`), correct the reported cause and rerun the same upgrade
  command. It creates a new backup bundle; previous bundles are retained.
- Once database migration may have started, the script refuses an automatic
  repeat. Inspect the failure and use the saved rollback, or seek assistance.
- Failures after downtime starts attempt to stop managed services. They do not
  silently restore an old database or claim that the upgrade completed.
- Recovery uses the saved runner; `--status` and `--rollback` do not need GitHub.

### One-command rollback

```bash
sudo bash UPGRADE_TO_V4.sh --rollback
```

Review the warning and type **`ROLL BACK TO V3`**. The script stops the managed
services, preserves current data in timestamped `*.before-rollback-*`
directories, restores the verified cold database/service snapshots and old
configuration, selects the recorded old image IDs, and starts v3.

**Rollback returns to the maintenance-window snapshot.** New database records,
KDM state or service changes made under v4 are not merged back. The current
files are retained for deliberate recovery. Enough extra free disk space is
required to restore the snapshots without deleting current data. Do not prune
old Docker images: rollback needs them.

After rollback, arrange a review before attempting the upgrade again. The
recovery Compose file deliberately pins old image IDs; it is not treated as a
fresh v3 installation by the automatic upgrader.

If no cold snapshot was completed and verified, rollback refuses to guess.
The original database has not yet been migrated; use the log and the saved
configuration to review recovery with an administrator.

## Supported layouts and deliberate stopping points

The guided path supports the standard local PostgreSQL 13 cluster at
`/opt/catcher/postgresql/data`, migrating to `/opt/catcher/postgresql/18`, with
service data under `/opt/catcher/{redis,ftpserver,aria2server}`. It supports
running or stopped v3 stacks, preserves site port/environment settings, and
merges required v4 mounts and new worker services.

It stops for review on ambiguous previous attempts, extra databases or database roles,
tablespaces/external WAL, alternate database/service data locations, custom
commands/entrypoints/services, Compose override files, or named volumes.
Missing required settings are reported rather than guessed. Redis data is
never discarded to bypass a compatibility or permissions problem.

These are reasons to require a reviewed plan, not reasons the normal upgrade
needs dozens of manual commands. The [advanced/manual guide](UPGRADING_FROM_V3_MANUAL.md)
remains available for unusual installations. Do not mix procedures mid-upgrade.

## After completion

- Open the web interface and sign in with the existing account.
- Review users; verify Player Status, AutoKDM, schedules and normal transfers.
- Keep the displayed recovery bundle, retained v3 data, and old images until
  operational checks pass and an off-host v4 backup has been verified.
- The script does not reboot the server or upgrade Docker/the operating system.
- Git history is untouched. The installed site files differ from the old
  checkout; do not blindly `git pull` or reset them. Normal v4 image updates can
  use `sudo bash update.sh`; future template changes must preserve the site's
  generated Compose configuration.

### Validation status

The earlier manual PostgreSQL upgrade was exercised on a real v3 site. The new
one-command coordinator has separate automated configuration and mocked
workflow tests; that is **not** a claim that this new coordinator has already
completed a production-site upgrade. Use a test installation before broad rollout.
