# test_concurrency.py - upload 4 batches x 10MB concurrently, measure total throughput
import sys, os, time, base64, mimetypes, requests, threading
sys.path.insert(0, r'D:\myblog')
import cf_upload as cf
from concurrent.futures import ThreadPoolExecutor, as_completed

def upload_one(jwt, meta):
    payload = []
    for rel, full, h in meta:
        with open(full, 'rb') as f:
            content = f.read()
        b64 = base64.b64encode(content).decode('ascii')
        ct = mimetypes.guess_type(rel)[0] or 'application/octet-stream'
        payload.append({"key": h, "value": b64, "metadata": {"contentType": ct}, "base64": True})
    r = requests.post(f"{cf.CLIENT}/pages/assets/upload",
                      headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
                      json=payload, timeout=900)
    return r.status_code < 400

# build 4 batches of ~10MB from different folders
folders = [d for d in os.listdir(r'D:\myblog\public\album\家庭照片') if os.path.isdir(os.path.join(r'D:\myblog\public\album\家庭照片', d))][:8]
batches = []
for fi in range(4):
    base = os.path.join(r'D:\myblog\public\album\家庭照片', folders[fi])
    meta = []
    total = 0
    for fn in sorted(os.listdir(base)):
        full = os.path.join(base, fn)
        sz = os.path.getsize(full)
        if total + sz > 10*1024*1024:
            break
        with open(full, 'rb') as f:
            data = f.read()
        rel = 'album/家庭照片/' + folders[fi] + '/' + fn
        h = cf.cf_hash(data, rel)
        meta.append((rel, full, h))
        total += sz
    batches.append(meta)

jwt = cf.get_jwt()
allh = []
for b in batches:
    allh += [m[2] for m in b]
ok, err, miss = cf.check_missing(jwt, allh)
print(f'total missing before: {len(miss)}', flush=True)

t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    futs = [ex.submit(upload_one, jwt, b) for b in batches]
    results = [f.result() for f in as_completed(futs)]
t1 = time.time()
print(f'4x10MB concurrent upload took {t1-t0:.0f}s ({4*10*1024/1024/(t1-t0)*1024:.0f} KB/s aggregate)', flush=True)
print(f'results: {results}', flush=True)
ok2, err2, miss2 = cf.check_missing(jwt, allh)
print(f'missing after upload: {len(miss2)} (upload does not affect missing)', flush=True)
