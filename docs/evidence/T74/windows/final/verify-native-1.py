import os,sys,runpy
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\.cache\\tmp'
assert sys.platform=='win32'
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\tools\\desktop-ui\\redesign.py', '--scenario', 'shell', '--template', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\.cache\\e010-r0008-halftime.sav', '--data', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\.cache\\GOAL.DAT', '--evidence-dir', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T74-shell-bf1846663b4e-1792329435412773751\\evidence\\scale-1', '--single-scale']
runpy.run_path(sys.argv[0],run_name='__main__')
