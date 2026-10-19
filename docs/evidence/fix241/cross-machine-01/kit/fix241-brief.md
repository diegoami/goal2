[designed: owner report, 2026-10-19] In the newer Windows playable build (`Start-goal2-modern.cmd`, accepted source `5c26616917d19a77a0e548a0baa2a3997112c477`), the owner cannot scroll down the players tables on **Squad & tactics** and **National pool**.

Scope: reproduce the actual native Windows wheel/scrollbar/keyboard behavior, make all 20 squad rows and all 80 national-pool reserves reachable, and preserve selection, full player IDs, private XI/captain/tactics drafts, Confirm/Discard and the persistent action bar. Investigate nested page/table scrolling and refresh behavior rather than guessing the cause.

Done when:
- A real input regression demonstrates the current failure and reaches the first and last roster rows after the fix using wheel and keyboard/scrollbar input.
- All squad and national-pool players remain readable/selectable at the accepted small-window and Qt 1x/2x targets on actual Windows; focused/selected row remains visible.
- Scrolling/selection preserves complete model/save state and existing draft-management guards; applicable retained squad/management checks pass.

[designed] High importance: blocks routine access to the squad. Provisional Medium difficulty pending reproduction. Implementation awaits the owner-selected implementer; no fix has started. Full original-style attributes are a separate requested enhancement.

[confirmed: main native planning, 2026-10-19] Actual Windows Qt1x reproduction against the delivered immutable accepted5c release: active-country squad wheel reaches scroll16/16 (row19), active-country pool wheel reaches76/76. Changing country13 to preview14 disables the squad table and the entire pool panel; wheel remains0 for both despite nonzero scroll maxima. A runtime-only enable mock restores wheel movement16/76 without changing encoded active state. This is feasibility evidence, not an accepted implementation. Native raw log and receipt retained privately under `.cache/kept/review-receipts/fix241-planning-1792362138840962259/`. The probe's original-draft comparison becomes false during preview because displayed team changes; do not treat that as a mutation claim. Final tests must compare per-context drafts and separately prove active-draft restoration on Return.

[designed] Concrete implementation contract:
- Own only the browsing/editability boundary in `goal2/desktop/window.py`, `squad_page.py`, `pool_page.py`, plus focused tests/new owned native scenario helper, dispatcher registration if needed, guide corrections and `docs/evidence/fix241/`. No attributes expansion here (#242), no engine, save schema, worker/controller, publication or pool-policy change. Coordinate any overlap in window.py with active T79/PR240; do not edit its worktree.
- Permit safe read-only wheel/scrollbar/keyboard selection and existing player detail inspection in country preview; changing XI/captain/tactics, exchange, confirm/save and other active-game mutations remain refused. Do not fix scrolling by enabling all management controls. Preserve intentional match-busy editing guards; if allowing busy inspection, prove it independently and do not mutate jobs.
- Test active and preview countries independently, both tables, first/last/full-ID selected-player detail. Use genuine input dispatch, acquire/assert focus, and prove row/scroll visibility after input, not a programmatic scroll-to-only test. Check all20/80-row reading coverage at actual1x1440x900,1050x780,900x700 and2x900x640. Main runs Windows final frozen-source acceptance.
- Prove encoded active and preview state, both RNG words, current save bytes and correct per-context private draft unchanged by scrolling/inspection; Return restores the active draft. Read-only preview XI checkbox Space/mouse, captain/tactic/exchange/Confirm actions cannot publish changes. Retain full integer IDs, eligibility and unavailable-starter removal in active mode.
- Saved-byte negative controls restore source in finally; serialize controls and all source readers. The old disable behavior must fail the new scrolling assertions; an accidental enable-everything mutant must fail read-only guards. No weakening existing accepted tests.
- Run focused new tests and applicable retained country selection, squad/pool scenarios and controls, management/pool/halftime proofs/acceptance, shell/overview checks if shared window/navigation affected, plus clean exact-head premerge. Any fixture/setup defect is reported to main before edits outside scope. Immutable failed runs stay labeled honestly.

Owner selected Native Sol Medium implementation and MiniMax M3 (`mm-m3`) review for #241 and #242. Main owns merge and native Windows execution. Reviewer launch occurs only after a concrete validated ready PR; owner selection persists through rework.




[designed: T24] Both clients use this same contract. Codex native subagents
receive the full task and this block; the main session supplies the worktree,
because native Codex dispatch does not invoke Claude's isolation parameter or
PreToolUse hooks. No-stash, no-force-push, scope and main-session-only merge rules
remain instructions under Codex's native approval/sandbox controls.

The brief is the task file pasted in full, then this block, then on a rework round the review's URL.
The `implementer` agent file repeats the run mechanics; this block is the contract, for the main
session implementing directly as much as for the subagent. Lines an OpenCode reviewer cannot reach
are the main session's to run (L57).

```text
You implement <T<nn>>. The task file above is the contract.
- Build only what the task asks for, even inside a file it requires; say why for each changed file. (L44)
- A Done-when you cannot meet: stop and report. Never weaken an assertion, skip a test or edit the task file.
- Every new test fails before your change and passes after it; say how you checked.
- If you measure: every output a finding or the PR may cite goes under a tracked path the task owns,
  pushed per batch and every 30 min, never deleted or overwritten; originals out, hashes recorded. (L40)
- A comment that asserts behaviour at an edge comes with the test that visits that edge.
- Every behaviour claim carries its evidence tag (CLAUDE.md rule 17); vendored engine files are
  never edited (rule 18); nothing of the original enters the tree (rule 19).
- A defect you find outside the task: report it. A one-file mechanical fix that blocks you may
  ride this PR, declared under Scope in the PR body.
- Update any document your change makes wrong, in this PR. Never write status into a document.
- Commit and push after each step, at least every 20 minutes and before any command that runs longer
  than 5 minutes; after your first push, open the PR as a draft (`gh pr create --draft`). A crash then
  loses one step, and the branch shows where you are. (L103)
- A command that can run past 10 minutes never pipes through `tail`/`head`: an agent's tool call
  has a timeout of its own (L10). Run it detached (`nohup … > log 2>&1 &` or `setsid`), verify it
  survived the tool call with `ps`, then poll the log in short calls.
- PR body: Closes #<issue>; Scope (files and why); a fenced block with each Done-when command and
  the tail of its output; Docs changed.
```

