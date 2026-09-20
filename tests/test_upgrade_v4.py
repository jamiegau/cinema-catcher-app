"""Passive tests: all Docker commands mocked; no production data/network used."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('upgrade_v4', ROOT / 'upgrade/upgrade_v4.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def mount(source, target):
    return {'type': 'bind', 'source': str(source), 'target': target}


def configurations():
    names = ('pgdatabase', 'redis', 'backend', 'backendc', 'worker', 'worker_mon', 'beat', 'nginx', 'aria2server', 'ftpserver', 'samba')
    old = {'name': 'site-catcher', 'networks': {'backend_network': {'name': 'site-catcher_backend_network'}}, 'services': {}}
    for name in names:
        old['services'][name] = {'image': 'jamiegau/catcher_' + name + ':3.0',
                                 'networks': {'backend_network': None}, 'restart': 'always'}
    old['services']['pgdatabase'].update(image='postgres:13.1', environment={
        'POSTGRES_USER': 'catcher_user', 'POSTGRES_DB': 'catcher_db', 'POSTGRES_PASSWORD': 'fixture-only'},
        volumes=[mount(u.OLD_DATA, '/var/lib/postgresql/data')])
    old['services']['backend'].update(image='jamiegau/catcher_backend:3.0', hostname='real-site',
        environment={'TIMEZONE_NAME': 'Australia/Perth', 'IN_PRODUCTION': 'True'},
        ports=[{'target': 8000, 'published': '18000', 'host_ip': '127.0.0.1', 'protocol': 'tcp'}],
        volumes=[mount('/srv/cinema-library', '/opt/catcher/storage')], command=['gunicorn', 'app'])
    old['services']['redis'].update(image='redislabs/redistimeseries:latest', command=list(u.V3_REDIS_COMMAND),
                                   volumes=[mount(u.SERVICE_ROOT/'redis', '/opt/catcher/redis')])
    for name in ('aria2server', 'ftpserver'):
        old['services'][name]['volumes'] = [mount(u.SERVICE_ROOT/name, '/opt/catcher/' + name)]
    new = copy.deepcopy(old)
    for name, service in new['services'].items():
        service['image'] = service['image'].replace(':3.0', ':4.0')
    new['services']['pgdatabase'].update(image='postgres:18-trixie', volumes=[mount(u.NEW_DATA, '/var/lib/postgresql')])
    new['services']['redis'].update(image='redis:8-trixie', command=['redis-server', '--dir', '/data'],
                                   volumes=[mount(u.SERVICE_ROOT/'redis', '/data')])
    new['services']['backend']['volumes'] = [mount('/opt/catcher/storage', '/opt/catcher/storage'), mount('/dev', '/dev'), mount('/run/udev', '/run/udev')]
    new['services']['nginx']['volumes'] = [mount('/opt/catcher/storage', '/opt/catcher/storage')]
    for name in ('worker_kdm', 'network-monitor'):
        new['services'][name] = {'image': 'jamiegau/catcher_backend:4.0', 'networks': {'backend_network': None},
                                 'volumes': [mount('/opt/catcher/storage', '/opt/catcher/storage')]}
    return old, new


class ConfigTests(unittest.TestCase):
    def test_preserves_site_identity_credentials_ports_and_custom_media_mount(self):
        old, new = configurations()
        result = u.make_candidate(old, new)
        self.assertEqual(result['name'], old['name'])
        backend = result['services']['backend']
        self.assertEqual(backend['ports'], old['services']['backend']['ports'])
        self.assertEqual(backend['environment'], old['services']['backend']['environment'])
        self.assertEqual(backend['hostname'], 'real-site')
        self.assertEqual(u.bind_for(backend, '/opt/catcher/storage')['source'], '/srv/cinema-library')
        self.assertEqual(u.bind_for(backend, '/dev')['source'], '/dev')
        self.assertEqual(u.bind_for(result['services']['nginx'], '/opt/catcher/storage')['source'], '/srv/cinema-library')
        self.assertEqual(result['services']['pgdatabase']['image'], 'postgres:18-trixie')
        self.assertEqual(u.bind_for(result['services']['pgdatabase'], '/var/lib/postgresql')['source'], str(u.NEW_DATA))
        self.assertEqual(u.bind_for(result['services']['redis'], '/data')['source'], '/opt/catcher/redis')
        for name in ('worker_kdm', 'network-monitor'):
            self.assertEqual(u.bind_for(result['services'][name], '/opt/catcher/storage')['source'], '/srv/cinema-library')
            self.assertEqual(result['services'][name]['environment']['TIMEZONE_NAME'], 'Australia/Perth')
        self.assertEqual(old['services']['pgdatabase']['image'], 'postgres:13.1', 'inputs are not mutated')

    def test_netbird_keeps_existing_connection_settings_but_is_not_default_started(self):
        old, new = configurations()
        old['services']['netbird'] = {'image': 'netbirdio/netbird:old', 'environment': {'NB_SETUP_KEY': 'fixture'}, 'network_mode': 'host'}
        new['services']['netbird'] = {'image': 'netbirdio/netbird:latest'}
        result = u.make_candidate(old, new)['services']['netbird']
        self.assertEqual(result['image'], 'netbirdio/netbird:old')
        self.assertEqual(result['environment'], old['services']['netbird']['environment'])
        self.assertEqual(result['profiles'], ['netbird'])

    def test_ambiguous_customizations_are_not_silently_discarded(self):
        changes = [
            lambda c: c['services']['backend'].update(command=['custom-entry']),
            lambda c: c['services']['backend'].update(entrypoint=['custom']),
            lambda c: c['services'].update(extra={}),
            lambda c: c.update(volumes={'external': {}}),
            lambda c: c['services']['pgdatabase'].update(image='postgres:18'),
            lambda c: c['services']['pgdatabase']['volumes'][0].update(source='/different/database'),
            lambda c: c['services']['pgdatabase']['environment'].update(POSTGRES_DB='../unsafe'),
            lambda c: c['services']['backend'].update(profiles=['custom']),
            lambda c: c['services']['redis'].update(command=['redis-server', '--requirepass', 'fixture']),
        ]
        for change in changes:
            old, new = configurations()
            change(old)
            with self.assertRaises(u.UpgradeError):
                u.make_candidate(old, new)


class FakeUpgrade(u.Upgrade):
    def __init__(self, install, release, fail=None):
        super().__init__(install, release)
        self.commands = []
        self.fail = fail
        self.running = set()

    def log(self, message):
        pass

    def preflight(self):
        self.old, release = configurations()
        self.candidate = u.make_candidate(self.old, release)
        self.services = list(self.old['services'])
        self.state = {'project': 'site-catcher', 'install': str(self.install)}

    def confirm(self, *_):
        pass

    def assert_no_foreign_database(self, *_):
        pass

    def wait_database(self, file, expected):
        self.commands.append(['ready-database', str(expected)])

    def wait_redis(self, file):
        self.commands.append(['ready-redis'])

    def snapshot(self, source, destination):
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)

    def run(self, args, **kwargs):
        args = [str(a) for a in args]
        self.commands.append(args)
        if self.fail == 'pull' and 'pull' in args:
            raise u.UpgradeError('simulated image failure')
        if self.fail == 'migrate' and 'migrate' in args:
            raise u.UpgradeError('simulated Django failure')
        data, code = b'', 0
        if args[0] == 'git':
            data = b'abc123\n'
        elif args[:2] == ['docker', 'image']:
            data = b'sha256:fixture\n'
        elif args[0] == 'du':
            data = b'1\tfixture\n'
        elif args[0] == 'pgrep':
            code = 1
        elif args[0] == 'bash':
            if self.fail == 'database':
                raise u.UpgradeError('simulated database failure')
            preserved = u.OLD_DATA.with_name('data.postgres13-fixture')
            u.OLD_DATA.rename(preserved)
            u.NEW_DATA.mkdir()
            (u.NEW_DATA/'PG_VERSION').write_text('18')
            u.write_json(Path(args[args.index('--result-file') + 1]), {
                'postgres13': str(preserved), 'postgres18': str(u.NEW_DATA), 'archive': 'fixture.dump'})
        if 'stop' in args:
            self.running.clear()
        if 'up' in args:
            self.running.update(args[args.index('--no-deps')+1:])
        if 'ps' in args and '--services' in args:
            data = '\n'.join(self.running).encode()
        if any('FROM pg_database' in a or 'FROM pg_roles' in a or 'FROM information_schema.tables' in a for a in args):
            data = b'0\n'
        if 'config' in args and '--format' in args:
            data = Path(args[args.index('-f') + 1]).read_bytes()
        if kwargs.get('stdout'):
            kwargs['stdout'].write(b'fixture dump')
        return subprocess.CompletedProcess(args, code, stdout=data, stderr=b'')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name, value in {'SERVICE_ROOT': root/'data', 'OLD_DATA': root/'data/postgresql/data',
                            'NEW_DATA': root/'data/postgresql/18', 'BACKUPS': root/'data/backups'}.items():
            patcher = patch.object(u, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        u.OLD_DATA.mkdir(parents=True)
        (u.OLD_DATA/'PG_VERSION').write_text('13')
        for name in ('redis', 'ftpserver', 'aria2server'):
            (u.SERVICE_ROOT/name).mkdir()
            (u.SERVICE_ROOT/name/'important').write_text('original')
        self.install = root/'installation'
        self.install.mkdir()
        for name in u.FILES:
            (self.install/name).write_text('original ' + name)
        self.engine = FakeUpgrade(self.install, ROOT)
        self.addCleanup(lambda: self.engine.logfile and self.engine.logfile.close())

    def test_full_sequence_migrates_before_starting_writers_and_preserves_credentials(self):
        self.engine.execute()
        self.assertEqual(self.engine.state['phase'], 'complete')
        self.assertEqual((self.install/'.env').read_text(), 'original .env')
        self.assertEqual((self.install/'database.env').read_text(), 'original database.env')
        installed = json.loads((self.install/'docker-compose.yml').read_text())
        self.assertEqual(installed['services']['backend']['image'], 'jamiegau/catcher_backend:4.0')
        commands = self.engine.commands
        for command in commands:
            if 'python3' in command and '-c' in command:
                compile(command[command.index('-c') + 1], '<container-readiness>', 'exec')
        migration = next(i for i, c in enumerate(commands) if 'migrate' in c)
        writers = [i for i,c in enumerate(commands) if 'up' in c and 'worker' in c]
        self.assertTrue(writers and all(i > migration for i in writers))
        self.assertTrue(any('catcher_setup' in ' '.join(c) for c in commands))
        self.assertFalse(any('flushall' in ' '.join(c).lower() or 'prune' in c for c in commands))
        backup = Path(self.engine.state['backup'])
        self.assertEqual(u.version(backup/'postgres13-cold'), '13')
        self.assertTrue((backup/'catcher-postgres18.dump.sha256').is_file())
        self.assertEqual((self.install/'docker-compose.yml').stat().st_mode & 0o777, 0o600)

    def test_pull_failure_does_not_stop_services_or_replace_compose(self):
        self.engine.fail = 'pull'
        with self.assertRaises(u.UpgradeError):
            self.engine.execute()
        self.assertFalse(any('stop' in c for c in self.engine.commands))
        self.assertEqual((self.install/'docker-compose.yml').read_text(), 'original docker-compose.yml')
        self.assertEqual(u.version(u.OLD_DATA), '13')

    def test_interrupted_database_phase_refuses_automatic_repeat(self):
        engine = u.Upgrade(self.install, ROOT)
        engine.state = {'phase': 'migrating-postgres'}
        with patch.object(engine, 'run') as run:
            with self.assertRaisesRegex(u.UpgradeError, 'migration may already have started'):
                engine.preflight()
            run.assert_not_called()

    def test_rollback_records_actual_container_image_not_mutable_tag(self):
        original_run = self.engine.run
        def run(args, **kwargs):
            tokens = [str(a) for a in args]
            if tokens[-3:] == ['ps', '-aq', 'backend']:
                return subprocess.CompletedProcess(tokens, 0, stdout=b'old-backend-container\n')
            if tokens[:3] == ['docker', 'inspect', 'old-backend-container']:
                return subprocess.CompletedProcess(tokens, 0, stdout=b'sha256:actual-running-image\n')
            return original_run(args, **kwargs)
        with patch.object(self.engine, 'run', side_effect=run):
            self.engine.execute()
        saved = json.loads((Path(self.engine.state['backup'])/'rollback-compose.json').read_text())
        self.assertEqual(saved['services']['backend']['image'], 'sha256:actual-running-image')

    def test_database_failure_does_not_install_v4_or_start_writers(self):
        self.engine.fail = 'database'
        with self.assertRaises(u.UpgradeError):
            self.engine.execute()
        self.assertEqual((self.install/'docker-compose.yml').read_text(), 'original docker-compose.yml')
        self.assertFalse(any('up' in c and 'worker' in c for c in self.engine.commands))
        self.assertEqual(u.version(Path(self.engine.state['backup'])/'postgres13-cold'), '13')

    def test_application_failure_retains_rollback_without_starting_workers(self):
        self.engine.fail = 'migrate'
        with self.assertRaises(u.UpgradeError):
            self.engine.execute()
        self.assertEqual(self.engine.state['phase'], 'app-migrations')
        self.assertEqual(u.version(Path(self.engine.state['database_result']['postgres13'])), '13')
        self.assertFalse(any('up' in c and 'worker' in c for c in self.engine.commands))

    def test_rollback_preserves_new_data_and_restores_verified_v3_snapshot(self):
        self.engine.execute()
        (u.SERVICE_ROOT/'redis/important').write_text('new v4 data')
        self.engine.rollback()
        self.assertEqual(self.engine.state['phase'], 'rolled-back')
        self.assertEqual(u.version(u.OLD_DATA), '13')
        self.assertFalse(u.NEW_DATA.exists())
        self.assertEqual((u.SERVICE_ROOT/'redis/important').read_text(), 'original')
        saved = list(u.SERVICE_ROOT.glob('redis.before-rollback-*'))
        self.assertEqual((saved[0]/'important').read_text(), 'new v4 data')
        restored = json.loads((self.install/'docker-compose.yml').read_text())
        self.assertEqual(restored['services']['backend']['image'], 'sha256:fixture')


if __name__ == '__main__':
    unittest.main()
