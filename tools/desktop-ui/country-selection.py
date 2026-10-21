#!/usr/bin/env python3
"""[designed: #181] Real Qt country previews preserve active ownership and saves."""
from navigation import reveal
import argparse
import copy
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--template',required=True);parser.add_argument('--data',required=True)
    args=parser.parse_args();app=QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'game.g2save'
        model=DesktopModel.open(args.template,args.data,path,country=1)
        model.save(path);saved=path.read_bytes();original=copy.deepcopy(model.state)
        window=ManagementWindow(model);window.show();app.processEvents()
        def select(country):
            window.country.setCurrentIndex(window.country.findData(country));app.processEvents()
        def click(button):
            reveal(button);QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
        def assert_display(expected):
            view=expected.view();state=expected.state
            assert window.title.text()==view['country_name'],'selected country header remains on previous country'
            assert [window.table.item(row,1).text() for row in range(20)]==[p['name'] for p in view['players']]
            for row,player in enumerate(view['players']):
                reason=', '.join(player['availability']['reasons']) or 'Available'
                if player['availability']['carried_bookings']:reason+='; carried booking'
                assert [window.table.item(row,col).text() for col in range(1,7)]==[str(value) for value in (player['name'],player['role'],player['position'],player['energy'],player['confidence'],reason)]
            assert window.selected_ids()==state.starting_eleven
            assert window.captain.currentData()==(state.captain if state.captain in state.starting_eleven else state.starting_eleven[0])
            assert [box.isChecked() for bit,box in window.tactics]==[bool(state.country_tactics & (1<<(bit-1))) for bit,box in window.tactics]
            assert str(view['morale']) in window.summary.text() and view['fixture'] in window.summary.text()
            reserves=expected.pool_view()['reserves']
            assert window.reserves.rowCount()==80
            assert expected.pool_view()['window']['reason'] in window.pool_summary.text()
            assert [window.reserves.item(row,1).text() for row in range(80)]==[p['name'] for p in reserves]
            assert 'No match played' in window.result.text()
        # [designed: #181] Preserve unconfirmed XI/captain/tactics while browsing.
        window.table.item(0,0).setCheckState(Qt.CheckState.Unchecked)
        window.tactics[0][1].toggle()
        draft=(window.selected_ids(),window.captain.currentData(),[box.isChecked() for _,box in window.tactics])
        for country in (13,4,13):
            expected=DesktopModel.open(args.template,args.data,path,country=country)
            select(country);assert_display(expected)
            assert 'New campaign' in window.status.text() and 'preview' in window.status.text().lower()
            for button in (window.confirm,window.cancel,window.save,window.play,window.standings,window.exchange):assert not button.isEnabled()
            # [designed: #181] Direct callbacks are guarded as well as disabled buttons.
            window.confirm_draft();window.start_match();window.exchange_selected();window.show_standings()
            window.action(lambda:(_ for _ in ()).throw(AssertionError('preview save operation executed')),'Unexpected save')
            click(window.save);window.refresh();assert_display(expected)
            assert model.state==original and path.read_bytes()==saved
        select(1)
        assert (window.selected_ids(),window.captain.currentData(),[box.isChecked() for _,box in window.tactics])==draft
        click(window.cancel);assert model.state==original
        select(13);click(window.new);assert model.state.managed_country==13;assert_display(model)
        select(4);click(window.friendly);assert model.state.managed_country==4 and model.state.campaign is None
        select(13);click(window.resume);assert model.state==original and window.country.currentData()==1
        assert path.read_bytes()==saved
        # [designed: #181] In-flight ownership survives forced selector signals and redraw.
        click(window.friendly);click(window.confirm);before=copy.deepcopy(model.state)
        click(window.play);assert window.jobs.busy
        select(13);assert window.country.currentData()==1 and window.title.text()==model.goaldat.country_names[1]
        window.refresh();assert model.state==before and path.read_bytes()==saved
        click(window.stop);assert not window.jobs.busy and model.state==before
        select(13);assert window.title.text()==model.goaldat.country_names[13]
        select(1);click(window.play);deadline=time.monotonic()+30
        while window.jobs.busy and time.monotonic()<deadline:
            app.processEvents();window.poll_match();QTest.qWait(10)
        assert not window.jobs.busy and model.state.last_match is not None
        completed=copy.deepcopy(model.state);result=window.result.text()
        select(13);assert 'No match played' in window.result.text() and result!=window.result.text()
        select(1);assert window.result.text()==result and model.state==completed and path.read_bytes()==saved
        window.close();app.processEvents()
    print('PASS country selection: header/all20 names/captain/tactics/morale/fixture/pool, draft return, explicit modes/resume, save bytes, busy ownership and retained results')

if __name__=='__main__':main()
