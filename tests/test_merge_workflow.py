"""[designed: fix #65] Regression checks for the documented merge recipe and local state."""
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude/skills/run-task/SKILL.md"
PROCESS = ROOT / "docs/process.md"
REVIEWED_SHA = "0123456789abcdef0123456789abcdef01234567"


def documented_merge_args(text):
    match = re.search(r"`(gh pr merge <pr>[^`]+)`", text)
    if not match:
        raise AssertionError("documented gh pr merge recipe is missing")
    command = match.group(1).replace("<pr>", "63").replace("<reviewed-sha>", REVIEWED_SHA)
    return shlex.split(command)


def validate_merge_args(args):
    if "--delete-branch" in args:
        raise ValueError("automatic branch deletion can remove the local worktree")
    if "--squash" not in args:
        raise ValueError("merge must squash")
    try:
        index = args.index("--match-head-commit")
    except ValueError as exc:
        raise ValueError("merge must be pinned to the reviewed head") from exc
    if index + 1 >= len(args) or args[index + 1] != REVIEWED_SHA:
        raise ValueError("merge head does not match the reviewed SHA")


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


class MergeWorkflowTests(unittest.TestCase):
    def test_documents_use_squash_merge_pinned_to_reviewed_head(self):
        skill_args = documented_merge_args(SKILL.read_text())
        process_args = documented_merge_args(PROCESS.read_text())
        self.assertEqual(skill_args, process_args)
        validate_merge_args(skill_args)
        self.assertEqual(
            skill_args,
            ["gh", "pr", "merge", "63", "--squash", "--match-head-commit", REVIEWED_SHA],
        )

    def test_safe_recipe_keeps_local_worktree_notes_and_cache(self):
        with tempfile.TemporaryDirectory(prefix="goal2-merge-fixture-") as temp:
            root = Path(temp)
            repo = root / "repo"
            worktree = root / "task-worktree"
            repo.mkdir()
            git(repo, "init", "-b", "main")
            git(repo, "config", "user.name", "Merge Fixture")
            git(repo, "config", "user.email", "fixture@example.invalid")
            (repo / ".gitignore").write_text("RUN-NOTES.md\n.cache/\n")
            (repo / "base.txt").write_text("base\n")
            git(repo, "add", ".gitignore", "base.txt")
            git(repo, "commit", "-m", "fixture base")
            git(repo, "branch", "task/63")
            git(repo, "worktree", "add", str(worktree), "task/63")

            notes = worktree / "RUN-NOTES.md"
            cache = worktree / ".cache" / "GOAL.DAT"
            cache.parent.mkdir()
            notes.write_text("preserved run notes\n")
            cache.write_bytes(b"fixture cache sentinel")
            before = (notes.read_bytes(), cache.read_bytes())

            documented_args = documented_merge_args(SKILL.read_text())
            unsafe_args = [
                "gh", "pr", "merge", "63", "--squash", "--delete-branch",
                "--match-head-commit", REVIEWED_SHA,
            ]
            with self.assertRaisesRegex(ValueError, "automatic branch deletion"):
                validate_merge_args(unsafe_args)

            # [designed: fix #65] Mock the external merge: validate the documented
            # arguments without contacting GitHub or running cleanup against the fixture.
            validate_merge_args(documented_args)
            self.assertEqual(git(repo, "branch", "--show-current"), "main")
            self.assertEqual(git(repo, "show-ref", "--verify", "refs/heads/task/63").split()[1],
                             "refs/heads/task/63")
            self.assertIn(str(worktree), git(repo, "worktree", "list", "--porcelain"))
            self.assertEqual(git(worktree, "branch", "--show-current"), "task/63")
            self.assertEqual((notes.read_bytes(), cache.read_bytes()), before)
            self.assertEqual(git(worktree, "check-ignore", "RUN-NOTES.md", ".cache/GOAL.DAT").splitlines(),
                             ["RUN-NOTES.md", ".cache/GOAL.DAT"])


if __name__ == "__main__":
    unittest.main()
