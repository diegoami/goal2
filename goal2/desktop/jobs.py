"""[designed: T70] UI-owned job lifecycle; subprocesses never own active state."""
from pathlib import Path
import subprocess
import sys
import tempfile
from goal2.game.session_save import encode, load
from goal2.game.quick_match import resolve_full_matchup
from goal2.engine.savestate import Savestate
from goal2.game.state import to_savestate


class QuickJobs:
    """[designed] One snapshot/job at a time, validated once-only publication."""
    def __init__(self,model,*,command=None):
        self.model=model;self.command=command;self.process=None;self.folder=None
        self.halftime=None;self.continued=False;self.interactive=False

    @property
    def busy(self):return self.process is not None

    def start(self,*,halftime=False):
        if self.busy:raise ValueError('A friendly is already running')
        model=self.model
        self.interactive=halftime;self.halftime=None;self.continued=False
        resolve_full_matchup(Savestate(to_savestate(model.state,original=model.template_bytes)),model.state)
        self.original=model.state
        self.snapshot=encode(model.state,model.template_bytes)
        self.folder=tempfile.TemporaryDirectory(prefix='goal2-friendly-')
        self.directory=Path(self.folder.name)
        source=self.directory/'input.g2save';self.output=self.directory/'output.g2save'
        source.write_bytes(self.snapshot)
        self.errors=(self.directory/'error.txt').open('wb')
        try:
            command=([sys.executable,'-m','goal2.desktop.worker'] if self.command is None else list(self.command))
            self.process=subprocess.Popen(command+[str(source),str(self.output)]+(['--halftime'] if halftime else []),cwd=Path(__file__).resolve().parents[2],
                                          stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=self.errors)
            model.match_pending=True
        except Exception:
            self._release();raise

    def poll(self):
        """[designed] Called by the UI thread; None while pending, True once."""
        if not self.busy:return None
        code=self.process.poll()
        if code is None:
            if self.interactive and not self.continued and self.halftime is None:
                preview=self.directory/'halftime.json'
                if preview.exists():
                    import json
                    self.halftime=json.loads(preview.read_text())
            return None
        try:
            self.errors.flush()
            if code!=0:
                detail=(self.directory/'error.txt').read_text(errors='replace')[-1500:]
                raise ValueError(f'Friendly worker failed ({code}): {detail}')
            model=self.model
            if model.state is not self.original or encode(model.state,model.template_bytes)!=self.snapshot:
                raise ValueError('Friendly completion is stale; active game changed')
            candidate,template=load(self.output)
            if template!=model.template_bytes or candidate.match_count!=self.original.match_count+1:
                raise ValueError('Invalid friendly worker continuation')
            model.view(candidate)
            model.state=candidate
            return True
        finally:self._release()

    def substitute(self,outgoing,incoming):
        """[designed: T47] Draft only; worker validates again on continuation."""
        if self.halftime is None or self.continued:raise ValueError('No pending halftime decision')
        from goal2.game.substitutions import swap
        self.halftime=swap(self.halftime,outgoing,incoming)

    def continue_match(self):
        """[designed: T47] One command for the same running child; stale fails closed."""
        if not self.busy or self.halftime is None or self.continued:
            raise ValueError('Halftime continuation was already used or is unavailable')
        if self.model.state is not self.original or encode(self.model.state,self.model.template_bytes)!=self.snapshot:
            self.cancel();raise ValueError('Halftime continuation is stale; active game changed')
        from goal2.desktop.worker import write_json
        write_json(self.directory/'continue.json',self.halftime['changes'])
        self.continued=True;self.halftime=None

    def _release(self):
        self.process=None;self.halftime=None;self.model.match_pending=False
        if self.folder is not None:
            self.errors.close();self.folder.cleanup();self.folder=None

    def cancel(self):
        """[designed] Bound termination waits and reap; never publish on close."""
        if self.busy:
            self.process.terminate()
            try:self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=0.5)
            finally:self._release()
