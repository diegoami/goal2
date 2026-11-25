"""[designed: owner playtest, #778] Content must not erase panel outlines."""
import math
import os
import subprocess
import sys
import unittest

from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QLabel, QWidget
from goal2.ui import theme
from goal2.ui.frame import Frame
from goal2.ui.cell_parts import CellFacts
from goal2.ui.screen import GridOption


class ClosedFrames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.previous=cls.app.font();theme.install(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.previous)

    def shown(self, widget, width, height):
        widget.resize(width,height);widget.show();self.app.processEvents()
        self.addCleanup(widget.close)
        return widget

    def image(self, widget):
        result=QImage(widget.size(),QImage.Format.Format_RGB32)
        result.fill(QColor(theme.GROUND));widget.render(result)
        return result

    def assert_closed(self, image, top, columns=None):
        columns=(0,image.width()-1) if columns is None else columns
        missing=[(x,y) for x in columns for y in range(top,image.height())
                 if image.pixelColor(x,y).name()!=theme.FRAME]
        missing += [(x,image.height()-1) for x in range(image.width())
                    if image.pixelColor(x,image.height()-1).name()!=theme.FRAME]
        self.assertFalse(missing[:8],f'outline gaps with visible content: {missing[:8]}')

    def test_opaque_body_does_not_erase_edges_at_different_sizes(self):
        frame=Frame('test')
        body=QLabel('visible content');body.setStyleSheet('background:#000000;color:white;')
        frame.add(body,1)
        for width,height in ((320,200),(477,301),(768,429)):
            with self.subTest(size=(width,height)):
                self.shown(frame,width,height)
                self.assertFalse(body.isHidden())
                self.assertEqual(body.geometry().x(),0,'no added padding')
                self.assert_closed(self.image(frame),frame.rule.height()//2)

    def test_later_added_content_and_resizing_keep_outline(self):
        frame=self.shown(Frame('test'),320,160)
        body=QLabel('added after first paint');body.setStyleSheet('background:#000000;')
        frame.add(body,1);self.app.processEvents()
        frame.resize(480,240);self.app.processEvents()
        self.assert_closed(self.image(frame),frame.rule.height()//2)

    def test_fact_values_cannot_erase_column_or_bottom_lines(self):
        facts=CellFacts({'age':8,'caps':8},rows=2)
        facts.set({'age':'25','caps':'15'},theme.VALUE)
        for value in facts.values.values():value.setStyleSheet('background:#000000;')
        self.shown(facts,256,96)
        self.assert_closed(self.image(facts),32,columns=(0,128,255))
        self.assertEqual([v.text() for v in facts.values.values()],['25','15'])

    def test_outline_does_not_intercept_content_clicks(self):
        frame=Frame('test');button=QPushButton('click')
        button.setStyleSheet('background:#000000;border:none;')
        clicked=[];button.clicked.connect(lambda:clicked.append(True))
        frame.add(button,1);self.shown(frame,320,200)
        point=button.mapToGlobal(button.rect().center())
        target=self.app.widgetAt(point)
        self.assertIs(target,button)
        QTest.mouseClick(target,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,target.mapFromGlobal(point))
        self.assertEqual(clicked,[True])

    def test_never_shown_layout_places_outline_at_actual_panel_size(self):
        panels=[Frame('hidden'),CellFacts({'age':8,'caps':8},rows=2)]
        for panel in panels:
            with self.subTest(panel=type(panel).__name__):
                self.addCleanup(panel.close)
                panel.resize(256,96)
                panel.layout().invalidate();panel.layout().activate()
                self.assertEqual(panel.outline.geometry(),panel.rect())

    def test_edges_survive_fractional_display_scaling(self):
        # Qt reads the display scale before creating QApplication.
        env = os.environ | {'QT_QPA_PLATFORM': 'offscreen', 'QT_SCALE_FACTOR': '1.5'}
        result = subprocess.run(
            [sys.executable, '-c', 'from goal2.tests.test_ui_closed_frames_778 import fractional_outline_gaps; '
             'assert not (gaps := fractional_outline_gaps()), gaps'],
            env=env, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


def fractional_outline_gaps():
    app = QApplication([])
    theme.install(app)
    host = QWidget()
    host.resize(520, 220)
    frame = Frame('roster', parent=host)
    frame.setGeometry(111, 11, 145, 141)
    body = QLabel('Visible roster')
    body.setStyleSheet('background:#000000;color:white;')
    frame.add(body, 1)
    facts = CellFacts({'age': 4, 'caps': 6})
    facts.setParent(host)
    facts.setGeometry(311, 11, 160, 141)
    facts.set({'age': '25', 'caps': '15'}, theme.VALUE)
    action = GridOption(None, 'players', lambda: None)
    action.setParent(host)
    action.setGeometry(111, 159, 145, 45)
    host.show()
    app.processEvents()
    pixmap = host.grab()
    ratio = pixmap.devicePixelRatio()
    if ratio != 1.5:
        raise AssertionError(f'Expected a 150% display, got {ratio}')
    image = pixmap.toImage()
    gaps = []
    panels = ((frame, frame.rule.height() // 2), (facts, facts.labels['age'].height() // 2), (action, 0))
    for panel, heading_middle in panels:
        x, y, width, height = panel.geometry().getRect()
        top = math.ceil((y + heading_middle) * ratio) + 2
        bottom = math.floor((y + height) * ratio) - 3
        for edge, coordinate in (('left', x), ('right', x + width - 1)):
            column = coordinate * ratio
            if not any(all(image.pixelColor(px, py).name() == theme.FRAME for py in range(top, bottom))
                       for px in range(math.floor(column) - 1, math.ceil(column) + 2)):
                gaps.append(f'{type(panel).__name__} {edge} border')
        row = (y + height - 1) * ratio
        left = math.ceil(x * ratio) + 2
        right = math.floor((x + width) * ratio) - 3
        if not any(all(image.pixelColor(px, py).name() == theme.FRAME for px in range(left, right))
                   for py in range(math.floor(row) - 1, math.ceil(row) + 2)):
            gaps.append(f'{type(panel).__name__} bottom border')
    return gaps
