"""[designed: T70] UI-owned job lifecycle; subprocesses never own active state."""
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
        if self.busy or getattr(self.model,'match_pending',False):raise ValueError('A match is already running')
        if self.folder is not None:raise ValueError('Worker cleanup is pending; cancel again before starting')
        model=self.model
        if halftime and model.state.campaign is None:raise ValueError('Halftime interaction requires a campaign')
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
                    try:
                        packet=json.loads(preview.read_text());self.validate_halftime(packet)
                    except (OSError,ValueError,TypeError,KeyError) as exc:
                        self.cancel();raise ValueError(f'Invalid halftime preview: {exc}') from exc
                    self.halftime=packet
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

    def validate_halftime(self,packet):
        """[designed: T47] Reject malformed IPC before showing editable controls."""
        keys={'eleven','bench','available','captain','kind','removed','changes','score','teams'}
        if not isinstance(packet,dict) or set(packet)!=keys:raise ValueError('missing preview fields')
        for key in ('eleven','bench','available','score','teams'):
            if not isinstance(packet[key],list) or any(type(w) is not int for w in packet[key]):
                raise ValueError('invalid preview values')
        words=packet['eleven']+packet['bench']
        if (len(packet['eleven'])!=11 or len(packet['bench'])!=9 or len(set(words))!=20
                or set(words)!=set(self.original.managed_squad) or not set(packet['available'])<=set(words)
                or type(packet['captain']) is not int or packet['captain']!=self.original.captain
                or type(packet['kind']) is not int or packet['kind']!=1 or packet['removed']!=[] or packet['changes']!=[]
                or len(packet['score'])!=2 or min(packet['score'])<0):
            raise ValueError('preview differs from the pending game')
        fixture=self.original.campaign.next_fixture
        if packet['teams']!=[fixture.side_a,fixture.side_b]:raise ValueError('preview fixture changed')

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
        # [designed: T76/#233] A Windows venv child may still be closing inherited stderr after launcher wait.
        if self.folder is not None:
            self.errors.close();deadline=time.monotonic()+.5
            while True:
                try:
                    self.folder.cleanup()
                    break
                except PermissionError as exc:
                    remaining=deadline-time.monotonic()
                    if getattr(exc,'winerror',None)!=32 or remaining<=0:raise
                    time.sleep(min(.02,remaining))
                    if time.monotonic()>=deadline:raise
            self.folder=None
        self.process=None;self.halftime=None;self.model.match_pending=False

    def cancel(self):
        """[designed] Bound termination waits and reap; never publish on close."""
        if self.busy and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait(timeout=0.5)
            finally:self._release()
        elif self.folder is not None:self._release()
