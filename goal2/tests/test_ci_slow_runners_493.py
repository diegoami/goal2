"""[designed: owner, 2026-11-01, #493] The Windows and Linux slow workflows run the full gate with --slow on
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

    def test_it_runs_on_prs_main_and_dispatch(self):
        on = re.search(r"^on:\n(.*?)^\S", self.text, re.M | re.S).group(1)
        self.assertRegex(on, r"(?m)^  pull_request:")
        self.assertRegex(on, r"(?m)^  push:\n    branches: \[main\]")
        self.assertRegex(on, r"(?m)^  workflow_dispatch:")

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
        for needle in ("  pull_request:", "    branches: [main]", "  workflow_dispatch:",
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


if __name__ == "__main__":
    unittest.main()
