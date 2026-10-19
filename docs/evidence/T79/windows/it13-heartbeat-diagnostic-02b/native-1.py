import os,sys,runpy,json,traceback,platform
from pathlib import Path
os.environ['PYTHONPATH']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\python-libs-T78;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\python-libs-T79'
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\tmp'
sys.path[:0]=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\tools\\desktop-ui', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\python-libs-T78', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\python-libs-T79']
import pygame,unicorn
assert sys.platform=="win32" and pygame.version.ver=="2.5.8" and unicorn.__version__=="2.1.4"
from PySide6.QtCore import QCoreApplication,QEvent,qVersion
from PySide6.QtWidgets import QApplication
callbacks=[]
def callback_error(kind,error,tb):
 callbacks.append("".join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)
sys.excepthook=callback_error
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\tools\\desktop-ui\\redesign.py', '--scenario', 'match-handoff', '--single-scale', '--template', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\e010-r0008-halftime.sav', '--data', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\.cache\\GOAL.DAT', '--evidence-dir', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\observations\\scale-1']
import time,match_handoff_scenario as diagnostic_module
phase_timings=[]
real_geometry=diagnostic_module.geometry
def diagnostic_geometry(*args,**kwargs):
 start=time.monotonic()
 try: return real_geometry(*args,**kwargs)
 finally: phase_timings.append({"stage":args[4],"start":start,"end":time.monotonic()})
diagnostic_module.geometry=diagnostic_geometry
try:
 runpy.run_path('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\tools\\desktop-ui\\redesign.py',run_name="__main__")
except BaseException as diagnostic_error:
 tb=diagnostic_error.__traceback__
 detail={"phase_timings":phase_timings}
 while tb is not None:
  if tb.tb_frame.f_code.co_name=="scenario":
   local=tb.tb_frame.f_locals;beats=local.get("beats",[]);detail.update(round=local.get("round_index"),heartbeat_count=len(beats),long_gaps=[{"start":a,"end":b,"seconds":b-a} for a,b in zip(beats,beats[1:]) if b-a>=.3])
  tb=tb.tb_next
 Path('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-production-dfe955cf57e3-1792404630707523255\\heartbeat-diagnostic-1.json').write_text(json.dumps(detail,indent=2)+"\n")
 raise
finally:
 app=QApplication.instance()
 if app is not None:
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
  assert not app.topLevelWidgets(),"owned T79 Qt widgets remain"
 assert not callbacks,callbacks
