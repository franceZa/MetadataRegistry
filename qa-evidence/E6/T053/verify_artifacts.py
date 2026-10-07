"""Verify real downloaded GitHub zip against Volume read-back, without rebuilding."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from observe import mask

OUT = Path(__file__).parent
RID = 'mdf-b255065b505d'
WORK = Path('C:/Users/User/AppData/Local/Temp/t053-release/build/deliver') / RID
meta = json.loads(subprocess.check_output(
    ['gh', 'release', 'view', RID, '--json', 'url,tagName,targetCommitish,body,assets'],
    encoding='utf-8'))
(OUT / 'release-metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
zip_path = WORK / 'zip-download' / (RID + '.zip')
zip_digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
assert len(meta['assets']) == 1
assert meta['assets'][0]['name'] == zip_path.name
assert meta['assets'][0]['digest'] == 'sha256:' + zip_digest
with zipfile.ZipFile(zip_path) as z:
    files = sorted(n for n in z.namelist() if not n.endswith('/'))
    manifest_bytes = z.read('manifest.json')
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    assert manifest['manifest_version'] == 3
    assert manifest['file_count'] == 9
    assert len(files) == 11
    assert len([f for f in files if f.endswith('.resolved.json')]) == 6
    assert len([f for f in files if f.endswith('.odcs.yaml')]) == 3
    assert 'manifest_sha256: ' + digest in meta['body']
    for entry in manifest['files']:
        raw = z.read(entry['path'])
        assert hashlib.sha256(raw).hexdigest() == entry['sha256']
        assert raw == (WORK / 'back' / entry['path']).read_bytes()
    assert manifest_bytes == (WORK / 'back' / 'manifest.json').read_bytes()
    assert z.read('validation-report.json') == (WORK / 'back' / 'validation-report.json').read_bytes()
listing = json.loads((OUT / 'volume-listing.json').read_text())
assert len([e for e in listing['root'] if not e['is_directory']]) == 2
assert len(listing['cc']) == 9
sample = json.loads((OUT / 'resolved-sample.json').read_text())
assert 'calendar' in sample and 'reader' in sample
assert all('pii' in c and 'pci' in c for c in sample['schema'])
rows = json.loads((OUT / 'registry-observation.json').read_text())
assert rows[1]['rows'][0][0] == RID
assert any(r[0] == 'REGISTERED' and r[1] == RID and r[2] == digest and r[3] == '9' and r[4] == 'u2m'
           for r in rows[0]['rows'])
result = {'status': 'PASS', 'release_id': RID, 'manifest_version': 3,
          'manifest_sha256': digest, 'zip_sha256': zip_digest,
          'files': files, 'file_count': manifest['file_count'],
          'zip_volume_bytes_match': True, 'final_active_release': rows[1]['rows'][0]}
(OUT / 'artifact-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
(OUT / 'delivery-evidence.md').write_text(mask((WORK / 'evidence.md').read_text(encoding='utf-8')),
                                           encoding='utf-8')
print(json.dumps(result, indent=2))
