// Tests the speech proxy without Cloudflare or Google: both are mocked.
// Run: node tts-proxy/worker.test.mjs
import worker from './worker.js';

let fails = 0;
const ok = (cond, label) => { if (!cond) { fails++; console.log('FAIL', label); } };

// mock edge cache
const store = new Map();
globalThis.caches = { default: { match: async (k) => store.get(k.url)?.clone(), put: async (k, r) => { store.set(k.url, r); } } };
// mock Google TTS
const calls = [];
globalThis.fetch = async (url, init) => {
  calls.push({ url: String(url), body: JSON.parse(init.body) });
  if (String(url).includes('key=BAD')) return new Response('{"error":"bad key"}', { status: 403 });
  return new Response(JSON.stringify({ audioContent: btoa('ID3fake-mp3') }), { status: 200 });
};
const env = { GOOGLE_TTS_KEY: 'K' };
const ctx = { waitUntil: (p) => p };
const get = (q, origin = 'https://ravivh.com', e = env) =>
  worker.fetch(new Request('https://proxy.example/?' + q, { headers: origin ? { Origin: origin } : {} }), e, ctx);

const t = encodeURIComponent('כמה זה 3 ועוד 4?');
let r = await get('l=he-IL&t=' + t);
ok(r.status === 200, 'hebrew sentence -> 200');
ok(r.headers.get('Content-Type') === 'audio/mpeg', 'mp3 content type');
ok(r.headers.get('Access-Control-Allow-Origin') === 'https://ravivh.com', 'CORS for the app origin');
ok(new TextDecoder().decode(await r.arrayBuffer()) === 'ID3fake-mp3', 'audio bytes passed through');
ok(calls.length === 1 && calls[0].body.voice.languageCode === 'he-IL' && calls[0].body.input.text === 'כמה זה 3 ועוד 4?', 'google called with hebrew voice and the text');
ok(calls[0].url.includes('key=K'), 'key comes from the secret');

r = await get('l=he-IL&t=' + t);
ok(r.status === 200 && calls.length === 1, 'second identical request served from cache (no second google call)');

ok((await get('l=he-IL&t=' + t, 'https://evil.example')).status === 403, 'other origins blocked');
ok((await get('l=fr-FR&t=abc')).status === 400, 'unsupported language rejected');
ok((await get('l=he-IL&t=')).status === 400, 'empty text rejected');
ok((await get('l=he-IL&t=' + 'א'.repeat(301))).status === 413, 'long text rejected');
ok((await get('l=he-IL&t=abc', 'https://ravivh.com', {})).status === 500, 'missing key -> 500, not a crash');
ok((await get('l=he-IL&t=xyz', 'https://ravivh.com', { GOOGLE_TTS_KEY: 'BAD' })).status === 502, 'google error -> 502');
const pre = await worker.fetch(new Request('https://proxy.example/', { method: 'OPTIONS', headers: { Origin: 'https://ravivh.com' } }), env, ctx);
ok(pre.status === 204 && pre.headers.get('Access-Control-Allow-Methods').includes('GET'), 'CORS preflight');
ok((await get('l=en-US&t=hello')).status === 200 && calls.at(-1).body.voice.languageCode === 'en-US', 'english works too');

console.log(fails ? `${fails} FAILED` : 'tts-proxy: all tests passed');
process.exit(fails ? 1 : 0);
