"""Main-owned native Windows planning mock; not T75 implementation acceptance."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

ROOT = Path('/home/diego/projects/goal2')
WIN = Path('/mnt/c/Users/diego/projects/goal2-exe')
WT = Path('/home/diego/projects/goal2-work/T75-football-ui')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def windows(path):
    return 'C:\\' + str(path.relative_to('/mnt/c')).replace('/', '\\')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--head', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert len(args.head) == 40
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip() == args.head
    subprocess.run(['git','diff','--quiet','HEAD','--','goal2','tools'],cwd=WT,check=True)
    output = Path(args.output)
    assert output.is_relative_to(ROOT / '.cache') and not output.exists()
    output.mkdir(parents=True)
    folder = WIN / '.goal2-validation' / ('T75-preflight-' + args.head[:12] + '-' + str(time.time_ns()))
    assert not folder.exists()
    protected = {str(p):sha(p) for p in (WIN/'.cache').rglob('*')
                 if p.is_file() and p.suffix.lower() in ('.sav','.g2save','.dat')}
    protected[str(WIN/'Start-goal2.cmd')] = sha(WIN/'Start-goal2.cmd')
    receipt = {'tag':'[designed: T75 planning only]','head':args.head,'directory':str(folder),
               'protected_before':protected,'runs':[],'result':'INCOMPLETE'}
    folder.mkdir(parents=True)
    archive_bytes = subprocess.check_output(['git','archive',args.head,'goal2','tools/desktop-ui/redesign.py'],cwd=WT)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
        for member in archive.getmembers():
            assert not member.issym() and not member.islnk()
            path = folder / member.name
            assert path.resolve().is_relative_to(folder.resolve())
            if member.isdir():
                path.mkdir(parents=True,exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(archive.extractfile(member).read())
    probe = ROOT/'.cache/kept/review-receipts/T75-main-preflight.py'
    (folder/'main-overview-preflight.py').write_bytes(probe.read_bytes())
    sources = {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}
    receipt['source_files'] = sources
    cache = folder/'.cache'
    cache.mkdir()
    (cache/'tmp').mkdir()
    fixtures = {}
    for name in ('e010-r0008-halftime.sav','GOAL.DAT'):
        source = WT/'.cache'/name
        target = cache/name
        target.write_bytes(source.read_bytes())
        assert sha(target) == sha(source)
        fixtures[name] = sha(source)
    receipt['fixtures'] = fixtures
    try:
        for scale in ('1','2'):
            wrapper = folder/('verify-native-'+scale+'.py')
            evidence = folder/'evidence'/('scale-'+scale)
            wrapper.write_text(
                'import os,sys,runpy\n'
                "os.environ['QT_QPA_PLATFORM']='windows'\n"
                "os.environ['QT_SCALE_FACTOR']="+repr(scale)+'\n'
                "os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'\n"
                "os.environ['PYTHONDONTWRITEBYTECODE']='1'\n"
                "os.environ['TMPDIR']="+repr(windows(cache/'tmp'))+'\n'
                "os.environ['TEMP']="+repr(windows(cache/'tmp'))+'\n'
                "os.environ['TMP']="+repr(windows(cache/'tmp'))+'\n'
                "assert sys.platform=='win32'\n"
                'sys.argv='+repr([windows(folder/'main-overview-preflight.py'),'--mode','mock','--output',windows(evidence)])+'\n'
                "runpy.run_path(sys.argv[0],run_name='__main__')\n")
            log = output/('native-scale-'+scale+'.log')
            started = time.monotonic()
            with log.open('xb') as stream:
                result = subprocess.run([str(WIN/'.venv/Scripts/python.exe'),'-B',windows(wrapper)],
                    cwd=folder,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,
                    stdout=stream,stderr=subprocess.STDOUT,timeout=240)
            entry = {'scale':scale,'exit':result.returncode,'seconds':round(time.monotonic()-started,3),
                     'log':log.name,'log_sha256':sha(log),'wrapper_sha256':sha(wrapper)}
            receipt['runs'].append(entry)
            assert result.returncode == 0, log.read_text(errors='replace')[-5000:]
            report = json.loads((evidence/'receipt.json').read_text())
            assert report['result'] == 'PASS' and report['qpa'] == 'windows'
            assert report['ratio'] == int(scale), report['ratio']
            assert report['requested_scale'] == scale and 'Windows' in report['platform']
            assert report['probe_sha256'] == sources['main-overview-preflight.py']
            for path, h in report['sources'].items():
                assert sources[path.replace('\\','/')] == h, path
            assert report['resources'] == fixtures
            assert len(report['steps'])==3 and all(row['all20_names'] and row['pool80'] and row['active_and_save_unchanged'] for row in report['steps'])
            assert all(report[key] for key in ('invalid_draft_return','explicit_campaign_friendly_resume','completed_result_restored','source_unchanged'))
            assert len(list(evidence.glob('preview-*.png')))==3
            assert report['initial_viewport'][0]<=report['available'][0] and report['initial_viewport'][1]<=report['available'][1]
            entry['interaction_sha256'] = sha(evidence/'receipt.json')
            entry['actual_ratio'] = report['ratio']
            entry['platform'] = report['platform']
            entry['qt'] = report['qt']
            entry['captures'] = len(list(evidence.glob('preview-*.png')))
            entry['countries'] = [row['name'] for row in report['steps']]
        assert all(sha(folder/path) == h for path,h in sources.items()), 'staged source changed'
        assert all(sha(cache/name) == h for name,h in fixtures.items()), 'fixture changed'
        assert all(sha(Path(path)) == h for path,h in protected.items()), 'protected Windows files changed'
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=WT,text=True).strip() == args.head
        subprocess.run(['git','diff','--quiet','HEAD','--','goal2','tools'],cwd=WT,check=True)
        receipt['result'] = 'PASS'
    finally:
        receipt['protected_after'] = {path:sha(Path(path)) for path in protected}
        receipt['artifacts'] = {str(p.relative_to(folder)):sha(p) for p in (folder/'evidence').rglob('*') if p.is_file()}
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'result':receipt['result'],'head':args.head,'windows_directory':str(folder),
                      'runs':receipt['runs'],'protected_files':len(protected)}),flush=True)

if __name__ == '__main__':
    main()
