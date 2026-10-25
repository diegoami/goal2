"""[designed: T123] Private original-machine evidence and strict cycle verification.

Structural validation alone is not a proof. verify() also binds source/runtime,
the complete input trace, real saved machines, and independently executed replay.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import zipfile

from goal2.core.cycle_player import POLICY

ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    'boot': {'name': 'e039-r0005-date-call.sav', 'sha256': '0d9c683023c7327f17bfc29900f2eff4e703641d21d3f353693f09654688494b'},
    'data': {'name': 'GOAL.DAT', 'sha256': 'bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca'},
}
# [confirmed: E031 C52/b/d/e, C65b at the exact source manifest pin]
PHASES = ((0, 3, 2028), (1, 5, 2030), (1, 7, 2030), (2, 2, 2032))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def expected_sources():
    return json.loads((ROOT/'docs/evidence/T123/sources.json').read_text())


def check_sources(repository=None):
    expected = expected_sources()
    repository = Path(repository or os.environ.get('GOAL2_ARCHAEOLOGY', ROOT.parent/'goal2-archaeology'))
    content = {}
    for item in expected['files']:
        raw = subprocess.check_output(['git', '-C', str(repository), 'show', expected['commit'] + ':' + item['path']])
        if sha(raw) != item['sha256'] or len(raw) != item['bytes']:
            raise ValueError('E031 source hash/length mismatch: ' + item['path'])
        content[item['path']] = raw.decode()
    claims = content['experiments/E031-play-the-game/claims.tsv']
    if not all(any(line.startswith(key+'\t') for line in claims.splitlines()) for key in expected['claim_ids']):
        raise ValueError('Missing pinned E031 structural claim')
    progress = content['experiments/E031-play-the-game/out/g1/progress.md']
    if 'stage 2, season word 2' not in progress or 'stage 3, season word 0' not in progress:
        raise ValueError('Pinned E031 progression is incomplete')
    return expected


def runtime_paths():
    paths = list((ROOT/'goal2/core').glob('*.py')) + list((ROOT/'goal2/engine').rglob('*.py'))
    paths += [ROOT/p for p in ('goal2/desktop/core_model.py', 'tools/prove_core_cycle.py',
              'tools/verify_core_cycle.py', 'PROVENANCE.md', 'pyproject.toml',
              'docs/evidence/T123/sources.json', 'docs/tasks/T123.md')]
    return sorted(p for p in paths if p.is_file())


def runtime_manifest():
    return dict(head=git('rev-parse', 'HEAD'), files={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in runtime_paths()})


def fingerprint(core):
    snap = core.m.snapshot()
    return dict(memory=sha(snap['memory']), cpu=sha(canonical(snap['regs'])), keys=sha(canonical(core.keys)),
                key_count=len(core.keys), save=sha(core.save()), kind=core.wait.kind,
                site=core.wait.site, poll=core.wait.poll)


def progress(core):
    """[confirmed: F007/F023/F030 at archaeology 44cea4de; views at goal2 c0c7057e]
    Raw game calendar words plus the manager-title year calculation and named RNG words."""
    from goal2.core import views
    m = views.Memory(core.wait.state)
    stage, season, klass = m.game(0x3C), m.game(0x38, 2), m.game(0x40)
    return dict(stage=stage, season=season, year=m.game(0x3A, 2)+2*season-2*(klass != int(stage > 4)),
                start_year=m.game(0x3A, 2), klass=klass, fixture=m.game(0x26, 2), fixtures=m.game(0x28, 2),
                country=m.manager_country(0x80+m.game(1)),
                seeds={f'{a:04X}': core.m.rd(a) for a in (0x7B62, 0x7B64, 0x8336)})


def saved_path(root, name):
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError('Evidence paths must be local basenames')
    path = (Path(root)/name).resolve()
    if path.parent != Path(root).resolve():
        raise ValueError('Evidence path escaped its private directory')
    return path


class Trace:
    """Read-only host observation; original methods supply every guest key/write."""
    def __init__(self, core, root):
        self.core, self.root = core, Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root/'trace.jsonl'
        self.stream = self.path.open('x', encoding='utf-8')
        self.rows = self.operations = 0
        self.chain = '0'*64
        self.consumed = []
        self.game_started = False
        self.boundaries = []
        self.originals = {}
        self.last_kind = None
        self.last_error = None
        for name in ('press', 'release', 'advance'):
            original = getattr(core, name)
            self.originals[name] = original
            def observed(*args, _name=name, _original=original, **kwargs):
                wait = core.wait
                row = dict(op=_name,args=list(args),kwargs=kwargs,kind=wait.kind if wait else None,
                           site=wait.site if wait else None,explicit_before=len(core.keys),
                           stops=sorted(core.stops),queued=list(core.queued))
                try:
                    if self.game_started:row['progress_before']=self.observe_progress()
                    if wait is not None and (_name != 'advance' or wait.kind != 'match-live' or self.last_kind != 'match-live'):
                        (self.root/'last-before.g2core').write_bytes(core.save())
                        self.last_kind = wait.kind
                    self.operations += 1
                    result = _original(*args, **kwargs)
                    row.update(after=core.wait.kind,explicit_after=len(core.keys))
                    if self.game_started:row['progress_after']=self.observe_progress()
                    self._append(row)
                    return result
                except BaseException as error:
                    row.update(error=type(error).__name__,message=str(error).splitlines()[0])
                    self._append(row)
                    self.capture_failure(error)
                    raise
            setattr(core, name, observed)
        self.originals['_answer'] = core._answer
        original_answer = core._answer
        def answered(key):
            # Includes queued boot/name/captain keys, which Core.keys alone does
            # not enumerate. Observe the actual read, not the requested queue.
            m = core.m
            site = m.where(m.stack_word(2), m.stack_word(0))
            result = original_answer(key)
            self.consumed.append(key)
            self._append(dict(op='key',key=key,site=site))
            return result
        core._answer = answered

    def observe_progress(self):
        state=progress(self.core)
        key=tuple(state[k] for k in ('season','stage','year'))
        if not self.boundaries or key != tuple(self.boundaries[-1][k] for k in ('season','stage','year')):
            self.boundaries.append(state)
        return state

    def start_game(self):
        self.game_started=True
        self.observe_progress()

    def _append(self, row):
        row = dict(row, n=self.rows, previous=self.chain)
        self.chain = sha(canonical(row))
        row['chain'] = self.chain
        self.stream.write(json.dumps(row, sort_keys=True)+'\n');self.stream.flush()
        self.rows += 1

    def capture_failure(self, error):
        snap = self.core.m.snapshot()
        with zipfile.ZipFile(self.root/'actual.ucstate', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('memory.bin', snap['memory'])
            archive.writestr('registers.json', json.dumps(dict(load=self.core.m.load, regs=snap['regs']), sort_keys=True))
        self.last_error = dict(type=type(error).__name__,message=str(error).splitlines()[0],
                               machine='actual.ucstate',sha256=sha((self.root/'actual.ucstate').read_bytes()))

    def close(self):
        for name, original in self.originals.items():
            setattr(self.core, name, original)
        if not self.stream.closed:
            self.stream.close()

    def summary(self):
        self.stream.flush() if not self.stream.closed else None
        return dict(rows=self.rows,operations=self.operations,sha256=sha(self.path.read_bytes()),last_chain=self.chain,
                    consumed=len(self.consumed),keys_sha256=sha(canonical(self.consumed)))


def replay_step(core, data_path, root, stem):
    from goal2.core import Core
    from goal2.core.driver import Driver
    from goal2.core.cycle_player import Player
    raw = core.save()
    name = stem+'.g2core'
    saved_path(root,name).write_bytes(raw)
    other = Core.load(raw, goal_dat=data_path)
    action = Player(Driver(core)).step()
    repeated = Player(Driver(other)).step()
    direct, resumed = fingerprint(core), fingerprint(other)
    if action != repeated or direct != resumed:
        raise ValueError('Annual original-key replay differs in memory/CPU/keys/save or destination')
    return dict(before=name,before_sha256=sha(raw),action=action,direct=direct,resumed=resumed)


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_report(report):
    """Structural checks only; callers must use verify() for machine-backed acceptance."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(isinstance(report,dict),'Cycle report must be an object')
    require(type(report.get('schema')) is int and report['schema'] == 1 and report.get('status') == 'complete','Incomplete/failed cycle report')
    require(report.get('variant') == POLICY and report.get('inputs') == INPUTS,'Cycle input/policy mismatch')
    require(report.get('sources') == expected_sources(),'Cycle E031 source contract mismatch')
    require(report.get('start_year') == 2028,'Cycle start year differs')
    require(report.get('dos_date') == [2027,10,4] and report.get('dos_time') == [10,0,0,0],'Cycle DOS inputs differ')
    require(report.get('errors') == [],'Cycle contains errors')
    for key, expected in (('initial',(0,2,2028)),('final',(2,2,2032))):
        value=report.get(key,{})
        require(all(type(value.get(k)) is int for k in ('season','stage','year')),'Invalid '+key+' boundary types')
        require(tuple(value.get(k) for k in ('season','stage','year')) == expected,'Wrong '+key+' cycle boundary')
    require(type(report.get('initial_country')) is int and 1 <= report['initial_country'] <= 128,'Missing initial country')
    require(type(report.get('steps')) is int and report['steps'] > 0,'Empty policy execution')
    bounds=report.get('bounds',{})
    require(all(type(bounds.get(k)) is int and bounds[k] > 0 for k in ('steps','rounds','seconds')),'Missing execution bounds')
    require(report['steps'] <= bounds['steps'] and type(report.get('rounds')) is int and 0 < report['rounds'] <= bounds['rounds'],'Execution exceeded step/round bounds')
    elapsed=report.get('elapsed_seconds')
    require(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0 < elapsed <= bounds['seconds'],'Execution exceeded time bound')
    runtime=report.get('runtime',{})
    require(isinstance(runtime.get('head'),str) and re.fullmatch('[0-9a-f]{40}',runtime['head']) is not None,'Missing runtime head')
    require(isinstance(runtime.get('files'),dict) and bool(runtime['files']) and all(_digest(v) for v in runtime['files'].values()),'Missing runtime hashes')
    trace=report.get('trace',{})
    require(type(trace.get('rows')) is int and trace['rows'] > 0 and _digest(trace.get('sha256')) and _digest(trace.get('last_chain')),'Missing trace evidence')
    require(type(trace.get('operations')) is int and trace['operations'] > 0 and type(trace.get('consumed')) is int
            and trace['consumed'] > 0 and _digest(trace.get('keys_sha256')),'Missing consumed input evidence')
    annual=report.get('annual')
    require(isinstance(annual,list) and len(annual) == 4,'Four annual boundaries are required')
    for index,(entry,phase) in enumerate(zip(annual,PHASES),1):
        require(entry.get('number') == index,'Annual boundary order differs')
        p=entry.get('progress',{})
        require(all(type(p.get(k)) is int for k in ('season','stage','year')),'Invalid annual boundary types')
        require(tuple(p.get(k) for k in ('season','stage','year')) == phase,'Wrong annual stage/season/year')
        replay=entry.get('replay',{})
        require(isinstance(replay.get('before'),str) and Path(replay['before']).name == replay['before'],'Invalid annual save path')
        require(_digest(replay.get('before_sha256')) and bool(replay.get('action')),'Missing annual replay evidence')
        direct=replay.get('direct',{})
        require(bool(direct) and direct == replay.get('resumed'),'Annual replay mismatch')
        require(all(_digest(direct.get(k)) for k in ('memory','cpu','keys','save')),'Missing machine replay hashes')
        require(type(direct.get('key_count')) is int and bool(direct.get('kind')) and bool(direct.get('site')),'Missing replay destination')
    transitions=report.get('transitions')
    require(isinstance(transitions,list) and bool(transitions),'Missing observed progression boundaries')
    observed=[tuple(p.get(k) for k in ('season','stage','year')) for p in transitions]
    require(observed[0] == (0,2,2028),'Observed progression has no fresh starting boundary')
    # A source claim establishes annual boundaries, not a prescribed count of
    # intermediate screens/qualification-dependent phases. Require them in order.
    cursor=0
    for phase in PHASES:
        try:cursor=observed.index(phase,cursor)+1
        except ValueError as error:raise ValueError('Observed progression is missing/reordered') from error
    require(isinstance(report.get('final_save'),str) and Path(report['final_save']).name == report['final_save'] and _digest(report.get('final_sha256')),'Missing final save')
    require([r.get('season') for r in report.get('history',[])] == ['2027/28','2029/30'],'Missing/incorrect original history seasons')
    return report


def verify(root, data_path=None, archaeology=None):
    """Accept only source-bound traces and original machines with independently replayed annual steps."""
    from goal2.core import Core, views
    from goal2.core.driver import Driver
    from goal2.core.cycle_player import Player
    from goal2.core.patches import OWNER_SUBSTITUTIONS
    root=Path(root)
    report=validate_report(json.loads((root/'report.json').read_text()))
    data_path=Path(data_path or ROOT/'.cache/GOAL.DAT')
    if sha(data_path.read_bytes()) != INPUTS['data']['sha256']:
        raise ValueError('Original data hash mismatch')
    check_sources(archaeology)
    current=runtime_manifest()
    if current['files'] != report['runtime']['files']:
        raise ValueError('Current runtime differs from the executed proof')
    for path,digest in report['runtime']['files'].items():
        try:
            raw=subprocess.check_output(['git','show',report['runtime']['head']+':'+path],cwd=ROOT,stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as error:
            raise ValueError('Recorded proof runtime source is unavailable: '+path) from error
        if sha(raw) != digest:
            raise ValueError('Proof runtime was not its recorded committed source: '+path)
    trace=(root/'trace.jsonl').read_bytes()
    if sha(trace) != report['trace']['sha256']:
        raise ValueError('Original input trace hash mismatch')
    rows=[json.loads(line) for line in trace.splitlines()]
    chain='0'*64;keys=[];observed=[]
    explicit_count=0
    for index,row in enumerate(rows):
        item=dict(row);claimed=item.pop('chain',None)
        if item.get('n') != index or item.get('previous') != chain or claimed != sha(canonical(item)) or item.get('error'):
            raise ValueError('Truncated/failed/reordered original input trace')
        if item.get('op') not in ('key','press','release','advance'):
            raise ValueError('Unsupported trace operation')
        if item['op'] == 'key':keys.append(item['key'])
        else:
            if item.get('explicit_before') != explicit_count:
                raise ValueError('Original explicit key count is discontinuous')
            if item['op']=='press':explicit_count+=1
            if item.get('explicit_after') != explicit_count:
                raise ValueError('Original explicit key count differs after operation')
            for name in ('progress_before','progress_after'):
                state=item.get(name)
                if state is not None and (not observed or tuple(state[k] for k in ('season','stage','year')) !=
                                           tuple(observed[-1][k] for k in ('season','stage','year'))):
                    observed.append(state)
        chain=claimed
    if len(rows) != report['trace']['rows'] or chain != report['trace']['last_chain'] or not keys:
        raise ValueError('Incomplete original input trace')
    if report['trace'].get('consumed') != len(keys) or report['trace'].get('keys_sha256') != sha(canonical(keys)):
        raise ValueError('Consumed original keys differ')
    if observed != report['transitions']:
        raise ValueError('Reported boundaries differ from actual original input trace')
    for entry in report['annual']:
        replay=entry['replay'];raw=saved_path(root,replay['before']).read_bytes()
        if sha(raw) != replay['before_sha256']:
            raise ValueError('Annual original machine hash mismatch')
        core=Core.load(raw,goal_dat=data_path)
        if core.patches != (OWNER_SUBSTITUTIONS,) or core.wait.kind != 'manager-menu' or progress(core) != entry['progress']:
            raise ValueError('Annual original machine boundary/policy differs')
        action=Player(Driver(core)).step()
        if action != replay['action'] or fingerprint(core) != replay['direct']:
            raise ValueError('Independent annual original-key replay differs')
    initial=(root/'initial.g2core').read_bytes()
    if sha(initial) != report.get('initial_sha256'):
        raise ValueError('Fresh initial original machine hash mismatch')
    core=Core.load(initial,goal_dat=data_path)
    if (core.patches != (OWNER_SUBSTITUTIONS,) or core.template_sha256 != INPUTS['boot']['sha256']
            or core.date != (2027,10,4) or core.dos_time != (10,0,0,0)
            or core.wait.kind != 'manager-menu' or progress(core) != report['initial']
            or views.country_card(core.wait.state,report['initial_country'])['name'].casefold() != 'holland'):
        raise ValueError('Initial original machine is not the declared fresh Holland career')
    if fingerprint(core) != report.get('initial_keys'):
        raise ValueError('Initial original machine input/save identity differs')
    if report.get('dos_date') != list(core.date) or report.get('dos_time') != list(core.dos_time):
        raise ValueError('Reported DOS inputs differ from the saved original machine')
    initial_keys=list(core.keys)
    ending=(root/'trace-end.g2core').read_bytes()
    if sha(ending) != report.get('trace_end_sha256'):
        raise ValueError('Trace-end original machine hash mismatch')
    end_core=Core.load(ending,goal_dat=data_path)
    if fingerprint(end_core) != report.get('trace_end'):
        raise ValueError('Trace-end original machine differs')
    explicit=[ord(r['args'][0]) if isinstance(r['args'][0],str) else r['args'][0] for r in rows if r['op']=='press']
    if explicit != end_core.keys:
        raise ValueError('Original explicit key log does not match the executed trace')
    if end_core.keys[:len(initial_keys)] != initial_keys:
        raise ValueError('Fresh initial key history is not a prefix of the played campaign')
    raw=saved_path(root,report['final_save']).read_bytes()
    if sha(raw) != report['final_sha256']:
        raise ValueError('Final original machine hash mismatch')
    core=Core.load(raw,goal_dat=data_path)
    if core.patches != (OWNER_SUBSTITUTIONS,) or core.wait.kind != 'manager-menu' or progress(core) != report['final']:
        raise ValueError('Final original machine is not the reported cycle endpoint')
    history=views.history(core.wait.state,report['initial_country'])['results']
    if history != report['history']:
        raise ValueError('Original history differs from the cycle report')
    return report
