"""[designed: owner #452/T141] Contextual Team Info navigation on genuine Core/Qt.

Native mode is a separate process, e.g. --native --factor 2 --out .cache/T141-native-v1.
It requires an actual windows/xcb/wayland platform and records rebuilt-window captures privately.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from goal2.tests import requires

NATIVE=False
CAPTURES=None
FACTOR=None
OBSERVED=set()
NEEDS=dict(modules=('unicorn','PySide6'),files=('e006-r0001-main.sav','GOAL.DAT'))

@requires.need(**NEEDS)
class Navigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NATIVE:os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
        if NATIVE and cls.app.platformName() not in ('windows','xcb','wayland','wayland-egl'):
            raise AssertionError('Native proof requires a real windows/xcb/wayland Qt platform')

    def setUp(self):
        from goal2.tests.test_core_team_t107 import model
        from goal2.desktop.core_window import CoreWindow
        from PySide6.QtTest import QTest
        self.w=CoreWindow(model())
        if NATIVE:self.w.resize(900,640);self.w.move(0,0)
        self.w.show();self.w.raise_();self.w.activateWindow()
        self.app.processEvents()
        if NATIVE:
            self.assertTrue(QTest.qWaitForWindowActive(self.w,5000))
            self.assertAlmostEqual(self.w.devicePixelRatioF(),FACTOR)
            OBSERVED.add(self.w.devicePixelRatioF())
        self.before=self.w.model.memory_sha256()
        self.save_before=hashlib.sha256(self.w.model.core.save()).hexdigest()
        self.actions=patch.object(self.w.model,'act',side_effect=AssertionError('Presentation navigation must not drive the core'))
        self.actions.start()
        self.addCleanup(self.close)

    def close(self):
        self.actions.stop()
        self.w.close();self.app.processEvents()

    def unchanged(self):
        self.assertEqual(self.w.model.memory_sha256(),self.before)
        self.assertEqual(hashlib.sha256(self.w.model.core.save()).hexdigest(),self.save_before)
        self.assertFalse(self.w.core_jobs.busy)

    def click(self,button):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        self.assertTrue(button.isVisible() and button.isEnabled())
        self.assertTrue(button.visibleRegion().contains(button.rect().center()))
        if NATIVE:
            self.assertTrue(self.w.screen().geometry().contains(button.mapToGlobal(button.rect().center())))
        QTest.mouseClick(button,Qt.MouseButton.LeftButton,pos=button.rect().center())
        self.app.processEvents()

    def escape(self,widget):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        QTest.keyClick(widget,Qt.Key.Key_Escape);self.app.processEvents()

    def info_from_country(self):
        self.w.navigate(0);self.w.country_views.show_view(0)
        self.w.country_roster.set_current(5);self.w.team_roster.set_current(7)
        self.app.processEvents()
        self.click(self.w.core_routes['team info'])
        self.assertEqual((self.w.page_stack.currentIndex(),self.w.team_views.currentIndex()),(1,1))

    def back_button(self):
        from PySide6.QtWidgets import QPushButton
        button=self.w.findChild(QPushButton,'coreTeamInfoBack')
        self.assertIsNotNone(button,'Team Info needs a visible Back to team control')
        self.assertEqual(button.accessibleName(),'Back to team')
        return button

    def capture(self,name):
        if CAPTURES is not None:
            self.assertTrue(self.w.grab().save(str(CAPTURES/name)))

    def test_mouse_back_restores_country_and_repeated_entry(self):
        for entry in range(3):
            self.info_from_country()
            self.capture(f'country-team-info-{entry}.png')
            self.click(self.back_button())
            self.assertEqual((self.w.page_stack.currentIndex(),self.w.country_views.currentIndex()),(0,0))
            self.assertEqual((self.w.country_roster.current,self.w.team_roster.current),(5,7))
            if NATIVE:self.assertIs(self.app.focusWidget(),self.w.core_routes['team info'])
            self.unchanged()

    def test_escape_restores_country_then_local_team_origin(self):
        self.info_from_country();self.escape(self.w.tactics[0][1])
        self.assertEqual(self.w.page_stack.currentIndex(),0)
        self.assertEqual(self.w.country_roster.current,5)
        self.w.navigate(1);self.w.team_views.show_view(0);self.w.team_roster.set_current(9)
        self.app.processEvents();self.click(self.w.core_team_buttons['teamTacticsRoute'])
        self.assertEqual(self.w.team_views.currentIndex(),1)
        self.escape(self.w.tactics[0][1])
        self.assertEqual((self.w.page_stack.currentIndex(),self.w.team_views.currentIndex()),(1,0))
        self.assertEqual(self.w.team_roster.current,9)
        if NATIVE:self.assertIs(self.app.focusWidget(),self.w.core_team_buttons['teamTacticsRoute'])
        self.unchanged()

    def test_modal_escape_closes_only_the_dialog(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog
        from PySide6.QtTest import QTest
        self.info_from_country()
        dialog=QDialog(self.w);dialog.setWindowModality(Qt.WindowModality.WindowModal);dialog.open()
        self.app.processEvents()
        if NATIVE:self.assertTrue(QTest.qWaitForWindowActive(dialog,5000))
        self.escape(dialog)
        self.assertFalse(dialog.isVisible())
        self.assertEqual((self.w.page_stack.currentIndex(),self.w.team_views.currentIndex()),(1,1))
        self.escape(self.w.tactics[0][1])
        self.assertEqual(self.w.page_stack.currentIndex(),0)
        self.unchanged()

    def test_back_control_keeps_existing_page_bounds_and_reserve(self):
        from goal2.desktop.fixed_page import problems
        from goal2.tests.test_core_team_t107 import SIZES
        self.info_from_country();button=self.back_button()
        for width,height in SIZES:
            self.w.resize(width,height);self.app.processEvents()
            self.assertEqual(problems(self.w),[],(width,height))
            page=self.w.pages[1];need=page.minimumSizeHint()
            self.assertLessEqual(need.width(),0.9*page.width())
            self.assertLessEqual(need.height(),0.9*page.height())
            self.assertTrue(button.visibleRegion().contains(button.rect().center()))
            self.capture(f'team-info-{width}x{height}.png')
        if NATIVE:self.w.resize(900,640);self.w.move(0,0);self.app.processEvents()
        self.click(button);self.assertEqual(self.w.page_stack.currentIndex(),0)
        self.unchanged()


def native():
    import argparse
    import subprocess
    global NATIVE,CAPTURES,FACTOR
    parser=argparse.ArgumentParser()
    parser.add_argument('--native',action='store_true',required=True)
    parser.add_argument('--factor',type=int,choices=(1,2),default=1)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    folder=Path(args.out)
    folder.mkdir(parents=True,exist_ok=False)
    NATIVE=True;CAPTURES=folder;FACTOR=args.factor
    os.environ['QT_SCALE_FACTOR']=str(args.factor)
    with (folder/'tests.log').open('x') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Navigation))
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance()
    root=Path(__file__).resolve().parents[2]
    files=('goal2/desktop/squad_page.py','goal2/desktop/overview_page.py','goal2/desktop/pages.py',str(Path(__file__).relative_to(root)))
    receipt=dict(platform=sys.platform,qt_platform=app.platformName() if app else None,factor=args.factor,
                 observed_dpr=sorted(OBSERVED),tests=result.testsRun,skips=len(result.skipped),pass_=result.wasSuccessful() and not result.skipped,
                 head=subprocess.check_output(['git','-c',f'safe.directory={root.as_posix()}','rev-parse','HEAD'],cwd=root,text=True).strip(),
                 source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files},
                 captures={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.png')})
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    raise SystemExit(0 if receipt['pass_'] else 1)

if __name__=='__main__':
    native() if '--native' in sys.argv else unittest.main()
