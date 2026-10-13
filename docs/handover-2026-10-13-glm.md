# Handover — 2026-10-13 → GLM session

Aimed at the next session, which will start on GLM-5.3 (Z.AI) via clother.
The previous session ran on MiniMax-M3 and committed L109 at `b105cc2`.
**Read this first**, before re-reading CLAUDE.md or process docs.

The durable end-of-day record is `docs/handover-2026-10-13.md`. Lessons
L105–L109 are in `docs/lessons.md`. This file is the *delta*: things a GLM
session needs that the durable record doesn't.

## Backend you'll be on

- `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic` (set by clother).
- Heavy: `glm-5.3` (opus / sonnet slot). Light: `glm-5.3-flash` (haiku slot).
- Both are the same family for the reviewer rule: GLM. Don't review with a
  GLM agent; the OpenCode `review.mjs` script enforces this (rule 3).
- Confirm with `echo $ANTHROPIC_BASE_URL $ANTHROPIC_MODEL
  $ANTHROPIC_DEFAULT_OPUS_MODEL $ANTHROPIC_DEFAULT_SONNET_MODEL
  $ANTHROPIC_DEFAULT_HAIKU_MODEL`. The non-claude-backend skill is the
  authority on the slot table; `harness.json`'s "under Z.AI `sonnet` is
  GLM-5.3 Flash" wording is the older version and may be stale — check
  the env vars, not the prose.

## What was just done (this handover's "now")

- L109 commit `b105cc2`: `docs/lessons.md` row forbidding non-rule-17
  bracketed prefixes (`[design check]`, `[R1 fix]`, …) in implementer
  briefs. The shape is enforced by an explicit brief reminder; a pre-commit
  grep is a future change.
- `harness.lock` SHA-256 for `docs/lessons.md` refreshed to
  `95fe6366...4e5213`. Lock passes `sha256sum -c --quiet`.
- Pushed: `c5fccff..b105cc2  main -> main`.

## Session-start protocol (do these in order, before any work)

1. **Confirm backend.** `echo $ANTHROPIC_BASE_URL $ANTHROPIC_MODEL`. Expect
   z.ai and `glm-5.3`. The `non-claude-backend` skill is in effect; Claude's
   quota is irrelevant.
2. **gh triage** (rule 14): `gh issue list --label triage:needed --state open`.
   Expect: Issue #11 "T03 follow-up: reconcile LCG draw order against E006
   byte-exact" (open since 2026-10-12). Decide: triage now, defer, or
   `post-playable` (rule 11).
3. **In-flight check** (rule 14): any task open in `docs/tasks/`? Any
   unmerged PR? `gh pr list --state open`.
4. **Worktree sweep** (rule 2a, 14). For each worktree, check:
   - no process cwd or open file there (`ls -l /proc/*/cwd`, `lsof +D`)
   - no systemd unit / monitor uses it
   - newest file and last commit > 7 days old
   - branch merged or gone on origin (`git branch --merged main`)
   - clean (else save diff beside first: `git diff <branch>..main > <path>.patch`)
   If ALL hold, copy cached states to `.cache/kept/`, then
   `git worktree remove` + `git branch -D`. Report what was removed/kept.

The T17 / T18 worktrees (`.claude/worktrees/agent-a222edf83e310599d`,
`agent-abc5e33612c4c7a2a`) are 0 days old — not eligible today. The T01–T15
worktrees in `goal2-work/` may be; check dates before any removal.

## Quota strategy on GLM

- Z.AI peak: Mon–Fri 14:00–18:00 UTC+8. During peak, `glm-5.3` costs 3x
  quota (1x off-peak); `glm-5.3-flash` 1.2x (0.4x). `promo_off_peak_until`
  is set during promotions. Check
  `curl -s localhost:8765/quota/zai | jq .pricing.peak_now` before each
  implementer dispatch and reviewer launch. Prefer `glm-5.3-flash` for
  small tasks during peak.
- For reviewer choice: `curl -s 'localhost:8765/recommend?tier=heavy'`,
  follow `rank`, skip the GLM family, skip the blocked list (DeepSeek
  today, `harness.json`). Don't trust tables from memory; re-query.
- "Claude's quota" is irrelevant here (non-claude-backend skill). For any
  "quota first" rule, your agent's provider is `zai`, not `claude`.

## Choosing models for the next task

1. **Before each implementation**, ask the user ONE question (rule 1):
   which subagent implements, or does the main session? Propose
   `harness.json`'s `implementer.default` first. **Always pass
   `isolation: "worktree"`** to the Agent tool (L107). Brief format:
   `Tnn review (Model)`, no extra text (L105). The brief carries the task
   file pasted in full (rule 15).
2. **Before each review**, ask the user ONE question (rule 2): which
   OpenCode model reviews? `curl -s 'localhost:8765/recommend?tier=heavy'`,
   pick first row whose family is not `zai` and not blocked. Then
   `tools/harness/review.mjs --pr <n> --brief <file> --issue <n>
   --apply-label [--reviewer <name>]`.
3. Record implementer + reviewer on the issue or PR (rules 1, 2, 5).

## Open items, in priority order

1. **Issue #11** — T03 LCG draw order (~7,510 / 12,244 bytes differ). The
   engine's randomness is unverified; BM-1..BM-7 (P4) rely on seeded
   behaviour. 1–2 days of triage.
2. **Worktree sweep** — see session-start step 4.
3. **Auto-memory slim-down** (rule 13a) — being done as part of this
   handover; the new memory file is pointers only.
4. **P4** — BM-1..BM-7. Starts after Issue #11.

## What the durable record already covers (don't re-derive)

- State: `docs/handover-2026-10-13.md` (T15 / T16 / T17 / T18 all merged;
  195/195 tests OK; main at `b105cc2`).
- Rules: `CLAUDE.md` rules 1–22; `docs/lessons.md` L105–L109.
- Process: `docs/process.md`. Plan: `docs/plan.md`.
- Tasks: `docs/tasks/T<nn>.md` (indexed in `docs/tasks/README.md`).

## What NOT to do (this session's known footguns)

- Don't check `/quota/claude` (irrelevant on a non-Claude backend).
- Don't spawn a `reviewer` agent unless the user asks (rule 3).
- Don't use a model on `harness.json`'s `blocked` list (DeepSeek today).
- Don't work in the main checkout (rule 2); subagents need
  `isolation: "worktree"`.
- Don't remove a worktree without the sweep (rule 2a).
- Don't ship a commit that touches a file in `harness.lock` without
  refreshing the SHA-256 entry (L108). Use `python3` not `python`.
- Don't weaken a Done-when (rule 5). Amend on `main` with the reason.
- Don't repeat the evidence-tag-prefix mistake (L109). The implementer
  brief must say: only `[confirmed]` / `[derived]` / `[designed]`; meta
  goes in `# NOTE:` or plain comments.
