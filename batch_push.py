# -*- coding: utf-8 -*-
# Batch push gh-pages: split 103 family photo albums into 20 smaller batches
import os, subprocess, sys, math

os.chdir(r"D:\myblog\public")
ALBUM = "album/家庭照片"

dirs = sorted(os.listdir(ALBUM))
total = len(dirs)
batches = 35
batch_size = 3
print(f"Total folders: {total}, batch size ~{batch_size}, batches: {batches}", flush=True)

def run(cmd, cwd=None, timeout=3600):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    return r.returncode, (r.stdout + r.stderr).strip()

batch_num = 0
start = 0
failed = False

while start < total:
    batch_num += 1
    end = min(start + batch_size - 1, total - 1)
    slice_dirs = dirs[start:end+1]
    print("")
    print(f"===== Batch {batch_num}/{batches} (folders {start+1}-{end+1}, {len(slice_dirs)} items) =====", flush=True)
    
    paths = [f"{ALBUM}/{d}" for d in slice_dirs]
    code, out = run(["git", "add", "--"] + paths)
    if code != 0:
        print(f"[FAIL] add failed batch {batch_num}: {out}", flush=True)
        failed = True
        break
    
    if end == total - 1:
        code, out = run(["git", "add", "--", "albums/index.html"])
        print("(includes albums index.html)", flush=True)
    
    code, out = run(["git", "diff", "--cached", "--name-only"])
    staged_count = len([l for l in out.splitlines() if l.strip()])
    print(f"Staged files this batch: {staged_count}", flush=True)
    if staged_count == 0:
        print("[SKIP] no change", flush=True)
        start = end + 1
        continue
    
    code, out = run(["git", "commit", "-m", f"family photos album batch {batch_num}/{batches}"])
    print(out[-200:], flush=True)
    if code != 0:
        print(f"[FAIL] commit failed batch {batch_num}", flush=True)
        failed = True
        break
    
    # push with retry until success (up to 20 tries, 300s wait between - patient for network recovery)
    pushed = False
    for attempt in range(1, 21):
        print(f"Pushing batch {batch_num} (attempt {attempt}/20)...", flush=True)
        try:
            code, out = run(["git", "push", "origin", "gh-pages"], timeout=2400)
            print(out[-200:], flush=True)
            if code == 0:
                pushed = True
                break
            print(f"push attempt {attempt} failed code {code}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"push attempt {attempt} timeout", flush=True)
        # pause 300s (5 min) before next retry to let network recover
        subprocess.run(["powershell", "-Command", "Start-Sleep -Seconds 300"])
    
    if not pushed:
        print(f"[WARN] push failed after 6 attempts batch {batch_num}, will retry", flush=True)
        # keep going, next loop iteration the same batch is re-staged and re-pushed
        failed = True
        break
    print(f"Batch {batch_num} done OK", flush=True)
    start = end + 1

if failed:
    print(f"===== FAILED, stopped at batch {batch_num} =====", flush=True)
else:
    print(f"===== ALL {batch_num} batches pushed =====", flush=True)
code, out = run(["git", "log", "--oneline", "-1"])
print(f"Final HEAD: {out}", flush=True)
