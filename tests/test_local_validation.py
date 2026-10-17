"""[designed: #127] Exercise local validation against synthetic git repositories."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import check_premerge as validator


class LocalValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="goal2-local-check-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Validation Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / "input.txt").write_text("synthetic fixture\n")
        digest = hashlib.sha256((self.root / "input.txt").read_bytes()).hexdigest()
        (self.root / "harness.lock").write_text(digest + "  input.txt\n")
        (self.root / ".gitignore").write_text(".cache/\nRUN-NOTES.md\n")
        self.commit()
        self.sha = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              capture_output=True, text=True).stdout

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-m", "synthetic fixture")

    def test_wrong_or_abbreviated_head_is_rejected(self):
        for value in ("0" * 40, self.sha[:7], "main"):
            with self.subTest(value=value), self.assertRaises(validator.ValidationError):
                validator.check_checkout(self.root, value)

    def test_staged_and_unstaged_changes_are_rejected(self):
        (self.root / "input.txt").write_text("changed\n")
        with self.assertRaisesRegex(validator.ValidationError, "dirty"):
            validator.check_checkout(self.root, self.sha)
        self.git("add", "input.txt")
        with self.assertRaisesRegex(validator.ValidationError, "dirty"):
            validator.check_checkout(self.root, self.sha)

    def test_untracked_and_ignored_user_files_are_preserved(self):
        paths = (self.root / "owner-file.txt", self.root / "RUN-NOTES.md",
                 self.root / ".cache" / "session.g2save")
        for path in paths:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"synthetic sentinel")
        validator.check_checkout(self.root, self.sha)
        validator.check_originals(self.root)
        self.assertEqual([p.read_bytes() for p in paths], [b"synthetic sentinel"] * 3)

    def test_committed_lock_mismatch_is_rejected(self):
        (self.root / "input.txt").write_text("committed drift\n")
        self.commit()
        validator.check_checkout(self.root, self.git("rev-parse", "HEAD").strip())
        with self.assertRaisesRegex(validator.ValidationError, "hash mismatch"):
            validator.check_lock(self.root)

    def test_missing_empty_and_malformed_lock_fail(self):
        lock = self.root / "harness.lock"
        for content in ("# no hashes\n", "not a valid entry\n", "a" * 64 + "  missing.txt\n"):
            lock.write_text(content)
            with self.subTest(content=content), self.assertRaises((validator.ValidationError, OSError)):
                validator.check_lock(self.root)

    def test_tracked_original_and_session_names_are_rejected(self):
        # These contain synthetic text, never bytes of the original game.
        for name in ("GOAL.DAT", "fixture.sav", "session.g2save", "program.EXE"):
            path = self.root / name
            path.write_text("synthetic sentinel\n")
            self.git("add", name)
            with self.subTest(name=name), self.assertRaisesRegex(validator.ValidationError, "tracked original"):
                validator.check_originals(self.root)

    def test_child_failure_and_missing_tool_fail_the_command(self):
        real_run = subprocess.run
        for failure in (subprocess.CalledProcessError(7, ["synthetic check"]),
                        FileNotFoundError("synthetic missing node")):
            children = []

            def run(args, **kwargs):
                if args[0] == "git":
                    return real_run(args, **kwargs)
                children.append(args)
                if isinstance(failure, subprocess.CalledProcessError) and not kwargs.get("check"):
                    return subprocess.CompletedProcess(args, failure.returncode)
                raise failure

            with self.subTest(failure=failure), patch.object(validator.subprocess, "run", side_effect=run):
                with self.assertRaises(type(failure)):
                    validator.validate(self.root, self.sha)
            self.assertEqual(len(children), 1, "a failing check must stop validation")
        with patch.object(validator, "validate", side_effect=FileNotFoundError("missing tool")):
            self.assertEqual(validator.main(["--expected-head", self.sha]), 1)

    def test_success_runs_checks_and_rechecks_the_commit(self):
        real_run = subprocess.run
        children = []

        def run(args, **kwargs):
            if args[0] == "git":
                return real_run(args, **kwargs)
            children.append(args)
            return subprocess.CompletedProcess(args, 0)

        with patch.object(validator.subprocess, "run", side_effect=run):
            validator.validate(self.root, self.sha)
        self.assertEqual(len(children), 4)
        self.assertTrue(any("tools/check_links.py" in c for c in children))
        self.assertTrue(any("--self-test" in c for c in children))
        self.assertTrue(any("tests/harness_clients.test.mjs" in c for c in children))
        self.assertTrue(any("tests/opencode_protocol.test.mjs" in c for c in children))
        self.assertTrue(any("tests.test_agent_permissions" in c for c in children))

    def test_child_cannot_dirty_or_move_the_verified_checkout(self):
        real_run = subprocess.run
        for change in ("dirty", "head"):
            def run(args, **kwargs):
                if args[0] == "git":
                    return real_run(args, **kwargs)
                if change == "dirty":
                    (self.root / "input.txt").write_text("child changed tracked input\n")
                else:
                    real_run(["git", "commit", "--allow-empty", "-m", "child moved head"],
                             cwd=self.root, check=True, capture_output=True)
                return subprocess.CompletedProcess(args, 0)

            with self.subTest(change=change), patch.object(validator.subprocess, "run", side_effect=run):
                with self.assertRaisesRegex(validator.ValidationError, "dirty|HEAD mismatch"):
                    validator.validate(self.root, self.sha)
            # Restore our synthetic fixture using saved content and a new commit, never reset.
            (self.root / "input.txt").write_text("synthetic fixture\n")
            if change == "dirty":
                validator.check_checkout(self.root, self.sha)

    def test_hosted_workflow_is_manual_and_uses_the_same_validator(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/ci.yml").read_text()
        trigger = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertEqual(trigger.strip(), "workflow_dispatch:")
        self.assertIn('python3 tools/check_premerge.py --expected-head "$GITHUB_SHA"', workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("timeout-minutes: 5", workflow)


if __name__ == "__main__":
    unittest.main()
