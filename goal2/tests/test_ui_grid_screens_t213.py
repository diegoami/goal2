"""[designed: owner, #667; T213] Match-day screens fit their cells at each supported size; existing game-flow tests guard behavior."""
import unittest
from types import SimpleNamespace
from goal2.tests import requires
from goal2.tests.test_ui_grid_screens_t211b import Base
from goal2.tests.test_ui_match_day_t167 import CAREER, career, tearDownModule
requires.require(modules=("PySide6",))
from goal2.ui.s12_tournament import TournamentScreen
from goal2.ui.s13_history import HistoryScreen
from goal2.ui.s14_round import RoundScreen
from goal2.ui.s15_match_menu import MenuScreen, SavedGoalMenu
from goal2.ui.s20_board import BoardScreen, COUNTERS
from goal2.ui.kits import for_fixture
from goal2.ui.cells import CellPara
from goal2.ui import theme
from goal2.ui.frame import FrameRule

@CAREER
class MatchDayOnTheGrid(Base):
    EMPTY = ("default",)  # These read-only families have fewer widgets than the squad; geometry checks still visit every widget.
    kind = MenuScreen
    phase = "before"
    quick = False
    watch = True

    def make(self, window):
        model = career()
        window.open_career(model)
        fixture = model.state.campaign.next_fixture
        day = SimpleNamespace(model=model, fixture=fixture, kind_name="friendly", replay_auto=False,
                              watch=self.watch, bench=None, asks_watch=lambda *a: True, exit=lambda: None,
                              set_replay_auto=lambda *a: None, refresh_menu=lambda *a: None)
        if self.kind is MenuScreen:
            screen = self.kind(window, day, self.phase)
        elif self.kind is RoundScreen:
            row = dict(home_name="Trinidad/Tobago", away_name="Trinidad/Tobago", score=[12, 12], kind_name="continental semi-finals and final")
            screen = self.kind(window, dict(round=2,results=[row]*16,match=dict(row,score=None)),lambda:None)
            screen.timer.stop()
            while screen.arriving: screen.arrive()
        elif self.kind is BoardScreen:
            data = dict(score=[2,1],half_time=[0,0],scorers=[[(model.state.managed_squad[1],12)],[]],
                        counters={key:[2,1] for key,_ in COUNTERS},bars=[[123,456],[123,456]],
                        man_of_the_match=model.state.managed_squad[1],quick=self.quick)
            screen = self.kind(window,model,["Trinidad/Tobago"]*2,"continental semi-finals and final",self.phase,
                               data,lambda *a:None,for_fixture(model,fixture),save_summary=self.phase=="full")
        elif self.kind is SavedGoalMenu:
            data = dict(countries=["Trinidad/Tobago"]*2,score=[12,12],kind="continental semi-finals and final",
                        scorer="X Abcdefghij",minute=120,kits=dict(shirt=[1,2],keeper=[3,4]),
                        menu={str(i):["4-4-2",[("D","X Abcdefghij")]*11] for i in (0,1)})
            screen = self.kind(window,model,dict(data=data))
        else:
            screen = self.kind(window,model)
        return window.push(screen)

    def test_every_match_day_screen_fits_and_sits_on_the_grid(self):
        for kind in (MenuScreen,RoundScreen,TournamentScreen,HistoryScreen,BoardScreen,SavedGoalMenu):
            self.kind = kind
            self.phase = "full" if kind is BoardScreen else "before"
            with self.subTest(screen=kind.__name__):
                self.every_state_fits()
                self.not_pending(kind.__name__,kind)

    def test_menu_breaks_watch_question_and_board_modes_keep_all_text(self):
        for kind,phases in ((MenuScreen,("before","half","extra","full","pause","stop")),
                            (BoardScreen,("half","extra","full"))):
            self.kind = kind
            for phase in phases:
                self.phase = phase
                self.watch = None if phase=="before" else True
                with self.subTest(screen=kind.__name__,phase=phase):
                    self.every_state_fits()
                    window,screen = self.canonical(self.make)
                    self.text_fits_its_cells(screen)
                    for label in screen.findChildren(CellPara):
                        if label.isVisibleTo(screen):
                            self.assertLessEqual(len(label.lines()),self.rows_of(label),label.text())

    def test_half_time_menu_has_even_lineups_and_boxed_actions(self):
        self.phase = "half"
        _, screen = self.canonical(self.make)
        for rows in screen.lineup_rows.values():
            self.assertEqual(len(rows), 11)
            self.assertEqual([row.y() - rows[0].y() for row in rows],
                             [index * rows[0].height() for index in range(11)])
        for option in screen.options:
            if option is screen.highlighted():
                continue
            image = option.grab().toImage()
            for x, y in ((0, image.height() // 2), (image.width() // 2, 0),
                         (image.width() - 1, image.height() // 2), (image.width() // 2, image.height() - 1)):
                self.assertEqual(image.pixelColor(x, y).name(), theme.FRAME, option.text_label.text())

    def test_match_menu_groups_each_side_with_its_own_actions(self):
        self.phase = "half"
        _, screen = self.canonical(self.make)
        left = screen.lineup_headings[screen.home_country].parentWidget()
        right = screen.lineup_headings[screen.away_country].parentWidget()
        for country, panel in ((screen.home_country, left), (screen.away_country, right)):
            for option in screen.country_options[country]:
                self.assertTrue(panel.isAncestorOf(option))
            labels = [rule.label for rule in panel.findChildren(FrameRule)]
            self.assertEqual("view only" in labels, country != screen.model.state.managed_country)
        for option in screen.shared_options:
            self.assertLess(left.geometry().right(), option.x())
            self.assertLess(option.geometry().right(), right.x())
        self.assertIs(screen.highlighted(), screen.play)
        self.assertGreater(screen.replay_label.y(), left.geometry().bottom())

        self.phase = "full"
        _, full = self.canonical(self.make)
        for heading in full.lineup_headings.values():
            self.assertIn("view only", [rule.label for rule in heading.parentWidget().findChildren(FrameRule)])
        self.assertEqual(full.highlighted().enter, "Exit")

    def test_tournament_tabs_missing_stages_and_results_message_fit(self):
        self.kind = TournamentScreen
        window,screen = self.canonical(self.make)
        for continent in range(4):
            screen.choose_continent(continent)
            for group in range(8):
                screen.group=group
                screen._show()
                self.relayout(window)
                self.text_fits_its_cells(screen)
        for display in (1,2):
            screen.choose_display(display)
            screen.championship_results()
            self.relayout(window)
            self.on_the_grid(window,20)
            for text in (screen.note,screen.message_label):
                self.assertLessEqual(len(text.lines()),self.rows_of(text))

    def test_quick_boards_keep_scorers_and_every_menu_message_fits(self):
        self.kind = BoardScreen
        self.quick = True
        self.phase = "full"
        self.every_state_fits()
        self.kind = MenuScreen
        self.phase = "before"
        self.watch = None
        window,screen = self.canonical(self.make)
        for text in ("Answer the question first: Y to watch, N for a quick result.",
                     "Choose Play or press Enter to continue. The match stays stopped until you choose Play.",
                     "A quick result: the pitch shows HANG ON A TICK."):
            screen.say(text)
            self.relayout(window)
            self.assertLessEqual(len(screen.note.lines()),self.rows_of(screen.note))
            self.on_the_grid(window,20)


    def test_many_scorers_reflow_into_pairs_without_dropping_a_name_or_minute(self):
        from goal2.ui.s20_board import board
        self.kind = BoardScreen
        self.phase = "full"
        window,screen = self.canonical(self.make)
        # The board's renderer, not a claim about the result of an original match.
        model=window.career
        fixture=model.state.campaign.next_fixture
        data=dict(screen.data,scorers=[[(model.state.managed_squad[1],i) for i in range(12)],[]])
        window.pop()
        made=window.push(BoardScreen(window,model,["Trinidad/Tobago"]*2,"FRIENDLY","full",data,
                                     lambda *a:None,for_fixture(model,fixture)))
        self.relayout(window)
        from goal2.desktop import fixed_page
        self.assertEqual(fixed_page.problems(window),[])
        self.assertEqual(len(made.scorer_texts[1]),12)
        for i in range(12):self.assertTrue(any(line.endswith(f" {i}′") for line in made.scorer_texts[1]))


if __name__=="__main__": unittest.main()
