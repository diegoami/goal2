// The review reader's self-test: `node tools/harness/review.mjs --self-test`, and npm test in the
// harness repository. No model is called. Each sample asserts what review.mjs does with it (post
// and act, post flagged with no label, or fail) and the text it keeps.

import { readReview, briefTargets } from './chain.mjs';
import { planPost } from './post.mjs';

export const H = 'T07 review (luna)';
const FINDINGS = 'R1: a.js:10 skips the last item (blocking).\nR2: b.js:4 has no test (not blocking).';

// kind 'ok': the posted review is `review` exactly. kind 'flagged': it is the whole input, trimmed,
// with closing keywords rewritten. kind 'none': nothing is posted.
export const SAMPLES = [
  {
    name: 'a bold header after tool chatter',
    out: `reading a.js\nrunning npm test\n**${H}**\nrework\n\n${FINDINGS}\n\nrework\n`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'a heading header with a colon, in another case',
    out: `## ${H.toUpperCase()}:\nrework\n\n${FINDINGS}\n\nrework`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'a header in backticks with a full stop, after a preamble',
    out: `I checked the whole diff.\n\n\`${H}\`.\napprove\n\nR1: fine.\n\napprove`,
    kind: 'ok', review: `${H}\napprove\n\nR1: fine.\n\napprove`,
  },
  {
    name: 'blank lines before the verdict',
    out: `${H}\n\n\nrework\n\n${FINDINGS}\n\nrework`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'bold verdicts',
    out: `${H}\n**rework**\n\n${FINDINGS}\n\n**rework**`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'a "Verdict:" prefix, with the longest verdict matched first',
    out: `${H}\n**Verdict:** Approve after named fixes\n\nR1: rename x.\n\nVerdict: approve after named fixes`,
    kind: 'ok', review: `${H}\napprove after named fixes\n\nR1: rename x.\n\napprove after named fixes`,
  },
  {
    name: 'punctuated verdicts',
    out: `${H}\nRework.\n\n${FINDINGS}\n\nRework!`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'a four-line where-I-worked block before the verdict, kept',
    out: `${H}\nWorktree: /w/T07\nHEAD: abc1234\nDiff: a.js, b.js\nTests: npm test, 12 pass\nrework\n\n${FINDINGS}\n\nrework`,
    kind: 'ok',
    review: `${H}\nrework\n\nWorktree: /w/T07\nHEAD: abc1234\nDiff: a.js, b.js\nTests: npm test, 12 pass\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'Done-when lines (DW1, DW2) after the verdict, kept',
    out: `${H}\napprove\n\nDW1: ran npm test → 12 pass\nDW2: ran grep -n x a.js → 1 match\n\nR1: fine.\n\napprove`,
    kind: 'ok', review: `${H}\napprove\n\nDW1: ran npm test → 12 pass\nDW2: ran grep -n x a.js → 1 match\n\nR1: fine.\n\napprove`,
  },
  {
    name: 'a sign-off after the closing verdict: kept, the verdict not duplicated',
    out: `${H}\nrework\n\n${FINDINGS}\n\nrework\n\n— GPT-6 Luna, reviewing for T07`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\n— GPT-6 Luna, reviewing for T07\n\nrework`,
  },
  {
    name: 'closing keywords, rewritten',
    out: `${H}\napprove\n\nR1: fixes #551, Fixes: #12, fixes#13, CLOSES owner/repo#3.\n\napprove`,
    kind: 'ok', review: `${H}\napprove\n\nR1: fixes 551, Fixes: 12, fixes 13, CLOSES owner/repo 3.\n\napprove`,
  },
  {
    name: 'a review flattened onto one line',
    out: `${H} rework  R1: a.js:10 skips the last item.  R2: b.js:4 has no test.  rework`,
    kind: 'ok', review: `${H}\nrework\n\nR1: a.js:10 skips the last item.\n\nR2: b.js:4 has no test.\n\nrework`,
  },
  {
    name: 'the header in the middle of a line, the verdict on it',
    out: `Here is the ${H} — Rework\n\n${FINDINGS}\n\nrework`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'an echoed brief, then the review',
    out: `${H}\nReview PR #7.\n\n${H}\nrework\n\n${FINDINGS}\n\nrework`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'the header on its own line, then the review flattened onto one line',
    out: `${H}\nrework  R1: a.js:10 skips the last item.  rework`,
    kind: 'ok', review: `${H}\nrework\n\nR1: a.js:10 skips the last item.\n\nrework`,
  },
  {
    name: 'a flattened review with a sign-off',
    out: `${H} rework  R1: a.js:10 skips the last item.  rework\n— GPT-6 Luna`,
    kind: 'ok', review: `${H}\nrework\n\nR1: a.js:10 skips the last item.\n\n— GPT-6 Luna\n\nrework`,
  },
  {
    name: 'the closing verdict repeated: one verdict is kept',
    out: `${H}\nrework\n\n${FINDINGS}\n\nrework\n\nRework.`,
    kind: 'ok', review: `${H}\nrework\n\n${FINDINGS}\n\nrework`,
  },
  {
    name: 'a finding after the closing verdict',
    out: `${H}\nrework\n\nR1: a.\n\nrework\n- **R2.** b.js:4 has no test.`,
    kind: 'flagged', note: 'a finding after the closing verdict',
  },
  {
    name: 'a heading finding after the closing verdict',
    out: `${H}\napprove\n\nR1: fine.\n\napprove\n### R3 (blocking) c.js:1 crashes`,
    kind: 'flagged', note: 'a finding after the closing verdict',
  },
  {
    name: 'a "Finding R3" after the closing verdict',
    out: `${H}\napprove\n\nR1: fine.\n\napprove\n**Finding R3**: c.js:1 crashes`,
    kind: 'flagged', note: 'a finding after the closing verdict',
  },
  {
    name: 'a "1)" finding after the closing verdict',
    out: `${H}\napprove\n\nR1: fine.\n\napprove\n1) c.js:1 crashes`,
    kind: 'flagged', note: 'a finding after the closing verdict',
  },
  {
    name: 'a draft that approves, then the final review whose verdicts differ: never approved',
    out: `${H}\napprove\nLooks fine.\n\nWait, checking the tests.\n${H}\nrework\nR1 (blocking): the tests fail\napprove`,
    kind: 'flagged', note: 'verdicts differ: opens "rework", closes "approve"',
  },
  {
    name: 'a finding that quotes the header: posted whole, never read past it',
    out: `${H}\nrework\n\nR1: the line "${H}" is fine.\n\nrework`,
    kind: 'flagged', note: 'verdict unreadable',
  },
  {
    name: 'a sign-off with a date and a version is not a finding',
    out: `${H}\napprove\n\nR1: fine.\n\napprove\n2026-10-02, 1.0 release`,
    kind: 'ok', review: `${H}\napprove\n\nR1: fine.\n\n2026-10-02, 1.0 release\n\napprove`,
  },
  {
    name: 'a flattened review followed by a finding',
    out: `${H} approve  R1: fine.  approve\nR2: c.js:1 crashes`,
    kind: 'flagged', note: 'a finding after the closing verdict',
  },
  {
    name: 'a numbered finding after the closing verdict',
    out: `${H}\napprove\n\nR1: fine.\n\napprove\n2. one more thing`,
    kind: 'flagged', note: 'a finding after the closing verdict',
  },
  {
    name: 'no closing verdict, after a preamble that is kept',
    out: `Some notes first.\n${H}\nrework\n\nR1: the loop in`,
    kind: 'flagged', note: 'may be cut off',
  },
  {
    name: 'a where-I-worked block, then a review that is cut off',
    out: `${H}\nWorktree: /w/T07\nHEAD: abc1234\nrework\n\nR1: the loop in`,
    kind: 'flagged', note: 'may be cut off',
  },
  {
    name: 'an unreadable verdict',
    out: `${H}\nlooks good to me\n\nR1: fine\n\napprove`,
    kind: 'flagged', note: 'verdict unreadable',
  },
  {
    name: 'opening and closing verdicts that differ',
    out: `${H}\napprove\n\nR1: fine\n\nrework`,
    kind: 'flagged', note: 'verdicts differ: opens "approve", closes "rework"',
  },
  {
    name: 'a flattened review that is cut off',
    out: `${H} approve R1: fine and`,
    kind: 'flagged', note: 'may be cut off',
  },
  {
    name: 'a flattened review with an unreadable verdict',
    out: `${H} fine by me R1: ok. approve`,
    kind: 'flagged', note: 'verdict unreadable',
  },
  { name: 'tool chatter only', out: 'reading a.js\nrunning npm test\n', kind: 'none' },
  { name: 'nothing', out: '', kind: 'none' },
  {
    // PR 107 round 1 (#108): the brief was headed `#105 review (luna)` because tasks are issues;
    // undecorate that strips every leading `#` (any count) would have hidden the issue number.
    name: 'a header with a leading GitHub issue number, not a Markdown heading',
    out: `**#105 review (luna)**\nrework\n\n${FINDINGS}\n\nrework`,
    kind: 'ok',
    review: `#105 review (luna)\nrework\n\n${FINDINGS}\n\nrework`,
    header: '#105 review (luna)',
  },
];

// [designed: #165] A complete identity header missing only its terminal period is
// recoverable for human assessment, including unsafe/incomplete review bodies.
const IDENTITY = 'T32 review (MiniMax M3), PR #135 at b38110183a310303b1f9357272870817f166a16a';
const RECOVERY_NOTE = 'review header differs by its terminal period; manual assessment required';
const completed = `${IDENTITY}\napprove\nDW1: ran one → pass\nDW2: ran two → pass\nDW3: ran three → pass\nR1: fixes #136 (not blocking).\napprove`;
const recoveryCases = [
  ['completed final after preamble', `Final pass done.\n${completed}`],
  ['truncated', `${IDENTITY}\napprove\nR1: unfinished`],
  ['mismatched verdicts', `${IDENTITY}\napprove\nR1: issue\nrework`],
  ['finding after verdict', `${completed}\nR2: blocking`],
  ['missing DW', `${IDENTITY}\napprove\nR1: none\napprove`],
  ['DW not run', completed.replace('DW2: ran two → pass', 'DW2: not run — unavailable')],
  ['multiple near headers', `${completed}\n${completed}`],
  ['earlier exact draft then near final', `${IDENTITY}.\napprove\nDW1: ran one → pass\napprove\n${completed}`],
  ['earlier near draft then exact final', `${completed}\n${IDENTITY}.\napprove\napprove`],
];

// [designed: #204] Complete public issue156 contract; historical citations stay verbatim.
const ISSUE156 = "MiniMax-M3 approved PR #154 at 2a4066e656b9a353f1bd231976810b4a43b97911 with one non-blocking cosmetic finding: docs/desktop-management.md:22 uses fresh1990 and seeds4660/33590 without spaces. Values are correct and match the implemented fresh campaign defaults. Fix wording when documentation is next touched; preserve year/seeds and all runtime behavior. Difficulty: Easy. Triage: post-playable; no gameplay or merge blocker. Validation: links/JSON, whitespace and required exact-head local checks; no new behavior test needed for spacing.";
const CURRENT = '705e2576a51fcb197ea9759276f5a04aef813f3f';
const STALE = '2a4066e656b9a353f1bd231976810b4a43b97911';
const target = `You review PR #203 at ${CURRENT}.\nProve HEAD is ${CURRENT}.\n`;
const boundary = '# Issue #156 task contract';
const history = `${ISSUE156}\nAuthor notes: HEAD is ${STALE}; prior validation HEAD: ${STALE}.`;
const quotation = '````text\n' + history + '\n```\nexample\n```\n````';
const TARGET_CASES = [
  ['complete issue and historical notes', target + boundary + '\n' + quotation, [CURRENT, CURRENT]],
  ['CRLF issue boundary', (target + boundary + '\n' + quotation).replaceAll('\n', '\r\n'), [CURRENT, CURRENT]],
  ['actual stale target before issue', `Review PR #203 at ${STALE}\n${boundary}\n${quotation}`, [STALE]],
  ['multiple actual targets before issue', target + `HEAD: ${STALE}\n${boundary}\n${quotation}`, [CURRENT, CURRENT, STALE]],
  ['historical existing task title', target + '# T69 follow-up\n' + history, [CURRENT, CURRENT]],
  ['existing fenced task-title behavior', target + '````text\n# T69 follow-up\n' + history, [CURRENT, CURRENT]],
];
for (const heading of ['# Evidence', '## Notes', '# Issue #156', '# Issue #0 task contract', '# Issue #0156 task contract', '# Issue #-1 task contract', '# Issue #1.0 task contract', '## Issue #156 task contract', ' # Issue #156 task contract', '# Issue #156 task contract extra']) {
  TARGET_CASES.push([`ordinary heading ${heading}`, target + heading + `\nHEAD: ${STALE}`, [CURRENT, CURRENT, STALE]]);
}
for (const [name, example] of [
  ['backticks', '```text\n' + boundary + '\n```'],
  ['longer outer fence', '````text\n```\n' + boundary + '\n```\n````'],
  ['tilde fence with inner backticks', '~~~~text\n```\n' + boundary + '\n```\n~~~~'],
  ['wrong closing marker', '```text\n~~~\n' + boundary + '\n```'],
  ['indented fence', '   ```text\n' + boundary + '\n   ```'],
  ['unclosed fence', '```text\n' + boundary],
]) {
  TARGET_CASES.push([`quoted heading: ${name}`, target + example + `\nHEAD: ${STALE}`, [CURRENT, CURRENT, STALE]]);
}
// [designed: #204] Closing a fence re-enables only the exact canonical boundary.
TARGET_CASES.push(['boundary after quoted example', target + '~~~text\n' + boundary + '\n~~~\n' + boundary + '\n' + quotation, [CURRENT, CURRENT]]);

// Returns one line per failed sample (empty when all pass).
export function selfTest() {
  const failures = [];
  for (const [name, brief, expected] of TARGET_CASES) {
    const got = briefTargets(brief);
    if (JSON.stringify(got) !== JSON.stringify(expected)) failures.push(`${name}: expected targets ${JSON.stringify(expected)}, got ${JSON.stringify(got)}`);
  }
  for (const s of SAMPLES) {
    const r = readReview(s.out, s.header ?? H);
    const fail = (why) => failures.push(`${s.name}: ${why}\n  got ${JSON.stringify(r)}`);
    if (r.kind !== s.kind) { fail(`kind ${r.kind}, expected ${s.kind}`); continue; }
    if (s.kind === 'ok' && r.review !== s.review) fail('the posted text differs');
    if (s.kind === 'flagged') {
      if (r.note !== s.note) fail(`note "${r.note}", expected "${s.note}"`);
      if (r.review !== s.out.trim()) fail('the flagged review is not the whole input');
    }
  }
  for (const [name, out] of recoveryCases) {
    const r = readReview(out, IDENTITY + '.');
    const retained = out.replaceAll('fixes #136', 'fixes 136');
    if (r.kind !== 'flagged' || r.note !== RECOVERY_NOTE || r.review !== retained) {
      failures.push(`${name}: recovery must retain the whole final and flag it: ${JSON.stringify(r)}`);
      continue;
    }
    const post = planPost({ read: r, header: IDENTITY + '.', doneWhen: 3, source: 'self-test', signature: 'synthetic' });
    if (post.code !== 4 || post.label !== null || !post.body.includes(retained)) failures.push(`${name}: recovery must post whole, exit 4, no label`);
  }
  for (const wrong of [IDENTITY.replace('T32', 'T33'), IDENTITY.replace('#135', '#136'), IDENTITY.replace('b38110183a310303b1f9357272870817f166a16a', 'a'.repeat(40)), IDENTITY.replace('MiniMax M3', 'another reviewer')]) {
    if (readReview(completed.replace(IDENTITY, wrong), IDENTITY + '.').kind !== 'none') failures.push('wrong identity recovered');
  }
  // [designed: #165] Short headers and other punctuation are outside this recovery.
  for (const [out, header] of [['T32 review (MiniMax M3)\napprove\napprove', 'T32 review (MiniMax M3).'], [completed.replace(IDENTITY, IDENTITY + '!'), IDENTITY + '.']]) {
    if (readReview(out, header).kind !== 'none') failures.push('unbounded punctuation recovery');
  }
  for (const out of [recoveryCases[4][1], recoveryCases[5][1]]) {
    const exact = out.replace(IDENTITY, IDENTITY + '.');
    const r = readReview(exact, IDENTITY + '.');
    const post = planPost({ read: r, header: IDENTITY + '.', doneWhen: 3, source: 'self-test', signature: 'synthetic' });
    if (r.kind !== 'ok' || post.code !== 4 || post.label !== null || !post.unaccounted) failures.push('exact-header DW protection changed');
  }
  return failures;
}
