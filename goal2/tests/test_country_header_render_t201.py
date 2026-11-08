"""T201: delivered original Now/Top and glyph attributes in both supported card views."""
import copy
import unittest
from goal2.tests import requires
from goal2.tests.test_ui_start_t163 import App

@requires.need(modules=('PySide6',),**requires.HALFTIME)
class HeaderViews(App):
    def test_current_top_and_strip_pixels_fit_all_countries_and_three_sizes_without_state_write(self):
        from PySide6.QtGui import QColor
        from goal2.desktop import fixed_page
        from goal2.ui.kits import DOS
        self.data();window=self.window();screen=self.to_country_screen(window);screen.settle();window.grab()
        state=screen.browser.state;before=copy.deepcopy(state);view=screen.card_view
        for country in range(1,129):
            from goal2.game.country_card import card
            data=card(state,country,screen.browser.goaldat);view.set_card(data,screen.average,screen.first_match)
            self.app.processEvents()
            self.assertEqual(view.ranks['world'].text(),str(data['world']))
            self.assertEqual(view.ranks['top_world'].text(),str(data['top_world']))
            self.assertEqual(view.ranks['continental'].text(),str(data['continental']))
            self.assertEqual(view.ranks['top_continental'].text(),str(data['top_continental']))
            self.assertEqual(view.shape['strips'].attributes,data['strips'])
        data=copy.deepcopy(screen.card);data.update(top_world=3,top_continental=2,strips=(12,15,9))
        # Explicit display packet: distinguish Now/Top without a played ranking-history claim.
        view.set_card(data,screen.average,screen.first_match);self.app.processEvents()
        self.assertEqual(view.ranks['top_world'].text(),'3');self.assertEqual(view.ranks['top_continental'].text(),'2')
        for width,height in ((1440,900),(1800,1125),(2110,1213)):
            window.resize(width,height);self.app.processEvents();window.grab()
            self.assertEqual(fixed_page.problems(window),[],(width,height))
            image=view.shape['strips'].grab().toImage()
            colors={image.pixelColor(x,y).name() for y in range(image.height()) for x in range(image.width())}
            for index in data['strips']:self.assertIn(DOS[index],colors)
        data['strips']=None;view.set_card(data,screen.average,screen.first_match);self.app.processEvents()
        self.assertIsNone(view.shape['strips'].attributes)
        self.assertEqual(view.shape['strips'].display_attributes,(7,7,7),'original neutral template, not missing data')
        self.assertEqual(state,before)

    def test_legacy_game_consumes_fields_and_unsupported_core_card_retains_explicit_fallback(self):
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.model import DesktopModel
        from goal2.desktop.country_card import CountryCardView
        from goal2.game.country_card import card,NOT_DECODED
        from goal2.core import views
        from goal2.engine.original_match.image import Image
        model=DesktopModel.open(requires.CACHE/'e010-r0008-halftime.sav',requires.CACHE/'GOAL.DAT',self.tmp/'never-written',country=7)
        data=card(model.state,7,model.goaldat);before=copy.deepcopy(model.state)
        for width in (820,320):
            view=CountryCardView();view.resize(width,1400);view.set_card(data,'');drawn=[]
            view.text=lambda painter,x,y,text,*a,drawn=drawn,**k:drawn.append(str(text))
            view.grab();self.app.processEvents()
            self.assertEqual(view.painted_top,(data['top_world'],data['top_continental']))
            self.assertEqual(view.painted_strips,data['strips'])
            self.assertNotIn('Top: '+NOT_DECODED,drawn)
            # Core's source projection has not adopted these fields; do not invent them.
            raw=(requires.CACHE/'e010-r0008-halftime.sav').read_bytes()
            old=views.country_card(Image.from_savestate(raw),7);view.set_card(old,'');drawn.clear();view.grab()
            self.assertIn('Top: '+NOT_DECODED,drawn)
        self.assertEqual(model.state,before)

if __name__=='__main__':unittest.main()
