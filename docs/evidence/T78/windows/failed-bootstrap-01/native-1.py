import os,sys,runpy
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\.cache\\tmp'
assert sys.platform=='win32'
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\tools\\desktop-ui\\redesign.py', '--scenario', 'results', '--template', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\.cache\\e010-r0008-halftime.sav', '--data', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\.cache\\GOAL.DAT', '--evidence-dir', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T78-implementation-27b62e9e5c17-1792343689034656872\\observations\\scale-1', '--single-scale']
runpy.run_path(sys.argv[0],run_name='__main__')
