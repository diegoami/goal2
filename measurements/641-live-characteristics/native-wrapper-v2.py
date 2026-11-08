import os,runpy,sys
from pathlib import Path
root=Path(r'\\wsl.localhost\Ubuntu\home\diego\projects\m3-trackb\goal2-ci-policy')
os.chdir(root);sys.path.insert(0,str(root));os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ.pop('QT_PLUGIN_PATH',None);os.environ.pop('QT_QPA_PLATFORM_PLUGIN_PATH',None)
sys.argv=[str(root/'measurements/641-live-characteristics/widget-replay-v1.py'),
 '--input',r'\\wsl.localhost\Ubuntu\home\diego\projects\m3-trackb\goal2-archaeology-3\.cache\fix695\original-composite-v1\run.json',
 '--input-sha256','0e10b3f05561b32544fa25d75d0126a8edb0dab2b8e6d12d125e4ef5762a111d',
 '--template',r'\\wsl.localhost\Ubuntu\home\diego\projects\m3-trackb\goal2-archaeology-3\.cache\dl\e0afff6751747233-e006-1000-r0001.sav',
 '--out',str(root/'measurements/641-live-characteristics/prepared-native-v2.json'),
 '--captures',str(root/'.cache/641-prepared-native-v2'),'--native']
import goal2
assert Path(goal2.__file__).resolve().is_relative_to(root.resolve()),goal2.__file__
runpy.run_path(sys.argv[0],run_name='__main__')
