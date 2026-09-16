// test_https.js - upload ONE file via https.request with explicit Content-Length, then verify
const https = require('https');
const fs = require('fs');

const ACC = 'b3c6c92b00c7ee1a63a6c990b952aeb7';
const PROJ = 'hongshunli-blog';
const TOKEN = process.env.CLOUDFLARE_API_TOKEN;
const HOST = 'api.cloudflare.com';

function request(path, { method = 'GET', headers = {}, body = null } = {}) {
  return new Promise((resolve, reject) => {
    const hdrs = { ...headers };
    if (body) { hdrs['Content-Length'] = Buffer.byteLength(body); }
    const req = https.request({ host: HOST, path, method, headers: hdrs }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => resolve({ status: res.statusCode, text: data }));
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

(async () => {
  // reuse body prepared by python
  const payload = JSON.parse(fs.readFileSync('D:\\myblog\\_body.json', 'utf8'));
  const hash = payload[0].key;
  // get fresh jwt
  let r = await request(`/client/v4/accounts/${ACC}/pages/projects/${PROJ}/upload-token`, { headers: { Authorization: `Bearer ${TOKEN}` } });
  const jwt = JSON.parse(r.text).result.jwt;
  console.log('jwt ok', r.status);
  // upload with Content-Length
  const t0 = Date.now();
  r = await request('/client/v4/pages/assets/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${jwt}`, 'Content-Type': 'application/json', 'User-Agent': 'python-requests/2.28.1' },
    body: JSON.stringify(payload)
  });
  console.log(`upload: ${r.status} ${r.text.slice(0, 150)} ${((Date.now()-t0)/1000).toFixed(1)}s`);
  // upsert
  r = await request('/client/v4/pages/assets/upsert-hashes', {
    method: 'POST',
    headers: { Authorization: `Bearer ${jwt}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ hashes: [hash] })
  });
  console.log(`upsert: ${r.status} ${r.text.slice(0, 100)}`);
  // deployment (multipart)
  const manifest = JSON.stringify({ '/album/家庭照片/20110417太朴山/IMG_20110416_183302.jpg': hash });
  const boundary = '----nodeboundary' + Date.now();
  const parts = [];
  parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="branch"\r\n\r\nmain\r\n`);
  parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="manifest"\r\n\r\n${manifest}\r\n`);
  parts.push(`--${boundary}--\r\n`);
  const body = Buffer.from(parts.join(''));
  r = await request(`/client/v4/accounts/${ACC}/pages/projects/${PROJ}/deployments`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` },
    body
  });
  console.log(`deployment: ${r.status} ${r.text.slice(0, 150)}`);
  if (r.status < 400) {
    const dep = JSON.parse(r.text).result;
    const enc = encodeURI('/album/家庭照片/20110417太朴山/IMG_20110416_183302.jpg');
    const url = `https://${dep.id.slice(0,8)}.hongshunli-blog.pages.dev${enc}`;
    const r2 = await request(url, {});
    console.log(`asset: ${r2.status} ${url}`);
  }
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
