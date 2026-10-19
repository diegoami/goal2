"""[designed: #254] Actual original Qt/SDL acceptance; observational wrappers only.
The existing original-acceptance helper switches its accepted frames option on.
No status, sharing, renderer output, packet or model behavior is substituted.
"""
from pathlib import Path
import ctypes,faulthandler,json,os,platform,runpy,sys,threading,time,traceback,unittest
from ctypes import wintypes
from PySide6.QtCore import QCoreApplication,QEvent,QTimer,Qt,qVersion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
out=Path(os.environ['GOAL2_NATIVE_OBSERVATIONS']);out.mkdir(parents=True,exist_ok=False)
callbacks=[]
def callback_error(kind,error,tb):
    callbacks.append(''.join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)
sys.excepthook=callback_error
# [designed: #254] Fault-injection units are separate from the unmocked actual match path below.
first=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_desktop_watched_sharing'))
assert first.wasSuccessful()and not first.skipped
from goal2.desktop.watched import WatchedController
from goal2.desktop.window import ManagementWindow
u=ctypes.WinDLL('user32',use_last_error=True);u.GetWindowRect.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.RECT));u.GetWindowRect.restype=wintypes.BOOL
controllers=[];windows=[];frames=[];qt_captures=[];complete_acks=[];stderr_links=[];controller_errors=[];window_states=[];visibility_preflight=[]
# [designed: #254] Transparent timings and an independently scheduled own-process stack sampler.
from goal2.desktop import watched as watched_module
import _winapi
diagnostic={'slow_operations':[],'heartbeat_gaps':[],'stalls':[]}
def measured(name,operation,*args,**kw):
    began=time.monotonic()
    try:return operation(*args,**kw)
    finally:
        end=time.monotonic();elapsed=end-began
        if elapsed>=.05:diagnostic['slow_operations'].append({'name':name,'start':began,'end':end,'seconds':elapsed})
status_open=watched_module._open_status
class ObservedStatus:
    def __init__(self,stream):self.stream=stream
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):return measured('status.close',self.stream.__exit__,*args)
    def read(self,*args):return measured('status.read',self.stream.read,*args)
def observed_open(path):return ObservedStatus(measured('status.open',status_open,path))
watched_module._open_status=observed_open
path_exists=Path.exists
def observed_exists(path):
    if path.name=='status'and path.parent.name.startswith('goal2-viewer-'):
        return measured('status.exists',path_exists,path)
    return path_exists(path)
Path.exists=observed_exists
create_process=_winapi.CreateProcess
def observed_create_process(*args,**kw):return measured('CreateProcess',create_process,*args,**kw)
_winapi.CreateProcess=observed_create_process
stop_sampler=threading.Event()
def sample_stalls():
    previous=None
    with(out/'ui-thread-stalls.log').open('wb')as stream:
        while not stop_sampler.wait(.05):
            now=time.monotonic()
            for controller in tuple(controllers):
                beats=controller._native_beats
                if not beats or not(getattr(controller,'_native_starting',False)or controller.busy):continue
                gap=now-beats[-1];key=(id(controller),beats[-1],int(gap*2))
                if gap>=.4 and key!=previous:
                    previous=key
                    row={'time':now,'last_heartbeat':beats[-1],'gap':gap,'starting':getattr(controller,'_native_starting',False),'frame_ack':getattr(controller,'frame_ack',None)}
                    diagnostic['stalls'].append(row);stream.write((json.dumps(row)+'\n').encode());stream.flush()
                    faulthandler.dump_traceback(file=stream,all_threads=True)

init=WatchedController.__init__;poll=WatchedController.poll;start=WatchedController.start;close=WatchedController.close_viewer;window_init=ManagementWindow.__init__;run_path=runpy.run_path

def observe_init(self,*a,**kw):
    if kw.get('viewer_command')is None:kw['viewer_command']=[sys.executable,str(Path(__file__).with_name('viewer-observer.py'))]
    init(self,*a,**kw);controllers.append(self);self._native_beats=[]
WatchedController.__init__=observe_init

def observe_window(self,*a,**kw):
    window_init(self,*a,**kw);windows.append(self)
    size=(900,640)if os.environ['QT_SCALE_FACTOR']=='2'else(1050,780)
    self.resize(*size);self.move(20,20)
    timer=QTimer(self);timer.setInterval(5)
    def beat():
        if self.watched.busy:
            now=time.monotonic();beats=self.watched._native_beats
            if beats and now-beats[-1]>=.1:diagnostic['heartbeat_gaps'].append({'start':beats[-1],'end':now,'seconds':now-beats[-1],'frame_ack':self.watched.frame_ack})
            beats.append(now)
    timer.timeout.connect(beat);timer.start();self._native_heartbeat=timer
ManagementWindow.__init__=observe_window

window_change=ManagementWindow.changeEvent
def observe_window_change(self,event):
    result=window_change(self,event)
    if event.type()==QEvent.Type.WindowStateChange:
        window_states.append({'time':time.monotonic(),'minimized':self.isMinimized(),'busy':bool(getattr(self,'watched',None)and self.watched.busy)})
    return result
ManagementWindow.changeEvent=observe_window_change


def observe_start(self,*a,**kw):
    for window in windows:
        if window.model is self.model:
            if window.isMinimized():window.showNormal()
            window.raise_();window.activateWindow();QApplication.instance().processEvents()
            assert window.isVisible()and not window.isMinimized(),'owned Qt test window must be visible before Watch'
            visibility_preflight.append({'time':time.monotonic(),'visible':window.isVisible(),'minimized':window.isMinimized()})
    self._native_beats=[time.monotonic()];self._native_starting=True
    try:result=measured('controller.start',start,self,*a,**kw)
    finally:self._native_starting=False
    number=len(stderr_links)
    for role,handle in(('viewer',self.errors),('engine',self.engine._errors)):
        if handle is not None:
            destination=out/(role+'-stderr-'+str(number)+'.log');os.link(handle.name,destination);stderr_links.append(destination)
    return result
WatchedController.start=observe_start

def capture_qt(window,number):
    assert window.isVisible();app=QApplication.instance();window.raise_();window.activateWindow();app.processEvents()
    file=out/('qt-complete-'+str(number)+'.png');assert window.grab().save(str(file))
    ratio=window.devicePixelRatioF();assert ratio==float(os.environ['QT_SCALE_FACTOR'])
    size=[window.width(),window.height()];assert size==([900,640]if ratio==2 else[1050,780])
    rect=wintypes.RECT();assert u.GetWindowRect(int(window.winId()),ctypes.byref(rect))
    qt_captures.append({'file':file.name,'ratio':ratio,'logical_size':size,'qt_available':[window.screen().availableGeometry().width(),window.screen().availableGeometry().height()],'native_rect':[rect.left,rect.top,rect.right,rect.bottom],'active':window.isActiveWindow()})

def observe_poll(self):
    try:result=measured('controller.poll',poll,self)
    except Exception as error:
        controller_errors.append({'error':repr(error),'traceback':traceback.format_exc()})
        (out/'controller-errors.json').write_text(json.dumps(controller_errors,indent=2)+'\n')
        print('NATIVE REAL CONTROLLER ERROR',traceback.format_exc(),flush=True)
        raise
    if result:
        assert self.frames_enabled and self.display.frame_sequence>=1000
        assert self.frame_ack==self.display.frame_sequence and not self.display.frames
        assert self.last_status['frame_sequence']==self.frame_ack
        beats=[*self._native_beats,time.monotonic()];gap=max((b-a for a,b in zip(beats,beats[1:])),default=0)
        frames.append({'frames':self.display.frame_sequence+1,'final_ack':self.frame_ack,'frame_digest':self.last_status['frame_digest'],'heartbeats':len(beats),'maximum_heartbeat_gap':gap})
        print('PASS actual publication after final rendered-frame ACK',json.dumps(frames[-1]),flush=True)
        for w in windows:
            if w.model is self.model:QTimer.singleShot(0,lambda w=w,n=len(frames):capture_qt(w,n))
    return result
WatchedController.poll=observe_poll

def observe_close(self):
    # [designed: #254; confirmed: T79 concrete preflight] Final frame precedes complete-board ACK.
    if self.process is not None and self.process.poll()is None and not self.engine.busy and self.display is not None and self.display.result is not None:
        deadline=time.monotonic()+30
        while self.last_status is None or self.last_status['sequence']!=self.display.sequence or self.last_status['digest']!=self.display.digest():
            assert time.monotonic()<deadline,'complete-board ACK deadline'
            QApplication.instance().processEvents();QTest.qWait(10);poll(self)
        complete_acks.append({'sequence':self.last_status['sequence'],'digest':self.last_status['digest']})
    return close(self)
WatchedController.close_viewer=observe_close

def animated(path,*a,**kw):
    if Path(path).resolve()==Path('tools/desktop-ui/watched.py').resolve():
        text=Path(path).read_text();old='original_start(frames=False,**kw)';assert text.count(old)==1
        namespace={'__name__':'<main-owned animated acceptance>','__file__':str(Path(path).resolve())}
        exec(compile(text.replace(old,'original_start(frames=True,**kw)'),str(path),'exec'),namespace);return namespace
    return run_path(path,*a,**kw)
runpy.run_path=animated
before=list(sys.path)
sampler=threading.Thread(target=sample_stalls,name='main-owned-stall-observer');sampler.start()
try:
    second=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_pygame_match_view.OriginalQtAcceptance'))
finally:
    stop_sampler.set();sampler.join(timeout=5);assert not sampler.is_alive(),'owned stall observer did not stop'
    (out/'ui-thread-timing.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
app=QApplication.instance();assert app is not None
QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
sdl=[json.loads(p.read_text())for p in out.glob('goal2-viewer-*.json')]
clean=all(c.process is None and c.folder is None and c.directory is None and c.stream is None and c.errors is None and not c.engine.busy and not c._pending_owned for c in controllers)
report={'claim':'[designed: #254] Actual Qt/SDL original parity/save/resume acceptance; mode frames=True and capture/ACK observation only; preceding fault-injection units separate','result':'PASS','platform':platform.platform(),'python':sys.version,'qt':qVersion(),'qpa':app.platformName(),'requested_qt_scale':os.environ['QT_SCALE_FACTOR'],'actual_qt_ratio':app.primaryScreen().devicePixelRatio(),'controller_errors':controller_errors,'diagnostic_sampler_stopped':not sampler.is_alive(),'window_states':window_states,'visibility_preflight':visibility_preflight,'frames':frames,'complete_acks':complete_acks,'qt_captures':qt_captures,'sdl':sdl,'deterministic_tests':first.testsRun,'original_acceptance_tests':second.testsRun,'callbacks':callbacks,'owned_resources_closed':clean,'clean_widgets':not app.topLevelWidgets(),'import_context_restored':sys.path==before}
checks=[second.wasSuccessful()and not second.skipped,len(frames)==2,len(complete_acks)==2,len(qt_captures)==2,not callbacks,clean,not app.topLevelWidgets(),sys.path==before,all(x['maximum_heartbeat_gap']<1 and x['heartbeats']>5 for x in frames),len([x for x in sdl if x['stage']=='complete'])==2,all(x['driver']=='windows'for x in sdl)]
checks.append(not any(x['minimized']and x['busy']for x in window_states))
if not all(checks):report['result']='FAIL';report['checks']=checks
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);assert all(checks),'native actual-match acceptance failed'
