"""[designed: owner, #667; T214] Start/import screens keep complete fields and controls on the cell grid."""
import unittest
from pathlib import Path
from goal2.tests import requires
from goal2.tests.test_ui_grid_screens_t211b import Base
from goal2.tests.test_ui_match_day_t167 import CAREER, career, tearDownModule
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from goal2.ui.s01_import import ImportScreen,ROWS
from goal2.ui.s06_desk import ReimportScreen
from goal2.ui.s02_start import StartScreen
from goal2.ui.s03_new_game import NewGameScreen
from goal2.ui.friendly import FriendlyScreen
from goal2.ui.s04_country import PlayersScreen
from goal2.ui.cells import CellLabel, CellPara, Cells
from goal2.ui.corner_block import CornerBlock
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

    def test_start_carries_the_original_corner_and_keeps_the_load_question_at_the_foot(self):
        """[designed: owner, 2026-11-28, #673; T244] The original's corner block, not a wordmark, at the top left."""
        self.kind = StartScreen
        for self.saved in (False, True):
            with self.subTest(saved=self.saved):
                window, screen = self.canonical(self.make)
                corner = screen.findChild(CornerBlock)
                self.assertIsNotNone(corner)
                self.assertIs(screen.corner, corner)
                self.assertEqual((corner.x(), corner.y()), (0, 0), "the corner block is at the top left")
                self.assertTrue(corner.isVisibleTo(screen))
                self.assertFalse(corner.findChildren(QLabel), "the block paints, it is not a label")
                self.assertEqual([label.text() for label in screen.findChild(Cells, "startCopyright").findChildren(CellLabel)],
                                 ["(c)", "new era", "software", "1993"])
                self.assertEqual(screen.banner.shown_texts() if hasattr(screen.banner, "shown_texts") else
                                 [label.text() for label in screen.banner.findChildren(CellLabel)],
                                 ["THE international soccer management game"])
                self.assertEqual(screen.menu_box.label, "load a saved game?")
                self.assertGreater(screen.menu_box.y(), screen.body.height() * .8)
                if self.saved:
                    self.assertLess(screen.list_box.geometry().bottom(), screen.menu_box.y())
                    self.assertTrue(screen.load_item.isVisibleTo(screen))
                else:
                    self.assertFalse(screen.load_item.isVisibleTo(screen))
                    self.assertTrue(screen.empty_load.isVisibleTo(screen))
                    self.assertTrue(screen.new_item.property("on"))
                self.on_the_grid(window, 20)

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

    def test_windows_import_refusal_keeps_all_three_errors_and_the_folder(self):
        """[designed: T215] The actual Windows journey's two missing files and wrong optional help need seven rows."""
        from goal2.desktop import data_setup
        self.kind=ImportScreen
        folder=r"C:\Users\runneradmin\AppData\Local\Temp\goal2-ui-shots-12345678\offered"
        problems=[(data_setup.DATA_NAME,'missing'),(data_setup.TEMPLATE_NAME,'missing'),(data_setup.HELP_NAME,'wrong')]
        message=data_setup.describe(problems,folder)+"\nChoose the folder that holds all the files."
        def make(window):
            screen=self.make(window);screen.folder=folder
            screen.result={name:dict(problems)[name] for name in ROWS};screen._show(message)
            return screen
        def complete(window,screen):
            self.assertEqual(screen.error.text(),message)
            self.assertGreaterEqual(len(screen.error.lines()),7)
            self.assertLessEqual(len(screen.error.lines()),self.rows_of(screen.error))
            self.assertEqual(screen.folder_label.text(),folder)
        self.fitting(make,complete)
        window,screen=self.canonical(make);complete(window,screen);self.on_the_grid(window,20)

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
