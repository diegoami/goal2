import os,sys,runpy
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\tmp'
assert sys.platform=='win32'
sys.path.insert(0,'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\tools\\desktop-ui')
from pathlib import Path
import json
sys.path.insert(0,'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\python-libs')
import unicorn
assert unicorn.__version__=="2.1.4"
assert Path(unicorn.__file__).resolve().is_relative_to(Path('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\python-libs').resolve())
Path('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\native-runtime-1.json').write_text(json.dumps({"version":unicorn.__version__,"file":unicorn.__file__},indent=2)+"\n")
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\tools\\desktop-ui\\redesign.py', '--scenario', 'results', '--template', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\e010-r0008-halftime.sav', '--data', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\.cache\\GOAL.DAT', '--evidence-dir', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792344201461927018\\observations\\scale-1', '--single-scale']
runpy.run_path(sys.argv[0],run_name='__main__')
