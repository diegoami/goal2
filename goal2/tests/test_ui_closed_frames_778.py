"""[designed: owner playtest, #778] Content must not erase panel outlines."""
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
