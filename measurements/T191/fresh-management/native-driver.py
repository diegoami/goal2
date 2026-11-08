import os,sys,tempfile,subprocess,shutil
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=r'\\wsl.localhost\Ubuntu\tmp\goal2-track-a';script=r'\\wsl.localhost\Ubuntu\tmp\goal2-fresh-management-audit.py'
target=Path(tempfile.mkdtemp(prefix='goal2-track-a-management-audit-'))
public=Path(r'\\wsl.localhost\Ubuntu\tmp\goal2-fresh-management-audit-native');public.mkdir(parents=True,exist_ok=True)
print('Isolated native target:',target,flush=True)
for mode in ['create','resume','verify']:
 subprocess.run([sys.executable,'-X','utf8','-B',script,root,str(target),mode,'d56e793beebb72f3d7418db0d4bf764d1a4c4091',r'\\wsl.localhost\Ubuntu\tmp\goal2-fresh-management-fixtures'],check=True)
 shutil.copy2(target/(mode+'-receipt.json'),public/(mode+'-receipt.json'))
shutil.copytree(target/'captures',public/'captures',dirs_exist_ok=True)
print('PASS native fresh-management audit; original-derived saves/comparison state remain private in Windows Temp',flush=True)
