"""[designed: owner, 2026-11-02, T147] The portable Windows build (tools/build_portable.py, tools/portable/).

From given inputs (fake interpreter archives served by file:// URLs, a fake goal2 wheel, pip replaced by a fake that
unpacks what it is asked to install) the build lays out `python/`, `pypy/` and the launcher, records where every file
came from and zips it; it refuses a download whose SHA-256 differs from the manifest, an unhashed requirement and an
original-game file; the launcher gives the workers the bundled PyPy and passes its arguments through. The real build
and its packaged smoke run on Windows in .github/workflows/package.yml."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "portable"))
import build_portable as bp  # noqa: E402
import goal2_launch  # noqa: E402

PTH = "python313.zip\r\n.\r\n\r\n# Uncomment to run site.main() automatically\r\n#import site\r\n"
PREFIX = "pypy3.11-v7.3.23-win64/"


def write_zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


class FakePip:
    """pip's stand-in: the hash-pinned wheels become a few PySide6-like files (an .exe and a .dat among them, as Qt's
    are) and a console-script launcher; a wheel path is unpacked, with goal2's own console-script .exe beside it."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, check=False):
        self.calls.append(argv)
        target = Path(argv[argv.index("--target") + 1])
        target.mkdir(parents=True, exist_ok=True)
        if "-r" in argv:
            for rel, data in {"PySide6/Qt6Core.dll": b"qt", "PySide6/designer.exe": b"tool",
                              "PySide6/resources/icudtl.dat": b"icu", "Scripts/pyside6-designer.exe": b"x"}.items():
                (target / rel).parent.mkdir(parents=True, exist_ok=True)
                (target / rel).write_bytes(data)
        else:
            with zipfile.ZipFile(argv[-2] if argv[-1] == "--no-compile" else argv[-1]) as zf:
                zf.extractall(target)
            (target / "Scripts").mkdir(exist_ok=True)
            (target / "Scripts" / "goal2.exe").write_bytes(b"launcher")
        return subprocess.CompletedProcess(argv, 0)


class Inputs:
    """A manifest, its archives and requirements, and a goal2 wheel, in a temporary folder."""

    def __init__(self, tmp: Path, wheel_extra=None, tamper=None):
        self.tmp = tmp
        src = tmp / "src"
        src.mkdir()
        cpython = write_zip(src / "python-3.13.17-embed-amd64.zip", {
            "python.exe": b"MZ cpython", "pythonw.exe": b"MZ cpythonw", "python313.dll": b"dll",
            "vcruntime140.dll": b"vc", "vcruntime140_1.dll": b"vc1", "python313.zip": b"stdlib", "python313._pth": PTH})
        pypy = write_zip(src / "pypy3.11-v7.3.23-win64.zip", {
            PREFIX + "pypy.exe": b"MZ pypy", PREFIX + "pypyw.exe": b"MZ pypyw", PREFIX + "libpypy3.11-c.dll": b"lib",
            PREFIX + "Lib/os.py": b"", PREFIX + "Lib/site-packages/README.txt": b"site"})
        members = {"goal2/__init__.py": b"", "goal2/desktop/__main__.py": b"",
                   "goal2-0.1.0.dist-info/METADATA": b"Name: goal2\n"}
        members.update(wheel_extra or {})
        self.wheel = write_zip(tmp / "goal2-0.1.0-py3-none-any.whl", members)
        self.requirements = src / "requirements-win64.txt"
        self.requirements.write_text("# pinned\nshiboken6==6.12.0 --hash=sha256:" + "a" * 64 + "\n")
        manifest = {"cpython": {"version": "3.13.17", "url": cpython.as_uri(), "strip": "",
                                "sha256": hashlib.sha256(cpython.read_bytes()).hexdigest()},
                    "pypy": {"version": "7.3.23", "url": pypy.as_uri(), "strip": PREFIX,
                             "sha256": hashlib.sha256(pypy.read_bytes()).hexdigest()},
                    "wheels": {"requirements": self.requirements.name, "platform": "win_amd64",
                               "python_version": "3.13", "implementation": "cp", "abi": "cp313"}}
        if tamper:
            manifest[tamper]["sha256"] = "0" * 64
        self.manifest = src / "manifest.json"
        self.manifest.write_text(json.dumps(manifest))
        self.downloads, self.out = tmp / "downloads", tmp / "out"
        self.pip = FakePip()

    def build(self):
        return bp.build(self.out, self.wheel, self.downloads, self.manifest, run=self.pip, python="host-python",
                        name="goal2-0.1.0-win64")


class Layout(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2 t147 "))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def test_the_build_lays_out_python_pypy_and_the_launcher_and_zips_them(self):
        inputs = Inputs(self.tmp)
        folder, archive, stats = inputs.build()
        self.assertEqual(folder, inputs.out / "goal2-0.1.0-win64")
        for rel in ("python/python.exe", "python/pythonw.exe", "python/Lib/site-packages/goal2/__init__.py",
                    "python/Lib/site-packages/PySide6/Qt6Core.dll", "pypy/pypy.exe", "pypy/Lib/os.py",
                    "pypy/Lib/site-packages/goal2/__init__.py", "pypy/vcruntime140.dll", "pypy/vcruntime140_1.dll",
                    "goal2.cmd", "goal2_launch.py", bp.RECORD):
            self.assertTrue((folder / rel).is_file(), rel)
        # the archive prefix is stripped; PyPy gets goal2 only, never the UI's wheels; no console-script launchers
        self.assertFalse((folder / "pypy" / PREFIX).exists())
        self.assertFalse((folder / "pypy/Lib/site-packages/PySide6").exists())
        for target in ("python/Lib/site-packages", "pypy/Lib/site-packages"):
            self.assertFalse((folder / target / "Scripts").exists(), target)
        # the embeddable CPython reaches its site-packages
        self.assertEqual((folder / "python/python313._pth").read_bytes(),
                         b"python313.zip\r\n.\r\nLib\\site-packages\r\nimport site\r\n")
        self.assertIn(b"\r\n", (folder / "goal2.cmd").read_bytes())
        self.assertNotIn(b"\n", (folder / "goal2.cmd").read_bytes().replace(b"\r\n", b""))
        # pip: the wheels hash-checked for the bundled CPython, goal2's wheel into both interpreters
        wheels, ui, engine = inputs.pip.calls
        site = str(folder / "python/Lib/site-packages")
        self.assertEqual(wheels[wheels.index("--target") + 1], site)
        for flag in ("--require-hashes", "--no-deps", "--only-binary"):
            self.assertIn(flag, wheels)
        self.assertEqual(wheels[wheels.index("--platform") + 1], "win_amd64")
        self.assertEqual(wheels[wheels.index("--abi") + 1], "cp313")
        self.assertEqual(wheels[wheels.index("-r") + 1], str(inputs.requirements))
        self.assertEqual(ui[ui.index("--target") + 1], site)
        self.assertIn(str(inputs.wheel), ui)
        self.assertEqual("--no-compile" in ui, sys.version_info[:2] != (3, 13))     # .pyc only for its own version
        self.assertEqual(engine[engine.index("--target") + 1], str(folder / "pypy/Lib/site-packages"))
        self.assertIn("--no-compile", engine)
        # the record: every file and its source
        record = json.loads((folder / bp.RECORD).read_text())
        self.assertEqual(set(record["files"]), bp.files_of(folder) - {bp.RECORD})
        self.assertEqual(record["files"]["python/python.exe"], "cpython")
        self.assertEqual(record["files"]["pypy/pypy.exe"], "pypy")
        self.assertEqual(record["files"]["pypy/vcruntime140.dll"], "cpython")
        self.assertEqual(record["files"]["python/Lib/site-packages/PySide6/designer.exe"], "wheels")
        self.assertEqual(record["files"]["pypy/Lib/site-packages/goal2/__init__.py"], "goal2")
        self.assertEqual(record["files"]["goal2.cmd"], "launcher")
        # the ZIP: one folder, the same files, and its own check passes
        with zipfile.ZipFile(archive) as zf:
            names = {n for n in zf.namelist() if not n.endswith("/")}
        self.assertEqual(names, {f"goal2-0.1.0-win64/{r}" for r in bp.files_of(folder)})
        self.assertEqual(bp.check_zip(archive)["entries"], len(names))
        self.assertEqual((stats["zip_bytes"], stats["files"]), (archive.stat().st_size, len(names)))
        # the downloads were fetched from the manifest's URLs and kept
        self.assertEqual(sorted(p.name for p in inputs.downloads.iterdir()),
                         ["pypy3.11-v7.3.23-win64.zip", "python-3.13.17-embed-amd64.zip"])

    def test_a_download_whose_sha256_differs_from_the_manifest_is_refused(self):
        for which in ("cpython", "pypy"):
            with self.subTest(download=which):
                (self.tmp / which).mkdir()
                inputs = Inputs(self.tmp / which, tamper=which)
                with self.assertRaisesRegex(bp.BuildError, "is not the manifest's .*; refused"):
                    inputs.build()
                self.assertFalse(any(inputs.downloads.glob(f"{'pypy' if which == 'pypy' else 'python'}*.zip")))
                self.assertEqual(inputs.pip.calls, [])
                self.assertFalse((inputs.out / "goal2-0.1.0-win64.zip").exists())

    def test_a_cached_download_that_was_changed_is_refused(self):
        inputs = Inputs(self.tmp)
        inputs.downloads.mkdir()
        (inputs.downloads / "python-3.13.17-embed-amd64.zip").write_bytes(b"not the pinned file")
        with self.assertRaisesRegex(bp.BuildError, "python-3.13.17-embed-amd64.zip: SHA-256 .* refused"):
            inputs.build()
        self.assertFalse((inputs.downloads / "python-3.13.17-embed-amd64.zip").exists())

    def test_a_requirement_without_version_and_sha256_is_refused(self):
        inputs = Inputs(self.tmp)
        for line in ("shiboken6==6.12.0", "shiboken6 --hash=sha256:" + "a" * 64):
            with self.subTest(line=line):
                inputs.requirements.write_text(line + "\n")
                with self.assertRaisesRegex(bp.BuildError, "not pinned by version and SHA-256"):
                    inputs.build()

    def test_the_real_manifest_pins_every_download(self):
        manifest = json.loads(bp.MANIFEST.read_text())
        for key in ("cpython", "pypy"):
            self.assertRegex(manifest[key]["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn(manifest[key]["version"].split()[0], manifest[key]["url"])
        self.assertTrue(manifest["cpython"]["url"].endswith("-embed-amd64.zip"))
        self.assertIn("pypy3.11-", manifest["pypy"]["url"])
        lines = bp.requirements_hashed(bp.PORTABLE / manifest["wheels"]["requirements"])
        names = {l.split("==")[0] for l in lines}
        self.assertLessEqual({"pyside6", "unicorn", "pygame-ce"}, names)


class Originals(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2 t147 "))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def test_an_original_game_file_in_the_folder_is_refused(self):
        for name in ("goal2/GOAL.DAT", "goal2/data/GOAL.EXE", "goal2/x.sav", "goal2/y.g2save", "goal2/z.bat"):
            with self.subTest(file=name):
                (self.tmp / name.replace("/", "_")).mkdir()
                inputs = Inputs(self.tmp / name.replace("/", "_"), wheel_extra={name: b"original bytes"})
                with self.assertRaisesRegex(bp.BuildError, r"original-game file type .*" + Path(name).name + r" \(from goal2\)"):
                    inputs.build()
                self.assertFalse((inputs.out / "goal2-0.1.0-win64.zip").exists())

    def test_the_zip_check_refuses_an_unrecorded_file_and_an_original_s_bytes(self):
        inputs = Inputs(self.tmp)
        _, archive, _ = inputs.build()
        originals = self.tmp / "cache"
        originals.mkdir()
        (originals / "GOAL.EXE").write_bytes(b"MZ pypy")              # the bytes of an entry, under an original's name
        with self.assertRaisesRegex(bp.BuildError, "pypy/pypy.exe is the original-game file .*GOAL.EXE"):
            bp.check_zip(archive, originals)
        (originals / "GOAL.EXE").write_bytes(b"the original game")
        self.assertEqual(bp.check_zip(archive, originals)["originals_compared"], 1)
        with zipfile.ZipFile(archive, "a") as zf:
            zf.writestr("goal2-0.1.0-win64/GOAL.DAT", b"slipped in")
        with self.assertRaisesRegex(bp.BuildError, r"entries outside the record: \['GOAL.DAT'\]"):
            bp.check_zip(archive)

    def test_the_zip_check_needs_originals_to_compare_with(self):
        inputs = Inputs(self.tmp)
        _, archive, _ = inputs.build()
        (self.tmp / "empty").mkdir()
        with self.assertRaisesRegex(bp.BuildError, "no original-game file under"):
            bp.check_zip(archive, self.tmp / "empty")


class Launcher(unittest.TestCase):
    def test_it_gives_the_workers_the_bundled_pypy_and_passes_its_arguments_through(self):
        root = Path(tempfile.gettempdir()) / "goal2 portable ä"
        seen = {}

        def run(module, run_name, alter_sys):
            seen.update(module=module, run_name=run_name, argv=list(sys.argv), env=dict(os.environ))
        with patch.dict(os.environ, {"PYTHONPATH": "elsewhere", "PYTHONHOME": "x", "KEEP": "1"}), \
                patch.object(sys, "argv", ["goal2_launch.py"]):
            goal2_launch.main(["--data", "my data/GOAL.DAT", "--help"], root=root, run=run)
        self.assertEqual((seen["module"], seen["run_name"]), ("goal2.desktop", "__main__"))
        self.assertEqual(seen["argv"][1:], ["--data", "my data/GOAL.DAT", "--help"])
        env = seen["env"]
        self.assertEqual(env["GOAL2_ENGINE_PYTHON"], str(root / "pypy" / "pypy.exe"))
        self.assertEqual((env["PYTHONSAFEPATH"], env["PYTHONNOUSERSITE"], env["KEEP"]), ("1", "1", "1"))
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("PYTHONHOME", env)

    def test_its_own_folder_is_the_root(self):
        seen = {}
        with patch.dict(os.environ, {}), patch.object(sys, "argv", ["goal2_launch.py", "--x"]):
            goal2_launch.main(run=lambda *a, **k: seen.update(env=os.environ["GOAL2_ENGINE_PYTHON"], argv=sys.argv[1:]))
        self.assertEqual(seen, {"env": str(Path(goal2_launch.__file__).resolve().parent / "pypy" / "pypy.exe"),
                                "argv": ["--x"]})

    def test_it_runs_the_desktop_with_the_arguments(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools/portable/goal2_launch.py"), "--help"],
                           capture_output=True, text=True, cwd=tempfile.gettempdir(),
                           env=dict(os.environ, PYTHONPATH=str(ROOT)), timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("goal2 desktop country management", r.stdout)
        self.assertIn("--core-boot", r.stdout)

    def test_the_cmd_starts_the_launcher_under_pythonw_with_every_argument(self):
        text = (ROOT / "tools/portable/goal2.cmd").read_text()
        self.assertIn('"%~dp0python\\pythonw.exe" "%~dp0goal2_launch.py" %*\n', text)
        self.assertIn("exit /b %ERRORLEVEL%", text)


if __name__ == "__main__":
    unittest.main()
