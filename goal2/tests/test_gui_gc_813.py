"""[designed: #813] Automatic cyclic collection belongs to the GUI owner.

Probes run in child processes because the baseline violates Qt thread affinity.
No game asset or emulated match is involved.
"""
import json,os,subprocess,sys,unittest
from goal2.tests import requires
requires.require(modules=('PySide6',))


def probe(mode):
    import gc,threading,weakref
    if mode=='import':
        initial=gc.isenabled()
        from goal2.desktop import fixed_page
        assert gc.isenabled()==initial
        return {'gc_unchanged_before_application':True}
    from PySide6.QtCore import QEventLoop,QTimer
    from PySide6.QtWidgets import QApplication,QWidget
    app=QApplication([])
    if mode=='lifetime-disabled':gc.disable()
    initial=gc.isenabled();owner=threading.get_ident()
    page=None
    if mode!='control':
        from goal2.desktop.fixed_page import FixedPage
        window=QWidget();page=FixedPage(QWidget(),'',window)
    if mode.startswith('lifetime'):
        from goal2.desktop.gui_gc import install
        guard=install(app);second_window=QWidget();second=FixedPage(QWidget(),'',second_window)
        assert install(app) is guard
        assert not gc.isenabled()
        errors=[]
        def wrong_thread():
            try:guard.collect()
            except RuntimeError:errors.append('owner refusal')
        t=threading.Thread(target=wrong_thread);t.start();t.join()
        assert errors==['owner refusal']
        import shiboken6
        shiboken6.delete(app)
        assert gc.isenabled()==initial
        return {'restored':True,'idempotent':True,'worker_refused':True}
    # Keep the widget young until the existing worker starts allocating. Lower
    # thresholds inside that worker; no explicit worker gc.collect bypass.
    gc.collect();gc.set_threshold(10**8,10**8,10**8)
    events=[];deleted=[];ready=threading.Event();release=threading.Event()
    def observed(phase,info):
        if phase=='stop':events.append(threading.get_ident())
    gc.callbacks.append(observed)
    def allocate():
        ready.set();release.wait();gc.set_threshold(1,1,1)
        kept=[]
        for _ in range(10000):
            cycle=[];cycle.append(cycle);kept.append(cycle)
        gc.set_threshold(10**8,10**8,10**8)
    worker=threading.Thread(target=allocate);worker.start();ready.wait()
    class WidgetCycle(QWidget):
        def __del__(self):deleted.append(threading.get_ident())
    widget=WidgetCycle();widget.cycle=widget;reference=weakref.ref(widget)
    # The negative control proves worker traversal without deliberately
    # destroying a Qt widget on that wrong thread (especially on Windows).
    pinned=widget if mode=='control' else None
    del widget
    release.set();worker.join(timeout=10);assert not worker.is_alive()
    if mode=='control':
        assert any(t!=owner for t in events),'control failed to trigger automatic worker collection'
        gc.callbacks.remove(observed);del pinned;gc.collect()
        return {'worker_collection_observed':True}
    loop=QEventLoop();QTimer.singleShot(1300,loop.quit);loop.exec()
    assert events and all(t==owner for t in events),{'owner':owner,'collection_threads':sorted(set(events))}
    assert reference() is None and deleted==[owner],{'deleted':deleted,'owner':owner}
    gc.callbacks.remove(observed)
    return {'only_gui_collection':True,'widget_finalized_on_gui':True}


class GuiCollection(unittest.TestCase):
    def child(self,mode):
        result=subprocess.run([sys.executable,'-X','faulthandler','-m',__name__,'--gc-child',mode],
                              env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return json.loads(result.stdout.splitlines()[-1])

    def test_no_policy_control_observes_real_automatic_worker_collection(self):
        self.assertTrue(self.child('control')['worker_collection_observed'])

    def test_fixed_page_keeps_collection_and_widget_cleanup_on_gui_thread(self):
        self.assertTrue(all(self.child('page').values()))

    def test_application_policy_is_idempotent_restored_and_rejects_worker_collection(self):
        self.assertTrue(all(self.child('lifetime').values()))

    def test_application_restores_an_initially_disabled_collector(self):
        self.assertTrue(all(self.child('lifetime-disabled').values()))

    def test_import_without_a_gui_does_not_change_collection_policy(self):
        self.assertTrue(all(self.child('import').values()))


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--gc-child':print(json.dumps(probe(sys.argv[2])))
    else:unittest.main()
