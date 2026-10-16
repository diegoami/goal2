# Environment

What a session needs so the main session can delegate. Everything here is optional: each missing
piece turns one delegate off. The scripts exit 3; the main session diagnoses the cause
and asks the owner before substituting a reviewer.

## Codex and Claude

[designed: owner, 2026-10-14] Codex starts at AGENTS.md and uses the shared process.
Claude's entrypoint, aliases, SessionStart hook and isolated Agent dispatch remain
available. Native Codex uses its own tools/sandbox; Claude hooks do not enforce
Codex calls. Use the harness-configured worktreeRoot for task worktrees.

`HARNESS_CLIENT=codex|claude` selects the implementation client. Without it,
nonempty CODEX_THREAD_ID or CODEX_SESSION_ID selects Codex, else legacy Claude
endpoint detection applies. Codex is family openai; conflicting family overrides
are refused. Pass HARNESS_CLIENT=codex to detached review units because they do
not inherit the interactive session markers. Keep provider keys in the unit's
environment, never logs. `switch-model.mjs --show` reports the detected defaults.

[confirmed: T23 / PR #54, 2026-10-14] The installed Linux OpenCode 2.0.28 rejects
the current harness's `run --dir` and `--variant` flags before creating a session.
The existing 1.18.32 backup completed the GLM 5.3 Flash review (535 s). Where that
backup exists, select it per run without changing the default installation:

```bash
HARNESS_CLIENT=codex HARNESS_OPENCODE_EXE="$HOME/.opencode/bin/opencode.1.18.32.bak" \
  node tools/harness/review.mjs --pr <pr> --brief <brief> --issue <issue> \
  --apply-label --reviewer <owner-selected-model>
OPENCODE_BIN="$HOME/.opencode/bin/opencode.1.18.32.bak" tools/harness/peek.sh <session>
```

[confirmed: local 2.0.28 command help and
[official OpenCode v2 commands](https://dev.opencode.ai/v2/docs/cli/commands/)]
V2 selects effort as `provider/model#variant`, uses the working directory, and
exports via `opencode session export`. Its configuration uses ordered
`permissions` rules. [designed: T24] Allowing major version 2 is not proof of
compatible run/session/config/permission semantics; migration must preserve
the independent-review boundary and main-checkout configuration grants. This
task documents the differences and backup, without implementing a v2 adapter.

## On your desktop

Locally there is no network policy and no environment settings, and the session-start hook does
nothing. You need:
- Node 20 or later.
- `gh`, logged in (`gh auth login`). It needs no `GH_TOKEN`.
- OpenCode 1.18 (`opencode --version`), logged in to OpenCode Go (next section).
- Optional: the credential jail (`tools/harness/lib/jail.mjs`, #68), off by default. With
  `"jail": { "enabled": true }` in `harness.json` and bubblewrap installed on Linux or WSL
  (`sudo apt install bubblewrap`), reviewers run without your GitHub credentials; enabled where
  bwrap cannot run, the review hook and `review.mjs` print a warning. Off, only the guard stops a push.
- The other keys below, as user environment variables. On Windows, in PowerShell:
  `[Environment]::SetEnvironmentVariable("ELEVENLABS_API_KEY", "<key>", "User")`.
  Then restart the terminal and Claude Code, so they see it.

**In WSL** (Claude Code, or the desktop app, working in a WSL folder), use OpenCode's Linux binary.
OpenCode's own installer puts it in `~/.opencode/bin`; the release tarball `opencode-linux-x64.tar.gz`
works too. Avoid `opencode upgrade`, which may reach for the Windows npm. The `opencode` that WSL
finds on PATH is often the Windows npm shim under `/mnt/c`. That shim runs the Windows OpenCode,
which cannot use the run's Linux paths and survives the kill of a timed-out run: both real-OpenCode
tests failed through it. The runner skips the shim and falls back to `~/.opencode/bin/opencode`;
`HARNESS_OPENCODE_EXE` overrides both. WSL and Windows keep separate logins: log in from WSL.

**On Windows**, `npm install -g opencode-ai@1.18`.

Then run `npm test` in the harness repository. The tests against the real OpenCode run wherever
`opencode` is installed. Then do the first-session check at the end of this page.

## OpenCode Go

**History (the owner, 2026-10-11):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

The MiMo v2.6 reviewers are OpenCode Go's (`opencode-go/…`), a subscription. They are not OpenCode Zen's pay-per-token `opencode/…` models. Go comes from a console
(organisation) login, not from a key; `opencode auth login` and `OPENCODE_API_KEY` reach only Zen
(IC2 #551):
1. `opencode console login`, then approve the URL and code it prints in the browser;
2. `opencode models opencode-go` lists the models; without the login it lists none, although
   `opencode console orgs` still exits 0 ("No accounts found"). If a login lists none, run
   `opencode models --refresh`.

The login is stored in the database of OpenCode's data directory, not in `auth.json`. Another data
directory, another machine, WSL beside Windows, or a new cloud session each needs its own
`opencode console login`.

## OpenAI, for the reviewer

**History (the owner, 2026-10-11):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

The reviewer is GPT-5.6 Luna on the direct OpenAI route (`openai/gpt-5.6-luna`, L51), never a Luna
on Go (`opencode-go/…`): a third-party proxy behind Go's returned `Bad Request` in long agent loops
(L27). OpenAI is an ordinary OpenCode provider: log in once with `opencode auth login`, choose
OpenAI (a ChatGPT login or an API key), and check with `opencode models openai`. The login is kept in
`auth.json`, which the scripts copy into their own data directory (next section) whenever theirs is
missing or older. If OpenAI later asks for a new login, log in again in your usual OpenCode; the
next run copies it.

## Z.AI, for the GLM reviewers

**History (the owner, 2026-10-11):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

GLM-5.3 Flash, the default implementer (L42), and GLM-5.3, the first hard reviewer (L41), run on
Z.AI's coding plan (`zai-coding-plan/…`); both stay on watch (L35). Log in once with `opencode auth login` and choose Z.AI Coding Plan (an API
key; OpenCode also reads `ZHIPU_API_KEY`), then check with `opencode models zai-coding-plan`. The
key is kept in `auth.json`, which the scripts copy like OpenAI's. GLM-5.3-highspeed is refused by
the plan.

## Alibaba Token Plan and MiniMax, on watch

**History (the owner, 2026-10-11):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

Alibaba is usable (the owner lifted the ask-first gate, 2026-10-13). On an Alibaba quota or rate
error, stop and tell the owner, and do not retry: its monthly pool is small and is not monitored.

Registered 2026-10-05/06 (the owner), all on watch in `harness.json`, no chain seats. The key is the
env var `ALIBABA_TOKEN_PLAN_API_KEY` (or `MINIMAX_API_KEY`) from `~/.config/ai-keys.env` — never
`opencode auth login` for these (an `auth.json` entry overrides the variable). All probed
2026-10-06 19:39–19:40 (`switch-model.mjs --probe --dry-run`, answered; first probes 2026-10-05).
`opencode models <provider> --verbose` lists no effort ladders for these providers; the variants
below are the owner's live checks.

| Entry | Id | Variant | Heavy/light | Notes |
| --- | --- | --- | --- | --- |
| `ali-glm` | `alibaba-token-plan/glm-5.3` | low | heavy | GLM-5.3 on the monthly pool; no night discount; zai relief (and its 3x weekday-peak price from 8 Oct 2026) |
| `ali-qwen-max` | `alibaba-token-plan/qwen3.8-max` | low | heavy | new family; offers low, medium, xhigh |
| `ali-qwen-flash` | `alibaba-token-plan/qwen3.8-flash` | medium | light | offers low, medium, xhigh (no high); medium since 2026-10-06 (xhigh before) |
| `mimo-pro` | `opencode-go/mimo-v2.6-pro` | high | heavy | tested 2026-10-09 on implement, fix, review; MiMo is its own family |
| `mimo-flash` | `opencode-go/mimo-v2.6-flash` | high | light | tested 2026-10-09 on implement, fix, review |
| `mm-m3` | `minimax/MiniMax-M3` | thinking | heavy | offers only none and thinking; a new family, independent reviewer material |
| `mm-m2.7`, `mm-m2.7-highspeed` | `minimax/MiniMax-M2.7(-highspeed)` | — | light | no effort variants; a variant is ignored if sent |

Alibaba is one monthly pool for all its models (`curl -s localhost:8765/quota/alibaba`;
`pricing.discount_now` says whether the night discount is live, 22:00–08:00 UTC+8: qwen3.8 60% off,
`glm-5.3` none — prefer long alibaba runs while it is true). DeepSeek is usable on any route (the
owner lifted the blacklist, 2026-10-13). MiniMax has 5-hour and weekly windows
(`curl -s localhost:8765/quota/minimax`). Alibaba's Kimi and MiniMax models are Team-edition only
and fail; not registered.

Placements (the owner, 2026-10-09): the implementer chain runs `zai-glm-5.3-flash`, `mimo-flash`,
`mm-m2.7`, `ali-qwen-flash` (then Claude sonnet); the hard reviewer chain runs `zai-glm-5.3`,
`ali-glm`, `ali-qwen-max`, `mimo-pro`, `luna` (then Claude opus). `mm-m3` is the L38 heavy
escalation rung before the Claude fallback and the alternate for the Sol seat when openai is
exhausted. From 8 Oct 2026 `ali-glm` is the default GLM seat (zai's 3x weekday peak). From
9 Oct 2026 DeepSeek is blacklisted and MiMo replaces it on OpenCode Go. The lock bump to
`b8c6cde` awaits the owner's separate word.

## Quota: quota-tracker

**The harness no longer reads it** (the owner, 2026-10-11, CLAUDE.md "Choosing models"): `review.mjs` runs the model named whatever the quota, `lib/quota.mjs` and `choose.mjs` were removed, and no model question shows `/recommend`. The service stays useful to the user, and to the main session when a provider answers with a usage-limit error: then read `/quota/<provider>` and say when it is usable again.

Where the machine runs quota-tracker, a local service, it reports how much subscription quota is
left on each provider: `claude` (the main session and Claude agents), `openai` (Sol and Luna, via
OpenCode), `zai` (GLM-5.3 and GLM-5.3 Flash), `opencode_go` (MiMo v2.6) and `openrouter` (prepaid
credit). It is read-only, on
localhost, with no auth; results are cached 60 s, and `?refresh` bypasses the cache:
- `curl -s localhost:8765/quota`, or `/quota/<provider>` for one;
- `curl -s 'localhost:8765/recommend?tier=heavy'` (or `tier=light`): which model to use.
  `ranking` is best first, each row with `provider`, `model`, `command`, `score` (spare calls per
  day until the pool's reset; negative means the pool would run out before its reset at the current
  demand), `confidence` and `reasons`; `pick` is the first row; `skipped` lists the exhausted or
  nearly full providers, with why. OpenRouter scores 0 (prepaid); Alibaba is not ranked (occasional
  use only, in its discount hours). Right after the service restarts, `note` says the statistics
  are loading: retry after a minute or two. Do not rank by `/best` or `headroom_pct`: percentages
  are not comparable between providers, whose pools differ hugely in size, are monthly or weekly,
  and are partly used by Claude sessions running on them as their main model;
- `curl -s localhost:8765/avoid`: the providers out of quota, with when each is usable again.

Each provider has a `status`: `ok` (under 80% used), `low` (80% or more), `exhausted` (95% or
more: do not use it until `available_at` / `available_in`), `error` (it could not be checked;
`error` says why) or `not_configured`. `headroom_pct` is the percent left on its most-used window;
`windows[]` lists every limit with `used_pct` and when it resets. OpenRouter is prepaid: its
windows never reset, and `remaining_usd` is the balance. A model with a limit of its own is named
in its provider's `when_exhausted.usable_models`. Until 2026-10-09 GPT-5.6 Luna (the reviewer) ran
on a weekly pool of its own (`gpt-5.6-luna:7d`); that window is gone, and Luna is now a peer of
Sol in OpenAI's main pool. Read which pools exist from the windows the endpoint returns, not from
this page.

The models per provider, heavy and light:

| Provider | Heavy | Light |
| --- | --- | --- |
| claude | `claude --model opus` | `claude --model sonnet` |
| openai | `opencode -m openai/gpt-6.1-sol` | `opencode -m openai/gpt-5.6-luna` |
| zai | `opencode -m zai-coding-plan/glm-5.3` | `opencode -m zai-coding-plan/glm-5.3-flash` |
| opencode_go | `opencode -m opencode-go/mimo-v2.6-pro` | `opencode -m opencode-go/mimo-v2.6-flash` |
| openrouter | `opencode -m openrouter/<model>` | `opencode -m openrouter/<model>` |

GPT-5.6 Luna, the reviewer (L51), uses OpenAI's main quota like Sol. When OpenAI is `exhausted`,
Luna alone can still run while `/quota/openai`'s `when_exhausted.usable_models` lists
`gpt-5.6-luna` (the harness's L65 row).

If `curl -sf localhost:8765/health` fails where the service is installed:
1. `systemctl --user restart quota-tracker`, wait a few seconds, and check `/health` again.
2. If systemctl says `Failed to connect to bus`, the user's systemd instance is not running: ask
   the user to run `sudo loginctl enable-linger $USER`, then retry step 1.
3. If it still fails, read `journalctl --user -u quota-tracker -n 50` and tell the user what it says.
4. To run it without the service: `cd ~/projects/models_quota_tracker && uv run quota-tracker serve`
   in the background (it stops when the session ends).

`review.mjs` does not ask the service (above). *Superseded: the quota check before a chain ran
(L52), and `HARNESS_QUOTA_URL`.*

Never read or edit `~/.config/quota-tracker/config.toml`: it holds account tokens. A provider in
`error` over an expired cookie or token goes to the user, since renewing it needs their browser or
login. Where the service is not installed, go on without it, and count a usage-limit error as
`exhausted`.

## A shared machine

Other projects' sessions run on the same machine. Stop only processes you started, by PID; name
this repository's systemd units `goal2r-<name>`, so they never collide with another project's.

## OpenCode's agent permissions

`.opencode/agents/reviewer.md`, the one OpenCode agent since 2026-10-11 (the implementer agent went
with `implement.mjs`), allows `/tmp` and `/tmp/*` (PR 119, the owner, 2026-10-11: a model's scratch
file in `/tmp` was refused and the run ended with nothing posted) and the goal2-archaeology checkout (`tools/check_provenance.py` reads it).
The grant was lost twice, once by a harness bump; `tests/test_agent_permissions.py` now fails CI
without it, and `harness.lock` lists the file as adapted: carry it over on every bump. A run that
dies on another rejected path is fixed by widening the grant here, never by re-briefing.

## The scripts' own data directory

`review.mjs` and `switch-model.mjs` run OpenCode with a data directory of their own, so OpenCode's
desktop app (2.x) can never migrate their database to a schema the 1.x CLI cannot read (IC2 #540,
"no such column: project_id"). It is `~/.local/share/harness-opencode`, with `data/`, `cache/` and
`state/` set as `XDG_DATA_HOME`, `XDG_CACHE_HOME` and `XDG_STATE_HOME` for OpenCode's processes only.
`HARNESS_OPENCODE_HOME` moves it (a relative path is made absolute). `auth.json`, the API-key
providers, is copied in from `~/.local/share/opencode` (or `HARNESS_OPENCODE_AUTH_SOURCE`) when the
copy is missing or older; it is never read or printed.

Go's login does not travel with `auth.json`, so log in once for this directory. In bash (WSL, Linux):

```bash
XDG_DATA_HOME="$HOME/.local/share/harness-opencode/data" opencode console login
```

In PowerShell (Windows), in a new window afterwards:

```powershell
$env:XDG_DATA_HOME = "$HOME\.local\share\harness-opencode\data"; opencode console login
```

Check it with the same `XDG_DATA_HOME` and `opencode models opencode-go`. Before any run, each script
checks that OpenCode lists its model there; if not, it exits 3 with the command that fixes it (this
one for Go, `opencode auth login` for OpenAI), and nothing is billed. The scripts never change their
own process's environment, only that of the OpenCode processes they start, so nothing needs
restoring afterwards.

## Keys

In **Claude Code on the web**, set these in the environment's settings: the cloud environment menu
in the session's title bar, then **Edit**, then the environment variables (or API credentials, where
that section is offered). A new session picks them up. On **your machine**, set them in your shell.
Never paste a key into a chat, and never commit one.

| Variable | Used by | Without it |
| --- | --- | --- |
| `OPENCODE_API_KEY` | OpenCode Zen's `opencode/*` models, if `harness.json` names any. The default models are Go's, which need `opencode console login` instead (above) | nothing, while `harness.json` names only Go models |
| `OPENROUTER_API_KEY` | Jev, through OpenRouter (`jev.mjs`); also OpenCode's `openrouter/*` models, if `harness.json` names any | `jev.mjs` exits 3; the main session decides every item itself |
| `ELEVENLABS_API_KEY` | ElevenLabs: speech, voices, sound effects, music (`/delegate`, `models.mjs elevenlabs`) | no generated audio; the main session says so |
| `GH_TOKEN` | `gh`, inside the tools and inside OpenCode's runs: finding the PR, `gh pr create`, posting a review, labels | the scripts cannot find or post to PRs |
| `ANTHROPIC_BASE_URL` (with `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`) | the orchestrator itself: unset or Anthropic's for Claude; Z.AI's for GLM, MiniMax's, or Moonshot's for Kimi when Claude's tokens are out. `review.mjs` and `switch-model.mjs` read the session's family from it (CLAUDE.md "Choosing models" rule 0); pass it to a review's unit with `-E` | the session is Claude |
| `HARNESS_CLIENT` | [designed: T24] selects codex or claude explicitly; pass it to detached review units | Codex session markers select codex, otherwise legacy Claude detection |
| `HARNESS_SESSION_FAMILY` | overrides the Claude/provider family when the endpoint is unknown; a conflicting Codex family is refused | an unknown endpoint refuses to review until it is set |

For `GH_TOKEN`, use a fine-grained token limited to the project's repository, with read and write on
Contents, Pull requests and Issues.

OpenCode reads both `OPENCODE_API_KEY` and `OPENROUTER_API_KEY` from the environment (checked with
`opencode auth list` on 1.18.33), so those need no `opencode auth login`. Go is the exception: without
its console login, `review.mjs` exits 3: log in and run again.

## Network

A cloud environment's network policy must allow:

| Host | For |
| --- | --- |
| `opencode.ai` | OpenCode's own providers (Zen, Go) |
| `openrouter.ai` | Jev, OpenRouter models, image generation |
| `api.z.ai` | the GLM reviewers, GLM-5.3 and GLM-5.3 Flash |
| `api.elevenlabs.io` | ElevenLabs |
| `registry.npmjs.org` | installing OpenCode |
| `api.github.com`, `github.com` | `gh` and git |
| the Ubuntu package archive | installing `gh` with apt |
| `models.dev` | OpenCode's model list. Optional: runs worked without it, but allow it if `opencode models` shows stale ids. |

## The session-start hook

`.claude/hooks/session-start.sh`, registered in `.claude/settings.json`, runs at the start of every
session on the web (and does nothing locally). It:
- installs `opencode-ai@1.18` with npm and `gh` with apt, if they are missing;
- reports which keys are set, as the session's first context.

It never fails the session. OpenCode is pinned to the 1.18 line because the runner's assumptions were
checked against it:
- the `run` flags;
- `session list --format json`, with `id`, `title`, `directory`, `created` and `updated`;
- `export`, whose `info.agent` names the agent that actually ran.

Change the pin only after running the tools against the new version.

On your machine, install the same things yourself: `npm install -g opencode-ai@1.18`, `gh`, and
Node 20 or later.

## First session: check it works

1. The hook's report shows every key `set`, and no setup notes.
2. The hook's report says OpenAI is logged in (the default reviewer), and `opencode models openai`
   lists `harness.json`'s `luna` id. If an id differs, edit `harness.json`.
3. Jev: put two lines such as `{"id": 1, "state": {"title": "Game crashes on load"}}` in
   `items.jsonl`, then run `node tools/harness/jev.mjs ask --decision breaks-play --in items.jsonl`.
   It should print `asked 2 of 2`.
4. OpenCode: run `/run-task` on a small `fix`, and watch the first review: the tail of its log and
   the posted review.

## Local pre-merge validation

[designed: owner, #127, 2026-10-16] With Python 3.12 or later, Node 20 or later
and git installed, run from the clean implementation checkout:

```bash
python3 tools/check_premerge.py --expected-head <reviewed-sha>
```

Use the full reviewed commit SHA. The command refuses a different HEAD, dirty
tracked files, invalid lock hashes, tracked original/session assets or a failed
child check. Existing untracked user files and ignored caches/notes are retained.
It runs links/JSON, harness self-tests, client tests and permission/merge/validator
regressions without GitHub API access, original-game assets or an archaeology
checkout. Task-specific tests, fidelity/browser/provenance checks and independent
review remain separate requirements as applicable to the task.

Actions has only a manual `workflow_dispatch` trigger and runs the same command
on its checked-out SHA. It is optional independent verification; billing or an
absent hosted run does not block a locally validated merge. No self-hosted runner
or account billing change is required.

## Optional original-match runtime

[designed: T62] `python3 -m pip install '.[watched]'` installs tested Unicorn2.1.4;
`'.[desktop,watched]'` installs Qt and the runtime together. Quick play remains
usable without this optional dependency or its watched resources. For runtime
tests/verified assets and exact upstream reproduction, follow
[watched-kit-acceptance.md](watched-kit-acceptance.md). This installs the kit only;
application watched controls are later tasks. Full runtime tests need the verified
images and archaeology source described there; do not treat skipped upstream
original tests as accepted evidence.
