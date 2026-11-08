"""[confirmed: original t156-014-squad; owner2026-11-08] Full roster names carry positional colour."""
import unittest
from goal2.tests import requires
requires.require(modules=('PySide6',))
from PySide6.QtWidgets import QApplication
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtGui import QColor
from goal2.ui import theme
from goal2.ui.squad_card import Strip, LINE_COLOUR

class RosterColour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        theme.install(cls.app)

    def test_rendered_names_have_all_four_original_colours(self):
        strip=Strip();strip.setStyleSheet(theme.stylesheet());strip.resize(390,800)
        lines=('goalkeeper','defence','midfield','attack')
        strip.show_rows('TEST',[(str(i),line,'NAME '+line.upper()) for i,line in enumerate(lines)])
        strip.show();self.app.processEvents()
        try:
            for row,line in zip(strip.rows,lines):
                image=row.cells[1].grab().toImage();wanted=QColor(LINE_COLOUR[line]).rgba()
                pixels=sum(image.pixel(x,y)==wanted for x in range(image.width()) for y in range(image.height()))
                with self.subTest(line=line):self.assertGreater(pixels,10,'full name, not just role letter, must carry original colour')
        finally:strip.close();strip.deleteLater();self.app.processEvents()

    def test_selection_injury_and_unknown_role_stay_readable(self):
        strip=Strip();strip.setStyleSheet(theme.stylesheet());strip.resize(390,800)
        strip.show_rows('TEST',[('G','goalkeeper','SELECTED'),('D','midfield','INJURED'),('?','unknown','UNKNOWN')],current=0,injured={1})
        strip.show();self.app.processEvents()
        try:
            for row,tone in zip(strip.rows,(theme.ON_HIGHLIGHT,theme.BAD,theme.TEXT_NORMAL)):
                image=row.cells[1].grab().toImage();wanted=QColor(tone).rgba()
                pixels=sum(image.pixel(x,y)==wanted for x in range(image.width()) for y in range(image.height()))
                self.assertGreater(pixels,10)
            self.assertTrue(strip.rows[0].on)
            self.assertTrue(strip.rows[1].property('injured'))
            strip.show_rows('TEST',[('G','goalkeeper','RESTORED')])
            self.assertFalse(strip.rows[0].on)
            self.assertNotIn('INJURED',strip.shown_texts()[0])
        finally:strip.close();strip.deleteLater();self.app.processEvents()

    def test_match_menu_eleven_colours_the_full_names(self):
        from goal2.ui.s15_match_menu import MenuScreen
        from goal2.ui.squad_card import Row
        lines=('goalkeeper','defence','midfield','attack')
        names=['']*129;names[7]='TEST'
        state=SimpleNamespace(managed_country=4)
        model=SimpleNamespace(state=state,goaldat=SimpleNamespace(country_names=names))
        menu=SimpleNamespace(model=model,day=SimpleNamespace(bench=None),phase='before',lineups={})
        cards={i:{'role':str(i),'line':lines[(i-1)%4],'full_name':'NAME '+lines[(i-1)%4].upper()} for i in range(1,12)}
        with patch('goal2.game.country_card.card',return_value={'players':list(cards),'formation':'4-4-2'}),patch('goal2.game.player_card.card',side_effect=lambda state,word,data:cards[word]):
            frame=MenuScreen._lineup(menu,7)
            texts=menu.lineups[7][1]
        frame.setStyleSheet(theme.stylesheet());frame.resize(300,650);frame.show();self.app.processEvents()
        try:
            rows=frame.findChildren(Row)
            self.assertEqual(len(rows),11)
            self.assertEqual(len(texts),11)
            for row,card in zip(rows,cards.values()):
                image=row.cells[1].grab().toImage();wanted=QColor(LINE_COLOUR[card['line']]).rgba()
                pixels=sum(image.pixel(x,y)==wanted for x in range(image.width()) for y in range(image.height()))
                with self.subTest(line=card['line']):self.assertGreater(pixels,10)
        finally:frame.close();frame.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
