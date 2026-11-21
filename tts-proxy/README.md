# ehadi speech proxy

Many phones have no Hebrew text-to-speech voice (for example Samsung's default engine), so read-aloud was silent there.
When a phone has no voice for the language, the app now gets natural audio from this small proxy instead:

```
app  --GET ?l=he-IL&t=<sentence>-->  Cloudflare Worker (this folder)  --API key-->  Google Cloud Text-to-Speech
```

- Phones that do have a Hebrew voice keep using it (free, offline). The proxy is only used when needed.
- Only the sentence text is sent, never the child's name.
- Every sentence is cached at Cloudflare (shared by all phones) and on the phone (service worker cache `ehadi-tts`), so each sentence is paid for once.
- If the proxy can't be reached, the app falls back to the phone's own voice.
- The Google key is a Worker secret and never appears in the app.

Tests: `node tts-proxy/worker.test.mjs` (Google and Cloudflare are mocked).

## One-time setup (owner)

### 1. Google Cloud: API key for Text-to-Speech

1. https://console.cloud.google.com → create a project (e.g. `ehadi`). A billing account is required even for the free tier.
2. **APIs & Services → Library →** enable **Cloud Text-to-Speech API**.
3. **APIs & Services → Credentials → Create credentials → API key.** Then **edit the key**:
   - *API restrictions*: restrict to **Cloud Text-to-Speech API** only.
   - (Leave *Application restrictions* as None: the key is only used by the Worker, server-side.)
4. **Protect the bill.** In **IAM & Admin → Quotas**, find Cloud Text-to-Speech *requests per day* and set a cap (e.g. 5,000). Also add a **budget alert** in Billing.

Free tier (per month): about 1 million characters of WaveNet voices. A question is about 50–100 characters, and each sentence is only paid for the first time, so typical use stays free.

### 2. Cloudflare Worker

Either in the dashboard (no tools needed):

1. https://dash.cloudflare.com → sign up (free) → **Workers & Pages → Create → Create Worker**, name it `ehadi-tts`, **Deploy**.
2. **Edit code** → replace everything with the contents of `worker.js` → **Deploy**.
3. **Settings → Variables and Secrets → Add → Secret**: name `GOOGLE_TTS_KEY`, value = the Google API key → **Deploy**.
4. Note the Worker URL, e.g. `https://ehadi-tts.<your-subdomain>.workers.dev/`.

or with the CLI from this folder: `npx wrangler deploy` then `npx wrangler secret put GOOGLE_TTS_KEY`.

Check it: open `https://ehadi-tts.<your-subdomain>.workers.dev/?l=he-IL&t=שלום` in a browser. It should play "שלום".

### 3. Turn it on in the app

In `js/core.js` set `var TTS_URL = 'https://ehadi-tts.<your-subdomain>.workers.dev/';`, bump `CACHE` in `sw.js`, push, and publish (Run workflow on *Sync ehadi* in ravivhi/guessingGame).

## Changing the voice

`VOICES` at the top of `worker.js`. Hebrew options: `he-IL-Wavenet-A`/`C` (female), `he-IL-Wavenet-B`/`D` (male), or `he-IL-Standard-*` (cheaper, 4M free characters/month). Changing the voice doesn't refresh audio already cached on phones; also change the URL (e.g. add `v=2`) if you need that.
