"""[designed: #236] Audit main's native execution with an externally supplied receipt anchor.

This reads retained observations; it never launches Windows or accepts a new native run.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import struct
import subprocess

FROZEN = 'dfed1519af51dcb105d2526621eec9b313dd4b83'
FRAMES = [(4439,4438,'07a610d219ed816579ed91bf76319fa97a94062810ac38094034291f036db292'),
          (4830,4829,'81b1761ca799f98085f1c50de0d12b18f9aed7a9c09244566d41455e54cb47f1')]
RESOURCES = {'e010-r0008-halftime.sav':'ae2935b9c490745450462b981eb133e611bc72de4abfb11aba3e850caf4e9949',
             'GOAL.DAT':'bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca',
             'e0afff6751747233-e006-1000-r0001.sav':'e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def safe(root,name):
    parts=PurePosixPath(name)
    assert not parts.is_absolute() and '..' not in parts.parts and '\\' not in name, name
    path=root.joinpath(*parts.parts)
    assert not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),name
    return path

def png(path):
    raw=path.read_bytes()
    assert raw[:8]==b'\x89PNG\r\n\x1a\n' and raw[12:16]==b'IHDR',path
    width,height=struct.unpack('!II',raw[16:24]);assert width>0 and height>0
    return [width,height]

def audit(config,anchor):
    root=Path.cwd();evidence=safe(root,config['evidence']);original=safe(root,config['original_receipt'])
    assert re.fullmatch('[0-9a-f]{64}',anchor),'external receipt SHA256 required'
    assert sha(original)==anchor,'independent main receipt does not match external anchor'
    tracked=evidence/'host-receipt.json'
    assert sha(tracked)==anchor and tracked.read_bytes()==original.read_bytes(),'tracked receipt differs from main original'
    r=json.loads(original.read_text())
    assert r['head']==FROZEN and r['attempt']=='native-01' and r['result']=='PASS'
    assert r['protected_unchanged'] is True and r['protected_before']==r['protected_after']
    assert len(r['protected_before'])==4 and {Path(p).name for p in r['protected_before']}=={'desktop.g2save','e010-r0008-halftime.sav','GOAL.DAT','Start-goal2.cmd'}
    assert all(re.fullmatch('[0-9a-f]{64}',h)for h in r['protected_before'].values())
    assert r['resources']==RESOURCES
    archived=set(git('ls-tree','-r','--name-only',FROZEN,'goal2','tools/desktop-ui').splitlines())
    assert set(r['sources'])==archived and len(archived)==176,'native source inventory incomplete'
    for name,want in r['sources'].items():
        assert sha(safe(root,name))==want,('current source differs',name)
        raw=subprocess.check_output(['git','show',FROZEN+':'+name])
        assert hashlib.sha256(raw).hexdigest()==want,('frozen source differs',name)
    # [designed] Only owned evidence documentation may follow the native source checkpoint.
    changes=set(git('diff','--name-only',FROZEN,'HEAD').splitlines())
    changes.update(git('diff','--name-only','HEAD').splitlines())
    assert all(p.startswith('docs/evidence/fix236/')for p in changes),('non-evidence source carry',changes)
    versions={'T78':('2.1.4','unicorn',43),'T79':('2.5.8','pygame',523)}
    assert set(r['dependencies'])==set(versions)
    for task,(version,package,count) in versions.items():
        dep=r['dependencies'][task];assert dep['version']==dep['native_import']['version']==version
        assert '.goal2-validation' in dep['directory'] and dep['directory'].endswith('/python-libs')
        assert '.goal2-validation' in dep['native_import']['file']
        assert re.split(r'[\\/]+',dep['native_import']['file'])[-3:]==['python-libs',package,'__init__.py']
        assert len(dep['files'])==count and len(dep['wheels'])==1
        assert all(re.fullmatch('[0-9a-f]{64}',h)for h in [*dep['files'].values(),*dep['wheels'].values(),dep['setup_log_sha256']])
    for name,want in r['observers'].items():assert sha(safe(evidence,name))==want
    assert set(r['observers'])=={'parent-observer.py','viewer-observer.py'}
    assert len(r['artifacts'])==26
    for name,want in r['artifacts'].items():
        assert re.fullmatch(r'observations/scale-[12]/[^/]+\.(png|json|log)',name),name
        assert sha(safe(evidence,name))==want,('native artifact differs',name)
    observed={p.relative_to(evidence).as_posix()for p in (evidence/'observations').rglob('*')if p.is_file()}
    assert observed==set(r['artifacts']),'unreceipted or missing observations'
    assert [run['scale']for run in r['runs']]==['1','2']
    reports=[]
    for run in r['runs']:
        scale=run['scale'];assert run['exit']==0 and run['seconds']>0 and run['deterministic_tests']==13
        assert run['report']==f'observations/scale-{scale}/report.json'
        report_path=safe(evidence,run['report']);assert sha(report_path)==run['report_sha256']
        assert sha(evidence/f'native-{scale}.log')==run['log_sha256']
        assert sha(evidence/f'native-{scale}.py')==run['wrapper_sha256']
        log=(evidence/f'native-{scale}.log').read_text()
        assert all(word not in log for word in ('Traceback (most recent call last)','Error calling Python override','FAILED','skipped'))
        assert re.search(r'Ran 13 tests in [0-9.]+s',log)and re.search(r'Ran 1 test in [0-9.]+s',log)
        assert log.count('\nOK\n')==2 and log.count('"state_memory_rng_history_equal": true')==2
        outcomes,_=json.JSONDecoder().raw_decode(log[log.index('\n[\n')+1:])
        assert len(outcomes)==2
        for n,(outcome,fixture,events,score,seeds,memory) in enumerate(zip(outcomes,[1378,1471],[1171,1392],[[2,3],[2,0]],[[29619,33187],[36752,2052]],['3b90568c708215c1ec47c8eb6416e4afb8ef46cf36d4cf3f15397a7fb71f97fd','f13b94f7d91ac3db098c142a7467bcd08e2b6995a798dd93989b0d7a1073bd35']),1):
            assert outcome['round']==n and outcome['fixture']==fixture and outcome['events']==events and outcome['score']==score
            assert outcome['seeds']==seeds and outcome['image_sha256']==memory and outcome['state_memory_rng_history_equal']is True
            assert outcome['heartbeats']>5 and re.fullmatch('[0-9a-f]{64}',outcome['digest'])
            assert outcome['engine_year']==0 and outcome['captain']==64 and outcome['tactics']==152 and outcome['eleven']==list(range(61,72))
        report=json.loads(report_path.read_text())
        assert report['result']=='PASS' and report['qpa']=='windows' and 'Windows' in report['platform']
        assert report['qt']=='6.12.0' and report['python'].startswith('3.13.15')
        assert report['actual_qt_ratio']==float(scale) and report['requested_qt_scale']==scale
        assert report['deterministic_tests']==13 and report['original_acceptance_tests']==1
        assert report['callbacks']==[] and report['clean_widgets'] is True and report['owned_resources_closed'] is True
        expected=[{'frames':n,'final_ack':ack,'frame_digest':digest}for n,ack,digest in FRAMES]
        assert report['frames']==run['frames']==expected
        assert len(report['qt_captures'])==2
        for n,c in enumerate(report['qt_captures'],1):
            assert c['file']==f'qt-complete-{n}.png' and c['ratio']==float(scale)
            assert png(safe(report_path.parent,c['file']))==[int(v*float(scale))for v in c['logical_size']]
        sdl=report['sdl'];assert len(sdl)==4
        assert sorted(x['stage']for x in sdl)==['complete','complete','live','live']
        assert {x['frame_sequence']for x in sdl if x['stage']=='complete'}=={4438,4829}
        assert len({c['pid']for c in sdl})==2
        for pid in {c['pid']for c in sdl}:assert {c['stage']for c in sdl if c['pid']==pid}=={'live','complete'}
        for c in sdl:
            assert c['driver']=='windows' and c['surface']==c['window']==[1000,720] and c['dpi']==96
            assert c['qt_scale_requested']==scale and type(c['pid'])is int and c['pid']>0
            rect=c['window_rect'];assert len(rect)==4 and rect[2]>rect[0]and rect[3]>rect[1]
            if c['stage']=='complete':assert c['frame_consumed_before_status']==c['frame_sequence']
            else:assert c['frame_sequence']in(0,1)and c['frame_consumed_before_status']==-1
            meta=safe(report_path.parent,Path(c['capture']).with_suffix('.json').as_posix())
            assert json.loads(meta.read_text())==c
            assert png(safe(report_path.parent,c['capture']))==[1000,720]
        for p in report_path.parent.glob('viewer-stderr-*.log'):assert p.read_bytes()==b''
        reports.append({'scale':scale,'qt_ratio':report['actual_qt_ratio'],'sdl_surface':[1000,720],'sdl_dpi':96,'frames':report['frames']})
    inventory=json.loads((evidence/'inventory.json').read_text())
    for name,want in inventory.items():assert sha(safe(evidence,name))==want,('inventory differs',name)
    assert set(inventory)=={p.relative_to(evidence).as_posix()for p in evidence.rglob('*')if p.is_file()and p.name!='inventory.json'}
    return {'result':'PASS','claim':'Retained main execution evidence audit; no Windows re-execution','native_checkpoint':FROZEN,'current_head':git('rev-parse','HEAD'),'source_files':176,'dependency_files':566,'protected_unchanged':4,'resources':3,'reports':reports,'independent_main_receipt_sha256':anchor,'inventory_files':len(inventory)}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='.cache/main-native-proof-config.json');parser.add_argument('--expected-receipt-sha256',required=True)
    args=parser.parse_args();print(json.dumps(audit(json.loads(Path(args.config).read_text()),args.expected_receipt_sha256),indent=2))
