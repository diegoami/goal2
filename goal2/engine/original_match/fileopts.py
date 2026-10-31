"""The path options of the heavy entry points (#328): one definition of what a path must be, used by validation and by the run.

A command line is refused before a heavy-job slot is taken (runtime/heavy_slot.py), so a path option has to be checked by
the same operation the run applies to it later, or a path the check accepts fails after the queue, and a path the check
refuses would have worked. Each kind has a `check_*` (what validation calls, and the run calls first) and the operation
itself, which runs the check and then does the work:

    input            check_input / read_input           --image, --mask, the cached reference: a readable, regular file
    new output       check_new_output / create_new_output   --json, --find-ranges: created exclusively, never overwritten
    log output       check_log_output                    --out: appended to, resumed if it exists, its folders created
    folder output    check_folder_output                 --checkpoint: a folder files are written in, made if missing (#359)

Every refusal raises PathError("<option> <path>: <why>"). Nothing here needs the run (no image, no download)."""
import os
import stat


class PathError(Exception):
    """A path option that cannot be used the way the run uses it."""


def _fail(option, path, why):
    raise PathError(f"{option} {path}: {why}")


def _reason(e):
    return e.strerror or type(e).__name__


def check_input(path, option):
    """`path` is a regular file this process can open for reading (a symlink to one is fine; a broken link is not)."""
    try:
        mode = os.stat(path).st_mode                # "" is a missing file here, as it is to open()
        if stat.S_ISREG(mode):
            open(path, "rb").close()                  # the operation itself, not os.access: it is what the run does
    except FileNotFoundError:
        _fail(option, path, "does not exist (or its link points nowhere)")
    except OSError as e:
        _fail(option, path, f"cannot be read ({_reason(e)})")
    if not stat.S_ISREG(mode):                        # a folder, a FIFO (opening one would wait for a writer), a device
        _fail(option, path, "is not a file")


def read_input(path, option):
    """The bytes of an input file."""
    check_input(path, option)
    with open(path, "rb") as f:
        return f.read()


def _folder_is_writable(folder, option, path):
    if not os.path.isdir(folder):
        _fail(option, path, "its folder does not exist")
    if not os.access(folder, os.W_OK | os.X_OK):
        _fail(option, path, "its folder is not writable")


def check_new_output(path, option):
    """`path` can be created with open(path, "x"): nothing is there (not a file, a folder, or a symlink, broken or not) and
    its folder is an existing, writable folder."""
    if path == "":
        _fail(option, path, "is empty")
    if os.path.lexists(path):
        _fail(option, path, "exists (an output is never overwritten)")
    _folder_is_writable(os.path.dirname(path) or ".", option, path)


def create_new_output(path, option):
    """The file object of a newly created output (text mode)."""
    check_new_output(path, option)
    return open(path, "x")


def check_log_output(path, option):
    """`path` can be read if it exists and appended to, creating it and its missing folders: an existing path is a regular
    file this process can read and write (a broken link is refused); a missing one has an existing, writable folder above
    it, nearest first, with no file in the way."""
    if path == "":
        _fail(option, path, "is empty")
    if os.path.lexists(path):
        if not os.path.exists(path):
            _fail(option, path, "is a broken link")
        check_input(path, option)
        if not os.access(path, os.W_OK):
            _fail(option, path, "is not writable")
        return
    folder = os.path.dirname(path) or "."
    while not os.path.lexists(folder):
        folder = os.path.dirname(folder) or "."
    if not os.path.isdir(folder):
        _fail(option, path, "cannot create its folder (a file is in the way)")
    if not os.access(folder, os.W_OK | os.X_OK):
        _fail(option, path, "its folder is not writable")


def check_folder_output(path, option):
    """`path` is a folder files can be created and replaced in, or a missing one that can be made with its missing folders:
    an existing path is a folder (a symlink to one is fine) this process can write in; a missing one has an existing,
    writable folder above it, nearest first, with no file in the way."""
    if path == "":
        _fail(option, path, "is empty")
    if os.path.lexists(path):
        if not os.path.exists(path):
            _fail(option, path, "is a broken link")
        if not os.path.isdir(path):
            _fail(option, path, "is not a folder")
        if not os.access(path, os.W_OK | os.X_OK):
            _fail(option, path, "is not writable")
        return
    folder = os.path.dirname(path) or "."
    while not os.path.lexists(folder):
        folder = os.path.dirname(folder) or "."
    if not os.path.isdir(folder):
        _fail(option, path, "cannot create its folder (a file is in the way)")
    if not os.access(folder, os.W_OK | os.X_OK):
        _fail(option, path, "its folder is not writable")
