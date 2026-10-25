#!/usr/bin/env python3
"""[designed: T123] One fresh, bounded original-key four-year acceptance campaign.

Original bytes stay in a fresh private .cache directory. Ordinary test gates do
not invoke this campaign; they exercise bounded genuine decisions and replay.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goal2.core import Core, views
from goal2.core.driver import Driver
from goal2.core.patches import OWNER_SUBSTITUTIONS
from goal2.core.cycle_player import Player, POLICY
from goal2.core.cycle_evidence import (INPUTS, PHASES, Trace, check_sources, fingerprint,
    git, progress, replay_step, runtime_manifest, sha, verify, write_json)


def run(output, *, cache=ROOT/'.cache', archaeology=None, max_steps=100000,
        max_rounds=300, max_seconds=7200):
    if not output.resolve().is_relative_to((ROOT/'.cache').resolve()):
        raise ValueError('Original-machine output must stay under the private git-ignored .cache directory')
    if git('status','--porcelain','--untracked-files=no'):
        raise ValueError('The campaign requires a clean committed runtime')
    inputs={}
    for kind,item in INPUTS.items():
        path=Path(cache)/item['name']
        raw=path.read_bytes()
        if sha(raw) != item['sha256']:
            raise ValueError('Original '+kind+' input hash differs')
        inputs[kind]=(path,raw)
    sources=check_sources(archaeology)
    runtime=runtime_manifest()
    output.mkdir(parents=True,exist_ok=False)
    report=dict(schema=1,status='running',variant=POLICY,inputs=INPUTS,sources=sources,
        runtime=runtime,start_year=2028,initial_country=None,initial=None,final=None,
        annual=[],steps=0,rounds=0,errors=[],bounds=dict(steps=max_steps,rounds=max_rounds,seconds=max_seconds),
        environment=dict(python=platform.python_version(),platform=sys.platform,unicorn=importlib.metadata.version('unicorn')))
    active={}
    started=time.monotonic()

    class RecordedCore(Core):
        # [designed: T123] Observe from construction, including the original
        # queued title/name reads. No guest register/memory or DOS input changes.
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            active['core']=self
            active['trace']=Trace(self,output)

    def bound():
        if time.monotonic()-started > max_seconds or report['steps'] >= max_steps or report['rounds'] >= max_rounds:
            raise RuntimeError('Bounded G16 campaign exhausted its declared step/round/time budget')

    try:
        # [derived: T106/NG9 at goal2 c0c7057e; designed: T123] Same new-career boot/date as the desktop;
        # DOS date/time are explicit inputs, not guest-memory/seed edits.
        core=RecordedCore.boot(inputs['boot'][1],(2027,10,4),dos_time=(10,0,0,0),
                               goal_dat=inputs['data'][0],title_key='n').core
        d=Driver(core)
        if d.wait.kind=='title-player-count':d.press(13,expect=('country-select',))
        if d.wait.kind!='country-select':raise ValueError('Fresh original boot did not reach country selection')
        countries=views.country_select(d.wait.state)['countries']
        matches=[c['country'] for c in countries if c['name'].casefold()=='holland']
        if len(matches)!=1:raise ValueError('Original country catalogue has no unique Holland')
        country=matches[0]
        d.new_game(country,'G16 Proof')
        core.apply_patch(OWNER_SUBSTITUTIONS)
        active['trace'].start_game()
        initial=core.save();(output/'initial.g2core').write_bytes(initial)
        report.update(initial_country=country,initial=progress(core),initial_sha256=sha(initial),
                      dos_date=list(core.date),dos_time=list(core.dos_time),initial_keys=fingerprint(core))
        if (report['initial']['season'],report['initial']['stage'],report['initial']['year']) != (0,2,2028):
            raise ValueError('Original new career did not start at the declared source boundary')
        bound()
        player=Player(d)
        transitions=[]
        last_phase=None
        while True:
            bound()
            if core.wait.kind=='manager-menu':
                state=progress(core);phase=(state['season'],state['stage'],state['year'])
                if phase != last_phase:
                    transitions.append(state)
                    last_phase=phase
                    report['transitions']=transitions
                    write_json(output/'report.json',report)
                    print('G16 boundary',json.dumps(state,sort_keys=True),flush=True)
                index=len(report['annual'])
                if index < len(PHASES) and phase == PHASES[index]:
                    # Mutate only the real direct campaign, then independently
                    # execute that same named step from the annual private save.
                    replay=replay_step(core,inputs['data'][0],output,f'annual-{index+1}')
                    report['annual'].append(dict(number=index+1,progress=state,replay=replay))
                    report['steps']+=1
                    if replay['action']=='round_start':report['rounds']+=1
                    player=Player(Driver(core))
                    print('G16 annual exact replay',index+1,replay['action'],replay['direct']['kind'],flush=True)
                    if index+1==len(PHASES):
                        # The final proof boundary is the saved start of year5;
                        # its next-decision replay is evidence, not an extra year.
                        final=(output/replay['before']).read_bytes()
                        (output/'final.g2core').write_bytes(final)
                        final_core=Core.load(final,goal_dat=inputs['data'][0])
                        report.update(final=progress(final_core),final_save='final.g2core',final_sha256=sha(final),
                                      history=views.history(final_core.wait.state,country)['results'])
                        break
                    continue
                if state['season'] > 2:
                    raise ValueError('Campaign passed its target without the required annual boundaries')
            action=player.step()
            report['steps']+=1
            if action=='round_start':report['rounds']+=1
            if report['steps'] % 25 == 0:
                report['last_wait']=dict(kind=core.wait.kind,site=core.wait.site)
                write_json(output/'report.json',report)
                print('G16 progress',report['steps'],report['rounds'],core.wait.kind,flush=True)
        trace=active['trace'];trace.close()
        (output/'trace-end.g2core').write_bytes(core.save())
        report.update(trace=trace.summary(),status='complete',elapsed_seconds=time.monotonic()-started)
        report['transitions']=trace.boundaries
        report['trace_end']=fingerprint(core)
        report['trace_end_sha256']=sha((output/'trace-end.g2core').read_bytes())
        write_json(output/'report.json',report)
        verify(output,data_path=inputs['data'][0],archaeology=archaeology)
        if time.monotonic()-started > max_seconds:
            raise RuntimeError('G16 completed beyond its declared wall-time bound')
        report['elapsed_seconds']=time.monotonic()-started
        write_json(output/'report.json',report)
        print('PASS G16 four-year cycle and four independent annual original-key replays',flush=True)
        return report
    except BaseException as error:
        trace=active.get('trace')
        if trace is not None:
            if trace.last_error is None:trace.capture_failure(error)
            trace.close();report['trace']=trace.summary();report['failure']=trace.last_error
        report.update(status='failed',errors=[type(error).__name__+': '+str(error).splitlines()[0]],
                      elapsed_seconds=time.monotonic()-started)
        (output/'failure.txt').write_text(traceback.format_exc())
        write_json(output/'report.json',report)
        raise


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'.cache/T123-proof')
    p.add_argument('--cache',type=Path,default=ROOT/'.cache')
    p.add_argument('--archaeology',type=Path)
    p.add_argument('--max-steps',type=int,default=100000)
    p.add_argument('--max-rounds',type=int,default=300)
    p.add_argument('--max-seconds',type=int,default=7200)
    a=p.parse_args(argv)
    if min(a.max_steps,a.max_rounds,a.max_seconds)<=0:p.error('bounds must be positive')
    try:
        run(a.output,cache=a.cache,archaeology=a.archaeology,max_steps=a.max_steps,
            max_rounds=a.max_rounds,max_seconds=a.max_seconds)
    except Exception as error:
        print('FAIL G16:',error,file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':sys.exit(main())
