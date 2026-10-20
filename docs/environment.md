# Environment

> [designed: owner, 2026-10-20] Worktrees are no longer required and any model family may review
> (CLAUDE.md "Cloud-viable workflow"): read "review worktree" below as the checkout at the PR head,
> and the family checks as lifted. Original-game files come from the Google Drive folder
> ([artifacts.md](artifacts.md)); milestone reviews from [milestone-review.md](milestone-review.md).

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

[designed: T72; confirmed: measurements/T72, tests/opencode_workflow.test.mjs]
Routine review and peek use the installed current OpenCode (audited native2.0.28),
without a backup override. V2 uses the real working directory, `provider/model#variant`
and native ordered permissions; the harness starts its own `serve --stdio` execution
server and polls effective model/agent readiness before any generation. The trusted
launching checkout's reviewer overrides cwd config while global provider discovery
is preserved. A stored agent string alone is insufficient proof of its permissions.
The guard pins the audited native binary bytes/version; a newer or different build
fails before billing until its native enforcement is revalidated. Production wrappers
are refused; only the exact hashed nonbilling simulator is admitted inside Node tests. The v2 runner
requires an explicit trusted agentFile; it never defaults to the PR worktree.
Native model-series family labels are compared through the existing policy lineage
classifier while raw advertised labels remain in receipts; no route is substituted.

[designed: T72 rework1; confirmed: clean-install evidence under measurements/T72/rework1]
Each fresh author/reviewer checkout needs the exact local WASM grammar dependencies.
Setup is explicit; offline validation never fetches or installs them:

```bash
npm ci --prefix tools/harness/opencode-guard --ignore-scripts --no-audit --no-fund
node tools/harness/check-opencode-guard.mjs
HARNESS_CLIENT=codex node tools/harness/review.mjs --pr <pr> --brief <brief> \
  --issue <issue> --apply-label --reviewer <owner-selected-model>
tools/harness/peek.sh <session-or-run.json-or-log> -n 20
node tools/harness/preflight-opencode.mjs --out .cache/opencode-preflight
```

[designed: T72] Preflight is nonbilling: effective reviewer/MiniMax-M3 thinking,
owned empty session/list/export/peek and zero usage. It does not prove model access
or active-generation cancellation. The optional native probes below exercise
real dispatch/cancellation with an explicitly selected loopback fake provider;
reported fake token counts are simulated, and no external model call occurs:

```bash
node tools/harness/probe-opencode-guard.mjs --out .cache/opencode-native-proof
node tools/harness/probe-opencode-guard.mjs --active-cancel --out .cache/opencode-native-proof
node tools/harness/probe-opencode-plugins.mjs --out .cache/opencode-native-proof
```

[designed: T72] Review uses the exact owner-selected model;
missing profile/effort/permissions fail before billing, without substitution.

[confirmed: pinned v1/v2 sources and native dispatch evidence under measurements/T72/rework1]
Native2.0.28 stopped scanning file operands of shell commands such as `cat`, `rm`,
`cp` and `mv` for external-directory approval. A trusted local plugin restores
that legacy grammar-based check using the final native shell and cwd. Inside-worktree
paths and the exact existing tmp/research grants remain usable; other static file
operands tighten the existing shell request to `ask`, which native noninteractive
execution rejects. Native mutation denies remain intact. Both majors still give
allowed shell commands host authority; this static check is not an OS filesystem jail.

[designed: T72 rework1] A source-target native policy blocks external plugins before
import, while a frozen per-run configuration snapshot prevents later hook reloads.
A safe configuration survey and checks on both actual servers reject external
executable plugins and higher-authority plugin-allow policies before generation.
Native builtin disables are preserved; normal global provider metadata and native
v2 login storage remain. An external provider/auth plugin requires explicit audit;
the runner never silently drops it or substitutes a provider. This does not isolate
arbitrary trusted host/global code. The supported configuration and tested native
adversarial source/reload cases are documented in
[the guard contract](../tools/harness/opencode-guard/README.md).

[designed: T72 rework1] Retained transcripts, exports, finals and returned text redact
only the known short-lived owned-server transport nonce if echoed. Receipts disclose
that redaction and hash the resulting safe bytes; all other transcript content remains.
Never publish credential-bearing historical raw exports; preserve originals privately
and make a separate safe derivative when needed.

[confirmed: T23/PR54 historical failure; T72a pinned fixtures] The old v1 `--dir`,
`--variant` and top-level `export` commands fail on v2. Explicit v1 compatibility
remains available with an intentionally selected v1 binary and the untouched legacy
harness DB. Retain historical binaries and receipts; routine v2 needs no backup:

```bash
HARNESS_OPENCODE_EXE="$HOME/.opencode/bin/opencode.1.18.32.bak" \
  tools/harness/peek.sh <legacy-session> --major 1
```

## Optional direct Claude CLI review

[designed: T73; confirmed: measurements/T73/preflight.md and native-proof.md]
OpenCode remains the default. Direct Claude is an explicit reviewer backend for
an owner-selected independent Claude-family reviewer, never an implementer or
fallback. The audited Linux/WSL native build is2.1.292, SHA256
`a967e7b1d8b4e47ee421d5433027880347952b0c0857abf880e2c942a4ec93b3`.
A different executable/build fails closed pending revalidation. The selected
entry is `claude-sonnet`, actual model `claude-sonnet-5-5`, effort `medium`.

[designed: T73] Main prepares a trusted JSON permission file **outside the PR's
review worktree**, in the launching checkout or another owned evidence directory.
It contains exactly `commands` and `directories`. Commands are required exact
checks, including a substantive negative control; supported ` && ` compounds
receive separate native grants for their constituents. Include the exact
isolated-Python script invocation where needed. Direct commands do not grant
wildcards. The two ordinary external grants are `/tmp` and the physical
`goal2-archaeology` checkout. Example (replace paths and the full SHA):

```json
{
  "commands": [
    "git rev-parse HEAD",
    "node --test tests/claude_review.test.mjs && git diff --check",
    "python3 -I /trusted/t73-control.py"
  ],
  "directories": ["/tmp", "/home/owner/projects/goal2-archaeology"]
}
```

[designed: T73] After a clean validated ready PR, main launches the selected
real review and any same-reviewer follow-ups until accepted (CLAUDE.md rule 7),
each with a fixed UUID and full pinned head in its brief:

```bash
HARNESS_CLIENT=codex node tools/harness/review.mjs --pr <pr> --brief <brief> \
  --issue <issue> --apply-label --backend claude --reviewer claude-sonnet \
  --claude-policy /trusted/policy.json --claude-session-id <uuid> \
  --claude-negative-control 'python3 -I /trusted/t73-control.py'
```

[designed: T73] For checks requiring offline grammar dependencies, main first
creates and preserves an isolated review worktree at the full PR head under
`worktreeRoot`, makes its physical `.cache/tmp`, and runs the explicit
`npm ci --prefix tools/harness/opencode-guard --ignore-scripts --no-audit --no-fund`
setup there. Add `--claude-worktree /absolute/prepared/review-worktree` to use
that staged checkout. The entrypoint verifies its shared repository, location,
detached HEAD, clean tracked files and exact PR head before dispatch. No watcher is necessary.
The tracked `node --test --test-name-pattern=deletion tests/claude_review.test.mjs`
is an available substantive negative-control command; using it avoids staging
an extra helper. Its saved-byte mutations target policy and protocol guards;
workflow, scope and lifecycle have behavioral tests. Put that exact command in
policy and `--claude-negative-control`.

[designed: T73] Optional repeated `--claude-canary 'git push T73-NO-REMOTE'`
identifies deliberately forbidden calls; use only an inert owned target. Their
native denial must be observed exactly. Every other tool denial/error blocks
acceptance, including a required check even if the CLI exits0. A premerge command
in the actual policy must use the full reviewed SHA; the example negative-control
script is separately prepared, inspected and granted by main.

[designed: T73] Production reconstructs the child environment, forwarding ordinary
locale/path/home and existing native OAuth token only. Provider API/auth tokens,
endpoints/model aliases, proxy/host overrides and user/project/local settings
are excluded. Native OAuth storage stays native: no authfile is read/copied by
the harness. API-key-helper-only setups are unsupported by this profile and fail
closed; do not clear an endpoint while retaining its provider-specific token.

[confirmed: measurements/T73/native-account-projection.json; designed: T73]
A separate owned model-free control process verifies native account provider,
applied model/effort, exact effective trusted policy and every native live rule.
Its bounded stdin pipe carries only initialize/settings/rules/hooks requests;
it is a **control lease**, closed and reaped before actual generation. Raw
settings/account/env/hook replies never leave process memory; sanitized hashes,
rule-source metadata and the firstParty provider field are retained. Actual
review input is DEVNULL, with a short positional pointer to the retained full
brief, separated from variadic directory flags by an explicit `--` terminator.
The native loopback fixture uses this same production argument builder without
a trailing option masking positional parsing (measurements/T73/argv-regression.md).
It gets a distinct fixed UUID, its own process group and startup/idle/total
deadlines. Cancellation kills only owned descendants, including after leader exit.

[designed: T73] Mandatory managed startup hooks remain respected and may execute
before projection. A point-in-time projection does not freeze native policy
refresh between processes; policy drift or native refusal prevents acceptance.
Native file/tool grants and exact shell grants are not an OS jail: explicitly
allowed tests/Python scripts retain host authority and must be trusted. Safe mode
does not prove that a flag-defined hook gate ran; this transport claims no such
gate. The trusted policy/source comes from the launcher, never the PR.

[designed: T73] Local base/head commits drive complete rename-aware inventory and
24k-character diff chunks, retained with prompt, complete raw review stream/tool
results, stderr, complete final and hashed receipt under `.cache/claude-review-*`
in the preserved review worktree. Complete native result and final assistant text
must agree. Missing/truncated results fail; never buy another generation to repair
formatting. The parser also requires executed tree/check commands, every DW,
substantive-control accounting, per-file `COVER Fnnn: audited ...` lines and exact
PR/head/base identity. Main audits the complete native evidence and owns posting
and exact-head merge checks. Standalone `peek.sh` remains the OpenCode reader;
read the Claude receipt's full final/raw paths directly.

[confirmed: measurements/T73/native-proof.md] Offline regressions and the optional
synthetic native fixture are:

```bash
node --test tests/claude_review.test.mjs
node tools/harness/probe-claude-permissions.mjs --out .cache/t73-native \
  --archaeology /absolute/path/to/goal2-archaeology
```

[designed: T73] The second command uses scripted loopback responses and synthetic
credentials in a fresh own-cache CLI config directory. It is not Sonnet access
or a review; it proves native compound/Python/research/tmp permission behavior
and an intentional denial without external model inference. No extra paid smoke
is part of setup. Preserve failed and successful receipts.

## On your desktop

Locally there is no network policy and no environment settings, and the session-start hook does
nothing. You need:
- Node 20 or later.
- `gh`, logged in (`gh auth login`). It needs no `GH_TOKEN`.
- Installed current OpenCode 2 (`opencode --version`), with the selected provider configured (v2 data setup below).
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

[designed: T72] Install the current native v2 CLI using the
[official setup instructions](https://opencode.ai/v2/docs/). Retain existing v1 binaries;
the hook reports version mismatches instead of installing/downgrading a binary.
The native guard byte pin is currently the measured Linux/WSL2.0.28 build; another
platform/build needs source and enforcement revalidation before v2 review activation.

[designed: T72] Run the offline premerge checks and the nonbilling preflight above.
Only an owner-authorized review calls an external model; offline tests use protocol
stubs, and the optional native probes use an explicit loopback deterministic fake.

## OpenCode Go

**Historical v1 setup (the owner, 2026-10-11; v2 setup below):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

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

**Historical v1 setup (the owner, 2026-10-11; v2 setup below):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

The reviewer is GPT-5.6 Luna on the direct OpenAI route (`openai/gpt-5.6-luna`, L51), never a Luna
on Go (`opencode-go/…`): a third-party proxy behind Go's returned `Bad Request` in long agent loops
(L27). OpenAI is an ordinary OpenCode provider: log in once with `opencode auth login`, choose
OpenAI (a ChatGPT login or an API key), and check with `opencode models openai`. The login is kept in
`auth.json`, which the scripts copy into their own data directory (next section) whenever theirs is
missing or older. If OpenAI later asks for a new login, log in again in your usual OpenCode; the
next run copies it.

## Z.AI, for the GLM reviewers

**Historical v1 setup (the owner, 2026-10-11; v2 setup below):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

GLM-5.3 Flash, the default implementer (L42), and GLM-5.3, the first hard reviewer (L41), run on
Z.AI's coding plan (`zai-coding-plan/…`); both stay on watch (L35). Log in once with `opencode auth login` and choose Z.AI Coding Plan (an API
key; OpenCode also reads `ZHIPU_API_KEY`), then check with `opencode models zai-coding-plan`. The
key is kept in `auth.json`, which the scripts copy like OpenAI's. GLM-5.3-highspeed is refused by
the plan.

## Alibaba Token Plan and MiniMax, on watch

**Historical v1 setup (the owner, 2026-10-11; v2 setup below):** this section's seats, chains and placements no longer pick a model: the main session or a Claude agent implements, and `harness.json`'s `reviewer.default` reviews unless the user names another (CLAUDE.md "Choosing models"). Kept for the logins and probes.

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

[confirmed: measurements/T72/native-storage primary source; designed: T72]
`HARNESS_OPENCODE_HOME` (default `~/.local/share/harness-opencode`) contains distinct
major roots. Legacy v1 `data/`, `cache/`, `state/` and its existing receipt DB stay
intact. V2 persists native provider credentials and sessions only in
`v2/data/opencode/opencode.db`; it sets `OPENCODE_DB` explicitly so an inherited
path cannot migrate the legacy DB. Each invocation has its own cache/state, stdio
lease, protocol marker and receipt index under `v2/runs/run-*`. Multiple private
servers may read the same v2 DB; they own only their execution and session.

[confirmed: same primary source] Credentials and sessions share the native database;
fresh data on every run would lose one-time logins, even when a model catalogue
still lists the provider. V2 never copies `auth.json` or reads/exports credentials.
Environment API keys and ordinary global provider configuration remain available.
For native login providers, connect once to the v2-only root (never pass secrets
on the command line; use the native interactive form):

```bash
XDG_DATA_HOME="$HOME/.local/share/harness-opencode/v2/data" \
  OPENCODE_DB="$HOME/.local/share/harness-opencode/v2/data/opencode/opencode.db" \
  opencode auth login --standalone <integration>
```

[confirmed: native-storage/auth-login-help.txt] V2 `auth login` selects an integration
and supports a private `--standalone` server. With a custom harness root, substitute
that same absolute root in both paths. This is setup for the native v2 DB, not a
credential migration. The historical v1 path/copy behavior above is explicit v1
compatibility only. A catalogue projection proves advertised metadata, not login
validity or a billed provider request.

[designed: T72; confirmed: workflow tests] The log names a `run.json` manifest with
binary/source/policy identities, session/cwd/model/agent, source hashes, phase,
usage/duration and retained file paths. Raw stdout/stderr, full export response,
unwrapped export, full assistant/final text, brief and selected effective profile
are retained on success and failure before closing the owned server. Generated
transport nonces are redacted. Review worktrees remain intact. `peek.sh run.json`
works after completion; bare session IDs resolve through the receipt index. Live
peek uses private standalone export against this v2 DB, never the shared service.
V2 resume requires its exact retained manifest and matching session/cwd/model/agent.

[designed: T72] Cancellation interrupts only the owned session at the owned endpoint,
closes its stdin lease, then bounds cleanup of its own process groups, including
descendants after leader exit. It never stops a shared service. Complete final
exports decide completion/rejections/usage; transient console output cannot approve.
This transport migration does not resolve the separate formatting-parser #147 or
broader retention #142 requests.

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

[designed: T72] `.claude/hooks/session-start.sh` reports the current CLI version and
key presence for remote Claude sessions; it does not replace the installed CLI.
Install the current native v2 binary, `gh` and Node 20+ using their supported setup.
Keep the historical v1 binary when explicit compatibility is needed.

## First session: check it works

[designed: T72] Check `switch-model.mjs --show` for client/family/defaults, choose the
reviewer explicitly, run the nonbilling preflight above, then use one authorized
review of a validated PR. Follow its printed session ID or manifest with `peek.sh`.
Do not add a paid probe to a review whose one live run is already the acceptance smoke.

## Large reviewer command outputs

[designed: native MiniMax review evidence, 2026-10-18] Stage complete PR inventories
and diffs in the actual review checkout's ignored `.cache` before its fixture-ready
marker. Redirect large git output to those owned files and read bounded sections.
Native OpenCode may spill oversized stdout under its private data root, outside
the reviewer's exact permitted directories. A denied spill-file read invalidates
the review even when its tests and final verdict approve. Do not grant the broad
private data root or waive the denial; make the complete required artifact
available inside the permitted checkout and continue with the selected reviewer.
Preserve the failed export/final and distinguish recreated deterministic PR
inventory from the lost backend spill bytes. The serial validation driver creates
its own output directory; do not pre-create it or remove existing proof logs.

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

## Local validation caches across reboots

[designed: owner reboot cleanup, 2026-10-17] Keep reusable validation tools and
original fixtures in ignored repository caches rather than `/tmp`. On this machine,
Playwright is under `.cache/validation-tools/browser-tooling`; verified original
fixtures are under `.cache/validation-assets/original-match-fixtures`. Stage the
required fixtures into each task/review worktree's own `.cache` before testing.
These caches contain no provider credentials and are never committed.

[designed: same cleanup] For browser checks, export absolute paths rooted in the
main checkout:

```bash
export PLAYWRIGHT_MODULE="$PWD/.cache/validation-tools/browser-tooling/node_modules/playwright/index.js"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/validation-tools/browser-tooling/browser-cache"
```

[designed: T72 and owner cleanup] Create a physical `.cache/tmp` in the checkout
running a check and set `TMPDIR` to its absolute path. Detached services need this
explicitly in their environment. Preserve task/review worktrees and Windows saves;
remove only verified owned temporary files after their readers finish.

## Optional original-match runtime

[designed: T62] `python3 -m pip install '.[watched]'` installs tested Unicorn2.1.4;
`'.[desktop,watched]'` installs Qt and the runtime together. Quick play remains
usable without this optional dependency or its watched resources. For runtime
tests/verified assets and exact upstream reproduction, follow
[watched-kit-acceptance.md](watched-kit-acceptance.md). This installs the kit only;
application watched controls are later tasks. Full runtime tests need the verified
images and archaeology source described there; do not treat skipped upstream
original tests as accepted evidence.

## Original-game research handoffs

[designed: owner,2026-10-18] Main may file focused exploration or decompilation
issues in [goal2-archaeology](https://github.com/diegoami/goal2-archaeology) when a
rebuild task needs original-game evidence. Link the goal2 task, state the precise
question, existing findings/source pin, relevant binary addresses and reproducible
inputs/seeds where known, and request the evidence/artifact that resolves it.
Track the upstream response and link confirmed findings back before encoding the
behavior here. Continue independent work while research is pending. Original
assets remain private and vendored engine files follow the existing deliberate
re-vendor/provenance rule.

## Native Windows playable launcher on this machine

[confirmed: owner-authorized deployment, 2026-10-19; [receipt](evidence/windows-modern-demo/2026-10-19/deployment.json)] Double-click `C:\Users\diego\projects\goal2-exe\Start-goal2-modern.cmd` for the accepted football GUI and animated original-match pitch. This native Windows build uses immutable source `5c26616917d19a77a0e548a0baa2a3997112c477` in `.goal2-releases\accepted-5c266169`, the existing Windows Qt environment, and release-local pygame-ce2.5.8/Unicorn2.1.4. Its verified original reference image stays in the private release cache. Saves are in `.goal2-modern-saves\desktop.g2save`; the launcher resumes that file when present. Confirm selection in **Squad & tactics**, then choose **Fixtures & results → Watch original friendly** for an eligible friendly.

[confirmed: same receipt and native-demo.png] The deployment smoke used actual Windows Qt6.12.0, received rendered frameACK33, then cancelled and verified owned children/widgets cleanup and callbacks[]. All four existing resource/save/legacy-launcher hashes remained unchanged. The launcher pins this accepted source release. Task/review worktrees use separate runtime directories. Preserve both launcher files, release directories and save directories.

## Isolated Linux Qt validation displays

[designed: T79 and Windows-playtest follow-through,2026-10-19] For actual Linux
GUI checks, use a privately owned Xvfb display at2880×1800 and its own window
manager. Set `QT_QPA_PLATFORM=xcb` explicitly: starting Xvfb does not override an
inherited Wayland platform selection. When using staged xcb libraries on this
machine, `LD_LIBRARY_PATH` points to the running checkout's
`.cache/xcb-libs/extracted/usr/lib/x86_64-linux-gnu`. Give the owned window manager
private `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `XDG_RUNTIME_DIR`, and keep
`TMPDIR` inside the checkout cache. Do not operate the user's desktop or terminals.

[derived: T79 retained geometry probes] A1920×1440 test display can constrain
Qt at scale2 and prevent the required900×640 logical client size from settling.
Verify actual platform, ratio, available geometry, focus and ancestor clipping;
requested environment variables or resize calls alone do not prove them.
Infrastructure focus/geometry failures stay distinct from product regressions.
