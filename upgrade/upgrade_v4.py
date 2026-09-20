#!/usr/bin/env python3
"""Supervised, fail-closed v3 -> v4 upgrade. Python standard library only.

Use UPGRADE_TO_V4.sh, not this module directly. No live system actions on import.
"""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

SERVICE_ROOT = Path('/opt/catcher')
OLD_DATA = SERVICE_ROOT / 'postgresql/data'
NEW_DATA = SERVICE_ROOT / 'postgresql/18'
BACKUPS = SERVICE_ROOT / 'upgrade-backups'
FILES = ('docker-compose.yml', '.env', 'database.env', 'start.sh', 'update.sh', 'TAIL.sh')
INSTALL_FILES = ('start.sh', 'update.sh', 'TAIL.sh', 'UPGRADE_POSTGRES_13_TO_18.sh')
V3_REDIS_COMMAND = ['/usr/local/bin/redis-server', '--loadmodule', '/usr/lib/redis/modules/redistimeseries.so',
                    '--dir', '/opt/catcher/redis/.', '--dbfilename', 'redis_dump.rdb', '--save', '300', '100']


class UpgradeError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise UpgradeError(message)


def write_json(path, value):
    """Private, atomic, durable state/config; do not follow an existing symlink."""
    path = Path(path)
    require(not path.is_symlink(), 'Refusing symlink: ' + str(path))
    fd, temp = tempfile.mkstemp(prefix='.upgrade-', dir=str(path.parent))
    with os.fdopen(fd, 'w') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def version(path):
    marker = Path(path) / 'PG_VERSION'
    return marker.read_text().strip() if marker.is_file() else None


def write_compose(path, value):
    # `compose config` already escapes dollars for round-tripping. Retain that
    # canonical representation verbatim; escaping again changes passwords.
    write_json(path, value)


def command_tokens(command):
    return shlex.split(command) if isinstance(command, str) else (command or [])


def bind_for(service, target):
    matches = [v for v in service.get('volumes', []) if v.get('target', '').rstrip('/') == target.rstrip('/')]
    require(len(matches) == 1 and matches[0].get('type') == 'bind', 'Expected one bind mount at ' + target)
    return matches[0]


def make_candidate(old, release):
    """Preserve site settings, merge required v4 mounts/services, reject ambiguity.

    Input/output are Docker Compose's normalized JSON, which is also valid YAML.
    Commands and entrypoints are not silently replaced if locally customized.
    """
    result = copy.deepcopy(release)
    services = old['services']
    require({'pgdatabase', 'redis', 'backend', 'backendc', 'worker', 'beat', 'nginx', 'aria2server', 'ftpserver'} <= services.keys(),
            'The v3 stack is missing required services; manual review is needed.')
    require(set(services) <= set(release['services']), 'Custom services need review before automatic upgrade.')
    require(not old.get('volumes') and not old.get('configs') and not old.get('secrets'),
            'Named volumes, Docker configs or secrets require a reviewed upgrade plan.')
    require('backend_network' in old.get('networks', {}), 'Custom network layout needs review.')
    require(re.fullmatch(r'postgres:13(?:[.\-].*)?', services['pgdatabase']['image']) is not None,
            'Source Compose must still select PostgreSQL 13; do not overwrite it with v4 first.')
    require(bind_for(services['pgdatabase'], '/var/lib/postgresql/data')['source'] == str(OLD_DATA),
            'Non-standard PostgreSQL source directory requires manual review.')
    require(len(services['pgdatabase'].get('volumes', [])) == 1,
            'Additional PostgreSQL mounts/tablespaces require manual review.')
    require(services['backend']['image'] == 'jamiegau/catcher_backend:3.0', 'Expected the v3 backend image.')
    for key in ('POSTGRES_USER', 'POSTGRES_DB', 'POSTGRES_PASSWORD'):
        require(services['pgdatabase'].get('environment', {}).get(key) == release['services']['pgdatabase'].get('environment', {}).get(key),
                'The source database environment differs from database.env: ' + key)
    for key in ('POSTGRES_USER', 'POSTGRES_DB'):
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', services['pgdatabase'].get('environment', {}).get(key, '')) is not None,
                'Non-standard database/user name requires review: ' + key)
    result['name'] = old['name']
    result['networks'] = copy.deepcopy(old['networks'])
    for name, previous in services.items():
        if name == 'netbird':
            result['services'][name] = copy.deepcopy(previous)
            result['services'][name]['profiles'] = ['netbird']
            continue
        latest = result['services'][name]
        require(not previous.get('build') and not previous.get('entrypoint'), 'Custom build/entrypoint needs review: ' + name)
        require(not previous.get('profiles'), 'Custom service profiles need review: ' + name)
        if name not in ('pgdatabase', 'redis'):
            require(command_tokens(previous.get('command')) == command_tokens(latest.get('command')),
                    'Custom or unsupported service command needs review: ' + name)
        elif name == 'pgdatabase':
            require(not previous.get('command'), 'Custom PostgreSQL command needs review.')
        else:
            require(command_tokens(previous.get('command')) == V3_REDIS_COMMAND,
                    'Custom Redis command/persistence settings require review.')
        require(previous.get('working_dir') == latest.get('working_dir'), 'Custom working directory needs review: ' + name)
        require('backend_network' in previous.get('networks', {}) or name == 'samba', 'Custom service network needs review: ' + name)
        # Preserve all site-specific service settings except the managed fields.
        managed = {'image', 'command', 'depends_on', 'volumes', 'environment'}
        for key, value in previous.items():
            if key not in managed:
                latest[key] = copy.deepcopy(value)
        latest.setdefault('environment', {}).update(previous.get('environment', {}))
        for variable in ('PGDATA', 'POSTGRES_INITDB_ARGS', 'POSTGRES_INITDB_WALDIR'):
            require(variable not in latest.get('environment', {}), 'Custom PostgreSQL initialization requires review: ' + variable)
        if name == 'pgdatabase':
            continue
        mounts = {v['target'].rstrip('/'): copy.deepcopy(v) for v in latest.get('volumes', [])}
        for mount in previous.get('volumes', []):
            target = mount['target'].rstrip('/')
            if name == 'redis' and target == '/opt/catcher/redis':
                target = '/data'
                mount = dict(mount, target=target)
            if target in ('/dev', '/run/udev'):
                require(mount.get('source') == target, 'Unexpected device mount requires review: ' + name)
            mounts[target] = copy.deepcopy(mount)
        latest['volumes'] = list(mounts.values())
    # New background services need the same site environment and storage paths.
    for name in ('worker_kdm', 'network-monitor'):
        if name in services:
            continue
        target = result['services'][name]
        target.setdefault('environment', {}).update(services['backend'].get('environment', {}))
        target['networks'] = copy.deepcopy(services['backend']['networks'])
        by_target = {v['target'].rstrip('/'): v for v in services['backend'].get('volumes', [])}
        target['volumes'] = [copy.deepcopy(by_target.get(v['target'].rstrip('/'), v)) for v in target.get('volumes', [])]
    # Newly added media mounts (including nginx) must use this site's library,
    # not the release's default host directory.
    media = {v['target'].rstrip('/'): v for v in services['backend'].get('volumes', [])
             if v['target'].rstrip('/') in ('/opt/catcher/storage', '/opt/dcinenet/storage')}
    for name, service in result['services'].items():
        if name == 'netbird':
            continue
        previous_targets = {v['target'].rstrip('/') for v in services.get(name, {}).get('volumes', [])}
        service['volumes'] = [copy.deepcopy(media.get(v['target'].rstrip('/'), v))
                              if v['target'].rstrip('/') not in previous_targets else v
                              for v in service.get('volumes', [])]
    require(bind_for(result['services']['redis'], '/data')['source'] == str(SERVICE_ROOT / 'redis'), 'Custom Redis data path requires review.')
    for name in ('aria2server', 'ftpserver'):
        require(bind_for(result['services'][name], '/opt/catcher/' + name)['source'] == str(SERVICE_ROOT / name),
                'Custom persistent service data path requires review: ' + name)
    return result


class Upgrade:
    def __init__(self, install, release=None):
        self.install = Path(install).resolve()
        self.release = Path(release).resolve() if release else None
        self.control = self.install / '.catcher-upgrade'
        self.state_path = self.control / 'state.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.logfile = None
        self.env = dict(os.environ)
        # Shell Compose overrides must not silently select a second project/file.
        for key in list(self.env):
            if key.startswith('COMPOSE_') or key.startswith('POSTGRES_'):
                self.env.pop(key)

    def log(self, message):
        print('[catcher-upgrade] ' + message, flush=True)

    def run(self, args, *, capture=False, check=True, stdin=None, stdout=None):
        result = subprocess.run([str(a) for a in args], cwd=self.install, env=self.env,
                                stdin=stdin, stdout=subprocess.PIPE if capture else (stdout or self.logfile),
                                stderr=self.logfile or subprocess.PIPE)
        if check and result.returncode:
            raise UpgradeError('Command failed: ' + str(args[0]) + '. See the private upgrade log; services were not automatically restarted.')
        return result

    def compose(self, file, *args, **kwargs):
        command = ['docker', 'compose', '--project-directory', self.install, '--env-file', self.install / '.env']
        if self.state.get('project'):
            command += ['--project-name', self.state['project']]
        return self.run(command + ['-f', file] + list(args), **kwargs)

    def config(self, file):
        return json.loads(self.compose(file, '--profile', '*', 'config', '--format', 'json', capture=True).stdout)

    def save(self, phase):
        self.state['phase'] = phase
        write_json(self.state_path, self.state)
        self.log('Stage: ' + phase)

    def confirm(self, phrase, warning):
        self.log(warning)
        require(sys.stdin.isatty(), 'Interactive confirmation is required. Run in an SSH terminal, not a pipe.')
        require(input('Type ' + phrase + ' to continue: ').strip() == phrase, 'Cancelled; confirmation did not match.')

    def preflight(self):
        require(self.state.get('phase') in (None, 'prepared', 'stopping-v3', 'cold-backup-verified'),
                'A database migration may already have started. Use --status or --rollback; do not repeat it.')
        require(self.release is not None, 'Missing release directory.')
        for executable in ('docker', 'pgrep', 'cp', 'diff', 'du', 'df', 'bash', 'git'):
            require(shutil.which(executable), 'Install the required command before upgrading: ' + executable)
        for filename in ('docker-compose.yml', '.env', 'database.env'):
            path = self.install / filename
            require(path.is_file() and not path.is_symlink(), 'Missing or symlinked site file: ' + filename)
        for filename in ('compose.override.yaml', 'compose.override.yml', 'docker-compose.override.yml', 'docker-compose.override.yaml'):
            require(not (self.install / filename).exists(), 'Compose override file requires review: ' + filename)
        require(version(OLD_DATA) == '13', 'Expected an intact PostgreSQL 13 cluster at ' + str(OLD_DATA))
        require(not NEW_DATA.exists() or not any(NEW_DATA.iterdir()), 'PostgreSQL 18 data already exists. Investigate the earlier attempt first.')
        known_copy = self.state.get('database_result', {}).get('postgres13') if self.state.get('phase') == 'rolled-back' else None
        require(not [p for p in OLD_DATA.parent.glob('data.postgres13-*') if str(p) != known_copy],
                'Unknown PostgreSQL 13 rollback copies exist. Identify the active database before upgrading.')
        require(not OLD_DATA.is_symlink() and not NEW_DATA.is_symlink(), 'Database paths must not be symlinks.')
        require(not (OLD_DATA / 'pg_wal').is_symlink(), 'External WAL directory requires a separate backup plan.')
        require(not any((OLD_DATA / 'pg_tblspc').iterdir()), 'External PostgreSQL tablespaces need a separate plan.')
        self.run(['docker', 'compose', 'version'], capture=True)
        old = self.config(self.install / 'docker-compose.yml')
        self.state = {'project': old['name'], 'install': str(self.install)}
        # Render the new template with the site's env/credentials, never defaults
        # from the downloaded release. PG overrides are fixed in the candidate.
        saved_env = dict(self.env)
        self.env.update(POSTGRES_IMAGE='postgres:18-trixie', POSTGRES_DATA_DIR=str(NEW_DATA),
                        POSTGRES_CONTAINER_DATA_DIR='/var/lib/postgresql')
        try:
            release = self.config(self.release / 'docker-compose.yml')
        finally:
            self.env = saved_env
        candidate = make_candidate(old, release)
        require(candidate['services']['backend'].get('hostname'), 'CATCHER_HOSTNAME is missing.')
        require(candidate['services']['backend'].get('environment', {}).get('TIMEZONE_NAME'), 'LOCAL_TIMEZONE_NAME is missing.')
        self.assert_no_foreign_database(old['name'])
        for mount in old['services']['backend'].get('volumes', []):
            if mount.get('target') in ('/opt/catcher/storage', '/opt/dcinenet/storage'):
                require(Path(mount['source']).is_dir(), 'Content mount source is missing: ' + mount['source'])
        require(not self.run(['docker', 'ps', '-aq', '--filter', 'name=^/catcher-postgres18-upgrade$'], capture=True).stdout.strip(),
                'An earlier temporary database container exists; inspect it before retrying.')
        self.old, self.candidate = old, candidate
        self.services = [s for s in old['services'] if s != 'netbird']
        self.log('Installation: ' + str(self.install) + '; Compose project: ' + old['name'])
        self.log('PostgreSQL 13 -> 18; Catcher 3 -> 4. Existing site credentials, ports and storage mounts retained.')
        self.log('NetBird will be left running and will not be upgraded by this operation.')

    def assert_no_foreign_database(self, project):
        ids = self.run(['docker', 'ps', '-q'], capture=True).stdout.decode().split()
        if not ids:
            return
        containers = json.loads(self.run(['docker', 'inspect'] + ids, capture=True).stdout)
        for container in containers:
            labels = container.get('Config', {}).get('Labels') or {}
            if labels.get('com.docker.compose.project') == project and labels.get('com.docker.compose.service') == 'pgdatabase':
                require(any(m.get('Source') == str(OLD_DATA) for m in container.get('Mounts', [])),
                        'Running PostgreSQL uses a different data directory than the v3 Compose file.')
            for mount in container.get('Mounts', []):
                source = Path(mount.get('Source', '/nonexistent')).resolve()
                if source == OLD_DATA or source in OLD_DATA.parents or OLD_DATA in source.parents:
                    require(labels.get('com.docker.compose.project') == project and labels.get('com.docker.compose.service') == 'pgdatabase',
                            'Another running container can access the source database; stop and review it.')

    def wait_database(self, file, expected):
        for _ in range(90):
            result = self.compose(file, 'exec', '-T', 'pgdatabase', 'sh', '-c',
                                  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SHOW server_version_num"', capture=True, check=False)
            if result.returncode == 0 and result.stdout.strip().startswith(str(expected).encode()):
                return
            time.sleep(2)
        raise UpgradeError('PostgreSQL ' + str(expected) + ' did not become ready.')

    def wait_redis(self, file):
        for _ in range(60):
            result = self.compose(file, 'exec', '-T', 'redis', 'redis-cli', 'ping', capture=True, check=False)
            if result.returncode == 0 and result.stdout.strip() == b'PONG':
                return
            time.sleep(2)
        raise UpgradeError('Redis did not become ready. Old Redis data is retained; do not flush or delete it.')

    def snapshot(self, source, destination):
        require(not destination.exists(), 'Backup destination already exists: ' + str(destination))
        self.run(['cp', '-a', '--', source, destination])
        self.run(['diff', '-qr', '--', source, destination])

    def wait_http(self, file, *, aria2=False):
        request = ('r=requests.post("http://aria2server:16888/jsonrpc", json={"jsonrpc":"2.0","id":"upgrade","method":"aria2.getVersion"}, timeout=5)\n'
                   '        r.raise_for_status()\n        assert "result" in r.json()') if aria2 else (
                   'r=requests.get("http://nginx/api/catcher/GetVersion/",timeout=5)\n        r.raise_for_status()')
        script = ('import requests,time\n'
                  'for attempt in range(20):\n'
                  '    try:\n        ' + request + '\n        break\n'
                  '    except (requests.RequestException, ValueError, AssertionError):\n'
                  '        if attempt == 19: raise\n        time.sleep(2)\n')
        prefix = ('run', '--rm', '--no-deps') if aria2 else ('exec', '-T')
        self.compose(file, *prefix, 'backend', 'python3', '-c', script)

    def execute(self):
        self.preflight()
        self.confirm('UPGRADE TO V4', 'Finish all transfers, ingests and jobs; stop external database writers. Use LAN SSH/console, not the VPN being managed. Keep an off-host backup. Downtime starts after image downloads.')
        BACKUPS.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%d-%H%M%S-'), dir=str(BACKUPS)))
        self.state.update(backup=str(backup), services=self.services,
                          release=self.run(['git', '-C', self.release, 'rev-parse', 'HEAD'], capture=True).stdout.decode().strip())
        self.logfile = open(backup / 'upgrade.log', 'ab', buffering=0)
        self.log('Recovery bundle: ' + str(backup))
        self.control.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.control, 0o700)
        runner = self.control / 'runner'
        runner.mkdir(mode=0o700, exist_ok=True)
        shutil.copy2(self.release / 'upgrade' / 'upgrade_v4.py', runner / 'upgrade_v4.py')
        for filename in FILES + ('UPGRADE_POSTGRES_13_TO_18.sh',):
            if (self.install / filename).exists():
                self.snapshot(self.install / filename, backup / filename)
        maintenance_config = copy.deepcopy(self.old)
        for name in self.services:
            maintenance_config['services'][name]['restart'] = 'no'
        write_compose(backup / 'old-resolved.json', maintenance_config)
        write_compose(backup / 'candidate-v4.json', self.candidate)
        # Pin rollback images by ID before pulling mutable release tags.
        rollback_config = copy.deepcopy(self.old)
        for name in self.services:
            image = self.old['services'][name]['image']
            containers = self.compose(self.install / 'docker-compose.yml', 'ps', '-aq', name, capture=True).stdout.decode().split()
            require(len(containers) <= 1, 'Scaled v3 services require review: ' + name)
            if containers:
                result = self.run(['docker', 'inspect', containers[0], '--format', '{{.Image}}'], capture=True)
            else:
                result = self.run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'], capture=True)
            rollback_config['services'][name]['image'] = result.stdout.decode().strip()
        write_compose(backup / 'rollback-compose.json', rollback_config)
        self.save('prepared')
        self.compose(backup / 'candidate-v4.json', 'config', '--quiet')
        rendered = self.config(backup / 'candidate-v4.json')
        require(rendered['services']['pgdatabase']['environment'] == self.candidate['services']['pgdatabase']['environment'],
                'Compose did not preserve database environment values when re-reading the candidate.')
        self.log('Pulling v4 images before downtime; this may take several minutes.')
        self.compose(backup / 'candidate-v4.json', 'pull', *[s for s in self.candidate['services'] if s != 'netbird'])
        # Cold copy + restored cluster + compressed archive + service snapshots.
        sizes = {p: int(self.run(['du', '-sk', p], capture=True).stdout.split()[0]) * 1024
                 for p in (OLD_DATA, SERVICE_ROOT / 'redis', SERVICE_ROOT / 'ftpserver', SERVICE_ROOT / 'aria2server') if p.exists()}
        required = sizes[OLD_DATA] * 3 + sum(n for p, n in sizes.items() if p != OLD_DATA) + 1024**3
        require(shutil.disk_usage(OLD_DATA.parent).free >= required, 'Insufficient free disk space for cold copy, dump, restored database and headroom.')
        require(os.stat(backup).st_dev == os.stat(OLD_DATA.parent).st_dev, 'Backup and database must be on the same filesystem for this automatic space calculation.')
        self.save('stopping-v3')
        ids = self.compose(backup / 'old-resolved.json', 'ps', '-aq', *self.services, capture=True).stdout.decode().split()
        if ids:
            self.run(['docker', 'update', '--restart=no'] + ids)
        self.compose(backup / 'old-resolved.json', 'stop', *self.services)
        running = self.compose(backup / 'old-resolved.json', 'ps', '--status', 'running', '--services', capture=True).stdout.decode().split()
        require(not set(running) - {'netbird'}, 'Some v3 services are still running; cold backup aborted.')
        self.assert_no_foreign_database(self.state['project'])
        require(self.run(['pgrep', '-x', 'postgres'], capture=True, check=False).returncode == 1,
                'A PostgreSQL process is still running; cold backup aborted.')
        self.log('Creating and verifying the cold database and service-data backups.')
        self.snapshot(OLD_DATA, backup / 'postgres13-cold')
        for name in ('redis', 'ftpserver', 'aria2server'):
            source = SERVICE_ROOT / name
            require(source.is_dir() and not source.is_symlink(), 'Missing or symlinked service data: ' + name)
            self.snapshot(source, backup / name)
        self.save('cold-backup-verified')
        oldfile = backup / 'old-resolved.json'
        self.compose(oldfile, 'up', '-d', '--no-deps', 'pgdatabase')
        self.wait_database(oldfile, 13)
        other_dbs = self.compose(oldfile, 'exec', '-T', 'pgdatabase', 'sh', '-c',
                                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM pg_database WHERE NOT datistemplate AND datname NOT IN (\'postgres\', current_database())"', capture=True)
        require(other_dbs.stdout.strip() == b'0', 'This cluster contains other databases. A separate migration plan is required.')
        other_roles = self.compose(oldfile, 'exec', '-T', 'pgdatabase', 'sh', '-c',
                                  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM pg_roles WHERE rolname NOT LIKE \'pg_%\' AND rolname <> current_user"', capture=True)
        require(other_roles.stdout.strip() == b'0', 'Custom PostgreSQL roles need a reviewed roles/privileges migration.')
        maintenance_tables = self.compose(oldfile, 'exec', '-T', 'pgdatabase', 'sh', '-c',
                                         'psql -U "$POSTGRES_USER" -d postgres -Atqc "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN (\'pg_catalog\', \'information_schema\')"', capture=True)
        require(maintenance_tables.stdout.strip() == b'0', 'The maintenance postgres database contains user tables; a separate migration plan is required.')
        self.save('migrating-postgres')
        self.log('Migrating PostgreSQL and comparing exact per-table row counts.')
        # The old config retains the correct project and absolute bind sources.
        self.run(['bash', self.release / 'UPGRADE_POSTGRES_13_TO_18.sh', '--compose-file', oldfile,
                  '--env-file', self.install / 'database.env', '--backup-root', backup / 'database-archives',
                  '--result-file', backup / 'postgres-migration.json', '--yes'])
        result = json.loads((backup / 'postgres-migration.json').read_text())
        require(result['postgres18'] == str(NEW_DATA) and version(Path(result['postgres13'])) == '13', 'Unexpected database migration result.')
        self.state['database_result'] = result
        self.save('postgres-validated')
        # Credentials remain byte-for-byte unchanged; JSON is a valid Compose YAML file.
        for filename in ('.env', 'database.env'):
            require((self.install / filename).read_bytes() == (backup / filename).read_bytes(), 'Site settings changed during upgrade; stopping.')
        write_compose(self.install / 'docker-compose.yml', self.candidate)
        for filename in INSTALL_FILES:
            shutil.copy2(self.release / filename, self.install / filename)
        self.save('v4-compose-installed')
        file = self.install / 'docker-compose.yml'
        self.compose(file, 'up', '-d', '--no-deps', 'pgdatabase', 'redis')
        self.wait_database(file, 18)
        self.wait_redis(file)
        self.save('app-migrations')
        self.log('Applying and checking Catcher application migrations. Existing users/passwords are retained.')
        for args in (('migrate', '--noinput'), ('migrate', '--check'), ('check',)):
            self.compose(file, 'run', '--rm', '--no-deps', 'backend', 'python3', 'manage.py', *args)
        self.compose(file, 'up', '-d', '--no-deps', 'aria2server')
        # Setup updates default preferences and periodic jobs. Check readiness
        # first, and verify that it leaves all existing password hashes intact.
        self.wait_http(file, aria2=True)
        self.compose(file, 'run', '--rm', '--no-deps', 'backend', 'python3', 'manage.py', 'shell', '-c',
                     'from django.contrib.auth import get_user_model; from django.core.management import call_command; '
                     'U=get_user_model(); before=dict(U.objects.values_list("pk","password")); '
                     'call_command("catcher_setup"); after=dict(U.objects.values_list("pk","password")); '
                     'assert all(after.get(k)==v for k,v in before.items()), "Existing user passwords changed during setup"')
        self.log('Taking the PostgreSQL 18 recovery dump before enabling writers.')
        dump = backup / 'catcher-postgres18.dump'
        with open(dump, 'xb') as handle:
            self.compose(file, 'exec', '-T', 'pgdatabase', 'sh', '-c',
                         'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc', stdout=handle)
        require(dump.stat().st_size > 0, 'Post-upgrade dump is empty.')
        with open(dump, 'rb') as handle:
            self.compose(file, 'exec', '-T', 'pgdatabase', 'pg_restore', '--list', stdin=handle)
        digest = hashlib.sha256()
        with open(dump, 'rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        (backup / 'catcher-postgres18.dump.sha256').write_text(digest.hexdigest() + '  catcher-postgres18.dump\n')
        self.save('starting-v4')
        active = [s for s in self.candidate['services'] if s != 'netbird']
        self.compose(file, 'up', '-d', '--no-deps', *active)
        for _ in range(60):
            running = self.compose(file, 'ps', '--status', 'running', '--services', capture=True).stdout.decode().split()
            if set(active) <= set(running):
                break
            time.sleep(2)
        else:
            raise UpgradeError('Not all v4 services started. Inspect the private log and docker compose ps --all.')
        self.compose(file, 'exec', '-T', 'backend', 'python3', 'manage.py', 'migrate', '--check')
        self.compose(file, 'exec', '-T', 'backend', 'python3', 'manage.py', 'check')
        self.wait_http(file)
        self.compose(file, 'ps', '--all')
        self.save('complete')
        self.log('Upgrade completed. Verify browser login, Player Status, AutoKDM and transfers before ending maintenance.')
        self.log('Keep all rollback data and a separate off-host backup. Recovery bundle: ' + str(backup))
        self.log('The original Git checkout was not reset. Do not blindly git pull over the generated site Compose file.')

    def rollback(self):
        require(self.state.get('backup'), 'No saved upgrade is available.')
        require(self.state.get('phase') != 'rolled-back', 'This upgrade has already been rolled back.')
        backup = Path(self.state['backup'])
        require(backup.parent == BACKUPS and backup.is_dir() and not backup.is_symlink(), 'Invalid recovery bundle path.')
        require(version(backup / 'postgres13-cold') == '13', 'No verified cold snapshot; inspect the log before recovery.')
        require(self.state['phase'] not in ('prepared', 'stopping-v3'), 'Cold snapshot was not verified. Inspect the log; original v3 data is unchanged.')
        self.confirm('ROLL BACK TO V3', 'This restores the maintenance-window snapshot. Any new v4 database/service changes will not be merged. Current data will be preserved in renamed directories. External writers must be stopped.')
        required = sum(int(self.run(['du', '-sk', backup / name], capture=True).stdout.split()[0]) * 1024
                       for name in ('postgres13-cold', 'redis', 'ftpserver', 'aria2server')) + 1024**3
        require(shutil.disk_usage(OLD_DATA.parent).free >= required, 'Insufficient space to restore cold backups while retaining current data.')
        rollback_config = json.loads((backup / 'rollback-compose.json').read_text())
        for name in self.state['services']:
            self.run(['docker', 'image', 'inspect', rollback_config['services'][name]['image']], capture=True)
        if self.logfile:
            self.logfile.close()
        self.logfile = open(backup / 'rollback.log', 'ab', buffering=0)
        file = self.install / 'docker-compose.yml'
        config = self.config(file)
        self.compose(file, 'stop', *[s for s in config['services'] if s != 'netbird'])
        self.assert_no_foreign_database(self.state['project'])
        require(self.run(['pgrep', '-x', 'postgres'], capture=True, check=False).returncode == 1,
                'PostgreSQL is still running; rollback aborted.')
        self.save('rolling-back')
        suffix = '.before-rollback-' + time.strftime('%Y%m%d-%H%M%S')
        for path in (OLD_DATA, NEW_DATA, SERVICE_ROOT / 'redis', SERVICE_ROOT / 'ftpserver', SERVICE_ROOT / 'aria2server'):
            require(not path.is_symlink(), 'Refusing symlink during rollback: ' + str(path))
            if path.exists():
                preserved = path.with_name(path.name + suffix)
                require(not preserved.exists(), 'Rollback preservation path already exists.')
                path.rename(preserved)
                self.log('Preserved current data: ' + str(preserved))
        for source, target in [(backup / 'postgres13-cold', OLD_DATA)] + [(backup / name, SERVICE_ROOT / name) for name in ('redis', 'ftpserver', 'aria2server')]:
            self.snapshot(source, target)
        for filename in FILES:
            if (backup / filename).exists():
                require(not (self.install / filename).is_symlink(), 'Refusing symlink: ' + filename)
                shutil.copy2(backup / filename, self.install / filename)
        # Keep exact old images, even if a mutable tag changed during the upgrade.
        write_json(file, json.loads((backup / 'rollback-compose.json').read_text()))
        self.compose(file, 'up', '-d', '--no-deps', 'pgdatabase')
        self.wait_database(file, 13)
        self.compose(file, 'up', '-d', '--no-deps', *self.state['services'])
        self.save('rolled-back')
        self.log('Restored v3 from the verified snapshot. All v4 data was preserved, not deleted. Verify operation before reopening the site.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-dir', required=True)
    parser.add_argument('--release-dir')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--status', action='store_true')
    mode.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    require(os.geteuid() == 0 and sys.platform.startswith('linux'), 'Run as root on the Linux Catcher server.')
    os.umask(0o077)
    # Global lock protects standard data paths even if launched from two folders.
    with open('/var/lock/catcher-v3-v4.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise UpgradeError('Another Catcher upgrade is already running.')
        upgrade = Upgrade(args.install_dir, args.release_dir)
        if args.status:
            print(json.dumps(upgrade.state, indent=2))
            return
        def interrupted(signum, frame):
            raise UpgradeError('Interrupted. Inspect --status before any retry; do not start services blindly.')
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, interrupted)
        try:
            if args.rollback:
                upgrade.rollback()
            elif args.check:
                upgrade.preflight()
                upgrade.log('Preflight passed. No services stopped or database data changed.')
            else:
                upgrade.execute()
        except (UpgradeError, OSError, ValueError) as exc:
            if upgrade.state.get('phase') not in (None, 'prepared', 'complete', 'rolled-back'):
                # Never leave partially upgraded writers running after a failed
                # startup/check. This intentionally does not auto-restore data.
                try:
                    current = upgrade.install / 'docker-compose.yml'
                    names = upgrade.config(current)['services']
                    managed = [s for s in names if s != 'netbird']
                    ids = upgrade.compose(current, 'ps', '-aq', *managed, capture=True).stdout.decode().split()
                    if ids:
                        upgrade.run(['docker', 'update', '--restart=no'] + ids)
                    upgrade.compose(current, 'stop', *managed, check=False)
                except Exception:
                    upgrade.log('Could not confirm services stopped. Check docker compose ps --all before recovery.')
            upgrade.log('STOPPED: ' + str(exc))
            upgrade.log('Use sudo bash UPGRADE_TO_V4.sh --status. Recovery: --rollback (explicit confirmation required).')
            if upgrade.state.get('backup'):
                upgrade.log('Private log/recovery bundle: ' + upgrade.state['backup'])
            return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except UpgradeError as exc:
        print('[catcher-upgrade] ' + str(exc), file=sys.stderr)
        sys.exit(1)
