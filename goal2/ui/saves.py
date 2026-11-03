"""The new window's saved games: one file per save, under a free name, in the data root's `saves` folder.

[designed: owner decisions 4 and 8, #526; T163, #537] S02 lists the saves by the free names they were saved under, not
by file names. The name is stored with the save, so a file name is only derived from it, safely, and the list shows
the stored name. T168 adds saving under a name from the desk (`write` is the writer it calls); this module defines
the format and reads it.

The format [designed: T163]: a zip file named `<derived name>.g2game` holding two members,
- `goal2-save.json`: `{"format": "goal2-named-save", "version": 1, "name": <free name>, "saved": <ISO 8601 time,
  UTC>}`;
- `session.g2save`: the Python route's own session save, byte for byte as `DesktopModel.save` writes it
  (goal2/game/session_save.py), so the career is read back only by the model's validating loader
  (`DesktopModel.from_save`), never by this module.

Qt-free.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

FORMAT = "goal2-named-save"
VERSION = 1
SUFFIX = ".g2game"
META = "goal2-save.json"
SESSION = "session.g2save"
NAME_MAX = 32   # [designed: T163] a save's free name fits S02's name column at 16 px
# Names Windows reserves for devices, refused as file names whatever their extension. [derived: the Windows file
# naming rules]
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}


class SaveError(ValueError):
    """A save that cannot be written or read; the message says why in plain words."""


def clean_name(name) -> str:
    """The free name as stored: stripped, 1 to NAME_MAX printable characters."""
    if not isinstance(name, str):
        raise SaveError("a save's name must be text")
    name = " ".join(name.split())
    if not name:
        raise SaveError("a save needs a name")
    if len(name) > NAME_MAX:
        raise SaveError(f"a save's name has at most {NAME_MAX} characters")
    if not name.isprintable():
        raise SaveError("a save's name holds only printable characters")
    return name


def file_stem(name) -> str:
    """A file name for the free name, safe on every system: letters, digits, '-' and '_' only, lower case, never a
    name Windows reserves."""
    stem = re.sub(r"[^a-z0-9_]+", "-", clean_name(name).lower()).strip("-_") or "save"
    if stem in _RESERVED:
        stem = f"{stem}-save"
    return stem[:NAME_MAX]


def path_for(folder, name) -> Path:
    """Where `name` is saved in `folder`: its own file again when a save of that name is there, else a new file
    (`-2`, `-3`… when another name derives the same stem)."""
    folder = Path(folder)
    name = clean_name(name)
    stem = file_stem(name)
    for n in range(1, 1000):
        path = folder / (f"{stem}{SUFFIX}" if n == 1 else f"{stem}-{n}{SUFFIX}")
        if not path.exists():
            return path
        try:
            if read_meta(path)[0] == name:
                return path
        except SaveError:
            pass
    raise SaveError(f"too many saves named like {name!r} in {folder}")


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def write(model, folder, name, saved=None) -> Path:
    """Save `model`'s career in `folder` under the free `name`; returns the file. The session is written by the
    model's own save (`DesktopModel.save`), then stored with the name, and the file replaces any older one only once
    it is complete."""
    name = clean_name(name)
    saved = saved if saved is not None else now()
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = path_for(folder, name)
    meta = {"format": FORMAT, "version": VERSION, "name": name, "saved": saved.isoformat()}
    with tempfile.TemporaryDirectory(prefix="goal2-save-") as tmp:
        session = Path(tmp) / SESSION
        model.save(session)
        part = path.with_name(path.name + ".part")
        try:
            with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(META, json.dumps(meta, ensure_ascii=True))
                archive.write(session, SESSION)
            os.replace(part, path)
        except OSError as exc:
            raise SaveError(f"cannot write {path}: {exc}") from exc
    model.save_path = path
    return path


def read_meta(path):
    """The stored name and time of a save: (name, saved), or SaveError saying why it cannot be read."""
    try:
        with zipfile.ZipFile(path) as archive:
            meta = json.loads(archive.read(META).decode("utf-8"))
    except FileNotFoundError as exc:
        raise SaveError("the file is no longer there") from exc
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SaveError(f"not a goal2 save ({exc})") from exc
    if not isinstance(meta, dict) or meta.get("format") != FORMAT or meta.get("version") != VERSION:
        raise SaveError("not a goal2 save of a version this goal2 reads")
    name = clean_name(meta.get("name"))
    try:
        saved = datetime.datetime.fromisoformat(meta.get("saved"))
    except (TypeError, ValueError) as exc:
        raise SaveError("the save's time cannot be read") from exc
    if saved.tzinfo is None:
        raise SaveError("the save's time has no time zone")
    return name, saved


def load(path, data_path):
    """The career in the save at `path`, read by the model's validating loader; SaveError saying why when it cannot
    be opened."""
    from goal2.desktop.model import DesktopModel
    read_meta(path)
    with tempfile.TemporaryDirectory(prefix="goal2-load-") as tmp:
        session = Path(tmp) / SESSION
        try:
            with zipfile.ZipFile(path) as archive:
                session.write_bytes(archive.read(SESSION))
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            raise SaveError(f"the career is missing from the save ({exc})") from exc
        try:
            model = DesktopModel.from_save(session, data_path)
        except ValueError as exc:
            raise SaveError(str(exc)) from exc
    model.save_path = Path(path)
    return model


@dataclass
class Entry:
    """One save of the list: its file, its stored name and time, and its career or why it cannot be opened."""
    path: Path
    name: str
    saved: datetime.datetime
    model: object = None
    error: str | None = None


def entries(folder, data_path) -> list:
    """Every save in `folder`, newest first, each read through `load`. A file that cannot be read is listed under its
    file name and its file's time, with the reason."""
    folder = Path(folder)
    found = []
    for path in sorted(folder.glob(f"*{SUFFIX}")) if folder.is_dir() else ():
        try:
            name, saved = read_meta(path)
        except SaveError as exc:
            mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
            found.append(Entry(path, path.stem, mtime, error=str(exc)))
            continue
        try:
            found.append(Entry(path, name, saved, model=load(path, data_path)))
        except SaveError as exc:
            found.append(Entry(path, name, saved, error=str(exc)))
    return sorted(found, key=lambda e: e.saved, reverse=True)


def when(saved, today=None) -> str:
    """The time a save was made, as S02 shows it: 'today 21:04', else '29 Oct', with the year when not this one."""
    local = saved.astimezone()
    today = today if today is not None else datetime.datetime.now().astimezone().date()
    if local.date() == today:
        return f"today {local:%H:%M}"
    return f"{local.day} {local:%b}" + ("" if local.year == today.year else f" {local.year}")
