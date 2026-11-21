/* Checks that every translation key used in the code exists in BOTH English and Hebrew.
   Loads all app modules (except app.js boot) in Node, hooks the private i18n dictionary, then scans
   the sources for literal t('key') calls, route titles, nav keys, error keys and known dynamic key families.
   Run: node tests/i18n.test.js */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

global.window = global;
const memStore = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k), clear: () => m.clear(), key: (i) => [...m.keys()][i], get length() { return m.size; } }; };
global.localStorage = memStore();
global.sessionStorage = memStore();

const appDir = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(appDir, 'index.html'), 'utf8');
const files = [...html.matchAll(/<script src="js\/([\w.]+)"><\/script>/g)].map((m) => m[1]);
if (!files.length) throw new Error('no scripts found in index.html');
const sources = {};
for (const f of files) {
  let src = fs.readFileSync(path.join(appDir, 'js', f), 'utf8');
  sources[f] = src;
  if (f === 'app.js') continue; // boot code needs a real browser
  if (f === 'core.js') {
    const hooked = src.replace('var dict = { en: {}, he: {} };', 'var dict = global.__i18nDict = { en: {}, he: {} };');
    if (hooked === src) throw new Error('could not hook the i18n dictionary in core.js');
    src = hooked;
  }
  vm.runInThisContext(src, { filename: f });
}
const dict = global.__i18nDict, MA = global.MA;

const used = new Map();
const use = (key, where) => { if (!used.has(key)) used.set(key, where); };
const lineOf = (src, idx) => src.slice(0, idx).split('\n').length;
for (const [f, src] of Object.entries(sources)) {
  // a literal key must be the whole argument (followed by "," or ")"); 'st_' + x style prefixes are dynamic
  const scans = [
    /(?:^|[^\w$.])t\(\s*'([a-z][\w]*)'(?=\s*[,)])/g,           // t('key'
    /\bMA\.t\(\s*'([a-z][\w]*)'(?=\s*[,)])/g,                  // MA.t('key'
    /\bi18n\.(?:t|list)\(\s*'([a-z][\w]*)'(?=\s*[,)])/g,       // MA.i18n.t / list
    /\bErr\(\s*'([a-z][\w]*)'(?=\s*[,)])/g,                    // service errors
    /\btitle:\s*'([a-z][\w]*)'/g,                   // route titles (translated by the router)
    /'(nav_[a-z_]+)'/g,                             // navigation arrays
    /\bnotify\([^;]*?'(n_[a-z_]+)'/g                // notification keys
  ];
  for (const re of scans) for (const m of src.matchAll(re)) use(m[1], `${f}:${lineOf(src, m.index)}`);
}
// dynamic key families
const fam = (prefix, list, where) => list.forEach((x) => use(prefix + x, where));
fam('set_', ['readAloud', 'hints', 'largeText', 'highContrast', 'reducedMotion'], 'settings options');
fam('s_cat_', ['me', 'clothes', 'legs', 'hair', 'hats', 'jewels', 'toys', 'pets', 'room'], 'shop categories');
fam('rp_st_', ['star', 'good', 'ok', 'help', 'new'], 'report topic status');
fam('rp_why_', ['practice', 'keep_going', 'new_skill', 'review', 'challenge', 'gap'], 'report next-week reasons');

const missing = { en: [], he: [] }, kindMismatch = [];
const kind = (v) => (Array.isArray(v) ? 'array' : typeof v);
for (const [key, where] of used) {
  for (const l of ['en', 'he']) if (dict[l][key] == null) missing[l].push(`${key}  (${where})`);
  if (dict.en[key] != null && dict.he[key] != null && kind(dict.en[key]) !== kind(dict.he[key]) && !(kind(dict.en[key]) === 'string' && kind(dict.he[key]) === 'function')) kindMismatch.push(key);
}
// keys defined in one language only
const onlyEn = Object.keys(dict.en).filter((k) => dict.he[k] == null), onlyHe = Object.keys(dict.he).filter((k) => dict.en[k] == null);

console.log(`modules loaded: ${files.length - 1}, keys used: ${used.size}, keys defined en/he: ${Object.keys(dict.en).length}/${Object.keys(dict.he).length}`);
let fail = false;
for (const l of ['en', 'he']) if (missing[l].length) { fail = true; console.log(`\nMISSING in ${l} (${missing[l].length}):\n  ` + missing[l].join('\n  ')); }
if (onlyEn.length) { fail = true; console.log(`\nDefined in en but not he (${onlyEn.length}): ${onlyEn.join(', ')}`); }
if (onlyHe.length) { fail = true; console.log(`\nDefined in he but not en (${onlyHe.length}): ${onlyHe.join(', ')}`); }
if (kindMismatch.length) { fail = true; console.log(`\nValue kind differs between languages: ${kindMismatch.join(', ')}`); }
console.log(fail ? '\nI18N CHECK FAILED' : '\nALL TRANSLATION KEYS PRESENT IN EN + HE');
process.exit(fail ? 1 : 0);
