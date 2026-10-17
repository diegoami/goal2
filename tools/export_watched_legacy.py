#!/usr/bin/env python3
"""[designed: T51a] Reproduce pre-upgrade kit1 saves from an immutable reviewed T64 export.
Original resources and generated saves remain ignored. No retained worktree is touched.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
LEGACY_SOURCE = "3656a2d26e0f57a410d648edeaa6cd9eb7d1f607"
CHILD = r'''
import json,sys
from pathlib import Path
from goal2.engine.original_match import Fixture,VERSION
from goal2.game.state import from_savestate
from goal2.game.watched_match import run_watched_match
from goal2.game.watched_publication import WatchedPublication,ENGINE_ID
from goal2.game import session_save
from goal2.data.goaldat import load
from goal2.game.campaign_schedule import start_opening_campaign
root=Path.cwd();out=Path(sys.argv[1])
assert VERSION=="1" and ENGINE_ID.endswith(":1"), (VERSION,ENGINE_ID)
class Owner:
 def __init__(self,state,template):self.state=state;self.template_bytes=template
 def view(self,state):return state.last_match
for name in ("standalone","campaign"):
 if name=="standalone":
  template=(root/".cache/e0afff6751747233-e006-1000-r0001.sav").read_bytes()
  state=from_savestate(template);state.captain=0;fixture=Fixture(7,19,21)
 else:
  template=(root/".cache/e010-r0008-halftime.sav").read_bytes()
  data=load((root/".cache/GOAL.DAT").read_bytes())
  state,_=start_opening_campaign(data,template,managed_country=4,start_year=1990,
                               seed_7b62=4660,seed_8336=33590)
  f=state.campaign.next_fixture;fixture=Fixture(f.side_a,f.side_b,int(f.fixture_id.split(":")[1]))
 owner=Owner(state,template);pub=WatchedPublication(owner);job=pub.begin(fixture)
 outcome=run_watched_match(job.state,template,fixture);pub.complete(job.token,outcome)
 raw=session_save.encode(owner.state,template)
 restored,restored_template=session_save.decode(raw)
 assert restored==owner.state and restored_template==template
 assert json.loads(raw)["version"]==3
 target=out/(name+".g2save")
 if target.exists():assert target.read_bytes()==raw, "refusing to replace retained legacy evidence"
 else:target.write_bytes(raw)
 print(name+" kit1 saved and roundtripped",flush=True)
'''


def digest(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",required=True,help="full reviewed T64 application commit")
    args=parser.parse_args()
    if re.fullmatch("[0-9a-f]{40}",args.source) is None:parser.error("full source SHA required")
    folder=ROOT/".cache"/("watched-legacy-v3-"+args.source[:12])
    export=folder/"source"
    archive=subprocess.check_output(["git","archive",args.source],cwd=ROOT)
    manifest=subprocess.check_output(["git","show",args.source+":tools/watched-kit-hashes.json"],cwd=ROOT)
    if json.loads(manifest)["source"]!=LEGACY_SOURCE:raise ValueError("source is not the accepted kit1 application")
    export.mkdir(parents=True,exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(export,filter="data")
    inputs={}
    for name in ("e0afff6751747233-e006-1000-r0001.sav","e010-r0008-halftime.sav","GOAL.DAT"):
        raw=(ROOT/".cache"/name).read_bytes();inputs[name]=digest(raw)
        target=export/".cache"/name;target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
    subprocess.run([sys.executable,"-B","-c",CHILD,str(folder)],cwd=export,check=True)
    report={"application_source":args.source,"engine_source":LEGACY_SOURCE,
            "archive_sha256":digest(archive),"inputs":inputs,
            "saves":{name:digest((folder/(name+".g2save")).read_bytes()) for name in ("standalone","campaign")}}
    (folder/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(folder)


if __name__=="__main__":main()
