"""[designed: owner, 2026-11-02, T153] The first-run import of the player's data folder (docs/packaging.md, "The
player's data folder").

The portable build ships nothing of the original game (CLAUDE.md rule 14). The desktop's default start, the core
route's new career (`--core-boot`, docs/desktop-management.md), needs two files of the player's own copy of goal
(version 2): GOAL.EXE, which the core boots from its first instruction to the program's DOS date call [designed:
owner, 2026-11-13, #705; T222] (goal2/core/exeboot.py, docs/core.md "The new game"), and GOAL.DAT, the only file the
original's new game opens [confirmed: F032] (goal2/core/runner.py `DATA_NAME`). The recorded emulator state the
core booted from before T222 (e039-r0005-date-call.sav) is not asked for: a player cannot make it.

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
# time and never enter the repository. [confirmed: GOAL.DAT's is the released file's, goal2/core/runner.py's check;
# GOAL.EXE's the registered one's, goal2/engine/original_match/build.py:3, goal2/core/exeboot.py SHA256]
MANIFEST = (
    ("GOAL.DAT", "bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca"),
    ("GOAL.EXE", "a6928b0bb7cda0303ac8daf8690efc56ef1792dddaccb5c6f3d85af1f68d3664"),
)
DATA_NAME, BOOT_NAME = (name for name, _ in MANIFEST)
# WINDOW_MANIFEST: what the new window (goal2/ui, docs/ui.md) needs instead. [designed: owner, 2026-11-03, #527, D2;
# T163, #537] Its new careers run on the Python route (goal2/desktop/model.py `DesktopModel`), which starts from the
# E010 half-time template and GOAL.DAT, so the Core's boot state is not asked for. [confirmed: the template's digest
# is the one docs/evidence/T80/resources-and-source.json records for e010-r0008-halftime.sav; GOAL.DAT's is
# MANIFEST's]
TEMPLATE_NAME = "e010-r0008-halftime.sav"
WINDOW_MANIFEST = (
    (DATA_NAME, MANIFEST[0][1]),
    (TEMPLATE_NAME, "ae2935b9c490745450462b981eb133e611bc72de4abfb11aba3e850caf4e9949"),
)
# OPTIONAL: files taken when the offered folder has them, checked like MANIFEST's, but whose absence does not stop
# the import. [designed: owner, 2026-11-03, #526] GOAL.HLP, the original's help file, for the redesigned UI's F1
# (docs/design/ui-2026-11, S22). [confirmed: goal2-archaeology artifacts/known.json, GOAL.HLP, 32569 bytes]
OPTIONAL = (
    ("GOAL.HLP", "2f3be8648a52045b6f7af1f41cba020d6a662229e5db499e203c5d0957308f60"),
)
HELP_NAME = OPTIONAL[0][0]
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
    flavour = PureWindowsPath if windows else PurePosixPath
    if windows:
        local = env.get("LOCALAPPDATA", "")
        base = flavour(local) if _absolute(local, windows) else _home(env, windows) / "AppData" / "Local"
        root = base / "goal2"
    else:
        root = _home(env, windows) / ".local" / "share" / "goal2"
    if not root.is_absolute():
        raise SetupError(f"cannot place goal2's data folder: {root} is not an absolute path")
    return Path(root)


def _absolute(value, windows) -> bool:
    return bool(value) and (PureWindowsPath if windows else PurePosixPath)(value).is_absolute()


def _home(env, windows):
    """The home folder in the target platform's path flavour (so a check of one platform's paths runs anywhere)."""
    flavour = PureWindowsPath if windows else PurePosixPath
    for key in (("USERPROFILE", "HOME") if windows else ("HOME",)):
        if _absolute(env.get(key, ""), windows):
            return flavour(env[key])
    return flavour(Path.home())


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

    @property
    def help(self) -> Path:
        return self.data / HELP_NAME


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


def problems(folder, manifest=None) -> list:
    """What `folder` lacks of MANIFEST (or of `manifest`, a list like it): (name, 'missing') or (name, 'wrong') for
    each file absent, unreadable or with another digest; and (name, 'wrong') for an OPTIONAL file that is there but
    not the right one. Empty when the folder is complete."""
    manifest = MANIFEST if manifest is None else tuple(manifest)
    found = []
    for name, digest in manifest + OPTIONAL:
        path = find(folder, name)
        if path is None:
            if (name, digest) in manifest:
                found.append((name, "missing"))
            continue
        try:
            ok = sha256(path) == digest
        except OSError:
            ok = False
        if not ok:
            found.append((name, "wrong"))
    return found


def complete(folder, manifest=None) -> bool:
    return Path(folder).is_dir() and not problems(folder, manifest)


def describe(found, source) -> str:
    """The problems in plain words, one line per file."""
    lines = []
    for name, kind in found:
        if kind == "missing":
            lines.append(f"{name} is missing: it is not in {source}.")
        else:
            lines.append(f"{name} in {source} is not the right file: its contents differ from the one goal2 needs.")
    return "\n".join(lines)


def import_folder(source, target=None, manifest=None) -> list:
    """Check every file of MANIFEST in `source` (and of OPTIONAL that `source` has), then copy them into the data folder (`target`, a Paths; default
    the user's). Nothing is copied unless every file is right (ImportRefused names each that is not). A file is
    written beside its final name, checked again, then moved over it; one already right is left alone. Returns the
    names copied. Only the data folder is written: never `source`, the saves folder or the working directory.
    `manifest` replaces MANIFEST (the new window passes WINDOW_MANIFEST)."""
    manifest = MANIFEST if manifest is None else tuple(manifest)
    source = Path(source)
    target = target if target is not None else paths()
    if not source.is_dir():
        raise ImportRefused(source, [(name, "missing") for name, _ in manifest])
    found = problems(source, manifest)
    if found:
        raise ImportRefused(source, found)
    copied = []
    try:
        target.data.mkdir(parents=True, exist_ok=True)
        for name, digest in manifest + tuple(o for o in OPTIONAL if find(source, o[0]) is not None):
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


INTRO = ("goal2 needs two files of your copy of goal (version 2): {names}.\n"
         "It also takes the original's help file, {help}, when the folder has it.\n"
         "Choose the folder that holds them. goal2 checks each and copies it to\n{data}\n"
         "Your saved careers, in {saves}, are never touched.")


def intro(target) -> str:
    return INTRO.format(names=" and ".join(name for name, _ in MANIFEST), help=HELP_NAME, data=target.data,
                        saves=target.saves)


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
            self.choose = choose or (lambda: QFileDialog.getExistingDirectory(self, "The folder with GOAL.EXE and GOAL.DAT") or None)
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
