"""[designed: owner, 2026-11-02, T153] The first-run import of the player's data folder (goal2/desktop/data_setup.py)
and the desktop's default start over it (goal2/desktop/__main__.py).

Nothing of the original is in this file. The import's rules are visited with stand-in files of the two names,
checked against a stand-in manifest; the committed manifest is checked against the owner's files in `.cache/` when
they are there (docs/artifacts.md)."""
import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goal2.desktop import data_setup
from goal2.desktop import __main__ as entry
from goal2.tests import requires

STAND_IN = {"GOAL.DAT": b"stand-in data file\n", "e039-r0005-date-call.sav": b"stand-in date-call state\n"}
STAND_IN_MANIFEST = tuple((name, hashlib.sha256(raw).hexdigest()) for name, raw in STAND_IN.items())


def tree(root):
    """Every file under `root` with its bytes' digest, and every folder."""
    out = {}
    for path in sorted(Path(root).rglob("*")):
        out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "dir"
    return out


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t153-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        patcher = mock.patch.object(data_setup, "MANIFEST", STAND_IN_MANIFEST)
        patcher.start();self.addCleanup(patcher.stop)
        self.home = self.tmp / "home";self.home.mkdir()
        self.target = data_setup.Paths(self.home / "goal2")
        # The desktop's own lookup lands in this test's home on every platform.
        env = mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home),
                                           "LOCALAPPDATA": str(self.home / "AppData" / "Local")})
        env.start();self.addCleanup(env.stop)

    def source(self, name="offered", files=STAND_IN, extra=True):
        folder = self.tmp / name;folder.mkdir()
        for file, raw in files.items():
            (folder / file).write_bytes(raw)
        if extra:
            (folder / "unrelated.txt").write_bytes(b"not part of the manifest\n")
        return folder


class ImportCases(Case):
    def test_a_complete_folder_is_imported_and_verified(self):
        copied = data_setup.import_folder(self.source(), self.target)
        self.assertEqual(sorted(copied), sorted(STAND_IN))
        self.assertEqual(sorted(p.name for p in self.target.data.iterdir()), sorted(STAND_IN))
        for name, digest in STAND_IN_MANIFEST:
            self.assertEqual(data_setup.sha256(self.target.data / name), digest)
        self.assertTrue(data_setup.complete(self.target.data))
        self.assertEqual(data_setup.import_folder(self.source("again"), self.target), [], "already right: no copy")

    def test_a_missing_file_is_refused_naming_it(self):
        source = self.source(files={"GOAL.DAT": STAND_IN["GOAL.DAT"]})
        with self.assertRaises(data_setup.ImportRefused) as caught:
            data_setup.import_folder(source, self.target)
        self.assertEqual(caught.exception.problems, [("e039-r0005-date-call.sav", "missing")])
        self.assertIn("e039-r0005-date-call.sav is missing", str(caught.exception))
        self.assertNotIn("GOAL.DAT", str(caught.exception))
        self.assertFalse(self.target.root.exists(), "nothing is copied from a refused folder")

    def test_a_wrong_hash_is_refused_naming_it(self):
        source = self.source(files=dict(STAND_IN, **{"GOAL.DAT": b"an edited data file\n"}))
        with self.assertRaises(data_setup.ImportRefused) as caught:
            data_setup.import_folder(source, self.target)
        self.assertEqual(caught.exception.problems, [("GOAL.DAT", "wrong")])
        self.assertIn("GOAL.DAT in", str(caught.exception))
        self.assertIn("not the right file", str(caught.exception))
        self.assertNotIn("e039", str(caught.exception))
        self.assertFalse(self.target.root.exists(), "nothing is copied from a refused folder")

    def test_a_name_in_other_case_is_found(self):
        source = self.source(files={"goal.dat": STAND_IN["GOAL.DAT"],
                                    "E039-R0005-DATE-CALL.SAV": STAND_IN["e039-r0005-date-call.sav"]})
        data_setup.import_folder(source, self.target)
        self.assertEqual(sorted(p.name for p in self.target.data.iterdir()), sorted(STAND_IN))

    def test_nothing_is_written_outside_the_data_folder(self):
        source = self.source()
        self.target.saves.mkdir(parents=True)
        career = self.target.save;career.write_bytes(b"G2C1 a career that must survive a re-import")
        # A damaged data folder is re-imported over: its files are replaced, the career is not.
        self.target.data.mkdir();(self.target.data / "GOAL.DAT").write_bytes(b"damaged")
        work = self.tmp / "cwd";work.mkdir()
        before = tree(self.tmp)
        cwd = os.getcwd();os.chdir(work)
        try:
            data_setup.import_folder(source, self.target)
        finally:
            os.chdir(cwd)
        after = tree(self.tmp)
        changed = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
        data = str(self.target.data.relative_to(self.tmp))
        self.assertTrue(changed, "the import changed nothing")
        self.assertEqual({p for p in changed if not p.startswith(data + os.sep)}, set())
        self.assertEqual(after[str(career.relative_to(self.tmp))], before[str(career.relative_to(self.tmp))])
        self.assertEqual(list(work.iterdir()), [], "nothing in the working directory")
        self.assertFalse([p for p in self.target.data.iterdir() if p.name.endswith(data_setup.PART)])


class PlaceCases(unittest.TestCase):
    def test_the_data_folder_is_per_user_and_absolute(self):
        windows = data_setup.user_root({"LOCALAPPDATA": r"C:\Users\p\AppData\Local"}, "win32")
        self.assertEqual(str(windows).replace("/", "\\").lower(), r"c:\users\p\appdata\local\goal2")
        posix = data_setup.user_root({"HOME": "/home/p"}, "linux")
        self.assertEqual(posix.as_posix(), "/home/p/.local/share/goal2")
        relative = data_setup.user_root({"LOCALAPPDATA": "relative", "USERPROFILE": r"C:\Users\p"}, "win32")
        self.assertEqual(str(relative).replace("/", "\\").lower(), r"c:\users\p\appdata\local\goal2")
        target = data_setup.Paths(posix)
        self.assertEqual((target.data.name, target.saves.name, target.saves.parent), ("data", "saves", posix))

    def test_the_manifest_holds_names_and_digests_only(self):
        for name, digest in data_setup.MANIFEST:
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotIn("/", name)
        self.assertEqual([name for name, _ in data_setup.MANIFEST], ["GOAL.DAT", "e039-r0005-date-call.sav"])

    @requires.need(files=("GOAL.DAT", "e039-r0005-date-call.sav"))
    def test_the_manifest_matches_the_owners_data_folder(self):
        self.assertEqual(data_setup.problems(requires.CACHE), [])


class EntryCases(Case):
    """The desktop's start: `_core` (the core route's window) is replaced by a recorder."""

    def start(self, argv, dialog):
        seen = []
        with mock.patch.object(data_setup, "qt_dialog", dialog), \
             mock.patch.object(entry, "_core", lambda args: seen.append(args) or 0):
            status = entry.main(argv)
        return status, seen

    def importer(self, source, calls):
        def dialog(target):
            calls.append(target)
            data_setup.import_folder(source, target)
            return True
        return dialog

    @staticmethod
    def refuse(target):
        raise AssertionError("the import dialog was shown")

    def test_first_start_imports_then_a_second_start_goes_straight_in(self):
        calls = []
        status, seen = self.start([], self.importer(self.source(), calls))
        target = data_setup.paths()
        self.assertEqual((status, len(calls), len(seen)), (0, 1, 1))
        self.assertEqual(target.root, data_setup.user_root())
        self.assertTrue(str(target.root).startswith(str(self.home)), target.root)
        args = seen[0]
        self.assertEqual((args.data, args.core_boot, args.save), (target.goal_dat, target.boot, target.save))
        for path in (args.data, args.core_boot, args.save):
            self.assertTrue(path.is_absolute(), path)
        status, seen = self.start([], self.refuse)
        self.assertEqual((status, len(seen)), (0, 1))
        self.assertEqual((seen[0].data, seen[0].core_boot), (target.goal_dat, target.boot))

    def test_closing_the_dialog_starts_nothing(self):
        status, seen = self.start([], lambda target: False)
        self.assertEqual((status, seen), (2, []))

    def test_explicit_data_bypasses_the_import(self):
        boot, data = self.tmp / "boot.sav", self.tmp / "GOAL.DAT"
        status, seen = self.start(["--core-boot", str(boot), "--data", str(data)], self.refuse)
        self.assertEqual((status, seen[0].data, seen[0].core_boot), (0, data, boot))
        self.assertEqual(seen[0].save, entry.DEVELOPER_SAVE, "a developer's run keeps its .cache/ default")
        self.assertFalse(data_setup.paths().root.exists(), "no data folder for an explicit --data")

    def test_resume_without_data_takes_the_data_folder(self):
        data_setup.import_folder(self.source(), data_setup.paths())
        career = self.tmp / "career.g2core";career.write_bytes(b"G2C1")
        status, seen = self.start(["--resume", str(career)], self.refuse)
        self.assertEqual((status, seen[0].data, seen[0].core_boot, seen[0].resume),
                         (0, data_setup.paths().goal_dat, None, career))


@requires.need(modules=("PySide6",))
class DialogCases(Case):
    def test_the_dialog_names_a_refused_folder_and_accepts_a_complete_one(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QDialog
        app = QApplication.instance() or QApplication([])
        offered = [self.source("short", files={"GOAL.DAT": STAND_IN["GOAL.DAT"]}), self.source("complete")]
        dialog = data_setup.make_dialog(self.target, choose=lambda: str(offered.pop(0)))
        self.assertIn(str(self.target.data), dialog.intro.text())
        self.assertFalse(dialog.choose_and_import())
        self.assertIn("e039-r0005-date-call.sav is missing", dialog.status.text())
        self.assertTrue(dialog.choose_and_import())
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertTrue(data_setup.complete(self.target.data))
        dialog.deleteLater();app.processEvents()


if __name__ == "__main__":
    unittest.main()
