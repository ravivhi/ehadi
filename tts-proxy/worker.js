// ehadi speech proxy (Cloudflare Worker).
// GET /?l=he-IL&t=<sentence>  ->  MP3 from Google Cloud Text-to-Speech.
//
// Why it exists: many phones (e.g. Samsung's default engine) have no Hebrew voice. The app asks this proxy
// for natural audio instead. The Google API key stays here as a secret (GOOGLE_TTS_KEY), never in the app.
// Every sentence is cached at Cloudflare's edge (and on the phone by the app's service worker), so the same
// sentence is only paid for once.
//
// Limits against abuse: only the app's origins, only he-IL / en-US, sentences up to 300 characters.
// Also set a daily request quota for the Text-to-Speech API in Google Cloud (see README.md).

const VOICES = {
  'he-IL': { languageCode: 'he-IL', name: 'he-IL-Wavenet-A' },
  'en-US': { languageCode: 'en-US', name: 'en-US-Wavenet-F' },
};
const MAX_CHARS = 300;
const ALLOWED_ORIGINS = [/^https:\/\/ravivh\.com$/, /^https:\/\/www\.ravivh\.com$/, /^http:\/\/localhost(:\d+)?$/, /^http:\/\/127\.0\.0\.1(:\d+)?$/];

function cors(origin) {
  return {
    'Access-Control-Allow-Origin': origin || '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}
const reply = (status, body, origin, extra = {}) =>
  new Response(body, { status, headers: { 'Content-Type': 'text/plain; charset=utf-8', ...cors(origin), ...extra } });

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin') || '';
    const okOrigin = !origin || ALLOWED_ORIGINS.some((r) => r.test(origin));
    if (!okOrigin) return reply(403, 'origin not allowed', '');
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(origin) });
    if (request.method !== 'GET') return reply(405, 'GET only', origin);

    const url = new URL(request.url);
    const lang = url.searchParams.get('l') || 'he-IL';
    const text = (url.searchParams.get('t') || '').replace(/\s+/g, ' ').trim();
    const voice = VOICES[lang];
    if (!voice) return reply(400, 'unsupported language', origin);
    if (!text) return reply(400, 'missing text', origin);
    if (text.length > MAX_CHARS) return reply(413, 'text too long', origin);
    if (!env.GOOGLE_TTS_KEY) return reply(500, 'proxy not configured', origin);

    // edge cache, keyed only by language + text (not by origin), so every phone shares it
    const cacheKey = new Request(`https://tts-cache.invalid/${encodeURIComponent(lang)}/${encodeURIComponent(text)}`);
    const cache = typeof caches !== 'undefined' ? caches.default : null;
    if (cache) {
      const hit = await cache.match(cacheKey);
      if (hit) return withCors(hit, origin);
    }

    const g = await fetch(`https://texttospeech.googleapis.com/v1/text:synthesize?key=${env.GOOGLE_TTS_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: { text },
        voice,
        audioConfig: { audioEncoding: 'MP3', speakingRate: 0.9 },
      }),
    });
    if (!g.ok) {
      const detail = (await g.text()).slice(0, 300);
      console.log('google tts error', g.status, detail);
      return reply(502, 'speech service error', origin);
    }
    const { audioContent } = await g.json();
    const bytes = Uint8Array.from(atob(audioContent), (c) => c.charCodeAt(0));
    const res = new Response(bytes, {
      status: 200,
      headers: { 'Content-Type': 'audio/mpeg', 'Cache-Control': 'public, max-age=31536000, immutable' },
    });
    if (cache) ctx.waitUntil(cache.put(cacheKey, res.clone()));
    return withCors(res, origin);
  },
};

function withCors(res, origin) {
  const out = new Response(res.body, res);
  for (const [k, v] of Object.entries(cors(origin))) out.headers.set(k, v);
  return out;
}
