# Process

Adopted from goal2-archaeology's at `8dc4dc1` with its harness (2026-10-12); its research-only
sections (reverse engineering, the named view) are left out.

`CLAUDE.md` holds the rules, this file how they run, `/run-task` the procedure; each rule cites its lesson.

## 0. Order of work

1. **Evidence first** (for a rebuild): decode, decompile, and write the design with every claim
   tagged `[confirmed]`, `[derived]` or `[designed]`.
2. **A walking skeleton before the fan-out**: scaffolding, the seams the rules plug into, one rule
   end to end, a CLI, and a thin screen a person can use. (L1)
3. **The fan-out**: rules behind the seams, best-evidenced first.
4. **The first playable build**: once the skeleton exists, the UI chain goes before more rules.
   Until it ships, only a bug that breaks play is scheduled (crash, stall, unwinnable game, save
   that will not load, order that can never succeed). (L1)

Tag capability jumps, not phases. Release notes come from GitHub when the tag is cut.

## 1. Roles

[designed: owner, 2026-10-14] The Codex main session may implement directly or
dispatch a native Codex subagent into a worktree it prepared under the configured
worktreeRoot. Claude Code retains its native `implementer` Agent with
`isolation: "worktree"`, aliases and hooks. In the table's Claude-specific
dispatch below, substitute the Codex branch only when client=codex; all task,
evidence, review and merge checks are shared. OpenCode never implements.

Client-aware defaults and commands:

- `node tools/harness/switch-model.mjs --show` reports active client/family/defaults.
- `HARNESS_CLIENT=codex` selects native Codex; its implementation default is
  `implementer.defaultsByClient.codex` (`session`). Native OpenAI model IDs select
  Codex subagents; Claude aliases and OpenCode provider/model routes are refused.
- `HARNESS_CLIENT=claude` selects the existing Claude/provider workflow even if
  stale Codex markers remain. Its `implementer.default` and aliases are unchanged.
- Codex session markers select Codex automatically; installed CODEX_HOME alone
  does not. A Codex family override other than openai is refused, not trusted.
- Ask for the implementer/model before each new task and wait; a task request
  alone does not select a model. Keep the choice already made for that task.
  Open the validated PR first, then ask which eligible OpenCode model reviews.
  Same-family defaults are not proposed or silently replaced.

| Role | Who | Does |
| --- | --- | --- |
| Main session | Codex or Claude Code, the session the user talks to | Plans, writes task files, runs `/run-task`, triages, merges, reports |
| Implementer | Codex: native main session or authorized native Codex subagent in a prepared worktree. Claude: the **`implementer` subagent** spawned inside Claude Code (worktree isolation) on a model of its own, not the orchestrator's (Opus spawns Sonnet; under Z.AI `sonnet` is GLM-5.3 Flash), or **the main session** directly, in its own worktree, where the provider cannot spawn one; asked when not already authorized (CLAUDE.md "Choosing models" rule 1). *Superseded: OpenCode via `implement.mjs` (removed), the GLM/DeepSeek/Sonnet chain (L42), L46's heavier-model rule, the user asked before each run.* | One task, one branch, one PR, in its own worktree |
| Reviewer | **Selected OpenCode reviewer with follow-ups until accepted** via `tools/harness/review.mjs`, on the model the user names at the question before the review, `harness.json`'s `reviewer.default` (GPT-5.6 Luna) proposed first only if eligible (`sol-6.1` for hard reviews: an engine seam, a fidelity test, a vendored model); never the session's family (L27), never a blocked model. Exit 3: read the final message, fix the cause, run again; exit 4: the main session reads the flagged review and decides (L28). *Superseded: the quota-checked Sol / Luna / Opus order (L50, L51, L101), the Claude fallback, the user asked at every review.* | Re-runs the Done-when, audits scope and evidence, posts one PR comment, applies the label |
| Decider | Jev via `tools/harness/jev.mjs` (the `/jev` skill) | Repeated yes/no decisions over many items, at the confident ends only (§12) |
| Generator | Models on OpenRouter (images, other families) and ElevenLabs (speech, sound, music) | Assets, each committed with a sidecar naming provider, model, prompt, date and cost |

Ask for an implementer/model choice before each new task and wait for the answer;
keep a choice already explicitly made for that task through rework. After the
validated PR exists, ask which OpenCode model reviews; propose the configured
default only if eligible. No quota, tier or chain picks a model; the roster changes
through `/switch-model`. `lib/common.mjs` reports Codex as OpenAI and retains
Claude's existing Anthropic endpoint/override detection for its provider family.
The reviewer is never that family. Reviewer IDs come from `harness.json`,
`models.mjs` or `opencode models`; native implementer IDs come from the client's
supported models, never from an OpenCode route or an invented alias (L25).

## 2. Task files

`docs/tasks/T<nn>.md`, 150–400 words, from `docs/tasks/TEMPLATE.md`: Kind, Evidence, Owns,
Scope, Done when, Hazards, Implementer, Reviewer, Merge after. Rules:
- **Scope** says in one line what the task protects (the claim, guard or measurement a reviewer must
  not let anything past); on a guard task it lists the forbidden actions or results. The review
  brief's "Blocking means" item 2 names the same.
- **Owns** names directories or files. Go finer only when two tasks run at once in one file: function-level Owns made one project open 27 PRs that only widened a list. (L5)
- **Done when**: each line is one check a command can run. The main session runs each line before dispatch: it fails on `main` and passes on a mock fix. (L45)
- The main session edits task files directly on `main`, the reason in the commit; the reviewer sees it. (L6)
- **Milestones.** A task likely to outlast one implementer run (about an hour), or whose Done-when is all
  or nothing (an exact match, a whole model), is split into tasks that each merge on their own: the
  static reading (a finding's first part), any tool that produces ground truth, then the deliverable
  piece by piece. A milestone's Done-when measures progress as a number (the first divergent minute,
  the records matched), committed with each push, so a resumed run starts from it. (L102)
- **Orthogonal layers.** A task file's **Owns** and **Scope** sections name the layers it touches.
  Two layers are orthogonal if they can be merged independently: each is testable in isolation, the
  other layer's tests still pass without it, and the other layer is still useful in the field. When
  a task touches more than 3 orthogonal layers, **split it into T<nn>a, T<nn>b, ...** before
  dispatch. Each sub-task is its own mergeable PR with its own Done-when, reviewer, and merge
  cycle. goal2-archaeology's T34 (recorder 2) is the canonical case: 5 orthogonal layers (privacy & nested-display key
  logger; burst detection; scheduler timing; keymap & acceptance guard; CI apt step & latency
  probe) sat on one PR; the rework rounds each surfaced a defect in a different layer, the L38
  / family-rule bind fired per-round for the whole ticket, the 900 s idle limit per round had to
  cover all 5 layers, and the r3 round died without pushing. Per-layer splits would have closed
  each layer in 1 round. Defensive check: when reviewing a task file, ask "could this be two or
  three tasks instead?" If yes, split. The cost of splitting is small (more task files, more
  PRs); the cost of not splitting is what goal2-archaeology saw on T34. (L104)
- **Numbering.** Before writing a task file, `git pull` and take the next free number in
  `docs/tasks/`: another session may have written one (goal2-archaeology's T14 was overwritten once, 2026-10-05).

## 3. The loop

`ready → implement → review → approved + exact-head local checks → squash merge → follow-up → unblock → report`.
[designed: owner, 2026-10-18] Rework sends the full review back to the same branch.
Once selected, keep the same reviewer and continue meaningful follow-ups until accepted,
without repeated retry permission or an automatic round-count stop. Read complete results,
fix causes and validate the new head. Report real owner design/external-access blockers;
never silently switch providers, weaken acceptance or bypass safety. The implementer script resumes a pushed branch; it never starts over. Before a merge the
main session re-runs the check the approval rests on most; a different result is rework. (L46)

[designed: owner, 2026-10-14; L114] Only the main session merges, using
`gh pr merge <pr> --squash --match-head-commit <reviewed-sha>` so the command is bound to the
approved head. Omit `--delete-branch`, which can delete the local task branch and worktree. Keep
the task worktree, ignored RUN-NOTES.md and cached assets after the merge; optional cleanup may
remove only the remote branch.

[designed: owner, #127, 2026-10-16; L106] GitHub Actions is manual-only optional
verification on a fresh runner. Before merging, the main session runs
`python3 tools/check_premerge.py --expected-head <reviewed-sha>` in the clean
implementation checkout and records its successful SHA on the PR. This command
preserves the former workflow checks; task-specific Done-when checks and the
independent approving review remain mandatory. A missing or billing-blocked
Actions run does not block a locally validated merge. An optional Actions run
that exposes a real defect must be investigated; its optional trigger does not
permit ignoring a known failing check. No hosted check replaces exact-head local
validation.

What the review script guarantees, and why:
- [designed: T72] The run client starts with stdin closed; the owned v2 server keeps a separate stdin lease open until export recovery and cancellation finish. (L10)
- No session in 180 s, no progress in 600 s, or no exit in 1 h kills the run's process tree (L10);
  `--idle-timeout-sec` and `--total-timeout-sec` lengthen them for one run.
- [designed: T72] V2 verifies the trusted effective agent/permissions and native operand guard before generation, then validates exact session/cwd/model/effort/agent in complete exports; a rejected tool call fails the run (L11, L26),
  and the fix is a wider grant in the agent file, not a re-brief (CLAUDE.md "Choosing models" rule 4).
- [designed: T72 rework1] Install the exact local grammar dependencies in each fresh reviewer checkout with `npm ci --prefix tools/harness/opencode-guard --ignore-scripts --no-audit --no-fund` before offline checks. The validator verifies installed hashes and never fetches. Native source-target plugin policy, frozen config snapshots and repeated actual-server checks preserve the legacy static shell operand boundary; external executable plugins or widening plugin policies fail before billing. See docs/environment.md for the supported binary and explicit nonbilling native probes.
- [designed: T72 rework1] Complete retained outputs and returned records redact the known generated private-server nonce if echoed; receipts disclose this exact redaction and hash safe artifacts afterward. Preserve every other message, tool outcome and final finding.
- The brief passes by file: the runner writes it to `.harness-brief-<title>.md` at the review
  worktree's root and the command line carries only a pointer, so a long brief cannot exceed the
  command-line limit; the file is never committed and is retained with the logs on every outcome. (L60; designed: T72)
- [designed: T72] Routine review uses installed current v2 and a privately owned execution server; its worktree, complete export/final and manifest are retained. Explicit v1 compatibility keeps its separate legacy DB. Follow the printed session or run.json with `tools/harness/peek.sh`.
- The model runs at the effort its `harness.json` entry names (a heavy model at low, a light one
  at high), in the scripts' own data directory (L27, L29). One model, one run; no chain. The model
  is `reviewer.default`, or `--reviewer` (a harness.json key or `provider/model[@variant]`).
- [designed: #165] A complete task/reviewer/PR/full-SHA header missing only its
  expected terminal period is posted whole, flagged, with no label (exit 4).
  Any such near header holds the output, including multiple or mixed exact/near
  drafts. Other punctuation and wrong identities are outside this recovery.
  Read the retained final and manually assess verdicts, findings and every DW;
  formatting alone does not require another paid run. Existing closing-keyword
  rewriting still applies to posted text; retained final artifacts remain raw.
- Exit 0: posted and labelled. 2: a refused model (DeepSeek, an unknown name). 3: no review, nothing
  posted: read the final message ("Choosing models" rule 12), fix the cause, run again. 4: posted under a note, no
  label: the main session reads it and decides.

[designed: T73] An owner explicitly selecting direct Claude review uses
`review.mjs --backend claude --reviewer claude-sonnet`, with a trusted external
permission file, exact required negative-control command and fixed session UUID.
See [the direct Claude setup](environment.md#optional-direct-claude-cli-review).
This optional path preserves model-family exclusion and standard findings/DW
posting. Native model-free policy/account projection uses an owned pipe lease;
the distinct actual review process has closed input. Main alone runs the real
review and same-reviewer follow-ups after ready PR, audits all native outputs and distinguishes synthetic
permission checks/parent validation from reviewer-executed checks. Unknown routes,
required denials, incomplete final/identity/coverage and failed exact-head checks
prevent acceptance. No default/fallback, OS-jail or startup-hook isolation claim
is added. Preserve all historical agy preparation.

How the main session launches and watches a run (L103):
- Detached from its own session, so a restart of Codex or Claude Code does not kill the run, in the form of
  CLAUDE.md's "Choosing models" rule 9: `systemd-run --user --unit=goal2r-<task> --collect -E PATH="$PATH"
  -E MINIMAX_API_KEY -E ANTHROPIC_BASE_URL -E HARNESS_CLIENT -E HARNESS_SESSION_FAMILY -p WorkingDirectory=<repo> -p StandardInput=null -p StandardOutput=file:<log>
  -p StandardError=file:<log> <review.mjs command>`. A unit gets only the
  environment it is given, so each key a run needs is passed with `-E`; never a `bash -c` or
  `bash -lc` script (the safety check flags it).
- The watch follows the unit (`systemctl --user is-active goal2r-<task>`). A Claude implementer
  agent is watched by its transcript file's size and its worktree; when its worktree holds
  uncommitted work more than 20 minutes newer than its last commit, the main session archives it
  outside the worktree, read-only (it never touches the run's index).
- An implementer's PR may be a draft; the main session runs `gh pr ready <pr>` before the review.

## 4. The implementer brief

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

## 5. The reviewer brief

```text
<T<nn>> review (<model>)
You review PR #<n> at <sha>. You did not write it. The task file follows.
0. Prove the tree: HEAD is <sha> and the diff against origin/main is the PR's; findings name its files.
1. Re-run every Done-when line yourself, and account for each (L32). The PR's evidence is no proof.
2. [evidence-driven] Every constant traces to a fixture, report or investigation; a [designed] one says what was searched.
3. [seeded] No wall clock, unseeded random or order-dependent iteration in rule code.
4. Every changed file and behaviour is one the task asks for (L44); docs it makes wrong are updated.
5. Sweep the diff: tests that pass with the behaviour deleted (mutate, rebuild clean, re-take any
   negative result), branches no input reaches, edge comments without a test, <project classes>.
6. <docs/review-brief.md in full: "Blocking means" for this task, then its one-pass section (L47, L49)>
Prove each finding (run it, or delete the behaviour and name the test that fails) or label it
unverified. Your final message is the review: the header; the verdict (approve | approve after
named fixes | rework | user decision); per Done-when line `DW<k>: ran <command> → <result>` or
`DW<k>: not run — <reason>`; the findings R1..Rn (file:line, blocking or not); the verdict again
last. Never post it: the script posts it and applies the label.
```

Briefs here also add, under "Blocking means": an untagged behaviour claim (CLAUDE.md rule 17), an
edited vendored file (rule 18), anything of the original committed (rule 19), or a fidelity test
that never failed (rule 20).

Run mechanics, added to every brief here: the session is killed after 600 s without activity; keep
every shell command under 5 minutes, and work only inside the review worktree. Undo a mutation by
writing back the file's saved contents (read it first, restore it in a `finally`), never with
`git checkout`, `git restore` or `git reset` of the file: those return the last commit and destroy
any uncommitted work in it (PR 114 round 1). If a reviewer still
reports one blocker per round, stop after the second such round: the main session goes through the
whole diff for the same class of problem before the next review, and records the pattern in
`docs/model-trials.md` (L101).

Practical, not theoretical (the owner, 2026-10-05, after T12 took 4 rounds over a bypass no run
showed): a theoretical bypass is blocking only if it makes a claim false as worded, not merely
unproven. Accept what is about 80-90% likely, worded with its confidence and what remains
possible; narrow a claim's wording rather than add runs or rounds, and file stronger evidence as
a follow-up.

Proportionate reviews (the owner, 2026-10-20, after #253/PR #271 took four rounds over its own
planning-doc checker while its content was accepted every round):
1. **Review the task, not its tooling.** Blocking findings concern the task's Done-when and the one
   claim its Scope protects. Crafted-input attacks on helper scripts, validators, receipts or test
   tooling are out of scope unless the task itself delivers that tool as a protection (a guard, a
   permission, an engine seam).
2. **Docs and planning PRs: content first.** The reviewer judges the content. Their helper checks
   are consistency checks for honest edits; an adversarial bypass of one is never blocking.
3. **Same-class cap.** When the same class of finding returns in a second round, the main session
   narrows the claim and files a follow-up issue instead of a third round on that class. Only a
   real defect in what the task delivers keeps blocking.
4. **Severity bar.** Blocking means a real user or implementer would hit it through normal use or
   honest editing. A problem that needs deliberately crafted input is a follow-up, unless defeating
   crafted input is the task's own protected claim.
5. **Modest claims.** Implementers do not write guarantees their checks cannot back; a smaller
   claim beats a bigger checker.
6. **Reviews are posted on the PR.** `review.mjs` posts its own runs. A review run outside it (for
   example in the reviewer's own cloud session) ends by posting the complete review as one PR
   comment (`gh api repos/<owner>/<repo>/issues/<pr>/comments -X POST -F body=@<file>` where gh's
   GraphQL commands are unavailable), exactly once, changing no labels; the main session then
   reads it and applies the label it supports.

Before merging an approval that carries non-blocking findings, the main session reads them: a
proven way past what the task protects is rework whatever the reviewer rated it; it says so on the
PR and records it in `docs/model-trials.md` (L47: GLM-5.3 proved three guard bypasses, rated them
non-blocking and approved).

For a Claude reviewer, the main session also runs `/code-review <pr>` on architecture tasks,
always with the PR number: a bare invocation from an agent reviews the wrong tree. (L8)

## 6. Bugs, fixes, triage

Bugs and non-blocking review findings are filed with `triage:needed`: one `T<nn> follow-up` issue
per merge. Triage decides one of:
- **fix**: no ruleset value, fixture value, seeded measurement or golden line changes outside the
  bug's own reproduction. The bug issue is the contract; its Done-when is its reproduction as a
  failing-then-passing test; same-reviewer follow-ups until accepted (§3). (L4)
- **correction task**: anything that changes an outcome.
- **fold** into a task not yet ready, or **close**, with the reason.

Once `breaks-play` is trialled (§12), Jev settles the gate's confident ends; the main session the middle.

## 7. Escalate to the user when

A design question; a Done-when would have to weaken; a third rework round, except the narrow one
the main session may grant itself when the remaining findings are small and change no result
(CLAUDE.md rule 7); anything destructive (force-push, rewriting `main`, deleting an issue); a new
external dependency.

## 8. Labels

`task`, `bug`, `fix`, `triage:needed`, `post-playable`,
`status:{ready,in-progress,in-review,rework,approved,blocked,escalated,merged}`,
`review-round:{1,2}`, and `model:<name>` on a PR whose implementer was not the default.

## 9. Measure

After each merge, one PR comment records each Claude agent's token total (from its completion
notice), each OpenCode run's model and duration, and the review rounds. After 10–20 tasks, compare
the rework rate with the baseline in `docs/lessons.md` before changing models. (L13)

## 10. Adding a rule

A rule enters `CLAUDE.md` or this file only with a lesson in `docs/lessons.md`: a failure in a real
run, or the owner's decision with its basis. Plausible rules without either stay out. (L14)

## 12. Delegating decisions to Jev

Jev takes a decision only when it recurs over many items, its answers are known up front, and a
trial against labels has set its cutoffs, recorded in `harness.json` with the numbers. It answers
the confident ends and the main session the middle; a person's decision outranks both. Without its
key it is off. `/jev` has the procedure. (L24)
