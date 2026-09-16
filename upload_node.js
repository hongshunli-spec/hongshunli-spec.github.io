// upload_node.js v3 - upload public/ to Cloudflare Pages, NO upsert (upsert breaks serving!), local progress file for resume
const { blake3 } = require('@noble/hashes/blake3.js');
const fs = require('fs');
const path = require('path');

const ACC = 'b3c6c92b00c7ee1a63a6c990b952aeb7';
const PROJ = 'hongshunli-blog';
const CLIENT = 'https://api.cloudflare.com/client/v4';
const DIR = 'D:\\myblog\\public';
const TOKEN = process.env.CLOUDFLARE_API_TOKEN;
const H = { Authorization: `Bearer ${TOKEN}` };
const BATCH_BYTES = 10 * 1024 * 1024;
const REQ_TIMEOUT = 180000;
const PROGRESS = 'D:\\myblog\\cf_progress.json';

const CT_MAP = {
  '.html': 'text/html', '.htm': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
  '.json': 'application/json', '.xml': 'application/xml', '.txt': 'text/plain',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif',
  '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.bmp': 'image/bmp',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg', '.wav': 'audio/wav',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf',
  '.pdf': 'application/pdf', '.zip': 'application/zip', '.gz': 'application/gzip',
  '.md': 'text/markdown', '.webmanifest': 'application/manifest+json', '.map': 'application/json'
};

function cfHash(content, relPath) {
  const ext = path.extname(relPath).slice(1);
  const h = blake3(Buffer.from(content.toString('base64') + ext));
  return Buffer.from(h).toString('hex').slice(0, 32);
}

async function api(pathUrl, options = {}) {
  const res = await fetch(CLIENT + pathUrl, { ...options, signal: AbortSignal.timeout(REQ_TIMEOUT) });
  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} ${pathUrl}: ${text.slice(0, 300)}`);
  let data; try { data = JSON.parse(text); } catch (e) { throw new Error(`bad json ${pathUrl}: ${text.slice(0,200)}`); }
  return data;
}

async function getJwt() {
  const d = await api(`/accounts/${ACC}/pages/projects/${PROJ}/upload-token`, { headers: H });
  return d.result.jwt;
}

async function uploadBatch(jwt, batch) {
  const payload = batch.map(f => ({
    key: f.hash, value: f.content.toString('base64'),
    metadata: { contentType: f.contentType }, base64: true
  }));
  const d = await api(`/pages/assets/upload`, {
    method: 'POST', headers: { Authorization: `Bearer ${jwt}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return d;
}

async function createDeployment(manifest) {
  const form = new FormData();
  form.append('branch', 'main');
  form.append('manifest', JSON.stringify(manifest));
  const d = await api(`/accounts/${ACC}/pages/projects/${PROJ}/deployments`, {
    method: 'POST', headers: H, body: form
  });
  return d.result;
}

(async () => {
  try {
    // 1. walk files
    const files = [];
    (function walk(dir, rel) {
      for (const name of fs.readdirSync(dir)) {
        if (name === '.git') continue;
        const full = path.join(dir, name);
        const relPath = rel ? rel + '/' + name : name;
        const st = fs.statSync(full);
        if (st.isDirectory()) walk(full, relPath);
        else files.push({ relPath, full, size: st.size });
      }
    })(DIR, '');
    console.log(`Total files: ${files.length}`);
    // 2. hash all
    const t0 = Date.now();
    const hashed = [];
    for (const f of files) {
      const content = fs.readFileSync(f.full);
      const hash = cfHash(content, f.relPath);
      const ct = CT_MAP[path.extname(f.relPath).toLowerCase()] || 'application/octet-stream';
      hashed.push({ relPath: f.relPath, size: f.size, hash, content, contentType: ct });
    }
    console.log(`Hashed ${hashed.length} files in ${((Date.now()-t0)/1000).toFixed(0)}s`);
    // 3. local progress (hashes already uploaded this session)
    const doneSet = new Set();
    if (fs.existsSync(PROGRESS)) {
      try {
        for (const h of JSON.parse(fs.readFileSync(PROGRESS, 'utf8'))) doneSet.add(h);
      } catch (e) {}
    }
    const toUpload = hashed.filter(f => !doneSet.has(f.hash));
    console.log(`To upload: ${toUpload.length} of ${hashed.length} (${doneSet.size} done)`);
    if (toUpload.length === 0) { console.log('Nothing to upload'); }
    // 4. batches
    const batches = [];
    let cur = [], curSize = 0;
    for (const f of toUpload) {
      if (cur.length && curSize + f.size > BATCH_BYTES) { batches.push(cur); cur = []; curSize = 0; }
      cur.push(f); curSize += f.size;
    }
    if (cur.length) batches.push(cur);
    console.log(`Upload batches: ${batches.length}`);
    let done = 0;
    let jwt = await getJwt();
    for (let i = 0; i < batches.length; i++) {
      const b = batches[i];
      const t1 = Date.now();
      let ok = false;
      for (let attempt = 0; attempt < 5 && !ok; attempt++) {
        try {
          const j = (attempt === 0) ? jwt : await getJwt();
          await uploadBatch(j, b);
          ok = true;
        } catch (e) {
          console.log(`  batch ${i+1} fail try ${attempt+1}: ${e.message}`);
          await new Promise(r => setTimeout(r, 5000));
        }
      }
      if (!ok) throw new Error(`batch ${i+1} failed after retries`);
      // save progress (no upsert - it breaks serving!)
      for (const f of b) doneSet.add(f.hash);
      fs.writeFileSync(PROGRESS, JSON.stringify([...doneSet]));
      done += b.length;
      console.log(`  batch ${i+1}/${batches.length} uploaded (${done}/${toUpload.length}), ${((Date.now()-t1)/1000).toFixed(0)}s`);
    }
    // 5. create deployment with FULL manifest (all hashed files)
    console.log('Creating deployment...');
    const manifest = {};
    for (const f of hashed) manifest['/' + f.relPath] = f.hash;
    const dep = await createDeployment(manifest);
    console.log(`Deployment: ${dep.id} url: ${dep.url}`);
  } catch (e) {
    console.error('FATAL:', e.message);
    process.exit(1);
  }
})();
