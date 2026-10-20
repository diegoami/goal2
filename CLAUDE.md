# goal2

The faithful rebuild of *goal (version 2)* (New Era Software, 1993) and the bot that plays a
country competently for idle play (the owner, 2026-10-11), built from the evidence of the private
`goal2-archaeology` repository (findings `F0nn`, task records, releases). Python. The plan is
[`docs/plan.md`](docs/plan.md); the process is [`docs/process.md`](docs/process.md), read it before
running a task. Tasks are `docs/tasks/T<nn>.md`, indexed in `docs/tasks/README.md`.

The harness (`tools/harness/`, the skills, the agents) comes from goal2-archaeology at `8dc4dc1`
(`harness.lock`); rules 1-16 and "Choosing models" are its rules, numbered as there, because the
skills and agents cite them by number.

## Supported clients

[designed: owner, 2026-10-14] Codex and Claude Code share the rules below and
docs/process.md. Codex starts at AGENTS.md; Claude retains this entrypoint and
its native skills/hooks. Codex implements directly or with native Codex subagents;
Claude retains its existing aliases and isolated Agent dispatch. OpenCode reviews
only after the implementation PR exists, using the model the owner chooses.
Ask for an implementer/model choice before each new task and wait; a task request
alone is not a model choice (owner, 2026-10-14). Once chosen for that task, the
authorization persists through implementation/rework. harness.json retains Claude's implementer.default and adds the
Codex default at implementer.defaultsByClient.codex. See process §1 for dispatch.

## Rules
1. The main session plans, runs `/run-task`, triages and talks to the user. A subagent it spawns
   implements (or it does itself); honor authorized implementation choices and ask the user
   which OpenCode model reviews after the validated PR exists ("Choosing models" below). Repeated decisions
   go to Jev after a trial, and images and audio to OpenRouter or ElevenLabs models, whose ids come
   from live lists, never memory (`/delegate`).
2. Nobody works in the main checkout: the main session, when it implements, works in its own git
   worktree; OpenCode runs in the worktree the script makes; Claude agents run with worktree
   isolation. Never `git stash`.
2a. **Never remove a worktree** (the owner, 2026-10-11, after the main session removed a running
    review's worktree mid-run): not after a merge, not in a cleanup, not one that looks finished.
    The harness scripts' removal of their own worktree at the end of their own run is theirs.
    Old worktrees go only through the **sweep**, at session start (rule 14) and at least once a
    day: a worktree is old when ALL hold — no process has its cwd or an open file in it
    (`ls -l /proc/*/cwd`, `lsof +D`), no systemd unit or monitor of this or another session uses
    it, its newest file and last commit are more than 7 days old, its branch is merged or gone
    on origin, and it is clean (else its diff is saved as a patch beside it first). Keep its
    cached states under `.cache/kept/` before removing it. Anything in doubt stays, and the sweep
    lists what it removed and what it kept, and why.
3. Status lives in GitHub labels. No document carries a status snapshot.
4. A question is not a request to edit files. Answer it; propose any fix and wait.
5. The Done-when is not negotiable by the implementer. It stops and reports; it never weakens an
   assertion, skips a test or edits its task file. The main session amends a Done-when on `main`
   with the reason in the commit message.
6. The reviewer is never the implementer's model family. It re-runs every Done-when line itself.
7. Merge only with an approving review (tier 0: the main session's own checks, rule 7a) and the main session's pre-merge checks pass (process.md §3 — re-run the check the approval rests on, plus `python3 tools/check_premerge.py --expected-head <reviewed-sha>` in the clean implementation checkout; Actions is manual-only optional verification (owner, #127, 2026-10-16)). [designed: owner, 2026-10-18] Once the reviewer is selected, continue same-reviewer follow-ups and rework until accepted, without asking again for each review. This supersedes fixed round-count stops and one-trial limits as retry-permission gates. Read complete results, fix causes and validate each new head; never silently switch provider/model, weaken acceptance or bypass safety. Report real blockers needing an owner design or external-access decision. Merge only the accepted exact head after required checks, from the main session, without asking again (`--squash`).
7a. [designed: owner, 2026-10-20] **Review by risk tier.** The task file names its tier (an issue
    without one: the main session, at dispatch); when unsure, the higher tier.
    - **Tier 0:** docs, planning, task files and small fixes that change no outcome. No external
      review: the main session runs the task's checks and exact-head premerge, merges, and lists
      the PR for the next milestone review.
    - **Tier 1:** features and UI slices. One external review round by another family; what remains
      after one rework becomes follow-up issues, unless it is a real defect in what the task
      delivers (process.md §5 "Proportionate reviews").
    - **Tier 2:** engine, fidelity, vendored model, save/timing, guards and permissions. Per-PR
      review until accepted, as rules 6-7 say.
    - **Milestone review:** at each queue milestone, one review by another family over the
      integrated result, plus the owner's playtest; its findings become issues.
    Rules 6-7's external review applies to tiers 1-2.
8. Relay review findings in full. Read a run's final message before you retry or re-route it (L55).
9. A test proves behaviour only if it fails without that behaviour; re-take a claim that nothing failed.
9a. Undo a mutation or scratch edit by writing back the file's saved contents (read it first, restore
    it in a `finally`), or commit first; never `git checkout`, `git restore` or `git reset` a file with
    uncommitted work: they return the last commit and destroy the rest (PR 114 round 1).
10. A comment asserting behaviour at an edge arrives with the test that visits that edge.
11. Until the first playable build, schedule only bugs that break play; the rest are `post-playable`.
12. A bug whose fix stays in the files it names and changes no outcome is a `fix`; a blocking
    one-file mechanical fix may ride the PR that found it, declared under Scope.
13. Design decisions go to the user; nothing else waits for the user.
13a. A lesson or a decision of the owner goes into this file or `docs/` in a commit, never only
    into Claude's memory, which stays on one computer (the owner, 2026-10-11). Memory holds nothing
    the repository needs.
14. At session start: `gh issue list --label triage:needed --state open`, any task in flight, and
    the worktree sweep (rule 2a).

## Token economy
15. A brief carries the task file pasted in full, never a pointer to it.
16. Keep every file an agent must read under ~20k tokens. Scope searches to the source and test
    directories; keep terminal output quiet; show diffs, not files.


## This project
17. **Evidence tags.** Every behaviour claim in code or docs is tagged `[confirmed]`
    (cites the goal2-archaeology finding(s) and commit it rests on), `[derived]` (follows from
    confirmed claims) or `[designed]` (a choice of this rebuild, no original evidence). No untagged
    behaviour claims; a `[designed]` choice that later contradicts a finding is a bug.
18. **Engine truth is vendored, never edited.** Files under `goal2/engine/` are copies pinned in
    `PROVENANCE.md` (file, source repo, commit, findings). A defect in vendored code goes upstream to
    goal2-archaeology; the fix arrives here only as a deliberate re-vendor that records the new
    commit. Engine files carry no evidence tags of their own: their provenance row is the citation.
19. **Nothing of the original game is committed.** No GOAL2 asset, savestate or executable byte
    enters this repository (U17/U21). States load from local caches or the archaeology releases by
    path, git-ignored (`.cache/`).
20. **The fidelity test is the arbiter.** When this rebuild's behaviour and the vendored model
    disagree on a case the model is seed-exact for, the rebuild is wrong until proven otherwise. A
    fidelity test that has never failed proves nothing (state the case it fails without the fix).
21. **Tests fail before and pass after.** Every new behaviour arrives with the test that visits it;
    the PR says how the failure was shown.
22. **One task, one branch, one PR.** Task files say what is in scope; a Done-when line that cannot
    be met stops the task and reports, never weakens the line.

## Choosing models: who implements, who reviews (the owner, 2026-10-11 and 2026-10-12)
These rules replace every other model-choice rule in this project (goal2-archaeology's, adopted
2026-10-12 with its harness): goal2 issue #1's "follow quota-tracker's
/recommend and nothing else" (superseded 2026-10-12), and the global `~/.claude/CLAUDE.md` rule that quota-tracker
decides. What worked: a subagent spawned inside Claude Code implements (or the main session does, when
it cannot spawn one), and a separate OpenCode process of another family reviews. The roster is the owner's and changes often: the
defaults and the blocked list live in `harness.json` and change through `/switch-model`, never by
a rule that names a model. No quota, tier or difficulty table picks a model.

0. **Client detection precedes provider detection.** [designed: T24]
   `HARNESS_CLIENT=codex|claude` selects explicitly; otherwise nonempty
   `CODEX_THREAD_ID` / `CODEX_SESSION_ID` selects Codex, else Claude. Codex is family
   `openai`; a conflicting `HARNESS_SESSION_FAMILY` is refused. Pass
   `HARNESS_CLIENT=codex` to detached Codex review jobs.
   For Claude Code, **the orchestrator is set by the Anthropic environment variables** (`ANTHROPIC_BASE_URL`,
   `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`): Claude by default; when Claude's tokens are out, GLM-5.3
   through Z.AI's Anthropic-compatible endpoint, or MiniMax, or Moonshot's Kimi, which then work
   like Claude. These
   rules never name the orchestrator's model. The harness reads the orchestrator's **family** from
   that environment (`lib/common.mjs` `sessionFamily`: Claude when the base URL is unset or
   Anthropic's, GLM for Z.AI, MiniMax, Kimi for Moonshot; `HARNESS_SESSION_FAMILY` overrides, and an unknown endpoint refuses
   to review until it is set), because every subagent the session spawns, whatever its model,
   runs through the same endpoint and is of that provider's family. Pass `ANTHROPIC_BASE_URL` and `HARNESS_SESSION_FAMILY` to
   a review's systemd unit (rule 9).
1. **Implementation choice.** [designed: owner, 2026-10-14] Ask the owner which
   implementer/model to use before starting each new task, and wait. Keep a choice
   already explicitly made for that task through its implementation/rework.
   Codex defaults to the native session (or a native
   Codex subagent when authorized), in a worktree prepared by the main session
   under worktreeRoot. Do not dispatch Claude aliases through Codex or claim
   Claude hooks protect it. The following alias/Agent instructions are for Claude:
   when not already authorized, **ask the user ONE question** with the question tool: which
   **subagent** implements, or does the main session implement directly? The implementer is
   normally a subagent spawned inside Claude Code with the Agent tool
   (`subagent_type: "implementer"`, `.claude/agents/implementer.md`, **always pass
   `isolation: "worktree"` — L107: the guard refuses `git worktree`, so the worktree must
   come from the spawn, not the agent**) on a model of its own, not the orchestrator's:
   Opus orchestrates and spawns Sonnet. The Claude implementer model is a
   Claude Code alias (`sonnet`, `opus`, `haiku`, `fable`) or any model id the session's provider
   serves; under another Anthropic-compatible provider (Z.AI's GLM, MiniMax, Kimi) the same alias
   resolves to whatever that provider maps it to (GLM-5.3 Flash for `sonnet` on Z.AI), or the id
   names its model outright. When the provider cannot spawn a subagent (one model only, or the
   Agent tool's model is not honoured), the main session implements directly, in its own git
   worktree (never the main checkout). Propose `harness.json`'s `implementer.default` first.
   Whatever the model, a subagent runs through the session's endpoint, so its family for the
   reviewer rule is the session's (rule 0). OpenCode never implements: `implement.mjs` was
   removed, because its runs died on rejected paths, resets and early ends and did not follow the
   brief (L104). Whoever implements keeps `RUN-NOTES.md` in its worktree (`docs/running-notes.md`:
   the plan, a progress line per commit, an END block before stopping), pushes after every
   commit, and opens the PR. When a subagent ends, the main session reads its final report before
   acting and posts its notes on the issue.
2. **After creating and validating the PR, ask the user ONE question:** which OpenCode model reviews? Propose
   `harness.json`'s `reviewer.default` first (GPT-5.6 Luna today; `sol-6.1`, GPT-6.1 Sol at
   `low`, for hard reviews: an engine seam, a fidelity test, a vendored model), only if eligible for this client, and list the registered models that are neither of the
   session's family nor blocked. Then `tools/harness/review.mjs --pr <n> --brief <file> --issue
   <n> --apply-label [--reviewer <name>]`, same-reviewer follow-ups until accepted under rule 7; its
   findings are relayed in full (rule 8). OpenCode's models do not always follow the brief: the
   script posts what came back, flags what it cannot read (exit 4), and the main session reads a
   flagged review and decides the needed correction or targeted follow-up under rule 7. Record the answers to both
   questions on the issue or PR.
3. **The fixed rules:** the reviewer is never of the session's family (`review.mjs` refuses it
   from the environment; a `/code-review` or the `reviewer` agent, which are that family, run
   only when the user asks). No model or provider is otherwise gated: the owner emptied
   `harness.json`'s `blocked` list and lifted every provider limitation — DeepSeek, Alibaba,
   OpenCode routes, OpenAI — on 2026-10-13 ("Limitations on deepseek and alibaba and opencode
   and openai must go"); `/switch-model --block` re-adds a block only by the owner's word.
4. **Permissions, not briefs:** an agent gets the permissions its work needs, in its agent file
   (`.opencode/agents/reviewer.md`: all of `/tmp` and the goal2-archaeology checkout, which `tools/check_provenance.py` reads; `.claude/agents/*.md`:
   the guard hook refuses only a force-push, `git stash`, `git worktree`, a merge and, for the
   reviewer, every write). A run that dies on a rejected path is fixed by widening the grant,
   never by re-briefing.
5. A failed run is diagnosed and fixed, not silently re-routed: another model only when the
   provider does not answer, and the user names it. The PR records who implemented and which
   model reviewed.
6. These rules work whatever model the orchestrator itself runs on; they never name it.
7. **Still in force:** the effort rule (a heavy model, Opus, GPT-6.1 Sol, GLM-5.3, MiMo v2.6 Pro
   or MiniMax-M3, at `medium` at most and `low` when medium is not needed; a light model at
   `high`); every model id comes from a live list (`opencode models --standalone` on v2), never memory;
   the main session runs the lines an OpenCode reviewer cannot reach (L57).

[designed: T73] The owner may explicitly select the optional direct Claude CLI
reviewer described in docs/environment.md. It is reviewer-only, never a fallback
or a default change. Native Codex remains family openai; direct Claude remains
family claude and cannot review Claude-family implementation. Trusted launching
policy, complete identity/denial/scope evidence and main-only merge rules remain.

### Monitoring OpenCode sessions (and any other background agent)
8. [designed: T72] Start every OpenCode run in the background. The run client receives closed stdin; its private v2 server has a separately owned stdin lease. For direct v1 clients, use stdin from a file (never an inherited pipe:
   `opencode run` waits for stdin's end-of-file before it creates a session). Never wait on it blind.
9. Watch it with one monitor that checks every 1-2 minutes. Test a job's life by its systemd unit
   (`systemctl --user is-active <unit>`: start every long job as its own unit, L103) or its PID
   (`kill -0 <pid>`), never with `pgrep -f`, which matches the watching shell's own command line
   and never sees the job end (L48; isle-wars lost 1.5 h to it, 2026-10-11). A unit gets only the
   environment it is given: `systemd-run --user --unit=goal2r-<name> --collect -E PATH="$PATH"
   -E MINIMAX_API_KEY -E ANTHROPIC_BASE_URL -E HARNESS_CLIENT -E HARNESS_SESSION_FAMILY -p WorkingDirectory=<dir> -p StandardInput=null -p StandardOutput=file:<log>
   -p StandardError=file:<log> <command>` (without the key a MiniMax run stops with "minimax lists
   no models", 2026-10-11; never a `bash -c` script). It covers:
   - the session started (`opencode session list` in the run's directory, or the run's
     "session ses_... started" line), and the run's exit;
   - progress: the OpenCode log's size and the session's `updated` time, the worktree's changed
     files, new lines in the running-notes file, and new commits on the branch;
   - "possibly stuck" after ~10 minutes with no change; "unpushed" when a commit sits on the
     branch but not on origin for ~15 minutes (push it for the run and record it);
   - free memory, if the machine is short of it: run reviews and builds one at a time.
   For a Claude subagent, the progress signal is its transcript file's size plus its worktree.
10. Tell the user, in plain language, what each running agent is doing: the step it is on (as "step k
    of n" where the brief has steps), what it committed, what it found (from its notes, commits and
    latest session messages). Never raw log lines or byte counts. As soon as an OpenCode run's log
    shows `session ses_… started`, give the user the session id and the command to follow it,
    `tools/harness/peek.sh ses_… [-n 20]` (or the run log's path), and repeat the id in every update
    (the owner, 2026-10-11, after isle-wars-archaeology d1e0082).
11. On a "possibly stuck" flag: check the process is alive, read its newest session messages
    (`tools/harness/peek.sh <ses_...>` or its printed `run.json`; v1 uses explicit `--major 1`); a long build or test step
    is not stuck. A dead or 20-minute-silent run is stuck: stop it, but only if it is ours (the
    machine is shared).
12. When a run ends, read its final message before doing anything else. A review that stopped on
    a rejected path or an unreadable output gets its cause fixed (a wider grant, a brief line), not
    a retry on another model.
13. A review our own idle or total limit killed is run again with a longer limit
    (`review.mjs --total-timeout-sec <longer>`); a Claude agent our limits interrupted is resumed
    with a short "continue where you stopped" brief, never restarted from scratch.
