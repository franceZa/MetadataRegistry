"""Offline T-58 runner: capture real commands and preservation checks."""
import hashlib
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ['UV_OFFLINE'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
for key in ('TMPDIR', 'TMP', 'TEMP'):
    os.environ[key] = str(Path(os.environ['LOCALAPPDATA']) / 'Temp')


def run(label, command):
    if len(command) > 2 and command[:3] == ['uv', 'run', 'pytest']:
        os.environ['PYTEST_ADDOPTS'] = '--junitxml="' + str(EVIDENCE / (label + '.xml')) + '"'
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    # JUnit adds the workstation hostname by default; omit it from public evidence.
    if command[:3] == ['uv', 'run', 'pytest']:
        import xml.etree.ElementTree as ET
        junit = EVIDENCE / (label + '.xml')
        if junit.exists():
            tree = ET.parse(junit)
            for suite in tree.getroot().iter('testsuite'):
                suite.attrib.pop('hostname', None)
            tree.write(junit, encoding='utf-8', xml_declaration=True)
    text = '$ ' + shlex.join(command) + '\n' + result.stdout + result.stderr + f'\nEXIT={result.returncode}\n'
    (EVIDENCE / (label + '.txt')).write_text(text, encoding='utf-8')
    print(text)
    return result.returncode


if sys.argv[1] == 'snapshot':
    paths = ['DataContract/_template/contract/my_dataset.odcs.yaml'] + [
        f'DataContract/cc/contract/{name}.odcs.yaml' for name in ('customer', 'credit_card', 'credit_card_txn')]
    baseline = {p: (ROOT / p).read_text(encoding='utf-8') for p in paths}
    baseline['calendar_lines'] = len((ROOT / 'src/mdf/calendar.py').read_text(encoding='utf-8').splitlines())
    baseline['git_status'] = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True).stdout
    (EVIDENCE / 'before.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Calendar before:', baseline['calendar_lines'])
    print(baseline['git_status'])
else:
    sys.exit(run(sys.argv[1], sys.argv[2:]))
