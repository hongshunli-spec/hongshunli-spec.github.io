# cf_upload.py - Cloudflare Pages Direct Upload, official 5-step flow with BLAKE3 hashes
import os, sys, json, base64, mimetypes, requests, blake3, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

ACC = "b3c6c92b00c7ee1a63a6c990b952aeb7"
PROJ = "hongshunli-blog"
PUBLIC = r"D:\myblog\public"
CLIENT = "https://api.cloudflare.com/client/v4"
TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
H = {"Authorization": f"Bearer {TOKEN}"}

IGNORE_FILES = {"_worker.js", "_redirects", "_headers", "_routes.json", ".DS_Store"}
IGNORE_DIRS = {".git", "node_modules", "functions", ".wrangler"}

def cf_hash(data: bytes, rel: str) -> str:
    ext = os.path.splitext(rel)[1][1:]  # extension without dot
    b64 = base64.b64encode(data)
    return blake3.blake3(b64 + ext.encode("ascii")).hexdigest()[:32]

def get_jwt():
    r = requests.get(f"{CLIENT}/accounts/{ACC}/pages/projects/{PROJ}/upload-token", headers=H, timeout=60)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(f"upload-token failed: {d}")
    return d["result"]["jwt"]

def check_missing(jwt, hashes):
    r = requests.post(f"{CLIENT}/pages/assets/check-missing",
                      headers={"Authorization": f"Bearer {jwt}"},
                      json={"hashes": hashes}, timeout=120)
    if r.status_code >= 400:
        return False, f"HTTP {r.status_code}: {r.text[:300]}", []
    d = r.json()
    if not d.get("success"):
        return False, str(d.get("errors")), []
    return True, None, d.get("result", [])

def upload_batch(jwt, batch):
    # batch: list of (rel, full, hash). JSON array body
    payload = []
    for rel, full, h in batch:
        with open(full, "rb") as f:
            content = f.read()
        b64 = base64.b64encode(content).decode("ascii")
        ct = mimetypes.guess_type(rel)[0] or "application/octet-stream"
        payload.append({"key": h, "value": b64, "metadata": {"contentType": ct}, "base64": True})
    r = requests.post(f"{CLIENT}/pages/assets/upload",
                      headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
                      json=payload, timeout=900)
    if r.status_code >= 400:
        return False, f"HTTP {r.status_code}: {r.text[:300]}"
    d = r.json()
    if not d.get("success"):
        return False, str(d.get("errors"))
    return True, None

def upsert_hashes(jwt, hashes):
    r = requests.post(f"{CLIENT}/pages/assets/upsert-hashes",
                      headers={"Authorization": f"Bearer {jwt}"},
                      json={"hashes": hashes}, timeout=120)
    if r.status_code >= 400:
        return False, f"HTTP {r.status_code}: {r.text[:300]}"
    d = r.json()
    return d.get("success", False), d.get("errors")

def create_deployment(manifest, branch="main"):
    # must be multipart/form-data (not urlencoded)
    form = {"branch": (None, branch), "manifest": (None, json.dumps(manifest, separators=(",", ":")))}
    r = requests.post(f"{CLIENT}/accounts/{ACC}/pages/projects/{PROJ}/deployments",
                      headers=H, files=form, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"deployment HTTP {r.status_code}: {r.text[:500]}")
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(f"deployment failed: {json.dumps(d.get('errors'))}")
    return d["result"]

def list_files():
    files = []
    for root, dirs, fnames in os.walk(PUBLIC):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fn in fnames:
            if fn in IGNORE_FILES:
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, PUBLIC).replace("\\", "/")
            files.append((rel, full))
    return files

def main():
    files = list_files()
    print(f"Total files: {len(files)}", flush=True)
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
        files = files[:limit]
        print(f"TEST MODE: only {limit} files", flush=True)

    print("Computing BLAKE3 hashes...", flush=True)
    manifest = {}
    meta = []  # (rel, full, hash)
    for rel, full in files:
        with open(full, "rb") as f:
            data = f.read()
        h = cf_hash(data, rel)
        manifest["/" + rel] = h
        meta.append((rel, full, h))

    print("Getting upload JWT...", flush=True)
    jwt = get_jwt()

    print("Checking missing assets...", flush=True)
    all_hashes = [m[2] for m in meta]
    ok, err, missing = check_missing(jwt, all_hashes)
    if not ok:
        print(f"check-missing failed: {err}"); return 1
    print(f"Missing: {len(missing)} of {len(all_hashes)}", flush=True)
    missing_set = set(missing)
    to_upload = [m for m in meta if m[2] in missing_set]

    # upload in batches (<=20MB or 100 files), concurrent 3
    batches = []
    cur, cursz = [], 0
    for m in to_upload:
        sz = os.path.getsize(m[1])
        if cur and (len(cur) >= 100 or cursz + sz > 20*1024*1024):
            batches.append(cur); cur, cursz = [], 0
        cur.append(m); cursz += sz
    if cur:
        batches.append(cur)
    print(f"Upload batches: {len(batches)}", flush=True)
    okc = failc = 0
    jwt_holder = {"jwt": jwt, "lock": threading.Lock()}
    def up_with_retry(batch, attempts=4):
        for i in range(attempts):
            with jwt_holder["lock"]:
                cur_jwt = jwt_holder["jwt"]
            s, err = upload_batch(cur_jwt, batch)
            if s:
                return True, None
            print(f"    batch fail, refresh JWT (try {i+1}): {err}", flush=True)
            with jwt_holder["lock"]:
                jwt_holder["jwt"] = get_jwt()
        return False, err
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(up_with_retry, b): i for i, b in enumerate(batches)}
        for f in as_completed(futs):
            s, err = f.result()
            if s:
                okc += 1
            else:
                failc += 1
                print(f"  batch {futs[f]} FAILED: {err}", flush=True)
    print(f"Upload: ok={okc}, failed={failc}", flush=True)
    if failc > 0:
        print("ABORT: upload failed."); return 1

    print("Upserting hashes...", flush=True)
    uok = ufail = 0
    for i in range(0, len(all_hashes), 1000):
        s, err = upsert_hashes(jwt_holder["jwt"], all_hashes[i:i+1000])
        if s: uok += 1
        else:
            ufail += 1
            print(f"  upsert chunk {i//1000} FAILED: {err}", flush=True)
    print(f"Upsert: ok={uok}, failed={ufail}", flush=True)
    if ufail > 0:
        print("ABORT: upsert failed."); return 1

    print("Creating deployment...", flush=True)
    dep = create_deployment(manifest)
    print(f"Deployment: {dep.get('id')} url={dep.get('url')}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
