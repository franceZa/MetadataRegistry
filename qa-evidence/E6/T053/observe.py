"""Read-only T-53 observations. Run from repository root with profile mdf-free."""
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

OUT = Path(__file__).parent
RID = 'mdf-b255065b505d'
os.environ['DATABRICKS_CONFIG_PROFILE'] = 'mdf-free'


def mask(text):
    text = re.sub(r'https://[^/\s"\']*databricks\.(com|net)', 'https://<host>', text)
    return re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '<user>', text)


def cli(*args):
    p = subprocess.run(['databricks', *args], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError(mask(p.stdout + p.stderr))
    return p.stdout


def query(statement):
    wh = json.loads(cli('warehouses', 'list', '--output', 'json'))[0]['id']
    payload = {'statement': statement, 'warehouse_id': wh, 'wait_timeout': '50s',
               'on_wait_timeout': 'CONTINUE'}
    result = json.loads(cli('api', 'post', '/api/2.0/sql/statements',
                           '--json', json.dumps(payload)))
    for _ in range(60):
        if result['status']['state'] not in ('PENDING', 'RUNNING'):
            break
        time.sleep(5)
        result = json.loads(cli('api', 'get',
                               '/api/2.0/sql/statements/' + result['statement_id']))
    if result['status']['state'] != 'SUCCEEDED':
        raise RuntimeError(mask(json.dumps(result)))
    return {'statement': statement, 'status': result['status'],
            'columns': result.get('manifest', {}).get('schema', {}).get('columns'),
            'rows': result.get('result', {}).get('data_array', [])}


if __name__ == '__main__':
    statements = [
        "SELECT event, release_id, manifest_sha256, file_count, actor, "
        "CAST(event_ts AS STRING) AS event_ts FROM dev_catalog.ops.release_registry "
        "WHERE release_id IN ('mdf-b255065b505d','mdf-ef2f425903b6') ORDER BY event_ts",
        "SELECT release_id, actor, CAST(event_ts AS STRING) AS event_ts "
        "FROM dev_catalog.ops.release_registry WHERE event='ACTIVATED' "
        "ORDER BY event_ts DESC LIMIT 1",
    ]
    rows = [query(s) for s in statements]
    (OUT / 'registry-observation.json').write_text(mask(json.dumps(rows, indent=2)),
                                                 encoding='utf-8')
    print(mask(json.dumps(rows, indent=2)))
    base = 'dbfs:/Volumes/dev_catalog/ops/files/releases/' + RID
    listing = json.dumps({'root': json.loads(cli('fs', 'ls', base, '--output', 'json')),
                          'cc': json.loads(cli('fs', 'ls', base + '/cc', '--output', 'json'))},
                         indent=2)
    (OUT / 'volume-listing.json').write_text(mask(listing), encoding='utf-8')
    print(mask(listing))
