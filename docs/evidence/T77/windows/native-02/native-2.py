import os,sys,runpy
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='2'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\.cache\\tmp'
assert sys.platform=='win32'
sys.path.insert(0,'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\tools\\desktop-ui')
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\tools\\desktop-ui\\redesign.py', '--scenario', 'pool', '--template', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\.cache\\e010-r0008-halftime.sav', '--data', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\.cache\\GOAL.DAT', '--evidence-dir', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T77-implementation-403af66018a1-1792354400986785409\\observations\\scale-2', '--single-scale']
runpy.run_path(sys.argv[0],run_name='__main__')
