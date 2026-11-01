"""[designed: owner, 2026-11-01, #493] The Windows and Linux slow workflows run only when needed (a ready PR
whose push changes what the slow tests guard: tools/ci_changes.py), and run the full gate with --slow on
the owner's machines (self-hosted runners, labels goal2-slow and goal2-slow-linux), never for a fork PR,
without touching the owner's desktop: offscreen Qt, dummy SDL, no display change, no native-window
scenarios. Windows finds Git Bash by its path (bash on a Windows PATH can be WSL's) and the PC's own Python
(no admin: setup-python cannot install there); Linux takes uv's. tools/runner/ registers a machine with
exactly those labels, checksum-verified. Text checks: the workflow files are YAML, PyYAML is no dependency."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "windows-slow.yml"
LINUX = WORKFLOW.with_name("linux-slow.yml")
RUNNER = ROOT / "tools" / "runner"


class WindowsSlow(unittest.TestCase):
    def setUp(self):
        self.assertTrue(WORKFLOW.is_file(), "no Windows slow workflow")
        self.text = WORKFLOW.read_text()

    def test_only_when_needed_prs_and_dispatch_never_main_or_drafts(self):
        for path in (WORKFLOW, LINUX):
            with self.subTest(workflow=path.name):
                text = path.read_text()
                on = re.search(r"^on:\n(.*?)^\S", text, re.M | re.S).group(1)
                self.assertIn("  pull_request:\n    types: [opened, synchronize, reopened, ready_for_review]\n", on)
                self.assertRegex(on, r"(?m)^  workflow_dispatch:")
                self.assertNotRegex(on, r"(?m)^  push:")
                self.assertIn("!github.event.pull_request.draft", text)
                self.assertIn("python3 tools/ci_changes.py --kind slow ${since:+--since \"$since\"}", text)
                self.assertIn('[ "${{ github.event.action }}" = synchronize ] && since="${{ github.event.before }}"', text)
                job = text.split("\n  changes:\n")[1].split("\n  ", 1)[1]
                self.assertIn("needs: changes\n    if: needs.changes.outputs.run == 'true'\n", job)
                self.assertNotRegex(text, r"(?m)^concurrency:")     # job-level: a skipped push cancels nothing
                self.assertIn("    concurrency:\n      group:", job)

    def test_only_the_owners_runner_and_never_a_fork(self):
        self.assertIn("runs-on: [goal2-slow]", self.text)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", self.text)
        self.assertNotIn("pull_request_target", self.text)
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: read$")

    def test_the_full_gate_with_slow_tests(self):
        self.assertIn("python tools/check_premerge.py --expected-head \"$(git rev-parse HEAD)\" --slow", self.text)
        self.assertNotIn("GOAL2_CASES", self.text)
        self.assertNotIn("--batch-fast", self.text)
        minutes = int(re.search(r"timeout-minutes: (\d+)", self.text).group(1))
        self.assertLessEqual(minutes, 300)

    def test_the_owners_desktop_is_left_alone(self):
        for line in ("QT_QPA_PLATFORM: offscreen", "SDL_VIDEODRIVER: dummy", "SDL_AUDIODRIVER: dummy"):
            self.assertIn(line, self.text)
        self.assertNotIn("Set-DisplayResolution", self.text)
        self.assertNotIn("tools/desktop-ui", self.text)

    def test_git_bash_by_path_and_the_pcs_own_python(self):
        self.assertIn(r"shell: 'C:\PROGRA~1\Git\bin\bash.exe --noprofile --norc -eo pipefail {0}'", self.text)
        self.assertNotIn("actions/setup-python", self.text)
        self.assertIn("py -3.13 -m venv", self.text)

    def test_nothing_of_the_original_game_is_uploaded(self):
        self.assertIn(r"grep -iE '\.(exe|dat|hlp|hil|pif|bat|sav|gl|g2save)$'", self.text)


class LinuxSlow(unittest.TestCase):
    def setUp(self):
        self.assertTrue(LINUX.is_file(), "no Linux slow workflow")
        self.text = LINUX.read_text()

    def test_the_same_workflow_on_the_linux_label_with_uvs_python(self):
        windows = WORKFLOW.read_text()
        for needle in ("  pull_request:", "  workflow_dispatch:",
                       "github.event.pull_request.head.repo.full_name == github.repository",
                       "python tools/check_premerge.py --expected-head \"$(git rev-parse HEAD)\" --slow",
                       "QT_QPA_PLATFORM: offscreen", "SDL_VIDEODRIVER: dummy", "SDL_AUDIODRIVER: dummy",
                       r"grep -iE '\.(exe|dat|hlp|hil|pif|bat|sav|gl|g2save)$'"):
            with self.subTest(needle=needle):
                self.assertIn(needle, windows)
                self.assertIn(needle, self.text)
        self.assertIn("runs-on: [goal2-slow-linux]", self.text)
        self.assertIn("uv venv -q --seed --python 3.12", self.text)
        for absent in ("actions/setup-python", "sudo", "pull_request_target", "--batch-fast", "GOAL2_CASES"):
            self.assertNotIn(absent, self.text)


class SetupScripts(unittest.TestCase):
    def test_each_registers_its_label_only_checksum_verified(self):
        for script, label, workflow in (("setup-windows.ps1", "goal2-slow", WORKFLOW), ("setup-linux.sh", "goal2-slow-linux", LINUX)):
            with self.subTest(script=script):
                text = (RUNNER / script).read_text()
                self.assertRegex(text, rf"(?m)^\$?Label\s*=\s*'{label}'$|^LABEL={label}$")
                self.assertIn(f"runs-on: [{label}]", workflow.read_text())
                self.assertIn("--no-default-labels", text)
                self.assertIn("BEGIN SHA", text)
                self.assertIn("diegoami/goal2", text)

    def test_windows_checks_what_its_workflow_relies_on(self):
        text = (RUNNER / "setup-windows.ps1").read_text()
        self.assertIn(r"C:\PROGRA~1\Git\bin\bash.exe", text)
        self.assertIn("py -3.13", text)

    def test_linux_checks_uv_and_keeps_the_runner_up(self):
        text = (RUNNER / "setup-linux.sh").read_text()
        self.assertIn("need uv", text)
        self.assertIn("systemctl --user enable --now", text)
        self.assertIn("Restart=always", text)


class DriveMirror(unittest.TestCase):
    """[designed: owner, 2026-11-01, #493] Each runner keeps a mirror of the Drive folder outside its work folder."""

    def test_sync_into_a_mirror_outside_the_work_folder_then_a_local_copy(self):
        for path, mirror in ((WORKFLOW, 'mirror="$(cygpath -m "$LOCALAPPDATA")/goal2-runner/drive"'),
                             (LINUX, 'mirror="$HOME/.cache/goal2-runner/drive"')):
            with self.subTest(workflow=path.name):
                text = path.read_text()
                self.assertIn(mirror, text)
                self.assertIn('rclone sync --fast-list goal2drive: "$mirror"', text)     # sync: deletions too
                self.assertIn('cp -R "$mirror/." .cache/', text)
                self.assertNotIn("artifacts.py pull", text)
                self.assertLess(text.index("rclone sync"), text.index("check_goaldat.py"))
                self.assertIn('export RCLONE_CONFIG="$RUNNER_TEMP/rclone.conf"', text)


class HostedGates(unittest.TestCase):
    """[designed: owner, 2026-11-01, #493] The hosted Linux and Windows gates skip drafts and docs-only pushes."""

    def test_no_draft_and_only_pushes_beyond_docs(self):
        for name, job in (("ci.yml", "linux"), ("windows.yml", "windows")):
            with self.subTest(workflow=name):
                text = (ROOT / ".github" / "workflows" / name).read_text()
                on = re.search(r"^on:\n(.*?)^\S", text, re.M | re.S).group(1)
                self.assertIn("  pull_request:\n    types: [opened, synchronize, reopened, ready_for_review]\n", on)
                self.assertIn("  push:\n    branches: [main]\n    paths-ignore: ['docs/**', 'measurements/**', '**/*.md']\n", on)
                self.assertIn("!github.event.pull_request.draft", text)
                self.assertIn("python3 tools/ci_changes.py --kind code ${since:+--since \"$since\"}", text)
                self.assertIn(f"\n  {job}:\n    needs: changes\n    if: needs.changes.outputs.run == 'true'\n", text)
                self.assertNotRegex(text, r"(?m)^concurrency:")


class CiChanges(unittest.TestCase):
    """tools/ci_changes.py on a scratch repository: a branch off main, pushed twice."""

    def setUp(self):
        import os
        import shutil
        import stat
        import subprocess
        import sys
        import tempfile
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import ci_changes
        finally:
            sys.path.remove(str(ROOT / "tools"))
        self.cc = ci_changes
        self.repo = Path(tempfile.mkdtemp())

        def writable(func, path, _):        # git's objects are read-only, which Windows will not delete
            os.chmod(path, stat.S_IWRITE);func(path)
        self.addCleanup(shutil.rmtree, self.repo, **({"onexc": writable} if sys.version_info >= (3, 12) else {"onerror": writable}))
        self.run = lambda *a: subprocess.run(["git", *a], cwd=self.repo, check=True, capture_output=True, text=True).stdout.strip()
        self.run("init", "-q", "-b", "main");self.run("config", "user.email", "t@t");self.run("config", "user.name", "t")
        self.commit("README.md")
        self.run("update-ref", "refs/remotes/origin/main", "HEAD")
        self.run("switch", "-q", "-c", "work")

    def commit(self, path):
        f = self.repo / path;f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f.read_text() + "x" if f.exists() else "x")
        self.run("add", path);self.run("commit", "-qm", path)
        return self.run("rev-parse", "HEAD")

    def decide(self, since=None, kind="slow"):
        return self.cc.decide(since, cwd=self.repo, kind=kind)[0]

    def test_a_docs_push_after_an_engine_push_runs_nothing(self):
        engine = self.commit("goal2/engine/original_match/match.py")
        self.assertTrue(self.decide());self.assertTrue(self.decide(kind="code"))       # the first push: the branch
        self.commit("docs/process.md")
        self.assertFalse(self.decide(engine));self.assertFalse(self.decide(engine, kind="code"))
        self.assertTrue(self.decide())                                                    # ready-for-review: the branch

    def test_a_ui_push_runs_the_hosted_gates_only(self):
        first = self.commit("docs/x.md")
        self.assertFalse(self.decide(kind="code"))
        self.commit("goal2/desktop/shell.py")
        self.assertTrue(self.decide(first, kind="code"));self.assertFalse(self.decide(first))

    def test_a_rewritten_or_unknown_previous_head_counts_the_whole_branch(self):
        self.commit("goal2/core/game.py")
        for since in ("0" * 40, "f" * 40, None):
            with self.subTest(since=since):
                self.assertTrue(self.decide(since))

    def test_git_failing_runs_to_be_safe(self):
        self.run("update-ref", "-d", "refs/remotes/origin/main")
        self.assertTrue(self.decide())


if __name__ == "__main__":
    unittest.main()
