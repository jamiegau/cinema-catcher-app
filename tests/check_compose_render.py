"""Read-only Docker Compose validation of real v3/v4 templates with fake secrets.

No images are pulled and no containers are created. Requires Docker Compose.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('upgrade_v4', ROOT/'upgrade/upgrade_v4.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

with tempfile.TemporaryDirectory(prefix='catcher-compose-fixture-') as temporary:
    site = Path(temporary)
    (site/'.env').write_text('CATCHER_HOSTNAME=fixture-cinema\nLOCAL_TIMEZONE_NAME=Australia/Melbourne\nEXPOSED_IP_PROJECTION_NETWORK=192.0.2.10\n')
    (site/'database.env').write_text("POSTGRES_USER=catcher_user\nPOSTGRES_DB=catcher_db\nPOSTGRES_PASSWORD='fixture-$only'\n")
    legacy = subprocess.check_output(['git', 'show', '3dfca85^:docker-compose.yml'], cwd=ROOT, text=True)
    legacy = re.sub(r'NB_SETUP_KEY=.*', 'NB_SETUP_KEY=fixture-only', legacy)
    (site/'v3.yml').write_text(legacy)
    environment = {key: value for key, value in os.environ.items() if not key.startswith(('COMPOSE_', 'POSTGRES_'))}
    base = ['docker', 'compose', '--profile', '*', '--project-directory', str(site), '--env-file', str(site/'.env'), '--project-name', 'fixture-cinema']
    def config(path):
        return json.loads(subprocess.check_output(base + ['-f', str(path), 'config', '--format', 'json'], env=environment))
    old, latest = config(site/'v3.yml'), config(ROOT/'docker-compose.yml')
    candidate = u.make_candidate(old, latest)
    u.write_compose(site/'candidate.json', candidate)
    validated = config(site/'candidate.json')
    assert validated['name'] == 'fixture-cinema'
    assert validated['services']['pgdatabase']['environment']['POSTGRES_PASSWORD'] == old['services']['pgdatabase']['environment']['POSTGRES_PASSWORD']
    assert validated['services']['netbird']['profiles'] == ['netbird']
    assert u.bind_for(validated['services']['pgdatabase'], '/var/lib/postgresql')['source'] == '/opt/catcher/postgresql/18'
    assert u.bind_for(validated['services']['redis'], '/data')['source'] == '/opt/catcher/redis'
    assert validated['services']['backend']['image'] == 'jamiegau/catcher_backend:4.0'
    assert 'worker_kdm' in validated['services']
    print('PASS: actual historical v3 and current v4 Compose templates render and merge safely with site credentials.')
