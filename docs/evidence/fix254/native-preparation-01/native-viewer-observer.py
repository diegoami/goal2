"""[designed: #236] Observe actual fixed SDL renderer/status; no retries or protocol edits."""
from pathlib import Path
import ctypes,json,os,sys,time
from ctypes import wintypes
user32=ctypes.windll.user32
user32.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype=wintypes.BOOL
user32.GetDpiForWindow.argtypes=[wintypes.HWND]
user32.GetDpiForWindow.restype=wintypes.UINT
import pygame
from goal2.desktop import pygame_viewer as viewer
out=Path(os.environ['GOAL2_NATIVE_OBSERVATIONS']);out.mkdir(parents=True,exist_ok=True)
name=Path(sys.argv[1]).name;seen=set();last=[None];render=viewer.render_pitch;flip=pygame.display.flip

def observe_render(screen,font,display,scroll=0):
    result=render(screen,font,display,scroll);last[0]=display;return result

def observe_flip():
    result=flip();display=last[0]
    if display is None:return result
    stage='complete'if display.result is not None else'live'
    if stage in seen or(stage=='live'and display.frame is None):return result
    seen.add(stage);screen=pygame.display.get_surface();file=out/(name+'-'+stage+'.png');pygame.image.save(screen,str(file))
    handle=pygame.display.get_wm_info()['window'];rect=wintypes.RECT();assert user32.GetWindowRect(handle,ctypes.byref(rect))
    report={'stage':stage,'driver':pygame.display.get_driver(),'surface':list(screen.get_size()),'window':list(pygame.display.get_window_size()),'window_rect':[rect.left,rect.top,rect.right,rect.bottom],'dpi':user32.GetDpiForWindow(handle),'qt_scale_requested':os.environ['QT_SCALE_FACTOR'],'frame_sequence':display.frame_sequence,'frame_consumed_before_status':display.consumed,'capture':file.name,'pid':os.getpid(),'claim':'Actual fixed renderer flip observed; no SDL scale inference from Qt ratio'}
    (out/(name+'-'+stage+'.json')).write_text(json.dumps(report,indent=2)+'\n');return result
viewer.render_pitch=observe_render;pygame.display.flip=observe_flip
raise SystemExit(viewer.main())
