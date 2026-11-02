@echo off
rem [designed: owner, 2026-11-02, T147] The portable build's launcher: goal2_launch.py beside this file, under
rem the bundled CPython's pythonw.exe, with every argument passed through. %~dp0 is this file's folder, so it
rem runs from any working directory and any path (docs/packaging.md).
"%~dp0python\pythonw.exe" "%~dp0goal2_launch.py" %*
exit /b %ERRORLEVEL%
