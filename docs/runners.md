# CI runners: runbook

[designed: owner, 2026-11-01, #493] goal2's checks run on two kinds of machine:

| Check | Where | What | When |
|---|---|---|---|
| **Linux**, **Windows** (`ci.yml`, `windows.yml`) | GitHub's hosted machines (free: goal2 is public) | the gate with `--batch-fast`: every test module, the layout stage's slow tests, none of the full batch's | a ready PR's push that changes more than docs, measurements and Markdown; main's pushes beyond those; a dispatch |
| **Linux slow**, **Windows slow** (`linux-slow.yml`, `windows-slow.yml`) | the owner's own machines (self-hosted runners) | on a PR, the gate's own choice: slow tests only in the modules the change can reach (`tools/slow_reach.py`, #505); on a dispatch and every night at 01:00 UTC on main, `--slow`: every slow test, every case | a ready PR's push that changes what the slow tests guard (`SLOW_PATHS` in `tools/check_premerge.py`; not the CI plumbing); a dispatch; nightly on main. Never for a fork PR |

## When checks run

- **A draft PR runs nothing.** Work in a draft; mark it ready (`gh pr ready <pr>`) when it should be checked.
  Marking it ready checks everything the branch changes since `main`.
- **A later push** is judged on what it changes since the PR's previous push (`tools/ci_changes.py`):
  - only docs, measurements or Markdown: no check runs;
  - code outside what the slow tests guard: the hosted Linux and Windows checks;
  - anything the slow tests guard: the hosted checks and both slow checks.
  A skipped push does not cancel the run of an earlier push; a push that runs a check cancels that check's
  earlier run.
- **A milestone candidate**: Actions tab → each workflow → *Run workflow* on the branch (Linux and Windows with
  **slow** ticked, Linux slow, Windows slow). A dispatch always runs.

GitHub's own `paths` filters are not used for PRs because they judge the PR's whole diff, not the push.

## Merging with these checks

A PR merges when its Done-when lines and the local gate pass, and on GitHub:

1. the hosted Linux and Windows checks are green on **the last push that ran them**;
2. Linux slow and Windows slow are green on **the last push that ran them** (`gh run list --workflow
   linux-slow.yml --branch <branch>`), when a runner with that label was online;
3. a skipped check (grey, "skipped") on a later push is fine: that push changed nothing the check covers.

When no runner of a label is online, the slow run waits in the queue. The PR may merge on the other checks;
say so on the PR ("Windows slow: no runner online; the local gate ran --slow").

## The runners

| Name | Machine | Label | Folder | Started by |
|---|---|---|---|---|
| `goal2-pc` | the owner's PC, Windows | `goal2-slow` | `C:\Users\diego\ghr-goal2` | `goal2-runner.cmd` in the Startup folder, at logon |
| `goal2-WINDOWS-BJ0PUMB-linux` | the owner's PC, WSL (Ubuntu) | `goal2-slow-linux` | `~/actions-runner/goal2` | systemd user service `goal2-runner` |

Runners with the same label share one queue: two Windows machines check two PRs at once, and when one is
off the other takes the work. Check them on GitHub (Settings → Actions → Runners) or:

```bash
gh api repos/diegoami/goal2/actions/runners --jq '.runners[]|.name+" "+.status+" busy="+(.busy|tostring)'
```

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

- goal2 is public. A fork PR never runs the slow workflows (their jobs require the PR's head to be in this
  repository), and every outside contributor's workflow run waits for the owner's approval (repository
  setting *Require approval for all outside collaborators*, set 2026-11-01).
- The runners run as the owner's user, without admin rights. They see the `GOAL2_RCLONE_TOKEN` secret during a
  run; the rclone configuration lives in the job's temp folder, not the user's profile.
- Nothing of the original game is uploaded: each workflow refuses an upload with an original-game extension.
