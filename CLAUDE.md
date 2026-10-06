# goal2

The faithful rebuild of *goal (version 2)* (New Era Software, 1993) and the bot that maximises its
World Cup win rate, built from the evidence of the private `goal2-archaeology` repository (findings
`F0nn`, task records, releases). Python. Tasks in `docs/tasks/T<nn>.md`, one branch per task.

## Rules
1. **Evidence tags.** Every behaviour claim in code or docs is tagged `[confirmed]` (cites the
   goal2-archaeology finding(s) and commit it rests on), `[derived]` (follows from confirmed claims)
   or `[designed]` (a choice of this rebuild, no original evidence). No untagged behaviour claims;
   a `[designed]` choice that later contradicts a finding is a bug.
2. **Engine truth is vendored, never edited.** Files under `goal2/engine/` are copies pinned in
   `PROVENANCE.md` (file, source repo, commit, findings). A defect in vendored code goes upstream to
   goal2-archaeology; the fix arrives here only as a deliberate re-vendor that records the new
   commit. Engine files carry no evidence tags of their own — their provenance row is the citation.
3. **Nothing of the original game is committed.** No GOAL2 asset, savestate or executable byte
   enters this repository (U17/U21). States load from local caches or the archaeology releases by
   path, git-ignored (`.cache/`).
4. **The fidelity test is the arbiter.** When this rebuild's behaviour and the vendored model
   disagree on a case the model is seed-exact for, the rebuild is wrong until proven otherwise. A
   fidelity test that has never failed proves nothing (state the case it fails without the fix).
5. **Tests fail before and pass after.** Every new behaviour arrives with the test that visits it;
   the PR says how the failure was shown.
6. **One task, one branch, one PR.** Task files say what is in scope; a Done-when line that cannot
   be met stops the task and reports, never weakens the line.
