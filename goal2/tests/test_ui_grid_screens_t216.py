"""[designed: owner, #667; T216] Small screens retain content/actions and fit the shared grid, including failure states."""
import unittest
from pathlib import Path
from goal2.tests import requires
from goal2.tests.test_ui_grid_screens_t211b import Base
from goal2.tests.test_ui_grid_screens_t211 import SIZES
from goal2.tests.test_ui_match_day_t167 import CAREER,career,tearDownModule
requires.require(modules=('PySide6',))
from PySide6.QtCore import Qt
from goal2.desktop import fixed_page
from goal2.ui import grid_check,replays
from goal2.ui.home import HomeScreen
from goal2.ui.s05_bulletin import BulletinScreen
from goal2.ui.s21_save import SaveScreen,QuestionScreen
from goal2.ui.s22_help import HelpScreen
from goal2.ui.cells import CellPara

@CAREER
class SmallOnTheGrid(Base):
    kind='HomeScreen'
    failed=False
    help_present=False
    records=False

    def on_the_grid(self,window,at_least=10):
        self.assertGreater(len(grid_check.widgets(window)),10)
        self.assertEqual(grid_check.violations(window),[])

    def make(self,window):
        self.data();model=career();model.mark_saved();window.open_career(model);under=window.current()
        if self.kind=='HomeScreen':screen=HomeScreen(window)
        elif self.kind=='BulletinScreen':
            page={name:dict(masthead=name.upper()+' PAPER',lines=[name+' news line '+str(i) for i in range(9 if name!='middle' else 13)]) for name in ('left','middle','right')}
            screen=BulletinScreen(window,[page,page],lambda:None)
        elif self.kind=='QuestionScreen':screen=QuestionScreen(window,under,'quit','Quit','Are you sure you want to quit?',lambda:None,lambda:None,cancel=lambda:None)
        elif self.kind=='SaveScreen':
            screen=SaveScreen(window,under,model);screen.field.set_text('A full save <name> & literal')
            if self.failed:screen.say('The game was not saved: '+r'C:\Users\runneradmin\AppData\Local\Temp'+(r'\subfolder'*25)+r'\a-name.g2game: Access denied. Nothing was replaced.')
        elif self.kind=='HelpScreen':
            if self.help_present:window.target.help.write_bytes(b'OWNED HELP TEST\r\n'+b'A complete line of help text.\r\n'*100+b'\x1aignored')
            screen=HelpScreen(window,under,window.target)
        elif self.kind=='RecordingNameScreen':return replays.name_recording(window,under,'goal',{},lambda:None)
        else:
            if self.records:
                from goal2.tests.test_ui_replay_t181 import frames
                data=dict(frames=frames(),countries=['One','Two'],score=[0,1],minute=3,scorer='A Player',kits=dict(shirt=[1,2],keeper=[3,4]),kind='FRIENDLY')
                for i in range(10):replays.write(window.target.root/'recordings','goal',str(i)+' recording <h1> & name',data)
            return replays.open_list(window,model,'goal')
        return window.push(screen)

    def test_the_save_box_and_the_help_leave_their_right_rule_visible(self):
        """[designed: T243] The name field, the box's buttons and the help's Close button stop one cell short of
        the panel's right rule, so the rule is not swallowed by their background at any size."""
        for kind in ("SaveScreen", "HelpScreen"):
            self.kind = kind
            with self.subTest(screen=kind):
                window, screen = self.canonical(self.make)
                self.relayout(window)
                self.rule_stays_clear(screen, kind)
                shown = self.window()
                shown_screen = self.make(shown)
                for width, height in SIZES:
                    shown.resize(width, height)
                    shown.show()
                    for _ in range(3):
                        self.app.processEvents()
                    self.rule_stays_clear(shown_screen, kind, f"at {width}x{height}")

    def rule_stays_clear(self, screen, kind, where=""):
        from goal2.ui.cells import cell_w
        cell = round(cell_w(screen))
        if kind == "SaveScreen":
            row, widgets = screen.dialog, [screen.field, *screen.save_buttons]
        else:
            row, widgets = screen.close_button.parentWidget(), [screen.close_button]
        for widget in widgets:
            self.assertLessEqual(widget.x() + widget.width(), row.width() - cell + 1,
                                 f"{where} {type(widget).__name__} reaches the panel's rule")

    def test_the_help_names_the_screen_it_was_opened_on(self):
        self.kind = "HelpScreen"
        window, screen = self.canonical(self.make)
        self.assertEqual(screen.title, "manager's desk · help")
        self.assertEqual(screen.name_label.text(), "manager's desk · help")

    def test_every_small_screen_fits_all_sizes_and_is_on_the_grid(self):
        for kind in ('HomeScreen','BulletinScreen','QuestionScreen','SaveScreen','HelpScreen','RecordingNameScreen','RecordingsScreen'):
            self.kind=kind
            with self.subTest(screen=kind):
                self.every_state_fits()
                window,screen=self.canonical(self.make)
                self.not_pending(kind,type(screen))

    def test_long_failed_save_paths_fit_without_a_platform_exception(self):
        self.kind='SaveScreen';self.failed=True
        self.every_state_fits()
        window,screen=self.canonical(self.make)
        self.assertLessEqual(len(screen.problem.lines()),self.rows_of(screen.problem))
        self.assertIn('Access denied',screen.problem.text())

    def test_help_still_scrolls_and_fills_small_windows(self):
        self.kind='HelpScreen';self.help_present=True
        window,screen=self.canonical(self.make)
        window.resize(720,450);window.show()
        for _ in range(3):self.app.processEvents()
        self.assertEqual(fixed_page.problems(window),[])
        self.assertGreaterEqual(screen.viewer.height(),.7*window.page.height())
        self.assertIn('OWNED HELP TEST',screen.shown_text());self.assertNotIn('ignored',screen.shown_text())
        before=screen.viewer.verticalScrollBar().value();screen.scroll(1,page=True)
        self.assertGreater(screen.viewer.verticalScrollBar().value(),before)

    def test_recording_names_remain_literal_and_the_list_keeps_eight_rows(self):
        self.kind='RecordingsScreen';self.records=True
        window,screen=self.canonical(self.make)
        self.assertEqual(len(screen.rows),8)
        for row in screen.rows:
            self.assertIn('<h1>',row.text_label.text())
            self.assertEqual(row.text_label.textFormat(),Qt.TextFormat.PlainText)
        for _ in range(9):screen.move(1)
        self.relayout(window);self.assertEqual(fixed_page.problems(window),[])
        self.assertEqual(screen.position,9)

    def test_dialog_content_obscures_the_screen_behind_it(self):
        from PySide6.QtWidgets import QWidget
        from goal2.ui.screen import Screen
        from goal2.ui import theme
        window=self.window();model=career();model.mark_saved();window.open_career(model)
        under=Screen(window);surface=QWidget();surface.setStyleSheet('background: #ff0000;');under.body_layout.addWidget(surface,1)
        window.push(under);window.resize(1440,1080);window.show()
        for _ in range(3):self.app.processEvents()
        screen=window.push(SaveScreen(window,under,model))
        for _ in range(4):self.app.processEvents()
        point=screen.dialog.mapTo(window,screen.dialog.rect().topRight())
        image=window.grab().toImage()
        # This point is inside the modal's blank body, away from its frame label and controls.
        ratio=image.devicePixelRatio()
        self.assertEqual(image.pixelColor(round((point.x()-8)*ratio),round((point.y()+80)*ratio)).name(),theme.GROUND)


    def test_bulletin_papers_keep_their_colours_and_every_source_line(self):
        self.kind='BulletinScreen'
        window,screen=self.canonical(self.make)
        image=window.grab().toImage();ratio=image.devicePixelRatio()
        from PySide6.QtCore import QPoint
        from goal2.ui.cells import cell_w,row_px
        for name,colour in (('left','#aaaaaa'),('middle','#0000aa'),('right','#00aa00')):
            paper=screen.papers[name]
            point=paper.mapTo(window,QPoint(round(3*cell_w(paper)),row_px(paper)//2))
            self.assertEqual(image.pixelColor(round(point.x()*ratio),round(point.y()*ratio)).name(),colour)
            self.assertEqual(screen.panels[name][2].text(),screen.pages[0][name]['masthead'])
            self.assertEqual(screen.panels[name][3].text(),'\n'.join(screen.pages[0][name]['lines']))


    def test_prompt_is_anchored_at_the_foot_without_clipping_long_errors(self):
        from goal2.ui.cells import row_px
        self.kind='SaveScreen';self.failed=True
        window,screen=self.canonical(self.make)
        self.assertEqual(screen.dialog.geometry().bottom()+1,row_px(screen,25))
        self.assertEqual(fixed_page.problems(window),[])
        self.assertLessEqual(len(screen.problem.lines()),self.rows_of(screen.problem))


if __name__=='__main__':unittest.main()
