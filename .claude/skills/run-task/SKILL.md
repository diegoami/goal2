---
name: run-task
description: Run tasks or fixes end to end. A subagent spawned on a model of its own (or the main session directly) implements and one OpenCode model of another family reviews, honoring existing implementation authorization and asking the owner for review only after a validated PR exists; the main session watches, merges and reports. Main session only.
---

# /run-task [T<nn> | #<issue> ...]

[designed: owner, 2026-10-14] This procedure is shared by Codex and Claude.
Read AGENTS.md in Codex and CLAUDE.md in both; process §1 defines client dispatch.
Ask for an implementer/model before each new task and wait; a task request alone
does not select one. A choice explicitly made for that task persists through
implementation/rework. A review question always comes
after the validated PR exists. Propose a default only if it is eligible.

**Codex dispatch for step 2:** implement in the native main session by default,
or a native Codex subagent if authorized. The main session prepares its branch and
worktree under harness.json's worktreeRoot before dispatch; paste the complete task
and process §4 contract. Claude Agent aliases, isolation parameters and hooks do
not apply to native Codex tools. Keep the same notes, validation, push and PR rules.
For detached step-3 jobs set `HARNESS_CLIENT=codex`; OpenAI reviewers are refused.
The Claude-specific step-2 dispatch below remains in force for Claude Code.

Read `docs/process.md` §3–§6 first. Given ids, run them in order; given none, take the first
`status:ready` task in `docs/tasks/README.md`. Report after each task; stop at any escalation.
For `#<issue>` of a bug labelled `fix`, the bug body replaces the task file, the branch is
`fix/<issue>-<slug>`, and there is one review round.

Ask for the implementer/model before each new task unless the owner has already
explicitly chosen it for that task, then wait for the answer. For each
review, ask which OpenCode model after the validated PR exists. Propose only an
eligible configured default. The roster changes through `/switch-model`; no quota
is checked. `switch-model.mjs --show` reports the client and family: native Codex
is OpenAI, while Claude retains its Anthropic provider mapping. The reviewer is
never the implementer's family.

0. **Check.** The issue is `status:ready` and every Merge-after task is merged. Run
   `gh issue list --label triage:needed --state open`; triage anything that names this task first.
   If `harness.json` has cutoffs for `breaks-play`, route those issues through Jev first (`/jev`
   step 4). Act on its confident ends and triage the middle yourself; exit 3 means triage it all.

   Run every Done-when line yourself: it must fail on `main` and pass on a mock fix (a scratch
   change, then discarded). A line that cannot is amended on `main` before dispatch (L45).

1. **Brief.** The task file **pasted in full**, then `docs/process.md` §4's block, then (on
   rework) the review comment's URL. Never a pointer to the task file. The main session
   implementing itself reads the same block as its contract.

2. **Implement (Claude dispatch).** Unless already authorized, ask the user ONE question with the question tool (CLAUDE.md "Choosing models"
   rule 1): which subagent implements (the `implementer` agent on `sonnet`, `opus`, `haiku`, `fable`
   or a model id the session's provider serves), or does the main session implement directly (only
   where the provider cannot spawn one)? Put `harness.json`'s `implementer.default` first. A model on
   `harness.json`'s `blocked` list never implements, whoever names it: check the answer against
   `switch-model.mjs --show`'s blocked line (an alias that resolves to a blocked model included) and,
   if it is blocked, say so and ask again. Record the answer on the
   issue. Label `status:in-progress`. Then:
   - **The `implementer` subagent**: `Agent(subagent_type: "implementer", model: <the answer>,
     isolation: "worktree")` with the brief, on a model of its own, not the orchestrator's
     (`sonnet` under Opus; under Z.AI the same alias is GLM-5.3 Flash; a model id names the
     provider's model outright). Its agent file carries §4's block and the run mechanics; its
     hook refuses `git stash`, `git worktree`, a force-push and `gh pr merge`. Watch it by its
     transcript file's size and its worktree (CLAUDE.md "Choosing models" rules 9-11); tell the user in plain
     language what it is doing. Read its final report in full before acting ("Choosing models" rule 12), and post
     its `RUN-NOTES.md` on the issue. A report that stops on a Done-when it cannot meet gets an
     answer (amend the task on `main`, decide, or escalate), never a blind retry; a subagent our
     limits interrupted is resumed with a short "continue where you stopped" brief ("Choosing models" rule 13).
     Paths outside its worktree are reachable from a subagent (L57); an OpenCode reviewer reaches
     only `/tmp` and the goal2-archaeology checkout.
   - **The main session, directly**, only where the provider cannot spawn a subagent (one model,
     or the Agent tool's model not honoured) or the user says so: in its own `git worktree` on
     the task's branch (never the main checkout), keeping `RUN-NOTES.md` there
     (`docs/running-notes.md`), pushing after every commit and at least every 20 minutes, opening
     the PR as a draft after the first push and `gh pr ready` before the review.

3. **Review.** First ask the user ONE question (CLAUDE.md "Choosing models" rule 2): which
   OpenCode model reviews? Put `harness.json`'s `reviewer.default` first (`sol-6.1` for hard
   reviews: an engine seam, a fidelity test, a vendored model), then the registered models that are neither of the session's family nor
   blocked (`switch-model.mjs --show`). Record the answer on the PR. Label `status:in-review`.
   Name the PR's head in the brief only after the push has landed (`git rev-parse <branch>`); a
   brief naming another commit exits 2 before anything runs (L33). Then, as a systemd unit
   (CLAUDE.md "Choosing models" rule 9: `systemd-run --user --unit=goal2r-<task> --collect -E PATH="$PATH"
   -E MINIMAX_API_KEY -E ANTHROPIC_BASE_URL -E HARNESS_CLIENT -E HARNESS_SESSION_FAMILY -p WorkingDirectory=<repo>
   -p StandardInput=null -p StandardOutput=file:<log> -p StandardError=file:<log>
   node tools/harness/review.mjs --pr <pr> --brief <file> --issue <n> --apply-label
   [--reviewer <the answer>]`), watched ("Choosing models" rules 9-11). The script reads the session's family from
   client/provider settings, so the unit must carry HARNESS_CLIENT (Codex) or the Anthropic endpoint/override (Claude).
   One review per PR unless the user asks for more. Relay its findings in full (rule 8).
   - Exit 0: posted and labelled.
   - Exit 2: a refused model (blocked in `harness.json`, or an unknown name): tell the user.
   - Exit 3: no review came back (OpenCode, the login, the model, a rejected path, or a review
     the script could not find). Nothing was posted. Read the run's final message first ("Choosing models" rule 12,
     the snippet below), fix the cause (a wider grant in `.opencode/agents/reviewer.md`, a login,
     a brief line), and run again; killed by our own limit, run again with a longer
     `--total-timeout-sec`. Another model only when the provider does not answer, and the user
     names it.
   - Exit 4: a review was posted whole under a note (cut off, verdict unreadable, verdicts differ,
     a finding after the closing verdict, or an approve with a Done-when line unaccounted for or
     not run, L32). No label was applied. Read it on the PR and decide: apply the label it
     supports, ask for a supplementary review of the missing DW lines, or send it to rework.
     Never pay for a second review just because the first was flagged: OpenCode's models do not
     always follow the brief, and the script's reading is the safety net.
   - **Read before you act (L55).** The final message, read-only (never `auth.json` there), with
     the `session ses_…` id from the run's log:
     ```bash
     python3 - <<'PY'
     import sqlite3, json, os
     home = os.environ.get('HARNESS_OPENCODE_HOME') or os.path.expanduser('~/.local/share/harness-opencode')
     db = 'file:' + os.path.join(home, 'data', 'opencode', 'opencode.db') + '?mode=ro'   # the scripts' data directory
     c = sqlite3.connect(db, uri=True)
     sid = 'ses_...'   # the "session ses_..." line in the run's log
     parts = [json.loads(d) for (d,) in c.execute("select data from part where session_id=? order by time_created", (sid,))]
     texts = [p for p in parts if p.get('type') == 'text']
     print(texts[-1]['text'] if texts else 'no text part')
     PY
     ```
   - A Claude review (`/code-review <pr>`, always with the number, or the `reviewer` agent posted
     with `post-review.mjs`) only when the user asks: it is the implementer's family.

4. **Decide** on the label the reviewer applied.
   - `status:approved`:
     1. Wait for green CI.
     2. Re-run the check the approval rests on most (the Done-when line or the mutation that
        proves the task) on the PR's head yourself. A different result is rework, not a merge (L46).
        Read the non-blocking findings too: a proven way past what the task protects is rework
        whatever the reviewer rated it (L47).
     3. The main session merges the exact reviewed head with
        `gh pr merge <pr> --squash --match-head-commit <reviewed-sha>` (every PR squashes here,
        CLAUDE.md rule 7). Omit `--delete-branch`: it can delete the local task branch and its
        worktree. Keep the task branch, worktree, ignored RUN-NOTES.md and cached assets; any
        optional cleanup must affect only the remote branch. Then label `status:merged`.
     4. File one `T<nn> follow-up` issue (`triage:needed`) for the non-blocking findings.
     5. Unblock the tasks whose Merge-after are now all merged.
     6. Leave the task's worktrees: never remove one (CLAUDE.md rule 2a); the sweep removes old ones.
     7. Post §9's measurement comment on the PR, and a row in `docs/model-trials.md` when the
        review taught something.
     8. Report the merge, the findings, the follow-ups and what is ready next.
   - `status:rework`:
     1. Check that every finding names a file in `gh pr diff <pr> --name-only`. A review that
        does not reviewed the wrong tree: discard it, say so, and re-review.
     2. At `review-round:2` (at `review-round:1` for a fix), go to step 5.
        A reviewer that reports one blocking finding per round despite the brief's one-pass
        section (L49): after the second such round, stop. Request no further review until you
        have gone through the whole diff yourself for that class and fixed what you found, and
        recorded the pattern in `docs/model-trials.md` (L101). The review after that is the task's
        last before escalation (step 5).
     3. A heavy review (three or more blocking findings, or a repeated class) is fixed by class,
        not by instance: the next round sweeps the implementer's own code for the same class and
        lists the sweep in the PR body, and changes the approach when the class needs it, saying
        so on the task file. The round count does not reset, and the Done-when is never weakened.
     4. Set the next round and return to step 1, with the full review's URL in the brief. The
        implementer resumes the pushed branch; it never starts over.

5. **Escalate** (`docs/process.md` §7): label `status:escalated`, comment the evidence on the issue,
   and bring the user the decision with options and a recommendation. Stop.
   A defect found in merged code outside the task is filed as a bug (`triage:needed`). If it
   blocks the task: a one-file mechanical fix may ride this PR, declared under Scope; otherwise
   label the task `status:blocked` and stop.

Never:
- merge without an approving review and green CI;
- weaken a Done-when;
- let the implementer's model family review its PR;
- relay part of a review;
- force-push or rewrite `main`.
