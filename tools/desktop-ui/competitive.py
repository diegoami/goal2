#!/usr/bin/env python3
"""[designed: T51] Real Qt labels after original publication and actual save/reload."""
import copy
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from goal2.data.goaldat import load
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.tests.test_campaign_competitive_publication import campaign,publication
from goal2.tests.test_campaign_competitive_match import run
from goal2.tests.test_campaign_competitive_save import opening_qualifier


def main():
    app=QApplication.instance() or QApplication([])
    data=load((ROOT/'.cache/GOAL.DAT').read_bytes());rows=[]
    with tempfile.TemporaryDirectory() as folder:
        for kind,index,seed in ((2,21,257),(200,30,None),(200,42,None),(None,None,None)):
            if kind is None:
                _,state,raw,fixture,_,out=opening_qualifier();model=DesktopModel(data,raw,Path(folder)/'game.g2save')
                model.state=copy.deepcopy(state)
            else:
                state,raw,fixture=campaign(index,kind);model=DesktopModel(data,raw,Path(folder)/'game.g2save');model.state=state
                pub=publication(model);job=pub.begin(fixture);out=run(job.state,raw,fixture,reference_seed=seed)
                pub.complete(job.token,out)
            window=ManagementWindow(model);window.show();app.processEvents()
            snapshot=copy.deepcopy(model.state)
            for phase in ('published','reloaded'):
                window.refresh();app.processEvents();text=window.result.text()
                result=model.state.last_match['original'];a,b=result['first'],result['second']
                assert 'Original engine' in text,text
                assert data.country_names[a] in text and data.country_names[b] in text,text
                assert 'Regulation' in text,text
                if result['extra_time']:assert 'Extra time' in text,text
                if result['shootout'] is not None:
                    x,y=result['shootout']['score'];assert f'Penalties: {x} — {y}' in text,text
                if result['winner']!=2:
                    name=data.country_names[(a,b)[result['winner']]];assert f'Winner: {name}' in text,text
                else:assert 'Draw' in text,text
                assert 'Quick simulation' not in text,text
                assert model.state==snapshot
                rows.append({'kind':fixture.kind,'index':fixture.index,'phase':phase,'label':text})
                if phase=='published':
                    window.path.setText(str(model.save_path));window.save.click();app.processEvents()
                    window.resume.click();app.processEvents();assert model.state==snapshot
            window.close();window.deleteLater();app.processEvents()
    print(json.dumps(rows,indent=2));print('PASS Qt competitive:4 actual original results,8 publication/reload named labels, scores/winner/identity; no live controls')


if __name__=='__main__':main()
