# CI runners: runbook

[designed: owner, 2026-11-01, #493] goal2's checks run on two kinds of machine:

| Check | Where | What | When |
|---|---|---|---|
| **Linux**, **Windows** (`ci.yml`, `windows.yml`) | GitHub's hosted machines (free: goal2 is public) | the gate with `--batch-fast`: every test module, the layout stage's slow tests, none of the full batch's | a ready PR's push that changes more than docs, measurements and Markdown; main's pushes beyond those; a dispatch |
| **Linux slow**, **Windows slow** (`linux-slow.yml`, `windows-slow.yml`) | owner's self-hosted machines | `--slow`: every slow test and case | explicit dispatch for the integrated milestone or a justified investigation; never automatically on PR/push/weekly age |

## When checks run

[designed: owner, 2026-11-07] A ready PR's code push runs hosted Linux/Windows fast regression
and native scaling checks. Drafts and docs/measurement-only pushes retain the existing selector rules.
Run task-focused tests separately, including relevant slow cases. A skipped push does not cancel an
older run; a code push may supersede the same hosted check.

Full suites are manual. Dispatch **Linux slow** and **Windows slow** once on the integrated main
milestone candidate. The hosted workflows also offer an explicit slow dispatch for investigation,
but do not duplicate the same full validation there. There is no PR-driven or weekly full dispatch.

## Merging with these checks

A PR merges on its task-focused tests, the fast regression gate and hosted Linux/Windows checks.
Full self-hosted suites are milestone gates, not mandatory per-PR gates. After a fix rerun affected
checks; repeat a full suite only when the change or failure invalidates its coverage, explaining why.
Receipts may be reused for unchanged exercised inputs across metadata/ancestry changes, recording
both SHAs and identity/scope evidence ([validation.md](validation.md)). Known failures need their
existing explicit owner exception; a failed run is never reported as a pass.

If a runner is offline, milestone validation waits; that does not block unrelated focused PR merges.

## The runners

| Name | Machine | Label | Folder | Started by |
|---|---|---|---|---|
| `goal2-pc` | the owner's PC, Windows | `goal2-slow` | `C:\Users\diego\ghr-goal2` | `goal2-runner.cmd` in the Startup folder, at logon |
| `goal2-WINDOWS-BJ0PUMB-linux` | the owner's PC, WSL (Ubuntu) | `goal2-slow-linux` | `~/actions-runner/goal2` | systemd user service `goal2-runner` |
| `goal2-it13` | the owner's second computer (IT13), Windows, 6 gate jobs | `goal2-slow` | `C:\Users\diego\ghr-goal2` | `goal2-runner.cmd` in the Startup folder, at logon |
| `goal2-IT13-linux` | the owner's second computer (IT13), WSL (Ubuntu), 6 gate jobs | `goal2-slow-linux` | `~/actions-runner/goal2` | systemd user service `goal2-runner` |

Runners with the same label share one queue: two Windows machines check two PRs at once, and when one is
off the other takes the work. Check them on GitHub (Settings → Actions → Runners) or:

```bash
gh api repos/diegoami/goal2/actions/runners --jq '.runners[]|.name+" "+.status+" busy="+(.busy|tostring)'
```

## A machine shared by several runners or a working session

[designed: owner, 2026-11-03, #567] IT13 hosts both kinds of runner and a working session on 20 cores. Each gate
defaults to `min(8, cores)` jobs, so three at once overload it: one Windows slow bench test timed out that way (#417's
symptom, run 41628341112). On such a machine:

- **Each runner's gate is capped** by `GOAL2_GATE_JOBS` in the runner's `.env`, which the runner passes to every job.
  `check_premerge.py` takes its default from it and prints `game tests: <n> jobs (GOAL2_GATE_JOBS)`. Set it when
  installing or again later: `GOAL2_GATE_JOBS=6 bash tools/runner/setup-linux.sh` or
  `setup-windows.ps1 -GateJobs 6`. Then restart the runner when it is idle: a restart ends the job it is running.
- **A working session doesn't start a local gate while a runner on the same machine is busy.** A gate is
  `check_premerge.py`, `ci_gate.py run-tests` or a full unit suite, in either repository. Before starting one, check
  `gh api repos/diegoami/goal2/actions/runners --jq '.runners[]|.name+" busy="+(.busy|tostring)'`, and wait while one
  is busy. [designed: owner, 2026-11-04] The rule covers only starting a gate. A gate or suite that is already
  running is never stopped, whatever the runners are doing: stopping it throws its result away and frees nothing a
  runner is waiting for.
- Raising a job's priority does not help: Windows starts a child process at normal priority whatever its parent's
  (`CreateProcess` inherits only idle and below-normal), and it would only move the starvation onto the other runner.

## Adding a machine

Only a machine of the owner's that nobody else uses: every run pulls the original-game files from the owner's
Drive (CLAUDE.md rule 14). The scripts are in `tools/runner/`; each registers the machine with its label only,
verifies the runner's checksum, and sets it to start by itself. A registration token comes from `gh` logged in
as the owner (`gh auth login`), or from Settings → Actions → Runners → *New self-hosted runner* (valid one hour).

**Windows** (no admin needed):

1. `winget install Git.Git` and `winget install Python.Python.3.13` (the workflow runs `py -3.13` and Git Bash
   at `C:\PROGRA~1\Git\bin\bash.exe`; the script checks both).
2. In PowerShell:

   ```powershell
   iwr https://raw.githubusercontent.com/diegoami/goal2/main/tools/runner/setup-windows.ps1 -OutFile $env:TEMP\setup-goal2-runner.ps1
   powershell -ExecutionPolicy Bypass -File $env:TEMP\setup-goal2-runner.ps1               # token from gh
   powershell -ExecutionPolicy Bypass -File $env:TEMP\setup-goal2-runner.ps1 -Token <token> # or a pasted one
   ```

   `-Name` and `-Dir` override `goal2-<computer>` and `%USERPROFILE%\ghr-goal2`.

**Linux, or WSL**:

1. `git`, `curl`, `unzip`, systemd, `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`) and offscreen Qt's
   libraries (`sudo apt install libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3`); the script lists
   what is missing. WSL needs `systemd=true` in `/etc/wsl.conf`.
2. Then:

   ```bash
   curl -sSfL https://raw.githubusercontent.com/diegoami/goal2/main/tools/runner/setup-linux.sh | bash
   curl -sSfL https://raw.githubusercontent.com/diegoami/goal2/main/tools/runner/setup-linux.sh | GOAL2_RUNNER_TOKEN=<token> bash
   ```

3. On a machine that should run without anyone logged in: `sudo loginctl enable-linger $USER`.

Running a script again repairs the start-up and keeps the registration.

## Day to day

- **Offline runner**: the PC is off or asleep, the user logged off (Windows), or WSL stopped: Windows stops WSL
  some time after its last terminal closes. Start it again by logging in (Windows), opening a WSL terminal, or
  `systemctl --user start goal2-runner` (Linux).
- **"The runner registration has been deleted from the server"** right after a successful registration: the
  machine's clock is wrong. [confirmed: IT13, 2026-11-03] The clock was an hour behind while `timedatectl` said
  it was synchronized; the runner signs its session token with that clock and GitHub refuses it. Compare
  `date -u` with `curl -sI https://api.github.com | grep -i ^date`; fix the time on Windows (WSL follows it), then
  `systemctl --user restart goal2-runner`. The Linux service retries every 30 s by itself; the Windows listener
  exits and stays off until the next logon, or until `goal2-runner.cmd` in `shell:startup` is started again.
- **"Install goal2" fails 2 s in with the same `IncompleteRead(<n> bytes read, <m> more expected)` every time** on one
  runner while the others install fine: a truncated entry in that user's pip cache, which the job's fresh venv
  shares. [confirmed: #549, `goal2-it13`, 2026-11-03] Reproduce with the runner's Python in a fresh venv
  (`py -3.13 -m venv`, then `python -m pip install --upgrade pip`); if `--no-cache-dir` succeeds, it is the cache:
  `py -3.13 -m pip cache purge` (Linux: `python3 -m pip cache purge`), then rerun the failed job.
- **Logs of a run**: on GitHub (the run's page), and the uploaded `*-slow-evidence` artifact (the gate's log only).
- **The runner's own logs**: Windows `C:\Users\diego\ghr-goal2\_diag\`; Linux `journalctl --user -u goal2-runner`
  and `~/actions-runner/goal2/_diag/`.
- **Load**: a slow run uses up to 8 cores (`check_premerge.py --jobs`, default `min(8, cores)`) and a few GB of
  memory. The Windows and WSL runners share the PC's CPUs, as does a local gate.
- **Disk**: each runner keeps a checkout and the goal2-archaeology clone in its `w` folder; the job's Python and
  downloads are in its temp folder, removed after each run.
- **The Drive mirror**: each runner keeps a copy of the owner's Drive folder (about 600 MB) outside its work
  folder, which the checkout wipes: Windows `%LOCALAPPDATA%\goal2-runner\drive`, Linux
  `~/.cache/goal2-runner/drive`. Each run brings it up to date (`rclone sync`: only what changed, deletions
  too) and copies it into the run's `.cache/`. Deleting it is safe; the next run downloads it again in full.
- **Stop for a while**: Windows: end `Runner.Listener.exe` in Task Manager (it returns at the next logon);
  Linux: `systemctl --user stop goal2-runner`.

## Removing a machine

1. GitHub: Settings → Actions → Runners → the runner → *Remove*, or on the machine
   `config.cmd remove --token <token>` / `./config.sh remove --token <token>` in the runner's folder.
2. Windows: delete `goal2-runner.cmd` from the Startup folder (`shell:startup`), the runner's folder and
   `%LOCALAPPDATA%\goal2-runner`. Linux: `systemctl --user disable --now goal2-runner`, delete
   `~/.config/systemd/user/goal2-runner.service`, the runner's folder and `~/.cache/goal2-runner`.

## Security

- goal2 is public. A fork PR never runs the slow workflows (they have no PR event; dispatch requires repository write access), and every outside contributor's workflow run waits for the owner's approval (repository
  setting *Require approval for all outside collaborators*, set 2026-11-01).
- The runners run as the owner's user, without admin rights. They see the `GOAL2_RCLONE_TOKEN` secret during a
  run; the rclone configuration lives in the job's temp folder, not the user's profile.
- Nothing of the original game is uploaded: each workflow refuses an upload with an original-game extension.
