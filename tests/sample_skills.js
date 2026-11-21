/* Dev helper: print sample questions (and their read-aloud text) for skills matching a pattern.
   Run: node tests/sample_skills.js <skillRegex> [en|he|both] [perLevel] [outFile] */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

global.window = global;
const root = path.join(__dirname, '..', 'js');
['core.js', 'i18n_ui.js', 'curriculum.js', 'svg.js', 'gen_core.js', 'gen_number.js', 'gen_ops.js', 'gen_frac.js', 'gen_geo.js', 'gen_measure.js', 'gen_data.js', 'gen_adv.js']
  .forEach((f) => vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f }));

const MA = global.MA;
const re = new RegExp(process.argv[2] || '^g[56]-');
const langs = (process.argv[3] || 'both') === 'both' ? ['en', 'he'] : [process.argv[3]];
const per = +(process.argv[4] || 1);
const outFile = process.argv[5];
const lines = [];
const log = (s) => lines.push(s);
const strip = (s) => String(s == null ? '' : s).replace(/[\u2066-\u2069]/g, '');
const ans = (a) => (a && typeof a === 'object' ? JSON.stringify(a) : String(a));
for (const lang of langs) {
  MA.i18n.setLang(lang, true);
  for (const sk of MA.CURRICULUM.skills.filter((s) => re.test(s.id))) {
    log(`\n== ${sk.id} [${lang}] ${MA.tl(sk.name)}`);
    for (const level of [1, 3, 5]) {
      for (let i = 0; i < per; i++) {
        const q = MA.gen.make(sk, level, {});
        if (!q) { log(`  L${level}: (none)`); continue; }
        const spoken = MA.speech.text(MA.gen.spoken(q), MA.i18n.locale());
        log(`  L${level} ${q.ui}: ${strip(MA.gen.spoken(q))}`);
        log(`      answer=${ans(q.answer)} | explain=${strip(q.explain && q.explain.text)} | hint=${strip(q.hints[0] && q.hints[0].text)}`);
        log(`      SAY: ${spoken}`);
      }
    }
  }
}
if (outFile) fs.writeFileSync(outFile, '\uFEFF' + lines.join('\n'), 'utf8'); else console.log(lines.join('\n'));
