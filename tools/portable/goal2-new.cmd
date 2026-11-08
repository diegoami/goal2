@echo off
rem [designed: owner, 2026-11-03, T169] The new window's launcher, beside goal2.cmd (still the default, until T170):
rem goal2_launch.py with --window new under the bundled CPython's pythonw.exe, so the same environment as
rem goal2.cmd's (the bundled PyPy for the engine), then goal2.ui with every argument (docs/packaging.md).
"%~dp0python\pythonw.exe" "%~dp0goal2_launch.py" --window new %*
exit /b %ERRORLEVEL%
