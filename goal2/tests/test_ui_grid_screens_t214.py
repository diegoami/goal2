"""[designed: owner, #667; T214] Start/import screens keep complete fields and controls on the cell grid."""
import unittest
from pathlib import Path
from goal2.tests import requires
from goal2.tests.test_ui_grid_screens_t211b import Base
from goal2.tests.test_ui_match_day_t167 import CAREER, career, tearDownModule
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from goal2.ui.s01_import import ImportScreen,ROWS
from goal2.ui.s06_desk import ReimportScreen
from goal2.ui.s02_start import StartScreen
from goal2.ui.s03_new_game import NewGameScreen
from goal2.ui.friendly import FriendlyScreen
from goal2.ui.s04_country import PlayersScreen
from goal2.ui.cells import CellPara
from goal2.ui import saves

@CAREER
class StartOnTheGrid(Base):
    EMPTY=('default',)
    kind=ImportScreen
    saved=False

    def make(self,window):
        self.data()
        if self.saved:
            model=career()
            for i in range(6):saves.write(model,window.target.saves,(str(i)+' long save <h1> & record </h1>')[:32])
        if self.kind in (ImportScreen,ReimportScreen):screen=self.kind(window,window.target,choose=lambda:None)
        elif self.kind is PlayersScreen:screen=self.kind(window,career(),'Trinidad/Tobago')
        else:screen=self.kind(window)
        return window.push(screen)

    def test_every_start_flow_screen_fits_and_sits_on_the_grid(self):
        for kind in (ImportScreen,ReimportScreen,StartScreen,NewGameScreen,FriendlyScreen,PlayersScreen):
            self.kind=kind
            with self.subTest(screen=kind.__name__):
                self.every_state_fits()
                self.not_pending(kind.__name__,kind)

    def test_saved_games_keep_five_complete_rows_and_literal_free_names(self):
        self.kind=StartScreen
        self.saved=True
        self.every_state_fits()
        window,screen=self.canonical(self.make)
        self.assertEqual(len(screen.rows),5)
        expected=[entry.name for entry in screen.entries[:5]]
        self.assertEqual([row.cells[0].text() for row in screen.rows],expected)
        self.assertTrue(all('<h1>' in name and '&' in name for name in expected))
        for row,name in zip(screen.rows,expected):
            self.assertIsInstance(row.cells[0],CellPara)
            self.assertEqual(''.join(row.cells[0].lines()).replace(' ',''),name.replace(' ',''))
        for row in screen.rows:
            for cell in row.cells:self.assertLessEqual(len(cell.lines()),self.rows_of(cell))
        screen.move(5)
        self.assertEqual(screen.rows[-1].cells[0].text(),screen.entries[-1].name)

    def test_multiline_import_errors_and_folder_paths_stay_complete(self):
        self.kind=ImportScreen
        window,screen=self.canonical(self.make)
        screen.folder=Path('/'+'long-folder/'*20)
        screen.result={name:'missing' for name in ROWS}
        screen._show('The first line says what failed.\nChoose a folder containing all the files.')
        self.relayout(window)
        self.assertEqual(screen.error.lines(),['The first line says what failed.','Choose a folder containing all the files.'])
        self.assertEqual(''.join(screen.folder_label.lines()),str(screen.folder))
        self.assertLessEqual(len(screen.folder_label.lines()),self.rows_of(screen.folder_label))
        self.on_the_grid(window,20)

    def test_all_year_and_manager_messages_fit_and_the_year_remains_editable(self):
        self.kind=NewGameScreen
        window,screen=self.canonical(self.make)
        for year in ('','1980','2099','9999','1'):
            screen.year_field.set_text(year)
            for count in range(1,7):
                screen.choose(count)
                self.relayout(window)
                for text in screen.findChildren(CellPara):
                    if text.isVisibleTo(screen):self.assertLessEqual(len(text.lines()),self.rows_of(text),text.text())
        screen.toggle_year()
        screen.year_field.set_text('202')
        self.assertTrue(screen.type_text(Qt.Key.Key_8,'8'))
        self.assertEqual(screen.year_field.text,'2028')

if __name__=='__main__':unittest.main()
