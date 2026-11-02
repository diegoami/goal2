"""[designed: owner, 2026-11-03, #526] The first-run import also takes the original's help file, GOAL.HLP, when the
offered folder has it: the redesigned UI's F1 shows the original's own help (docs/design/ui-2026-11, S22). It is
optional, so a data folder without it still imports; a GOAL.HLP that is not the released file is refused by name.
Stand-in bytes only, as in test_first_run_t153."""
import hashlib
from unittest import mock

from goal2.desktop import data_setup
from goal2.tests.test_first_run_t153 import Case, STAND_IN

HELP = b"stand-in help file\n"
STAND_IN_OPTIONAL = (("GOAL.HLP", hashlib.sha256(HELP).hexdigest()),)
COMMITTED = getattr(data_setup, "OPTIONAL", None)   # before any test patches it


class HelpFile(Case):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(data_setup, "OPTIONAL", STAND_IN_OPTIONAL)
        patcher.start();self.addCleanup(patcher.stop)

    def test_a_folder_with_the_help_file_imports_it(self):
        copied = data_setup.import_folder(self.source(files=dict(STAND_IN, **{"GOAL.HLP": HELP})), self.target)
        self.assertIn("GOAL.HLP", copied)
        self.assertEqual(self.target.help.read_bytes(), HELP)
        self.assertEqual(self.target.help, self.target.data / "GOAL.HLP")

    def test_a_folder_without_it_still_imports(self):
        copied = data_setup.import_folder(self.source(), self.target)
        self.assertEqual(sorted(copied), sorted(STAND_IN))
        self.assertFalse(self.target.help.exists())
        self.assertTrue(data_setup.complete(self.target.data))

    def test_a_wrong_help_file_is_refused_by_name(self):
        source = self.source(files=dict(STAND_IN, **{"GOAL.HLP": b"another file\n"}))
        with self.assertRaises(data_setup.ImportRefused) as caught:
            data_setup.import_folder(source, self.target)
        self.assertEqual(caught.exception.problems, [("GOAL.HLP", "wrong")])
        self.assertIn("GOAL.HLP in", str(caught.exception))
        self.assertFalse(self.target.root.exists(), "nothing is copied from a refused folder")

    def test_the_committed_digest_is_the_released_file(self):
        # [confirmed: goal2-archaeology artifacts/known.json, GOAL.HLP, 32569 bytes, both release sets]
        self.assertEqual(COMMITTED,
                         (("GOAL.HLP", "2f3be8648a52045b6f7af1f41cba020d6a662229e5db499e203c5d0957308f60"),))
