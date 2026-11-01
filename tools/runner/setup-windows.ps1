# [designed: owner, 2026-11-01, #493] Make this Windows PC a goal2 slow-test runner: GitHub's runner,
# checksum-verified, registered for diegoami/goal2 with the label goal2-slow only, started hidden at logon
# (no admin: not a service). The owner runs it on each of their own PCs; every run pulls the original-game
# files from the owner's Drive, so never on a computer someone else uses.
#
#   powershell -ExecutionPolicy Bypass -File tools\runner\setup-windows.ps1              # token from gh
#   powershell -ExecutionPolicy Bypass -File tools\runner\setup-windows.ps1 -Token <t>   # or Settings > Actions > Runners
#
# -Dir (default %USERPROFILE%\ghr-goal2) and -Name (default goal2-<computer>) override the folder and the
# name. Run again to repair the logon start; an existing registration is kept.
param(
    [string]$Token = $env:GOAL2_RUNNER_TOKEN,
    [string]$Dir = "$env:USERPROFILE\ghr-goal2",
    [string]$Name = "goal2-$($env:COMPUTERNAME.ToLower())"
)
$ErrorActionPreference = 'Stop'
$Repo = 'diegoami/goal2'
$Label = 'goal2-slow'

# windows-slow.yml runs Git Bash by this short path (bash on PATH can be WSL's) and the PC's Python 3.13
$bash = 'C:\Program Files\Git\bin\bash.exe'
if (-not (Test-Path $bash)) { throw "Git for Windows is missing: winget install Git.Git" }
$short = (New-Object -ComObject Scripting.FileSystemObject).GetFile($bash).ShortPath
if ($short -ne 'C:\PROGRA~1\Git\bin\bash.exe') { throw "Git Bash's short path is $short, not the workflow's C:\PROGRA~1\Git\bin\bash.exe" }
& py -3.13 -c "pass" 2>$null
if ($LASTEXITCODE -ne 0) { throw "Python 3.13 is missing from the py launcher: winget install Python.Python.3.13" }

New-Item -ItemType Directory -Force $Dir | Out-Null
Set-Location $Dir
if (-not (Test-Path .runner)) {
    if (-not $Token) {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "no gh: pass -Token (Settings > Actions > Runners > New)" }
        $Token = gh api -X POST "repos/$Repo/actions/runners/registration-token" --jq .token
    }
    $release = Invoke-RestMethod https://api.github.com/repos/actions/runner/releases/latest
    $version = $release.tag_name.TrimStart('v')
    $sum = [regex]::Match($release.body, 'BEGIN SHA win-x64 -->([0-9a-f]{64})').Groups[1].Value
    $zip = "actions-runner-win-x64-$version.zip"
    Invoke-WebRequest "https://github.com/actions/runner/releases/download/v$version/$zip" -OutFile $zip
    if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $sum) { throw "checksum mismatch for $zip" }
    Expand-Archive -Force $zip .
    Remove-Item $zip
    & .\config.cmd --unattended --url "https://github.com/$Repo" --token $Token --name $Name `
        --labels $Label --no-default-labels --work w --replace
    if ($LASTEXITCODE -ne 0) { throw "config.cmd failed" }
}

$startup = [Environment]::GetFolderPath('Startup')
$start = "Start-Process -WindowStyle Hidden -WorkingDirectory '$Dir' '$Dir\run.cmd'"
Set-Content -Encoding ascii "$startup\goal2-runner.cmd" @(
    '@echo off',
    "rem goal2 Actions runner ($Name, label $Label; goal2#493), started hidden at logon",
    "powershell.exe -NoProfile -WindowStyle Hidden -Command `"$start`""
)
$running = Get-CimInstance Win32_Process -Filter "Name = 'Runner.Listener.exe'" |
    Where-Object { $_.ExecutablePath -like "$Dir\*" }
if (-not $running) { Invoke-Expression $start }
Write-Host "runner $Name (label $Label) installed in $Dir; starts at logon ($startup\goal2-runner.cmd)"
