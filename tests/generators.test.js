/* Validates every curriculum skill's question generator at every difficulty level, in English and Hebrew.
   Run: node tests/generators.test.js [samplesPerLevel] */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

global.window = global;
const root = path.join(__dirname, '..', 'js');
['core.js', 'i18n_ui.js', 'curriculum.js', 'svg.js', 'gen_core.js', 'gen_number.js', 'gen_ops.js', 'gen_frac.js', 'gen_geo.js', 'gen_measure.js', 'gen_data.js', 'gen_adv.js']
  .forEach((f) => vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f }));

const MA = global.MA;
const N = +(process.argv[2] || 60);
const failures = {};
const errors = [];
MA.errors.capture = (err) => errors.push(String(err.message || err));

let made = 0, nulls = 0;
const uiCount = {};
const perSkillUis = {};
for (const lang of ['en', 'he']) {
  MA.i18n.setLang(lang, true);
  for (const skill of MA.CURRICULUM.skills) {
    for (let level = 1; level <= 5; level++) {
      const seen = new Set();
      for (let i = 0; i < N; i++) {
        const q = MA.gen.make(skill, level, { seen: i % 3 ? seen : undefined });
        if (!q) { nulls++; const k = `${skill.id} L${level} [${lang}]`; failures[k] = (failures[k] || 0) + 1; continue; }
        made++;
        uiCount[q.ui] = (uiCount[q.ui] || 0) + 1;
        (perSkillUis[skill.id] = perSkillUis[skill.id] || new Set()).add(q.ui + '|' + q.sig.split(':')[0]);
        // an answer that differs from the canonical one must not pass the check (guards against always-true checks)
        if (q.ui === 'input' && typeof q.answer === 'number' && MA.gen.check(q, q.answer + 1) && MA.gen.check(q, q.answer + 7)) {
          const k = `${skill.id} L${level} [${lang}] check accepts wrong answers`; failures[k] = (failures[k] || 0) + 1;
        }
      }
    }
  }
}
const uniqErr = {};
errors.forEach((e) => { const k = e.replace(/\d+/g, '#').slice(0, 220); uniqErr[k] = (uniqErr[k] || 0) + 1; });

// variety: games that used to repeat themselves (the place-value chart always showed 1000, ordering fractions
// was always 1/4 2/4 3/4, ...). [skill, levels, min different, 'a' = answers | 's' = questions]
MA.i18n.setLang('en', true);
const VARIETY = [
  ['g2-num-n1000', [1, 2, 3, 4, 5], 25, 'a'], ['g3-num-n10000', [1, 2, 3, 4, 5], 25, 'a'], ['g4-num-n100k', [3, 4, 5], 25, 'a'], ['g4-frac-order', [1, 2], 6, 'a'],
  ['g1-num-countback', [1], 6, 'a'], ['g1-num-seqs', [1], 6, 'a'], ['g1-num-count100', [1], 6, 'a'], ['g1-add-addmental', [1, 2], 8, 'a'], ['g1-add-add5', [1], 3, 'a'],
  ['g3-frac-numer', [1, 2], 3, 'a'], ['g4-geo-right', [1], 2, 'a'], ['g4-geo-acute', [1], 2, 'a'], ['g4-geo-obtuse', [1], 2, 'a'], ['g2-frac-half', [1, 3, 4], 2, 'a'],
  ['g2-meas-capacity', [1], 6, 'a'], ['g3-meas-temp', [1, 2], 6, 'a'], ['g6-geo-carea', [1, 2], 7, 'a'], ['g6-geo-circumference', [1, 2], 7, 'a'], ['g3-div-word', [1], 6, 'a'],
  ['g3-frac-qty', [1], 4, 'a'], ['g1-time-months', [5], 4, 'a'], ['g3-geo-area', [5], 8, 'a'], ['g3-geo-perimeter', [5], 8, 's'], ['g2-datalogic-sorting', [1], 10, 's'],
  ['g1-geo-patterns', [1], 8, 's'], ['g2-meas-m', [1], 10, 's'], ['g2-meas-mass', [1], 10, 's'], ['g3-logic-spatial', [1], 6, 's'], ['g4-dec-fracdec', [5], 10, 's'], ['g1-geo-shapeprops', [5], 4, 's']
];
const ansKey = (q) => { const o = q.data && Array.isArray(q.data.options) ? q.data.options.find((x) => JSON.stringify(x.v) === JSON.stringify(q.answer)) : null; return o ? 'o:' + (o.label || o.html || o.aria) : JSON.stringify(q.answer); };
for (const [id, levels, min, what] of VARIETY) {
  const skill = MA.CURRICULUM.skills.find((s) => s.id === id);
  if (!skill) { failures[`${id} (variety check: unknown skill)`] = 1; continue; }
  for (const level of levels) {
    const seen = new Set();
    for (let i = 0; i < 120; i++) { const q = MA.gen.make(skill, level, {}); if (q) seen.add(what === 'a' ? ansKey(q) : q.sig); }
    if (seen.size < min) failures[`${id} L${level} too little variety: ${seen.size} different ${what === 'a' ? 'answers' : 'questions'} (want ${min})`] = 1;
  }
}
console.log(`questions generated: ${made}, failed generations: ${nulls}`);
console.log('ui usage:', JSON.stringify(uiCount));
const single = Object.keys(perSkillUis).filter((k) => perSkillUis[k].size < 2);
console.log(`skills with only one problem type (ui + form): ${single.length}${single.length ? ' -> ' + single.join(', ') : ''}`);
const fk = Object.keys(failures);
if (fk.length) {
  console.log('\nFAILURES (skill level [lang]: count):');
  fk.sort().slice(0, 80).forEach((k) => console.log('  ', k, failures[k]));
  console.log('\nDistinct error messages:');
  Object.keys(uniqErr).sort((a, b) => uniqErr[b] - uniqErr[a]).slice(0, 40).forEach((k) => console.log('  ', uniqErr[k], '×', k));
  process.exitCode = 1;
} else console.log('ALL GENERATORS VALID');
