# force_retest.py - force upload ONE file (skip check-missing) then verify via deployment URL
import sys, requests, base64, mimetypes
sys.path.insert(0, r'D:\myblog')
import cf_upload as cf

rel = 'album/家庭照片/20110417太朴山/IMG_20110416_180507.jpg'
full = r'D:\myblog\public\album\家庭照片\20110417太朴山\IMG_20110416_180507.jpg'
with open(full, 'rb') as f:
    content = f.read()
h = cf.cf_hash(content, rel)
print('hash:', h, flush=True)
jwt = cf.get_jwt()

# 1. check-missing
r = requests.post(cf.CLIENT + '/pages/assets/check-missing',
                  headers={'Authorization': 'Bearer ' + jwt, 'Content-Type': 'application/json'},
                  json={'hashes': [h]}, timeout=60)
print('check-missing:', r.json(), flush=True)

# 2. force upload (same format as before)
b64 = base64.b64encode(content).decode('ascii')
ct = mimetypes.guess_type(rel)[0] or 'application/octet-stream'
payload = [{'key': h, 'value': b64, 'metadata': {'contentType': ct}, 'base64': True}]
r = requests.post(cf.CLIENT + '/pages/assets/upload',
                  headers={'Authorization': 'Bearer ' + jwt, 'Content-Type': 'application/json'},
                  json=payload, timeout=300)
print('upload:', r.status_code, r.text[:300], flush=True)

# 3. upsert
r = requests.post(cf.CLIENT + '/pages/assets/upsert-hashes',
                  headers={'Authorization': 'Bearer ' + jwt, 'Content-Type': 'application/json'},
                  json={'hashes': [h]}, timeout=60)
print('upsert:', r.status_code, r.text[:200], flush=True)

# 4. verify via a small new deployment referencing only this file
import json as _json
manifest = {'/album/家庭照片/20110417太朴山/IMG_20110416_180507.jpg': h}
r = requests.post(f'{cf.CLIENT}/accounts/{cf.ACC}/pages/projects/{cf.PROJ}/deployments',
                  headers=cf.H,
                  files={'branch': (None, 'main'), 'manifest': (None, _json.dumps(manifest))}, timeout=60)
print('deployment:', r.status_code, r.text[:200], flush=True)
if r.status_code < 400:
    dep = r.json()['result']
    short = dep['id'][:8]
    url = f'https://{short}.hongshunli-blog.pages.dev/album/家庭照片/20110417太朴山/IMG_20110416_180507.jpg'
    r2 = requests.get(url, timeout=60)
    print('asset status:', r2.status_code, url, flush=True)
