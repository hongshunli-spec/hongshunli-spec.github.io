# test_proxy_speed.py - test upload via HTTP proxy 127.0.0.1:7897 vs direct (TUN)
import sys, os, time, requests
sys.path.insert(0, r'D:\myblog')
import cf_upload as cf

PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

def upload_batch_proxy(jwt, batch):
    payload = []
    for rel, full, h in batch:
        with open(full, 'rb') as f:
            content = f.read()
        import base64, mimetypes
        b64 = base64.b64encode(content).decode('ascii')
        ct = mimetypes.guess_type(rel)[0] or 'application/octet-stream'
        payload.append({"key": h, "value": b64, "metadata": {"contentType": ct}, "base64": True})
    r = requests.post(f"{cf.CLIENT}/pages/assets/upload",
                      headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
                      json=payload, proxies=PROXIES, timeout=600)
    return r.status_code < 400, r.text[:100]

base = r'D:\myblog\public\album\家庭照片\20110417太朴山'
fns = sorted(os.listdir(base))
meta = []
total = 0
for fn in fns:
    full = os.path.join(base, fn)
    sz = os.path.getsize(full)
    if total + sz > 10*1024*1024:
        break
    with open(full, 'rb') as f:
        data = f.read()
    rel = 'album/家庭照片/20110417太朴山/' + fn
    h = cf.cf_hash(data, rel)
    meta.append((rel, full, h))
    total += sz
print(f'batch: {len(meta)} files, {total//1024}KB', flush=True)
jwt = cf.get_jwt()
allh = [m[2] for m in meta]
ok, err, miss = cf.check_missing(jwt, allh)
print(f'before: missing {len(miss)}', flush=True)
t0 = time.time()
s, err = upload_batch_proxy(jwt, meta)
t1 = time.time()
print(f'upload via proxy: {s} {err}, took {t1-t0:.1f}s', flush=True)
