# Handover — 2026-10-15: the register rows from the owner's sitting

For a goal2 session. Read this, then `CLAUDE.md` and `docs/process.md`. It was written by a
goal2-archaeology session (Claude Sonnet 5.5) at the owner's request, on branch
`docs/register-sitting-20261015`; nothing else of goal2 was touched.

## What is on the branch

`docs/assumptions.md` only. Seven rows and one correction, all tagged `owner` with the sitting as
the source, none a `finding` (no method has checked them):

- A-WATCH-2 substitutions: requested during play, carried out when the game stops.
- A-WATCH-3 offside: called often, also against the team that is not attacking.
- A-WATCH-4 a sending off in a watched match (match type not recorded).
- GA-5 the prompts around a match and after a goal, and that they time out.
- GA-6 the match-screen keys and the four player display modes.
- GA-7 the owner's pre-match edits: positions, full-back tactics, marking, team tactics, formation.
- GA-4 corrected by the owner: **Y shows a replay, N skips it** (the row said Y skips). No code
  cites the old meaning (checked with grep for "replay"), but T29 and later screens should use the
  corrected one.

The evidence is goal2-archaeology's run records `runs/E015/E015-r0013.json` (this sitting, with
the owner's 39 notes) and `E015-r0017.json`, merged on its `main` (PRs 214 and 215). The notes are
in the records' observations; the raw savestates stay on the owner's machine.

## What to do

1. Read the rows against `goal2/` and `docs/tasks/T29.md` (in progress): does T29's match preview
   or kickoff confirmation touch GA-5 ("really watch it?", captain, goal-kick taker)? If so, the
   task says so and cites the row.
2. Open a PR for the branch through the normal process: a docs-only change, reviewed by an OpenCode
   model of another family (the owner chooses, rule 2). Merge as rule 7 says.
3. Do not turn a row into code from this handover alone. Each row's last column says what replaces
   it; until then they are `owner` statements, below a finding.

## Owner wishes (not rules, for P6, wording as given)

- A better way to search the national pool for players.
- Players' names should not be the same for each team (the exact meaning was not clarified: ask).

## What goal2-archaeology does next, and what will come back

Tasks it can take now, each ending in findings and then register rows from this repository's side:
Q037 (do substitutions persist into the next match, issue #146) and a reading of the sitting's
match events (red card, offside, injury requests) against A-WATCH-2..4; a static question on which
team the offside check applies to; later a sitting that reaches a knockout shoot-out (A-MATCH-3).
The match pace does not change results (goal2-archaeology C-MATCH-02), so no row.
