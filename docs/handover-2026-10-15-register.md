# Handover — 2026-10-15: the register rows from the owner's sitting

For a goal2 session. Read this, then `CLAUDE.md` and `docs/process.md`. It was written by a
goal2-archaeology session (Claude Sonnet 5.5) at the owner's request, on branch
`docs/register-sitting-20261015`; nothing else of goal2 was touched.

## What is on the branch

`docs/assumptions.md` only. Seven rows and one correction, all tagged `owner` with the sitting as
the source, none a `finding` (no method has checked them):

- A-WATCH-5 substitutions: requested during play, carried out when the game stops.
- A-WATCH-6 offside: called often, also against the team that is not attacking.
- A-WATCH-7 a sending off in a watched match (match type not recorded).
- GA-7 the prompts around a match and after a goal, and that they time out.
- GA-8 the match-screen keys and the four player display modes.
- GA-9 the owner's pre-match edits: positions, full-back tactics, marking, team tactics, formation.
- GA-4 corrected by the owner: **Y shows a replay, N skips it** (the row said Y skips). No code
  cites the old meaning (checked with grep for "replay"), but T29 and later screens should use the
  corrected one.

The evidence is goal2-archaeology's run records `runs/E015/E015-r0013.json` (this sitting, with
the owner's 39 notes) and `E015-r0017.json`, merged on its `main` (PRs 214 and 215). The notes are
in the records' observations; the raw savestates stay on the owner's machine.

## What to do

1. Read the rows against `goal2/` and `docs/tasks/T29.md` (in progress): does T29's match preview
   or kickoff confirmation touch GA-7 ("really watch it?", captain, goal-kick taker)? If so, the
   task says so and cites the row.
2. Open a PR for the branch through the normal process: a docs-only change, reviewed by an OpenCode
   model of another family (the owner chooses, rule 2). Merge as rule 7 says.
3. Do not turn a row into code from this handover alone. Each row's last column says what replaces
   it; until then they are `owner` statements, below a finding.

## Also on this branch: rows from the pass-one findings F022-F027 (merged from `docs/register-pass-one-findings`)

Written by a Sonnet subagent from the findings, checked by the main session against F023, F024, F025
and F027 for the claims that change a rule (the 5-or-2 substitution budget, no coin in the stage
code, `D47E` for silent results, no end condition). All sources say `(proposed, read from the
listing)`: nothing was run against the original unless the row says so. Ids of the sitting rows above
were renumbered to avoid the collision (A-WATCH-5..7, GA-7..9).

- Changed: NG-6 (the start year also sets the first stage), A-MATCH-2 (the foul path is gated by the
  fixture kind), A-MATCH-3 (extra time and a shoot-out for kinds {4, 8..203}), A-MATCH-5 (a host flag
  note), A-COMP-5 (the draw), A-COMP-6 (refuted: a silent result is `D47E`, not the quick engine),
  A-CPU-1 (the stored eleven corrected by `B11F`), A-CPU-3, BM-6, GA-1.
- New: A-MATCH-7..10 (cap of 3 lost, the foul chain, added time, substitutions), A-WATCH-2..4 (contests,
  what each tactic does, measured effects), BM-8, BM-9 (ban machine, injury duration), A-COMP-10..14
  (calendar, groups, finals, play-offs, table sort), A-CPU-4, A-CPU-5, GA-5, GA-6 (sacking and the
  confidence sum).
- **The three conflicts were decided by the owner on 2026-10-15** (recorded in goal2-archaeology
  `experiments/E015-human-playthrough/owner-questions-2026-10-11.md`, fff9dc6) and the rows now say so:
  BM-7: substitutions unlimited in a friendly, 5 in every other match, a deliberate rebuild rule that
  differs from the original (5 per side in a friendly, 2 otherwise, F027 §4); A-COMP-3 and A-COMP-4: follow
  the code, no coin.
- Not settled, left unchanged: A-COMP-7 (200 points per knockout fixture; F023 says kinds 3 and 7 also
  add 200: unclear against F017 §7), A-COMP-8/9, A-CPU-2, BM-3/5 (GA-6's confidence sum may be a
  different quantity from BM-3's).
- Uncertain in the new rows: BM-9 states DS:0F3E kinds as numbers although F027 says which kind is a
  qualifier is not established; A-CPU-5's element numbers are the finding's and may differ from SQ-2's;
  A-WATCH-4 gives only the flipped side's numbers.
- Nothing in the register describes goal2 code as live that these findings contradict. The new rows
  have Live "-" or a phase tag.

## Owner wishes (not rules, for P6, wording as given)

- A better way to search the national pool for players.
- Players' names should not be the same for each team (the exact meaning was not clarified: ask).

## What goal2-archaeology does next, and what will come back

Tasks it can take now, each ending in findings and then register rows from this repository's side:
Q037 (do substitutions persist into the next match, issue #146) and a reading of the sitting's
match events (red card, offside, injury requests) against A-WATCH-5..7; a static question on which
team the offside check applies to; later a sitting that reaches a knockout shoot-out (A-MATCH-3).
The match pace does not change results (goal2-archaeology C-MATCH-02), so no row.
