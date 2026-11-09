"""[designed: owner, 2026-11-09; T206, #683] `pull NAME` writes the file under its own name.

A drive remote ends with ':' ("goal2drive:"), so the joined source "goal2drive:GOAL.DAT" holds no
path separator and `Path(...).name` gives the whole string back. Taking the destination from the
joined source therefore wrote `.cache/goal2drive:GOAL.DAT`, and every later run looked for a file
that was not there. The destination comes from the name the caller gave.

Nothing here touches the network: `pull_commands` returns the arguments, it does not run them.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import artifacts  # noqa: E402


class PullDestination(unittest.TestCase):
    def cfg(self, remote):
        return {"remote": remote, "localDir": Path("/tmp/goal2-cache")}

    def test_a_drive_remote_writes_the_file_under_its_own_name(self):
        """The bug: a ':' remote has no separator, so the joined source is not a path."""
        commands = artifacts.pull_commands(self.cfg("goal2drive:"), ["GOAL.DAT"])
        self.assertEqual(commands, [["copyto", "goal2drive:GOAL.DAT",
                                     "/tmp/goal2-cache/GOAL.DAT"]])
        for command in commands:
            self.assertNotIn("goal2drive:", Path(command[-1]).name,
                             "the remote's prefix leaked into the local file name (#683)")

    def test_a_path_remote_writes_the_file_under_its_own_name(self):
        commands = artifacts.pull_commands(self.cfg("drive/goal2"), ["e006-r0001-main.sav"])
        self.assertEqual(commands, [["copyto", "drive/goal2/e006-r0001-main.sav",
                                     "/tmp/goal2-cache/e006-r0001-main.sav"]])

    def test_several_names_each_keep_their_own(self):
        names = ["GOAL.DAT", "e039-r0005-date-call.sav"]
        commands = artifacts.pull_commands(self.cfg("goal2drive:"), names)
        self.assertEqual([Path(c[-1]).name for c in commands], names)

    def test_no_name_copies_the_whole_folder(self):
        """The unnamed form was never broken and keeps `copy`, not `copyto`."""
        self.assertEqual(artifacts.pull_commands(self.cfg("goal2drive:"), []),
                         [["copy", "goal2drive:", "/tmp/goal2-cache"]])

    def test_a_name_with_a_folder_in_it_lands_in_the_cache(self):
        """A name the caller gives with a path keeps only its last part locally."""
        commands = artifacts.pull_commands(self.cfg("goal2drive:"), ["states/e006.sav"])
        self.assertEqual(commands[0][-1], "/tmp/goal2-cache/e006.sav")


if __name__ == "__main__":
    unittest.main()
