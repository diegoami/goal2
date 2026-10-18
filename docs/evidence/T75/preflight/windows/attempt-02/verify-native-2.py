import os,sys,runpy
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='2'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T75-preflight-cd081575ecdc-1792336456087894544\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T75-preflight-cd081575ecdc-1792336456087894544\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T75-preflight-cd081575ecdc-1792336456087894544\\.cache\\tmp'
assert sys.platform=='win32'
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T75-preflight-cd081575ecdc-1792336456087894544\\main-overview-preflight.py', '--mode', 'mock', '--output', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T75-preflight-cd081575ecdc-1792336456087894544\\evidence\\scale-2']
runpy.run_path(sys.argv[0],run_name='__main__')
