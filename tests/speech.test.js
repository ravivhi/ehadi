/* Checks that read-aloud text turns math notation into words and splits long text into short pieces.
   Run: node tests/speech.test.js */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

global.window = global;
const root = path.join(__dirname, '..', 'js');
['core.js', 'i18n_ui.js', 'curriculum.js', 'svg.js', 'gen_core.js', 'gen_number.js', 'gen_ops.js', 'gen_frac.js', 'gen_geo.js', 'gen_measure.js', 'gen_data.js', 'gen_adv.js']
  .forEach((f) => vm.runInThisContext(fs.readFileSync(path.join(root, f), 'utf8'), { filename: f }));
const MA = global.MA;
const say = (s, lang) => MA.speech.text(s, lang);
let fails = 0;
function eq(input, lang, want) {
  const got = say(input, lang);
  if (got !== want) { fails++; console.log(`FAIL [${lang}] ${JSON.stringify(input)}\n   got:  ${JSON.stringify(got)}\n   want: ${JSON.stringify(want)}`); }
}
eq('Solve: 6 + _ = 9', 'en-US', 'Solve: 6 plus what number equals 9');
eq('Divide. What is the remainder? 495 ÷ 2 = 247 R ?', 'en-US', 'Divide. What is the remainder? 495 divided by 2 equals 247 remainder what number');
eq('821 ÷ 8 = ? R 5', 'en-US', '821 divided by 8 equals what number remainder 5');
eq('3/4 = ?/8', 'en-US', '3 over 4 equals what number over 8');
eq('2 3/4 + 1/4 = ?/?', 'en-US', '2 and 3 over 4 plus 1 over 4 equals what number');
eq('Counting 0–20', 'en-US', 'Counting 0 to 20');
eq('Is 5 < 7?', 'en-US', 'Is 5 is less than 7?');
eq('The area is 12 cm².', 'en-US', 'The area is 12 square centimeters.');
eq('Calculate. (3 + 4) × 5 = ?', 'en-US', 'Calculate. 3 plus 4, times 5 equals what number');
eq('How many apples are there?', 'en-US', 'How many apples are there?');
eq('\u20667 − 2 = 5\u2069', 'en-US', '7 minus 2 equals 5');
eq('What is 35% of 80?', 'en-US', 'What is 35 percent of 80?');
eq('12² − 5² = ?', 'en-US', '12 squared minus 5 squared equals what number');
eq('פתרו: 6 + _ = 9', 'he-IL', 'פתרו: 6 ועוד כמה שווה 9');
eq('השטח הוא 12 סמ״ר', 'he-IL', 'השטח הוא 12 סנטימטר רבוע');
eq('אורך 5 ס״מ ו־3 מ״מ', 'he-IL', 'אורך 5 סנטימטר ו3 מילימטר');
eq('קנה המידה הוא 1 : 50,000', 'he-IL', 'קנה המידה הוא 1 ל50,000');
eq('כמה הם 35% מתוך 80?', 'he-IL', 'כמה הם 35 אחוז מתוך 80?');
eq('פתרו: 495 ÷ 2 = ?', 'he-IL', 'פתרו: 495 לחלק ל2 שווה כמה');
eq('495 ÷ 2 = 247 שארית ?', 'he-IL', '495 לחלק ל2 שווה 247 שארית כמה');
eq('56 ÷ ? = 7', 'he-IL', '56 לחלק לכמה שווה 7');
eq('מהו הטווח? (הגדול פחות הקטן). 5, 7.', 'he-IL', 'מהו הטווח? הגדול פחות הקטן. 5, 7.');
eq('נכון או לא נכון? ✅ נכון, ❌ לא נכון.', 'he-IL', 'נכון או לא נכון? נכון, לא נכון.');
eq('מכונית נוסעת ב־60 קמ״ש', 'he-IL', 'מכונית נוסעת ב60 קילומטר לשעה');
eq('המחיר 12 ₪', 'he-IL', 'המחיר 12 שקלים');
eq('2 3/4 + 1 1/2 = ?', 'he-IL', '2 ו3 חלקי 4 ועוד 1 ו1 חלקי 2 שווה כמה');
eq('המירו. 3 ק״מ 934 מ׳ = ? מ׳.', 'he-IL', 'המירו. 3 קילומטר 934 מטר שווה כמה מטר.');
eq('2 שע׳ 15 דק׳', 'he-IL', '2 שעות 15 דקות');

const long = Array.from({ length: 12 }, (_, i) => `This is sentence number ${i + 1}, which keeps going for a while.`).join(' ');
const parts = MA.speech.chunks(MA.speech.text(long, 'en-US'));
if (parts.some((p) => p.length > 160) || parts.join(' ') !== MA.speech.text(long, 'en-US')) { fails++; console.log('FAIL chunking', parts); }

// every generated question must become clean spoken text in both languages
for (const lang of ['en', 'he']) {
  MA.i18n.setLang(lang, true);
  for (const sk of MA.CURRICULUM.skills) {
    for (const level of [1, 3, 5]) {
      const q = MA.gen.make(sk, level, {});
      if (!q) continue;
      const s = say(MA.gen.spoken(q), MA.i18n.locale());
      if (!s || /undefined|NaN|\[object|[_×÷=+−□\u0007]|\?\s*\/|\/\s*\?/.test(s)) { fails++; console.log(`FAIL spoken ${sk.id} L${level} [${lang}]: ${s}`); }
    }
  }
}
console.log(fails ? `${fails} SPEECH CHECKS FAILED` : 'ALL SPEECH CHECKS PASSED');
process.exit(fails ? 1 : 0);
