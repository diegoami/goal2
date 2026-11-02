"""[designed: owner, 2026-11-02, T153] The first-run import of the player's data folder (docs/packaging.md, "The
player's data folder").

The portable build ships nothing of the original game (CLAUDE.md rule 14). The desktop's default start, the core
route's new career (`--core-boot`, docs/desktop-management.md), needs two of the owner's private files: the recorded
emulator state at the DOS date call, which holds GOAL.EXE in memory (docs/core.md), and GOAL.DAT, the only file the
original's new game opens [confirmed: F032] (goal2/core/runner.py `DATA_NAME`). A player's own goal install cannot
produce the recorded state, so the import takes the owner's data folder, the one `tools/artifacts.py pull` fills
(docs/artifacts.md).

Where the files go [designed: owner, 2026-11-02, T153]: a per-user folder, `%LOCALAPPDATA%\\goal2\\data` on Windows and
`~/.local/share/goal2/data` elsewhere; the desktop's saves go to `saves` beside it. Both are absolute, never relative
to the working directory. The import writes only into the data folder, and only the files of `MANIFEST`: it never
touches the saves, so a re-import cannot overwrite a career.

Usable without Qt: `python -m goal2.desktop.data_setup FOLDER` imports FOLDER the way the dialog does, and
`python -m goal2.desktop.data_setup --check` names what the data folder lacks.
"""
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

# MANIFEST: the names and SHA-256 digests of the original-game files the desktop's default start needs. It holds no
# byte of those files, only what each must hash to; the files themselves come from the player's data folder at run
# time and never enter the repository. [confirmed: goal2/core/cycle_evidence.py's `boot` and `data`, the same two
# digests; GOAL.DAT's is the released file's, goal2/core/runner.py's check]
MANIFEST = (
    ("GOAL.DAT", "bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca"),
    ("e039-r0005-date-call.sav", "0d9c683023c7327f17bfc29900f2eff4e703641d21d3f353693f09654688494b"),
)
DATA_NAME, BOOT_NAME = (name for name, _ in MANIFEST)
SAVE_NAME = "desktop.g2core"   # [designed: T153] the core route's default save in the saves folder
PART = ".part"                 # a copy being written, beside its final name in the data folder


class SetupError(RuntimeError):
    """The data folder cannot be located or written."""


class ImportRefused(SetupError):
    """The folder offered does not hold every file of MANIFEST, each with its digest; `problems` are
    (name, 'missing' | 'wrong') pairs and the message names each in plain words."""

    def __init__(self, source, problems):
        self.source, self.problems = Path(source), list(problems)
        super().__init__(describe(self.problems, self.source))


def user_root(env=None, platform=None) -> Path:
    """The per-user goal2 folder: `%LOCALAPPDATA%\\goal2` on Windows, `~/.local/share/goal2` elsewhere. Always
    absolute: a relative or missing LOCALAPPDATA falls back to the home folder's `AppData\\Local`."""
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    windows = platform.startswith("win")
    if windows:
        local = env.get("LOCALAPPDATA", "")
        base = Path(local) if _absolute(local, windows) else _home(env, windows) / "AppData" / "Local"
        root = base / "goal2"
    else:
        root = _home(env, windows) / ".local" / "share" / "goal2"
    if not _absolute(str(root), windows):
        raise SetupError(f"cannot place goal2's data folder: {root} is not an absolute path")
    return root


def _absolute(value, windows) -> bool:
    return bool(value) and (PureWindowsPath if windows else PurePosixPath)(value).is_absolute()


def _home(env, windows) -> Path:
    for key in (("USERPROFILE", "HOME") if windows else ("HOME",)):
        if _absolute(env.get(key, ""), windows):
            return Path(env[key])
    return Path.home()


@dataclass(frozen=True)
class Paths:
    """The per-user folders and the default paths the desktop starts with."""
    root: Path

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def saves(self) -> Path:
        return self.root / "saves"

    @property
    def goal_dat(self) -> Path:
        return self.data / DATA_NAME

    @property
    def boot(self) -> Path:
        return self.data / BOOT_NAME

    @property
    def save(self) -> Path:
        return self.saves / SAVE_NAME


def paths(root=None) -> Paths:
    return Paths(Path(root) if root is not None else user_root())


def sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def find(folder, name):
    """`name` in `folder`: the exact name, else the one entry that matches it ignoring case; None if absent."""
    folder = Path(folder)
    exact = folder / name
    if exact.is_file():
        return exact
    try:
        matches = [entry for entry in folder.iterdir() if entry.name.lower() == name.lower() and entry.is_file()]
    except OSError:
        return None
    return matches[0] if len(matches) == 1 else None


def problems(folder) -> list:
    """What `folder` lacks of MANIFEST: (name, 'missing') or (name, 'wrong') for each file absent, unreadable or
    with another digest. Empty when the folder is complete."""
    found = []
    for name, digest in MANIFEST:
        path = find(folder, name)
        if path is None:
            found.append((name, "missing"))
            continue
        try:
            ok = sha256(path) == digest
        except OSError:
            ok = False
        if not ok:
            found.append((name, "wrong"))
    return found


def complete(folder) -> bool:
    return Path(folder).is_dir() and not problems(folder)


def describe(found, source) -> str:
    """The problems in plain words, one line per file."""
    lines = []
    for name, kind in found:
        if kind == "missing":
            lines.append(f"{name} is missing: it is not in {source}.")
        else:
            lines.append(f"{name} in {source} is not the right file: its contents differ from the one goal2 needs.")
    return "\n".join(lines)


def import_folder(source, target=None) -> list:
    """Check every file of MANIFEST in `source`, then copy them into the data folder (`target`, a Paths; default
    the user's). Nothing is copied unless every file is right (ImportRefused names each that is not). A file is
    written beside its final name, checked again, then moved over it; one already right is left alone. Returns the
    names copied. Only the data folder is written: never `source`, the saves folder or the working directory."""
    source = Path(source)
    target = target if target is not None else paths()
    if not source.is_dir():
        raise ImportRefused(source, [(name, "missing") for name, _ in MANIFEST])
    found = problems(source)
    if found:
        raise ImportRefused(source, found)
    copied = []
    try:
        target.data.mkdir(parents=True, exist_ok=True)
        for name, digest in MANIFEST:
            final = target.data / name
            if final.is_file() and sha256(final) == digest:
                continue
            part = target.data / (name + PART)
            with open(find(source, name), "rb") as src, open(part, "wb") as dst:
                for block in iter(lambda: src.read(1 << 20), b""):
                    dst.write(block)
            if sha256(part) != digest:
                part.unlink()
                raise SetupError(f"{name} changed while it was copied from {source}; try again")
            os.replace(part, final)
            copied.append(name)
    except OSError as exc:
        raise SetupError(f"cannot write goal2's data folder {target.data}: {exc}") from exc
    return copied


def ensure(target=None, dialog=None):
    """The default paths once the data folder is complete: straight away if it is, else after the import dialog
    (`dialog(target)` returns True once it imported; default the Qt one). None if the player closed the dialog."""
    target = target if target is not None else paths()
    if complete(target.data):
        return target
    run = dialog if dialog is not None else qt_dialog
    return target if run(target) and complete(target.data) else None


INTRO = ("goal2 needs two files from your data folder (the folder tools/artifacts.py pull fills): {names}.\n"
         "Choose the folder that holds them. goal2 checks each and copies it to\n{data}\n"
         "Your saved careers, in {saves}, are never touched.")


def intro(target) -> str:
    return INTRO.format(names=" and ".join(name for name, _ in MANIFEST), data=target.data, saves=target.saves)


def make_dialog(target, choose=None):
    """The import dialog over `target` (a Paths). `choose()` returns the folder the player picked or None (default:
    the system's folder chooser). Choose folder imports the folder; a refused one is named in the dialog, which
    stays open for another; a complete import accepts the dialog."""
    from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

    class ImportDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("goal2 — Import your data folder")
            self.setObjectName("dataSetup")
            layout = QVBoxLayout(self)
            self.intro = QLabel(intro(target));self.intro.setWordWrap(True);self.intro.setObjectName("dataIntro")
            self.status = QLabel("");self.status.setWordWrap(True);self.status.setObjectName("dataStatus")
            self.status.setStyleSheet("color:#ff5555;font-weight:700;")
            layout.addWidget(self.intro);layout.addWidget(self.status)
            row = QHBoxLayout()
            self.choose_button = QPushButton("Choose folder…");self.choose_button.setObjectName("dataChoose")
            self.quit_button = QPushButton("Quit");self.quit_button.setObjectName("dataQuit")
            self.choose_button.clicked.connect(self.choose_and_import);self.quit_button.clicked.connect(self.reject)
            row.addWidget(self.choose_button);row.addStretch(1);row.addWidget(self.quit_button)
            layout.addLayout(row)
            self.choose = choose or (lambda: QFileDialog.getExistingDirectory(self, "The folder with GOAL.DAT") or None)
            self.resize(760, 260)

        def choose_and_import(self):
            folder = self.choose()
            if not folder:
                return False
            try:
                import_folder(folder, target)
            except SetupError as exc:
                self.status.setText(str(exc))
                return False
            self.status.setText("")
            self.accept()
            return True

    return ImportDialog()


def qt_dialog(target) -> bool:
    """Show the import dialog until the folder is imported (True) or the player quits (False)."""
    from PySide6.QtWidgets import QApplication, QDialog
    QApplication.instance() or QApplication(sys.argv[:1])
    dialog = make_dialog(target)
    return dialog.exec() == QDialog.DialogCode.Accepted


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Import the player's data folder into goal2's per-user data folder")
    parser.add_argument("folder", nargs="?", type=Path, help="the folder holding " + " and ".join(n for n, _ in MANIFEST))
    parser.add_argument("--check", action="store_true", help="only say whether the data folder is complete")
    args = parser.parse_args(argv)
    target = paths()
    if args.check or args.folder is None:
        found = problems(target.data) if target.data.is_dir() else [(name, "missing") for name, _ in MANIFEST]
        print(describe(found, target.data) if found else f"{target.data} is complete.")
        return 1 if found else 0
    try:
        copied = import_folder(args.folder, target)
    except SetupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Imported {', '.join(copied) or 'nothing new'} into {target.data}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
