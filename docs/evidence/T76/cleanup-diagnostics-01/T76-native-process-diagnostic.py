from pathlib import Path
import subprocess,base64,json,time
root=Path.cwd();out=root/'.cache'/('T76-native-diagnostic-'+str(time.time_ns()));out.mkdir()
script=r'''
$ErrorActionPreference='Stop'
$archive='C:\Users\diego\projects\goal2-exe\.goal2-validation\T76-implementation-3a76a704864f-1792344033654236591'
$all=@(Get-CimInstance Win32_Process)
$owned=@($all | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($archive) -and $_.CommandLine.Contains('goal2.desktop.worker') })
$rows=@(foreach($p in $owned){
 $parent=@($all | Where-Object { $_.ProcessId -eq $p.ParentProcessId })
 $parentOwned=($parent.Count -eq 1 -and $parent[0].CommandLine -and $parent[0].CommandLine.Contains($archive) -and $parent[0].CommandLine.Contains('goal2.desktop.worker'))
 $parentDetails=$null
 if($parentOwned){$parentDetails=[ordered]@{pid=[int]$parent[0].ProcessId;ppid=[int]$parent[0].ParentProcessId;executable=$parent[0].ExecutablePath;command=$parent[0].CommandLine;created=[string]$parent[0].CreationDate}}
 [ordered]@{pid=[int]$p.ProcessId;ppid=[int]$p.ParentProcessId;executable=$p.ExecutablePath;command=$p.CommandLine;created=[string]$p.CreationDate;parent_present=($parent.Count -eq 1);parent_owned=[bool]$parentOwned;owned_parent=$parentDetails}
})
$dirs=@(Get-ChildItem -LiteralPath ($archive+'\.cache\tmp') -Directory -Filter 'goal2-friendly-*' | ForEach-Object {
 $directory=$_.FullName
 $files=@(Get-ChildItem -LiteralPath $directory -File | ForEach-Object { [ordered]@{name=$_.Name;bytes=$_.Length;modified=$_.LastWriteTimeUtc.ToString('o')} })
 [ordered]@{path=$directory;files=$files}
})
[ordered]@{timestamp=[DateTime]::UtcNow.ToString('o');archive=$archive;filter='exact archive substring AND goal2.desktop.worker; parent command emitted only if same ownership filter';owned_processes=$rows;owned_worker_directories=$dirs} | ConvertTo-Json -Depth 8
'''
(out/'query.ps1').write_text(script)
encoded=base64.b64encode(script.encode('utf-16-le')).decode()
r=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],capture_output=True,text=True,timeout=60)
(out/'stdout.json').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr)
print('diagnostic',out,'exit',r.returncode)
print(r.stdout)
if r.stderr:print(r.stderr)
raise SystemExit(r.returncode)
