#!/usr/bin/env python3
"""[designed: T69] Real Qt interactions over verified local game resources."""
import argparse
import copy
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow


def management(template,data,screenshot=None):
    app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        save=Path(folder)/'desktop.g2save'
        model=DesktopModel.open(template,data,save,country=4)
        window=ManagementWindow(model);window.show();QTest.qWait(80)
        def click(widget):
            QTest.mouseClick(widget,Qt.MouseButton.LeftButton);app.processEvents()
        def country(number):
            window.country.setFocus();QTest.keyClick(window.country,Qt.Key.Key_Home)
            for _ in range(number-1):QTest.keyClick(window.country,Qt.Key.Key_Down)
        def toggle(row):
            window.table.setCurrentCell(row,0);window.table.setFocus();QTest.keyClick(window.table,Qt.Key.Key_Space);app.processEvents()
        original=copy.deepcopy(model.state)
        country(13)
        assert model.state==original,'country draft mutated active game'
        assert window.country.currentData()==13
        click(window.new)
        assert model.state.managed_country==13
        assert window.title.text()==model.goaldat.country_names[13]
        assert [window.table.item(i,1).text() for i in range(20)]==[model.goaldat.player_names[w] for w in model.state.managed_squad]
        for row in list(range(9))+list(range(11,20)):toggle(row)
        window.captain.setFocus();QTest.keyClick(window.captain,Qt.Key.Key_End)
        for _,box in window.tactics:
            if not box.isChecked():click(box)
        click(window.confirm)
        assert model.state.starting_eleven==list(range(250,261))
        assert model.state.captain==260 and model.state.country_tactics==255
        assert window.status.text()=='Management confirmed'
        confirmed=copy.deepcopy(model.state)
        toggle(19);click(window.confirm)
        assert model.state==confirmed and 'eleven' in window.status.text()
        click(window.cancel)
        assert window.selected_ids()==confirmed.starting_eleven
        injured=260;rec=bytearray(model.state.players[injured]);rec[14]=0;rec[16]=0x88;model.state.players[injured]=bytes(rec)
        window.refresh();before=copy.deepcopy(model.state);click(window.confirm)
        assert model.state==before and 'unavailable' in window.status.text()
        assert 'Injured' in window.table.item(19,6).text() and 'Suspended' in window.table.item(19,6).text() and 'carried booking' in window.table.item(19,6).text()
        toggle(19);toggle(0);click(window.confirm)
        assert injured not in model.state.starting_eleven and 241 in model.state.starting_eleven
        assert model.state.captain in model.state.starting_eleven
        click(window.save);assert save.is_file()
        saved=save.read_bytes();snapshot=copy.deepcopy(model.state)
        country(4);assert model.state==snapshot
        click(window.new);assert model.state.managed_country==4
        with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('resume regenerated players')):
            click(window.resume)
        assert model.state==snapshot,'complete saved state was not resumed'
        seeds=(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        window.refresh();window.refresh();assert model.state==snapshot
        assert seeds==(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        bad=Path(folder)/'bad.g2save';bad.write_bytes(b'broken')
        window.path.setText(str(bad));click(window.resume)
        assert model.state==snapshot and 'Cannot resume' in window.status.text()
        blocked=Path(folder)/'not-a-directory';blocked.write_text('blocked')
        window.path.setText(str(blocked/'save.g2save'));click(window.save)
        assert model.state==snapshot and 'Cannot save' in window.status.text() and save.read_bytes()==saved
        window.path.setText(str(save));click(window.resume)
        assert model.state==snapshot
        assert str(model.view()['morale']) in window.summary.text()
        if screenshot:window.grab().save(str(screenshot))
        window.close();app.processEvents()
    print('PASS management: real Qt country/draft/XI/captain260/all tactics, injury/ban repair, complete save/resume, failure rollback and pure redraw')


def main():
    p=argparse.ArgumentParser();p.add_argument('--scenario',choices=['management'],required=True)
    p.add_argument('--template',required=True,type=Path);p.add_argument('--data',required=True,type=Path);p.add_argument('--screenshot',type=Path)
    args=p.parse_args();management(args.template,args.data,args.screenshot)
if __name__=='__main__':main()
