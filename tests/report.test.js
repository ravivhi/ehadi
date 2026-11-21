/* Weekly report numbers from made-up play: minutes per day, the idle-time cap, success, topics, strengths,
   struggles, comparison with last week and next week's topics.  Run: node tests/report.test.js */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

global.window = global;
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
for (const f of [...html.matchAll(/<script src="js\/([^"]+)"/g)].map((m) => m[1])) {
  try { vm.runInThisContext(fs.readFileSync(path.join(root, 'js', f), 'utf8'), { filename: f }); } catch (e) { /* browser-only modules */ }
}
const MA = global.MA, U = MA.u, db = MA.db;
MA.errors.capture = (e) => { throw e; };
let failed = 0;
const ok = (cond, label) => { if (!cond) { failed++; console.log('FAIL:', label); } };

U._fakeNow = new Date(2026, 10, 21, 18, 0, 0).getTime();
db.open();
const st = MA.svc.createPlayer();
MA.svc.updatePlayer(st.id, { grade: 2, onboarded: true, name: 'Noa' });
const at = (daysAgo, hour) => new Date(2026, 10, 21 - daysAgo, hour || 17, 0, 0).getTime();
function play(daysAgo, skillId, results, minutes, o) {
  o = o || {};
  const start = at(daysAgo, o.hour);
  const att = db.insert('attempts', { studentId: st.id, activityId: 'pr-' + skillId, skillId, mode: 'practice', startedAt: start, status: o.status || 'completed', answered: results.length, correct: results.filter(Boolean).length, timeMs: minutes * 60000 });
  results.forEach((r, i) => {
    db.insert('answers', { attemptId: att.id, studentId: st.id, skillId, correct: !!r, firstTry: !!r, tries: r ? 1 : 2, hints: r ? 0 : (o.hints || 0), ms: 20000, revealed: !!(o.revealed && !r), ts: start + i * 20000, level: 2 });
    MA.adapt.record(st.id, skillId, { firstTry: !!r, hints: 0, level: 2, ts: start + i * 20000 });
  });
}
const A_SKILL = 'g2-add-mental', B_SKILL = 'g2-num-compare';
ok(MA.content.skill(A_SKILL) && MA.content.skill(B_SKILL), 'test skills exist');
play(0, A_SKILL, [1, 1, 1, 1, 1, 1, 1, 1, 1, 0], 5);
play(2, A_SKILL, [1, 1, 1, 1, 0, 1, 1, 1, 1, 1], 6);
play(4, B_SKILL, [0, 0, 1, 0, 0, 1, 0, 0], 7, { hints: 2 });
play(5, B_SKILL, [0, 1, 0], 180, { status: 'abandoned' });   // tab left open for 3 hours: 3 questions count as 6 min at most
play(9, A_SKILL, [1, 0, 1, 0, 1, 0], 4);                   // the week before

const W = MA.report.week(st);
ok(W.days.length === 7 && W.days[6].key === U.today(), 'seven days ending today');
ok(W.days[6].ms === 5 * 60000 && W.days[4].ms === 6 * 60000 && W.days[2].ms === 7 * 60000, 'minutes per day: ' + W.days.map((d) => d.ms / 60000));
ok(W.days[1].ms === 6 * 60000, 'an idle open game is capped at 2 minutes per question: ' + W.days[1].ms / 60000);
ok(W.minutes === 24, 'minutes this week: ' + W.minutes);
ok(W.prevMinutes === 4, 'minutes last week: ' + W.prevMinutes);
ok(W.daysPlayed === 4, 'days played: ' + W.daysPlayed);
ok(W.activities === 3, 'completed activities this week: ' + W.activities);
ok(W.answered === 31 && W.correct === 21, 'answers this week: ' + W.answered + '/' + W.correct);
ok(Math.abs(W.prevAcc - .5) < 1e-9, 'success last week: ' + W.prevAcc);
ok(W.topics.length === 2 && W.topics[0].skill.id === A_SKILL, 'topics sorted by questions');
const a = W.topics[0], b = W.topics[1];
ok(a.answered === 20 && Math.abs(a.acc - .9) < 1e-9 && a.series.length === 2, 'topic A numbers');
ok(b.answered === 11 && b.status === 'help' && b.manyHints, 'topic B needs practice, with many hints');
ok(W.strengths.length === 1 && W.strengths[0].skill.id === A_SKILL, 'strength: topic A');
ok(W.struggles.length === 1 && W.struggles[0].skill.id === B_SKILL, 'struggle: topic B');
ok(W.next.length >= 2 && W.next[0].skill.id === B_SKILL && W.next[0].reason === 'practice', 'next week starts with the hard topic');
ok(W.next.every((r) => MA.i18n.has('rp_why_' + r.reason)), 'every next-week reason has a text: ' + W.next.map((r) => r.reason));
ok(MA.report.fmtMinutes(0) === 'under a minute' && MA.report.fmtMinutes(45) === '45 min' && MA.report.fmtMinutes(80) === '1 h 20 min' && MA.report.fmtMinutes(120) === '2 h', 'time text (en)');
MA.i18n.setLang('he', true);
ok(MA.report.fmtMinutes(80) === 'שעה ו־20 דק׳' && MA.report.fmtMinutes(125) === 'שעתיים ו־5 דק׳' && MA.report.fmtMinutes(180) === '3 שעות', 'time text (he)');

const empty = MA.svc.createPlayer();
const E = MA.report.week(empty);
ok(E.answered === 0 && E.minutes === 0 && E.topics.length === 0 && E.acc === null && E.next.length > 0, 'a new player: an empty week, and something to start with');

console.log(failed ? `REPORT TEST FAILED (${failed})` : 'ALL REPORT CHECKS PASSED');
process.exitCode = failed ? 1 : 0;
setTimeout(() => process.exit(process.exitCode), 300);
