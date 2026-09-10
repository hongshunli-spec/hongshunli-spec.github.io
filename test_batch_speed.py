# test_batch_speed.py - upload a batch of ~10MB of real photos, time it, verify missing decreases
import sys, os, time, requests
sys.path.insert(0, r'D:\myblog')
import cf_upload as cf

# collect ~10MB of photos
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
allh = [m[2] for m in meta]
jwt = cf.get_jwt()
ok, err, miss = cf.check_missing(jwt, allh)
print(f'before: missing {len(miss)}', flush=True)
if not miss:
    print('nothing missing, skip', flush=True)
    sys.exit(0)
t0 = time.time()
s, err = cf.upload_batch(jwt, meta)
t1 = time.time()
print(f'upload result: {s} {err}, took {t1-t0:.1f}s', flush=True)
ok2, err2, miss2 = cf.check_missing(jwt, allh)
print(f'after upload: missing {len(miss2)}', flush=True)
s2, err3 = cf.upsert_hashes(jwt, allh)
print(f'upsert: {s2}, took {time.time()-t1:.1f}s', flush=True)
ok3, err4, miss3 = cf.check_missing(jwt, allh)
print(f'after upsert: missing {len(miss3)}', flush=True)
