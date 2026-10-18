import os,sys,runpy,json
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659\\.cache\\tmp'
sys.path.insert(0,'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659')
sys.path.insert(0,'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659\\tools\\desktop-ui')
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659\\.cache\\T77-main-planning-probe.py', '--mode', 'mock', '--output', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-planning-1792350260542666659\\observations\\mock-1']
runpy.run_path(sys.argv[0],run_name="__main__")
