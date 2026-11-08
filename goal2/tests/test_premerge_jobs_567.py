"""[designed: owner, 2026-11-03, #567] A machine that hosts several runners, or a runner and a working session,
sets each gate's job count with GOAL2_GATE_JOBS (written into the runner's .env by tools/runner/); without it the
gate keeps min(8, cores)."""
import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tools" / "runner"


def gate():
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        return importlib.import_module("check_premerge")
    finally:
        sys.path.remove(str(ROOT / "tools"))


class GateJobs(unittest.TestCase):
    def test_unset_keeps_eight_or_the_cores(self):
        g = gate()
        self.assertEqual(g.default_jobs({}, 20), (8, "min(8, cores)"))
        self.assertEqual(g.default_jobs({}, 4), (4, "min(8, cores)"))
        self.assertEqual(g.default_jobs({}, None), (2, "min(8, cores)"))
        self.assertEqual(g.default_jobs({"GOAL2_GATE_JOBS": ""}, 20), (8, "min(8, cores)"))

    def test_the_machine_setting_wins(self):
        self.assertEqual(gate().default_jobs({"GOAL2_GATE_JOBS": "6"}, 20), (6, "GOAL2_GATE_JOBS"))

    def test_a_bad_setting_is_refused_not_ignored(self):
        for bad in ("0", "-2", "six", "6.5"):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                gate().default_jobs({"GOAL2_GATE_JOBS": bad}, 20)

    def test_both_setup_scripts_write_it_into_the_runners_env_and_restart_nothing_themselves(self):
        linux = (RUNNER / "setup-linux.sh").read_text()
        windows = (RUNNER / "setup-windows.ps1").read_text()
        self.assertIn("GOAL2_GATE_JOBS", linux)
        self.assertIn('"$DIR/.env"', linux)
        self.assertIn("$GateJobs", windows)
        self.assertIn("'.env'", windows)
        for text in (linux, windows):
            self.assertIn("restart the runner when it is idle", text)


    @unittest.skipUnless(Path("/bin/bash").exists(), "needs bash (Linux)")
    def test_linux_writes_one_line_keeps_the_others_and_refuses_zero(self):
        import shutil, subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            home, bin_ = Path(tmp), Path(tmp) / "bin"
            bin_.mkdir()
            runner = home / "runner"
            runner.mkdir()
            (runner / ".runner").write_text("{}")          # registered already: the script keeps it
            (runner / ".env").write_text("LANG=C.UTF-8\nGOAL2_GATE_JOBS=8\n")
            listing = "".join(f"\\t{lib} (libc6,x86-64) => /x/{lib}\\n" for lib in
                              ("libEGL.so.1", "libGL.so.1", "libxkbcommon.so.0", "libfontconfig.so.1", "libdbus-1.so.3"))
            stubs = {n: "#!/bin/sh\nexit 0\n" for n in ("git", "curl", "unzip", "sha256sum", "tar", "uv", "systemctl")}
            stubs["ldconfig"] = f"#!/bin/sh\nprintf '{listing}'\n"
            for name, body in stubs.items():
                (bin_ / name).write_text(body)
                (bin_ / name).chmod(0o755)
            for tool in ("grep", "mkdir", "cat", "mv", "touch", "head"):
                (bin_ / tool).symlink_to(shutil.which(tool))

            def run(jobs):
                return subprocess.run(["/bin/bash", str(RUNNER / "setup-linux.sh")], capture_output=True, text=True,
                                      env={"PATH": str(bin_), "HOME": tmp, "GOAL2_RUNNER_NAME": "test",
                                           "GOAL2_RUNNER_DIR": str(runner), "GOAL2_GATE_JOBS": jobs, "USER": "test"}, timeout=60)
            for jobs in ("6", "5"):
                done = run(jobs)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("restart the runner when it is idle", done.stdout)
            self.assertEqual((runner / ".env").read_text(), "LANG=C.UTF-8\nGOAL2_GATE_JOBS=5\n")
            done = run("0")
            self.assertEqual(done.returncode, 1)
            self.assertEqual((runner / ".env").read_text(), "LANG=C.UTF-8\nGOAL2_GATE_JOBS=5\n")

if __name__ == "__main__":
    unittest.main()
