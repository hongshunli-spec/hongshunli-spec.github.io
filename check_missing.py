# check_missing.py - quick read-only check of how many files remain missing on Cloudflare
import sys, time
sys.path.insert(0, r'D:\myblog')
import cf_upload as cf

t0 = time.time()
files = cf.list_files()
hashes = []
for rel, full in files:
    with open(full, 'rb') as f:
        data = f.read()
    hashes.append(cf.cf_hash(data, rel))
print(f'files: {len(files)}, hash compute: {time.time()-t0:.0f}s', flush=True)
jwt = cf.get_jwt()
ok, err, missing = cf.check_missing(jwt, hashes)
if ok:
    print(f'missing: {len(missing)}', flush=True)
else:
    print(f'check failed: {err}', flush=True)
