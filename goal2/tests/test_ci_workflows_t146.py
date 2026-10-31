"""[designed: owner, 2026-10-29, T146] The Linux gate workflow is provisioned like the Windows one:
it runs on every PR and on main, pulls and verifies the original files before the gate (a missing
secret fails a same-repository run instead of turning into skips), clones goal2-archaeology, runs
offscreen, and uploads logs only. Text checks: the workflow files are YAML, PyYAML is no dependency."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MEASURED = ROOT / "measurements" / "T146"


class LinuxGate(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()

    def step(self, name):
        """The text of the step whose name starts with `name`, up to the next step."""
        m = re.search(r"^      - name: " + re.escape(name) + r".*?(?=^      - |\Z)", self.text, re.M | re.S)
        self.assertIsNotNone(m, f"no step {name!r}")
        return m.group(0)

    def test_it_runs_on_every_pr_on_main_and_on_dispatch_with_a_slow_input(self):
        on = re.search(r"^on:\n(.*?)^\S", self.text, re.M | re.S).group(1)
        self.assertRegex(on, r"(?m)^  pull_request:")
        self.assertRegex(on, r"(?m)^  push:\n    branches: \[main\]")
        self.assertRegex(on, r"(?m)^  workflow_dispatch:\n    inputs:\n      slow:")

    def test_a_pinned_image_and_a_measured_timeout_under_six_hours(self):
        self.assertRegex(self.text, r"runs-on: ubuntu-\d\d\.\d\d\n")
        minutes = int(re.search(r"timeout-minutes: (\d+)", self.text).group(1))
        self.assertLess(minutes, 360)
        receipts = sorted(MEASURED.glob("run-*-v1.json"))
        self.assertTrue(receipts, "the timeout must come from a measured slow run")
        import json
        slow = [json.loads(p.read_text()) for p in receipts]
        slow = [r for r in slow if r.get("slow")]
        self.assertTrue(slow, "no measured slow run")
        longest = max(r["gate_wall_s"] for r in slow) / 60
        self.assertGreaterEqual(minutes, 1.3 * longest, "the timeout leaves under 30 % margin")

    def test_automatic_slow_runs_play_one_case_and_a_slow_dispatch_all(self):
        # [designed: owner, 2026-10-31, #487] both workflows, the same rule
        for path in (WORKFLOW, WORKFLOW.with_name("windows.yml")):
            with self.subTest(workflow=path.name):
                self.assertIn('[ -z "$slow" ] && export GOAL2_CASES=1', path.read_text())

    def test_offscreen_qt_and_dummy_sdl(self):
        for line in ("QT_QPA_PLATFORM: offscreen", "SDL_VIDEODRIVER: dummy", "SDL_AUDIODRIVER: dummy"):
            self.assertIn(line, self.text)

    def test_originals_and_archaeology_come_before_the_gate(self):
        order = [self.text.index(s) for s in ("- name: Install goal2", "- name: Original-game files",
                                               "- name: goal2-archaeology", "- name: Game tests and pre-merge")]
        self.assertEqual(order, sorted(order))
        originals = self.step("Original-game files")
        self.assertIn("secrets.GOAL2_RCLONE_TOKEN", originals)
        self.assertIn("check_goaldat.py", originals)
        self.assertIn("sha256sum -c", originals)
        self.assertIn("python tools/check_premerge.py --expected-head", self.step("Game tests and pre-merge"))

    def test_a_missing_secret_fails_unless_the_pr_comes_from_a_fork(self):
        originals = self.step("Original-game files")
        missing = originals[originals.index('if [ -z "$GOAL2_RCLONE_TOKEN" ]'):originals.index("version=")]
        self.assertIn("head.repo.full_name != github.repository", originals)
        fork = missing.index('if [ "$FORK" = true ]')
        end = re.compile(r"^\s*fi$", re.M).search(missing, fork).start()  # the inner if's own fi
        self.assertIn("exit 0", missing[fork:end])
        self.assertNotIn("exit 1", missing[fork:end])
        self.assertIn("exit 1", missing[end:])

    def test_logs_only_through_the_refusal_filter_and_no_cache(self):
        keep = self.step("Keep only logs")
        self.assertIn(r"\.(exe|dat|hlp|hil|pif|bat|sav|gl|g2save)$", keep)
        self.assertNotRegex(self.text, r"actions/cache")
        uploads = re.findall(r"actions/upload-artifact@v\d+\n(?:.*\n)*?\s+path: (\S+)", self.text)
        self.assertEqual(uploads, ["upload"])
        self.assertNotRegex(keep, r"cp .*\.cache")


if __name__ == "__main__":
    unittest.main()
