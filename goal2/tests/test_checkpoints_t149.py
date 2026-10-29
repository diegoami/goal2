"""[designed: owner, 2026-10-29, T149] The job registry and the checkpoint snapshot (tools/jobs.py,
tools/checkpoint.py): jobs outlive the session and say how they ended; the snapshot says what is
where and reports a failed GitHub call instead of leaving it out."""
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


def tool(name):
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(ROOT / "tools"))


@unittest.skipIf(os.name == "nt", "tools/jobs.py is POSIX only (setsid, /proc)")
class Jobs(unittest.TestCase):
    def setUp(self):
        self.jobs = tool("jobs")
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(subprocess.run, ["rm", "-rf", str(self.root)])

    def started(self, name, *command):
        job = self.jobs.start(self.root, name, [sys.executable, "-c", *command])
        self.addCleanup(self.stop, name)
        return job

    def stop(self, name):
        job = self.jobs.read(self.root, name)
        for pid in (job.get("command_pid"), job.get("wrapper_pid")):
            if pid and self.jobs.alive(pid):
                os.kill(pid, signal.SIGKILL)

    def until(self, name, state, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            job = self.jobs.read(self.root, name)
            if job["state"] == state:
                return job
            time.sleep(0.05)
        self.fail(f"{name} never {state}: {job}")

    def test_a_job_runs_detached_and_records_its_exit_code_and_output(self):
        job = self.started("short", "import time;print('hello');time.sleep(0.5);raise SystemExit(3)")
        self.assertEqual(job["command"][-1].count("hello"), 1)
        self.assertEqual(self.jobs.read(self.root, "short")["state"], "running")
        done = self.jobs.wait(self.root, "short", timeout=20, poll=0.05)
        self.assertEqual((done["state"], done["exit_code"]), ("finished", 3))
        self.assertEqual(Path(done["log"]).read_text().strip(), "hello")
        self.assertIsInstance(done["command_pid"], int)
        self.assertEqual([j["name"] for j in self.jobs.jobs(self.root)], ["short"])

    def test_a_killed_job_is_vanished_not_running_or_finished(self):
        self.started("killed", "import time;time.sleep(60)")
        job = self.until("killed", "running")
        while "command_pid" not in job:
            time.sleep(0.05);job = self.jobs.read(self.root, "killed")
        os.kill(job["command_pid"], signal.SIGKILL);os.kill(job["wrapper_pid"], signal.SIGKILL)
        self.assertEqual(self.until("killed", "vanished")["state"], "vanished")

    def test_a_running_name_is_refused_and_a_finished_one_is_kept_then_replaced(self):
        self.started("twice", "import time;time.sleep(60)")
        with self.assertRaisesRegex(self.jobs.JobError, "is running"):
            self.jobs.start(self.root, "twice", [sys.executable, "-c", "pass"])
        self.stop("twice");self.until("twice", "vanished")
        self.started("twice", "pass");self.jobs.wait(self.root, "twice", timeout=20, poll=0.05)
        kept = sorted(p.name for p in (self.root / ".cache/jobs").glob("twice.*.json") if "exit" not in p.name
                      and "pids" not in p.name)
        self.assertEqual(len(kept), 1, kept)
        self.assertEqual([j["name"] for j in self.jobs.jobs(self.root)], ["twice"])

    def test_wait_returns_when_the_pid_exits(self):
        self.started("waited", "import time;time.sleep(1)")
        begin = time.monotonic()
        self.assertEqual(self.jobs.wait(self.root, "waited", timeout=20, poll=0.05)["exit_code"], 0)
        self.assertGreater(time.monotonic() - begin, 0.5)
        self.started("slow", "import time;time.sleep(60)")
        with self.assertRaises(TimeoutError):
            self.jobs.wait(self.root, "slow", timeout=0.3, poll=0.05)

    def test_secrets_bad_names_and_empty_commands_are_refused(self):
        for command in (["env", "GOAL2_RCLONE_TOKEN=x", "true"], ["tool", "--token", "x"], ["x", "API_KEY=1"]):
            with self.assertRaisesRegex(self.jobs.JobError, "secret"):
                self.jobs.start(self.root, "secret", command)
        for name in ("a.b", "../x", "", "-x"):
            with self.assertRaises(self.jobs.JobError):
                self.jobs.start(self.root, name, ["true"])
        with self.assertRaisesRegex(self.jobs.JobError, "no command"):
            self.jobs.start(self.root, "empty", [])
        self.assertFalse((self.root / ".cache/jobs/secret.json").exists())

    def test_the_command_line_interface(self):
        script = str(ROOT / "tools/jobs.py")
        run = lambda *a: subprocess.run([sys.executable, script, "--root", str(self.root), *a],
                                        capture_output=True, text=True)
        self.assertIn("no jobs", run("list").stdout)
        started = run("start", "cli", "--", sys.executable, "-c", "print('out')")
        self.addCleanup(self.stop, "cli")
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(run("wait", "cli", "--timeout", "20").returncode, 0)
        self.assertIn("finished exit 0", run("list").stdout)
        self.assertEqual(run("tail", "cli").stdout.strip(), "out")
        self.assertEqual(run("wait", "nothing").returncode, 2)
        elsewhere = Path(tempfile.mkdtemp());self.addCleanup(subprocess.run, ["rm", "-rf", str(elsewhere)])
        placed = run("start", "placed", "--cwd", str(elsewhere), "--", sys.executable, "-c",
                     "import os;print(os.getcwd())")
        self.addCleanup(self.stop, "placed")
        self.assertEqual(placed.returncode, 0, placed.stderr)
        self.assertEqual(run("wait", "placed", "--timeout", "20").returncode, 0)
        job = self.jobs.read(self.root, "placed")
        self.assertEqual(job["command"], [sys.executable, "-c", "import os;print(os.getcwd())"])
        self.assertEqual(run("tail", "placed").stdout.strip(), str(elsewhere.resolve()))
        self.assertEqual(run("start", "nocommand").returncode, 2)


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.cp = tool("checkpoint")

    def fake(self, prs=None, pr_error=None, issues=None):
        calls = []

        def run(args, cwd=None):
            calls.append(args)
            if args[:2] == ["git", "rev-parse"] and args[2] == "--show-toplevel":
                return 0, "/work/goal2\n", ""
            if args[:2] == ["git", "remote"]:
                return 0, "git@github.com:diegoami/goal2.git\n", ""
            if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
                return 0, "task/T149-checkpoints\n", ""
            if args[:2] == ["git", "rev-parse"]:
                return 0, "0123456789abcdef0123\n", ""
            if args[:2] == ["git", "status"]:
                return 0, " M tools/jobs.py\n?? 1\n?? error1.txt\n", ""
            if args[:2] == ["git", "rev-list"]:
                return 0, "0\t2\n", ""
            if args[:3] == ["gh", "pr", "list"]:
                return (1, "", pr_error + "\n") if pr_error else (0, json.dumps(prs or []), "")
            if args[:3] == ["gh", "issue", "list"]:
                return 0, json.dumps(issues if issues is not None else [{"number": 7}]), ""
            if args[:3] == ["gh", "issue", "comment"]:
                return 0, "https://github.com/diegoami/goal2/issues/7#issuecomment-1\n", ""
            raise AssertionError(args)
        return run, calls

    def test_the_snapshot_names_branch_head_dirty_state_and_pr_checks(self):
        prs = [{"number": 465, "title": "T144", "headRefName": "task/T144-team-panels",
                "headRefOid": "7bfe7d2e" + "0" * 32, "isDraft": True, "labels": [{"name": "status:in-review"}],
                "statusCheckRollup": [{"name": "windows", "status": "COMPLETED", "conclusion": "FAILURE"},
                                      {"name": "GitGuardian", "status": "COMPLETED", "conclusion": "SUCCESS"},
                                      {"name": "linux", "status": "IN_PROGRESS", "conclusion": None}]}]
        run, _ = self.fake(prs=prs)
        text = self.cp.snapshot([Path("/work/goal2")], run)
        self.assertIn("task/T149-checkpoints at 0123456789ab, 1 changed, 2 untracked, 2 ahead/0 behind", text)
        self.assertIn("#465 T144 (task/T144-team-panels at 7bfe7d2e0000, draft; status:in-review)", text)
        self.assertIn("failure 1 (windows)", text)
        self.assertIn("in_progress 1 (linux)", text)
        self.assertIn("success 1", text)
        self.assertNotIn("error1.txt", text)

    def test_a_failed_github_call_is_reported(self):
        run, _ = self.fake(pr_error="HTTP 403: rate limited")
        self.assertIn("FAILED to read PRs (HTTP 403: rate limited)", self.cp.snapshot([Path("/work/goal2")], run))

    def test_post_goes_only_to_the_one_checkpoint_issue(self):
        run, calls = self.fake()
        self.assertIn("issuecomment-1", self.cp.post("diegoami/goal2", "body", run))
        listed = next(c for c in calls if c[:3] == ["gh", "issue", "list"])
        self.assertEqual(listed[listed.index("--label") + 1], "checkpoint")
        comment = next(c for c in calls if c[:3] == ["gh", "issue", "comment"])
        self.assertEqual(comment[3], "7")
        for issues in ([], [{"number": 7}, {"number": 8}]):
            run, calls = self.fake(issues=issues)
            with self.assertRaisesRegex(self.cp.CheckpointError, "need exactly one"):
                self.cp.post("diegoami/goal2", "body", run)
            self.assertFalse(any(c[:3] == ["gh", "issue", "comment"] for c in calls))

    def test_it_runs_in_this_checkout(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools/checkpoint.py")], capture_output=True, text=True,
                           env={**os.environ, "GOAL2_CHECKOUTS": ""})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(ROOT), r.stdout)


if __name__ == "__main__":
    unittest.main()
