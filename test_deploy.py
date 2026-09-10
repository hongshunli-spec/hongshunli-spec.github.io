# test_deploy.py - ultimate test: create deployment with 3 real photos, verify asset URL
import sys, os, requests, time, json
sys.path.insert(0, r'D:\myblog')
import cf_upload as cf

base = r'D:\myblog\public\album\家庭照片\20110417太朴山'
fns = sorted(os.listdir(base))[6:9]
manifest = {}
for fn in fns:
    full = os.path.join(base, fn)
    with open(full, 'rb') as f:
        data = f.read()
    rel = 'album/家庭照片/20110417太朴山/' + fn
    h = cf.cf_hash(data, rel)
    manifest['/' + rel] = h
print('manifest keys:', list(manifest.keys()), flush=True)
dep = cf.create_deployment(manifest)
did = dep['id']
print('deployment:', did, flush=True)
for i in range(12):
    time.sleep(10)
    r = requests.get(f'{cf.CLIENT}/accounts/{cf.ACC}/pages/projects/{cf.PROJ}/deployments/{did}',
                     headers=cf.H, timeout=30)
    st = r.json()['result']['latest_stage']
    print(f'poll {i}: stage={st["name"]} status={st["status"]}', flush=True)
    if st['status'] in ('success', 'failure'):
        break
short = did[:8]
url = f'https://{short}.hongshunli-blog.pages.dev/album/家庭照片/20110417太朴山/{fns[0]}'
r2 = requests.get(url, timeout=30)
print('asset URL:', url, flush=True)
print('asset status:', r2.status_code, flush=True)
