from pathlib import Path
import py_compile
p=Path(__file__).parent
s=(p/'native-parent-observer-visible.py').read_text()
s=s.replace('import ctypes,json,os,platform,runpy,sys,time,traceback,unittest','import ctypes,faulthandler,json,os,platform,runpy,sys,threading,time,traceback,unittest')
key='init=WatchedController.__init__;poll='
pos=s.index(key)
block='''# [designed: #254] Transparent timings and an independently scheduled own-process stack sampler.
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
                    diagnostic['stalls'].append(row);stream.write((json.dumps(row)+'\\n').encode());stream.flush()
                    faulthandler.dump_traceback(file=stream,all_threads=True)

'''
s=s[:pos]+block+s[pos:]
old="if self.watched.busy:self.watched._native_beats.append(time.monotonic())"
new="""if self.watched.busy:
            now=time.monotonic();beats=self.watched._native_beats
            if beats and now-beats[-1]>=.1:diagnostic['heartbeat_gaps'].append({'start':beats[-1],'end':now,'seconds':now-beats[-1],'frame_ack':self.watched.frame_ack})
            beats.append(now)"""
assert s.count(old)==1;s=s.replace(old,new)
old='self._native_beats=[time.monotonic()];result=start(self,*a,**kw)'
new="""self._native_beats=[time.monotonic()];self._native_starting=True
    try:result=measured('controller.start',start,self,*a,**kw)
    finally:self._native_starting=False"""
assert s.count(old)==1;s=s.replace(old,new)
old='try:result=poll(self)';assert s.count(old)==1;s=s.replace(old,"try:result=measured('controller.poll',poll,self)")
old="second=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_pygame_match_view.OriginalQtAcceptance'))"
new="""sampler=threading.Thread(target=sample_stalls,name='main-owned-stall-observer');sampler.start()
try:
    second=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_pygame_match_view.OriginalQtAcceptance'))
finally:
    stop_sampler.set();sampler.join(timeout=5);assert not sampler.is_alive(),'owned stall observer did not stop'
    (out/'ui-thread-timing.json').write_text(json.dumps(diagnostic,indent=2)+'\\n')"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("'window_states':window_states,","'diagnostic_sampler_stopped':not sampler.is_alive(),'window_states':window_states,")
newp=p/'native-parent-observer-stall08.py';newp.write_text(s);py_compile.compile(str(newp),doraise=True)
s=(p/'native-full-visible-launcher.py').read_text().replace('native-parent-observer-visible.py','native-parent-observer-stall08.py')
# [designed: #254] Locate the recurrent 2x gap only; this diagnostic cannot claim both-scale ordinary acceptance.
s=s.replace("for scale in('1','2'):","for scale in('2',):")
newp=p/'native-stall08-launcher.py';newp.write_text(s);py_compile.compile(str(newp),doraise=True)
print('Compiled observational 2x watchdog/timing diagnostic; not executed')
