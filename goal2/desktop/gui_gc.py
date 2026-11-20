"""[designed: #813] Keep cyclic collection on the Qt application thread.

Python allocation-heavy workers can otherwise traverse/finalize Qt wrappers
while the owner is inside native layout code. Reference counting is unchanged;
a periodic owner-thread full collection still reclaims unreachable cycles.
This is installed only for a GUI application, never in engine processes.
"""
import gc
import threading

from PySide6.QtCore import QObject,QThread,QTimer

_ATTRIBUTE='_goal2_gui_collector'
INTERVAL_MS=1000


class GuiCollector(QObject):
    def __init__(self,app):
        super().__init__(app)
        self._owner=threading.get_ident()
        self._collecting=False
        self.timer=QTimer(self)
        self.timer.setInterval(INTERVAL_MS)
        self.timer.timeout.connect(self.collect)
        previous=gc.isenabled()
        # Only automatic collection is disabled. The application timer keeps
        # collecting explicitly on its owning thread throughout GUI lifetime.
        gc.disable()
        def restore():
            gc.enable() if previous else gc.disable()
        app.destroyed.connect(restore)
        self.timer.start()

    def collect(self):
        if threading.get_ident()!=self._owner:
            raise RuntimeError('GUI cycles must be collected on the application thread')
        if self._collecting:
            return 0
        self._collecting=True
        try:
            return gc.collect()
        finally:
            self._collecting=False


def install(app):
    """One collector for all windows; preserve the pre-application GC state."""
    if app is None or QThread.currentThread()!=app.thread():
        raise RuntimeError('Install the GUI collector on the application thread')
    collector=getattr(app,_ATTRIBUTE,None)
    if collector is None:
        collector=GuiCollector(app)
        setattr(app,_ATTRIBUTE,collector)
    return collector
