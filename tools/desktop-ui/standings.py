#!/usr/bin/env python3
"""[designed: T49] Actual desktop table wiring with a decisive goals-scored tie."""
import argparse,copy,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
from goal2.game.campaign_schedule import start_opening_campaign
from goal2.game.standings import opening_group


def main():
    p=argparse.ArgumentParser();p.add_argument('--template',required=True);p.add_argument('--data',required=True)
    args=p.parse_args();app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        model=DesktopModel.open(args.template,args.data,Path(folder)/'unused.g2save',country=4)
        model.state,_=start_opening_campaign(model.goaldat,model.template_bytes,managed_country=4,
                                             start_year=1992,seed_7b62=4660,seed_8336=33590)
        slots=opening_group(model.state,model.template_bytes)['slots']
        # [designed] Controlled completed-result input; no fixture execution or save publication.
        for a,b,gf,ga in ((slots[0],slots[1],2,1),(slots[2],slots[3],1,0)):
            f=next(f for f in model.state.campaign.world.fixtures if f.kind==2 and {f.side_a,f.side_b}=={a,b})
            model.state.campaign.world.results.append({'fixture_id':f.fixture_id,'teams':[f.side_a,f.side_b],
                'score':[gf,ga] if f.side_a==a else [ga,gf]})
        before=copy.deepcopy(model.state)
        backend=model.competition_table()
        assert [r['country'] for r in backend['rows'][:2]]==[slots[0],slots[2]],'decisive GF tiebreak'
        assert [(r['points'],r['goal_difference']) for r in backend['rows'][:2]]==[(2,1),(2,1)]
        assert [r['country'] for r in backend['rows'] if r['advances']]==[slots[0]],'wrong qualifier'
        window=ManagementWindow(model);window.show();app.processEvents()
        QTest.mouseClick(window.standings,Qt.MouseButton.LeftButton);app.processEvents()
        dialog=window.standings_dialog
        assert dialog is not None and dialog.isVisible(),'button did not open the table'
        table=dialog.table
        assert [table.item(i,1).data(Qt.ItemDataRole.UserRole) for i in range(4)]==[r['country'] for r in backend['rows']]
        for i,row in enumerate(backend['rows']):
            assert table.item(i,1).text()==row['name']
            assert [table.item(i,j).text() for j in range(2,10)]==[str(row[k]) for k in
                ('played','won','drawn','lost','goals_for','goals_against','goal_difference','points')]
            assert bool(table.item(i,10).text())==row['advances']
            assert not table.item(i,1).flags() & Qt.ItemFlag.ItemIsEditable
        assert model.state==before,'table read changed state/RNG'
        window.refresh();assert not dialog.isVisible(),'stale table survived an active-game refresh'
        model.state.campaign=None
        QTest.mouseClick(window.standings,Qt.MouseButton.LeftButton);app.processEvents()
        assert 'unavailable' in window.status.text().lower()
        window.close();app.processEvents()
    print('PASS desktop standings: forced points/GD tie decided by GF; backend/widget qualifiers match; reads preserve state/RNG')


if __name__=='__main__':main()
