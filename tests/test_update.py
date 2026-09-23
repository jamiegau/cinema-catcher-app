"""Exercise update.sh with fake Docker/sleep commands; never stop real services."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UpdateTests(unittest.TestCase):
    def run_update(self, fail='', database_ready=True, rollback=False, pg_version='18'):
        with tempfile.TemporaryDirectory() as directory:
            install = Path(directory)
            # Isolate the legacy-data guard from the developer's actual disks.
            version_file = install / 'PG_VERSION'
            version_file.write_text(pg_version)
            source = (ROOT / 'update.sh').read_text().replace(
                '/opt/catcher/postgresql/data/PG_VERSION', str(version_file))
            (install / 'update.sh').write_text(source)
            if rollback:
                (install / '.catcher-upgrade').mkdir()
                (install / '.catcher-upgrade/state.json').write_text('{}')
            binary = install / 'bin'
            binary.mkdir()
            docker = binary / 'docker'
            docker.write_text(f'#!{sys.executable}\n' + '''import json, os, sys
args = sys.argv[1:]
with open(os.environ['UPDATE_TEST_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if ' '.join(args) == os.environ.get('UPDATE_TEST_FAIL'):
    sys.exit(7)
if args[:5] == ['compose', 'exec', '-T', 'pgdatabase', 'sh']:
    sys.exit(0 if os.environ['UPDATE_TEST_DB_READY'] == '1' else 1)
''')
            docker.chmod(0o755)
            sleep = binary / 'sleep'
            sleep.write_text('#!/bin/sh\nexit 0\n')
            sleep.chmod(0o755)
            log = install / 'commands.jsonl'
            env = dict(os.environ, PATH=f'{binary}:{os.environ["PATH"]}',
                       UPDATE_TEST_LOG=str(log), UPDATE_TEST_FAIL=fail,
                       UPDATE_TEST_DB_READY='1' if database_ready else '0')
            result = subprocess.run(['bash', str(install / 'update.sh')], cwd='/',
                                    env=env, text=True, capture_output=True, timeout=30)
            commands = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            return result, commands

    def test_full_down_before_migrations_and_full_up_after_setup(self):
        result, commands = self.run_update()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(commands[:4], [
            ['compose', 'config', '--quiet'], ['compose', 'pull'],
            ['compose', 'down', '--remove-orphans', '--timeout', '60'],
            ['compose', 'up', '-d', 'pgdatabase', 'redis'],
        ])
        runs = [cmd for cmd in commands if cmd[:2] == ['compose', 'run']]
        self.assertEqual(runs, [
            ['compose', 'run', '--rm', '--no-deps', 'backend', 'python3', './manage.py', *args]
            for args in (['migrate'], ['migrate', '--check'], ['check'], ['catcher_setup'])
        ])
        self.assertGreater(commands.index(['compose', 'up', '-d']), commands.index(runs[-1]))
        self.assertEqual(commands[-1], ['compose', 'ps', '--all'])
        self.assertFalse(any('--volumes' in cmd or '-v' in cmd for cmd in commands))

    def test_validation_or_pull_failure_leaves_running_stack_untouched(self):
        for fail in ('compose config --quiet', 'compose pull'):
            with self.subTest(fail=fail):
                result, commands = self.run_update(fail=fail)
                self.assertEqual(result.returncode, 7)
                self.assertFalse(any(cmd[:2] == ['compose', 'down'] for cmd in commands))

    def test_down_migration_or_setup_failure_never_starts_application(self):
        for fail in ('compose down --remove-orphans --timeout 60',
                     'compose run --rm --no-deps backend python3 ./manage.py migrate',
                     'compose run --rm --no-deps backend python3 ./manage.py migrate --check',
                     'compose run --rm --no-deps backend python3 ./manage.py check',
                     'compose run --rm --no-deps backend python3 ./manage.py catcher_setup'):
            with self.subTest(fail=fail):
                result, commands = self.run_update(fail=fail)
                self.assertEqual(result.returncode, 7)
                self.assertIn('Update failed', result.stderr)
                self.assertNotIn(['compose', 'up', '-d'], commands)
                self.assertNotIn(['image', 'prune', '--force'], commands)

    def test_database_timeout_is_bounded_and_prevents_migrations(self):
        result, commands = self.run_update(database_ready=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PostgreSQL did not become ready', result.stderr)
        self.assertEqual(sum(cmd[:2] == ['compose', 'exec'] for cmd in commands), 30)
        self.assertFalse(any(cmd[:2] == ['compose', 'run'] for cmd in commands))
        self.assertNotIn(['compose', 'up', '-d'], commands)

    def test_failed_start_does_not_prune_images(self):
        result, commands = self.run_update(fail='compose up -d')
        self.assertEqual(result.returncode, 7)
        self.assertNotIn(['image', 'prune', '--force'], commands)

    def test_saved_rollback_images_are_preserved(self):
        result, commands = self.run_update(rollback=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(['image', 'prune', '--force'], commands)

    def test_v3_guard_prevents_all_docker_commands(self):
        result, commands = self.run_update(pg_version='13')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Catcher v3 / PostgreSQL 13', result.stderr)
        self.assertEqual(commands, [])


if __name__ == '__main__':
    unittest.main()
