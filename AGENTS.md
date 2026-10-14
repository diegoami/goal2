# goal2 — Codex entrypoint

[designed: T24] These dispatch instructions apply to Codex implementation
sessions. OpenCode review sessions follow their read-only reviewer agent and
supplied review brief; they do not implement or invoke the dispatch steps here.

[confirmed: [official OpenAI AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md)]
Codex reads repository AGENTS.md instructions.

[designed: owner, 2026-10-14] Read [CLAUDE.md](CLAUDE.md) for the shared numbered
rules, [docs/process.md](docs/process.md) for the task/PR loop, and
[docs/environment.md](docs/environment.md) for setup. Claude Code continues to
load CLAUDE.md and its existing skills/hooks. This file adapts client-specific
dispatch; it does not replace the shared evidence, provenance or merge rules.

1. Codex or a native Codex subagent implements. Use the current native Codex model
   by default; the Codex implementer default is `session` in harness.json.
   Ask the owner to choose the implementer/model before starting each new task,
   and wait for the answer; requesting a task alone does not select a model.
   Once chosen for that task, keep the choice for its implementation/rework.
2. Select/record a task, follow its scope and Done-when, and work in an isolated
   task branch/worktree under harness.json's `worktreeRoot`. Resolve it with
   `repoPaths` in tools/harness/lib/common.mjs; never use /tmp for task worktrees.
   For a native Codex subagent, the main session prepares its worktree before
   dispatch; do not assume the dispatch tool created one and pastes the full task plus process §4 contract.
   The main session may implement directly without a subagent.
3. Follow the shared run-task procedure in
   [.claude/skills/run-task/SKILL.md](.claude/skills/run-task/SKILL.md), using its
   Codex dispatch branch. Keep ignored RUN-NOTES.md, prove regressions, validate,
   commit/push, open a draft PR and mark it ready before asking for review.
4. Ask the owner which OpenCode model reviews only after a concrete PR exists;
   record the choice and run tools/harness/review.mjs. Codex is family `openai`,
   so OpenAI reviewers are ineligible. Do not choose or substitute a reviewer.
5. Detached harness jobs must carry `HARNESS_CLIENT=codex` (and required provider
   keys), because user services do not inherit Codex session markers. Native
   shell tools are detected via CODEX_THREAD_ID or CODEX_SESSION_ID; conflicting
   family overrides fail closed. Do not print credentials.
6. Claude's PreToolUse hooks are not installed on Codex. Follow the shared no-stash,
   no-force-push, no-worktree-removal and main-session-only merge rules; retain
   Codex's native approval/sandbox controls. This entrypoint is instruction,
   not a claim of hook enforcement. Never weaken reviewer permissions.
7. After approval and pre-merge checks, squash-merge under the shared process;
   preserve task worktrees and file non-blocking follow-ups. Status stays in
   GitHub labels, not documents. Questions alone do not authorize edits.
