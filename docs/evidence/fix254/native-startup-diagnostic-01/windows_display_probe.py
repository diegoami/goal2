import json,subprocess
PROBE="import ctypes,json,os,sys\nfrom ctypes import wintypes\nos.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']=str(int(sys.argv[1])*2/3);os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'\nfrom PySide6.QtWidgets import QApplication\napp=QApplication([]);s=app.primaryScreen();a=s.availableGeometry();u=ctypes.windll.user32;r=wintypes.RECT();assert u.SystemParametersInfoW(48,0,ctypes.byref(r),0)\nprint(json.dumps({'requested_qt_scale':sys.argv[1],'qt_scale_factor':os.environ['QT_SCALE_FACTOR'],'qt_ratio':s.devicePixelRatio(),'qt_name':s.name(),'qt_available':[a.width(),a.height()],'primary_pixels':[u.GetSystemMetrics(0),u.GetSystemMetrics(1)],'virtual_pixels':[u.GetSystemMetrics(78),u.GetSystemMetrics(79)],'workarea_pixels':[r.right-r.left,r.bottom-r.top],'os_dpi':u.GetDpiForSystem(),'qpa':app.platformName()}))\n"
def display(win,scale):
 raw=subprocess.check_output([str(win/'.venv/Scripts/python.exe'),'-B','-c',PROBE,str(scale)],stdin=subprocess.DEVNULL,timeout=30)
 value=json.loads(raw.decode('utf-8'));assert value['qpa']=='windows' and value['qt_ratio']==int(scale),value
 needed=(1440,900) if str(scale)=='1' else (900,640)
 assert all(a>=b for a,b in zip(value['qt_available'],needed)),('native screen unavailable for required visible window',value,needed)
 return value
