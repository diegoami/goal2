"""[designed: owner, 2026-11-09, #667; T211b] The country (S04), team info (S07) and fixtures (S11) screens on the 16 x 32 grid.

The claim it protects: **these screens fit and sit on the grid.** [designed: owner, 2026-11-08; docs/design/ui-2026-11/
fidelity-review.md §3] Each is laid out in cells (goal2/ui/cells.py) with frames for panels (goal2/ui/frame.py): at 1440x1080,
1440x900 and 2110x1213 (and 1440x1061, what a measured Windows runner gave a window asked for 1440x1080) `fixed_page.problems` is
empty, every widget rectangle is a multiple of the cell (T210's check, at the 4:3 page's own size) and there is no card (`#box`,
`#boxHeading`); and none of the three is on `reflow_pending.PENDING` or `grid_pending.PENDING`, so the helpers enforce it everywhere
else. It is true in every state the screens have, with the longest text each shows: the country card of each of the 128
countries fits the cells it is given, S04's name line open and its messages, S07's mark on a name of fifteen characters and the
performance panel, S11's longest kind and each message it says.

The geometry is measured on a window that is never shown where the grid is concerned (a desktop clamps a top-level window to its
work area); a shown window is asked for the sizes and the screen must fit the size it gets, whatever that is: no test here asserts a
size. The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them
(goal2/tests/requires.py).
"""
import shutil
import unittest

from goal2.tests import requires
from goal2.tests import grid_pending, reflow_pending
from goal2.tests import test_ui_boards_t178, test_ui_desk_t164
from goal2.tests.test_ui_boards_t178 import career, played_round
from goal2.tests.test_ui_desk_t164 import CAREER, holland
from goal2.tests.test_ui_grid_screens_t211 import SIZES, Base as GridBase

requires.require(modules=("PySide6",))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.game.country_card import card as country_card  # noqa: E402
from goal2.ui import cells, grid_check, s11_fixtures, theme  # noqa: E402
from goal2.ui.cells import CellLabel, CellPara  # noqa: E402
from goal2.ui.frame import Frame  # noqa: E402
from goal2.ui.s04_country import GROUP, LIST_COLS, NAME_NOTE, CountryCard, CountryScreen  # noqa: E402
from goal2.ui.s07_team_info import MARK, TeamInfoScreen  # noqa: E402
from goal2.ui.s11_fixtures import (LATER_FRIENDLY, LATER_WATCH, OWN_WATCHED, VISIBLE, FixturesScreen)  # noqa: E402
from goal2.ui.screen import Clickable  # noqa: E402

SCREENS = ("CountryScreen", "TeamInfoScreen", "FixturesScreen")
LONGEST_KIND = "continental semi-finals and final"   # [confirmed: goal2.desktop.model.STAGES, the longest word `kind_word` gives]
TRINIDAD = "Trinidad/Tobago"                          # fifteen characters: the longest country name


def tearDownModule():
    test_ui_desk_t164.tearDownModule()
    test_ui_boards_t178.tearDownModule()


class Base(GridBase):
    EMPTY = ()   # the states with no row in the list: fewer widgets

    def data(self):
        """The new window's two files, copied from .cache/ into the window's data folder (S04 opens private careers from them)."""
        target = data_setup.Paths(self.tmp / "goal2")
        target.data.mkdir(parents=True, exist_ok=True)
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(requires.CACHE / name, target.data / name)

    def on_the_grid(self, window, at_least=100):
        """No widget off the cell, no card: and the check saw the page (a list with no rows has fewer widgets: `at_least`)."""
        found = grid_check.violations(window)
        self.assertGreater(len(grid_check.widgets(window)), at_least, "the check saw the page's widgets")
        self.assertEqual(found, [], "on the 16 x 32 grid with no card")

    def states(self):
        """(name, how to put the screen in it) for each state the screen shows."""
        return (("default", lambda screen: None),)

    def check_state(self, name, put):
        """The state on a never-shown window at the page's own size (on the grid, no card, nothing squeezed) and on a shown
        window at each size of `SIZES` (`fixed_page.problems` is empty)."""
        window, screen = self.canonical(self.make)
        put(screen)
        self.relayout(window)
        self.assertIs(window.current(), screen)
        self.assertEqual(fixed_page.problems(window), [], f"{name}, the page's own size")
        self.on_the_grid(window, 100 if name not in self.EMPTY else 20)
        shown = self.window()
        shown_screen = self.make(shown)
        put(shown_screen)
        for width, height in SIZES:
            shown.resize(width, height)
            shown.show()
            for _ in range(3):
                self.app.processEvents()
            self.assertEqual(fixed_page.problems(shown), [], f"{name} at {shown.width()}x{shown.height()}")

    def every_state_fits(self):
        for name, put in self.states():
            with self.subTest(state=name):
                self.check_state(name, put)

    def text_fits_its_cells(self, root, message=""):
        """Every label of `root` has the cells its text takes (a label is as wide as its characters: none is clipped or squeezed)."""
        cell = cells.cell_w(root)
        for label in root.findChildren(CellLabel):
            if label.isVisibleTo(root):
                self.assertLessEqual(label.cols(), round(label.width() / cell), f"{message} {label.objectName()} {label.text()!r}")

    def rows_of(self, para):
        return para.height() // cells.row_px(para)

    def key_bar_is_two_rows(self, window, screen):
        self.assertEqual(screen.key_bar.height(), cells.span_px(screen, 2), "two rows, the page's own")
        self.assertEqual(screen.body.height(), window.page.height() - cells.row_px(screen) - screen.key_bar.height())

    def not_pending(self, name, kind):
        for lists in (reflow_pending.PENDING, grid_pending.PENDING):
            self.assertNotIn(name, lists)
        self.assertTrue(kind.GRID)


@CAREER
class CountryOnTheGrid(Base):
    """S04 with its card, its list of sixteen and its name line."""

    def make(self, window):
        self.data()
        screen = window.push(CountryScreen(window, 2028))
        screen.settle()
        return screen

    def states(self):
        def go_to(name):
            def put(screen):
                screen.index = next(i for i, c in enumerate(screen.order) if c[1] == name)
                screen.settle()
                screen._show()
            return put

        def naming(screen):
            screen.press_enter_key()
            screen.field.set_text("Trinidad Tobago")   # fourteen characters: the line is full

        def empty_name(screen):
            screen.press_enter_key()
            screen.press_enter_key()   # "Type the manager's name first"

        def world(screen):
            screen.toggle_rank()

        def second_group(screen):
            screen.group(1)

        def unknown(screen):
            # a country the route has not decoded: no strips, the words of `NOT_DECODED` for the rest
            data = dict(screen.card)
            data.pop("strips", None)
            data.pop("top_world", None)
            data.pop("top_continental", None)
            screen.card = data
            screen._show_card()
        return (("denmark, the first", lambda screen: None), ("the longest name", go_to(TRINIDAD)), ("naming", naming),
                ("an empty name", empty_name), ("world rank", world), ("the second group", second_group),
                ("undecoded fields", unknown))

    def test_the_country_screen_fits_in_every_state_at_every_size_and_is_on_the_grid(self):
        self.every_state_fits()

    def test_it_is_not_on_either_pending_list(self):
        """It was listed (reflow_pending: 1688x1176 needed, grid_pending: 174 widgets off the cell and 11 cards) until T211b."""
        self.not_pending("CountryScreen", CountryScreen)

    def test_its_panels_are_frames_a_rule_with_its_lowercase_label_and_none_is_a_card(self):
        window, screen = self.canonical(self.make)
        labels = [frame.label for frame in screen.findChildren(Frame)]
        self.assertEqual(sorted(labels), sorted(["team", "skills", "performance", "team tactics", "ranking", "line-up",
                                                  "characteristics", "player defaults", "continental rank", "manager's name"]))
        for frame in screen.findChildren(Frame):
            self.assertEqual(frame.rule.text()[0], "-")
            self.assertEqual(len(frame.rule.text()), frame.rule.cols(), "dashes to the panel's edge")
        self.assertEqual(grid_check.cards(window), [])
        self.assertEqual(screen.findChildren(QLabel, "boxHeading"), [])

    def test_the_card_and_the_list_fill_the_page_across_a_cell_apart(self):
        """The card is 60 cells, the list 29 and a cell between them: the 90 columns of the page, as S07's."""
        window, screen = self.canonical(self.make)
        cell = cells.cell_w(screen)
        self.assertEqual(round(screen.card_view.width() / cell), CountryCard.COLS)
        self.assertEqual(round(screen.countries_frame.width() / cell), LIST_COLS)
        gap = screen.countries_frame.x() - (screen.card_view.x() + screen.card_view.width())
        self.assertEqual(round(gap / cell), 1, "one empty cell separates")
        self.assertEqual(CountryCard.COLS + 1 + LIST_COLS, theme.COLS)
        self.assertEqual(len(screen.rows), GROUP)

    def test_every_country_of_the_game_fits_the_cells_its_card_gives_it(self):
        """The 128 countries' cards: no value is longer than its cells (the longest name, manager, status, tactic word, ...)."""
        window, screen = self.canonical(self.make)
        for number in range(1, 129):
            screen.browser.new_campaign(number, 2028)
            data = country_card(screen.browser.state, number, screen.browser.goaldat)
            screen.card_view.set_card(data)
            self.text_fits_its_cells(screen.card_view, f"country {number}")
        self.assertEqual(screen.card_view.name.text(), screen.browser.goaldat.country_names[128])

    def test_the_first_match_and_the_level_of_difficulty_are_rows_across_the_page(self):
        window, screen = self.canonical(self.make)
        self.assertEqual(screen.first.height(), cells.row_px(screen), "one row")
        longest = "first: 2028 Continental qualifying: " + TRINIDAD + " / Qualifier"   # the longest first match of a 2028 or 1993 start
        screen.first.setText(longest)
        self.text_fits_its_cells(screen.area)
        self.assertLessEqual(len(longest), theme.COLS)

    def test_the_name_line_and_what_it_says_fit_the_rows_they_have(self):
        window, screen = self.canonical(self.make)
        for message in (NAME_NOTE, "Type the manager's name first: 14 characters at most.", "x" * 60):
            screen._note(message)
            self.assertLessEqual(len(screen.name_note.lines()), self.rows_of(screen.name_note), message)
        self.assertEqual(self.rows_of(screen.name_note), 3)

    def test_the_bar_keeps_its_two_rows_for_each_enter_hint(self):
        window, screen = self.canonical(self.make)
        self.key_bar_is_two_rows(window, screen)
        for put in (lambda: screen.press_enter_key(), lambda: screen.escape()):
            put()
            self.relayout(window)
            self.key_bar_is_two_rows(window, screen)

    def test_the_list_highlights_one_row_and_a_click_chooses_it(self):
        window, screen = self.canonical(self.make)
        self.assertEqual([row.on for row in screen.rows].count(True), 1)
        self.assertEqual(screen.visible_ranks()[0], "1")
        screen.rows[3].clicked.emit()
        self.assertEqual(screen.index, 3)


@CAREER
class TeamInfoOnTheGrid(Base):
    """S07 with the card, the heading and the sixteen countries, the next opponent marked."""

    def make(self, window):
        model = holland()
        window.open_career(model)
        screen = window.push(TeamInfoScreen(window, model))
        screen.settle()
        return screen

    def states(self):
        def opponent(name):
            def put(screen):
                number = next(c[0] for c in screen.order if c[1] == name)
                screen.opponent = number
                screen.index = next(i for i, c in enumerate(screen.order) if c[0] == number)
                screen.settle()
                screen._show()
            return put

        def performance(screen):
            screen.card_view.match_context = True   # the original's active match: the performance bars (T198)
            screen.previewed = None
            screen.preview()

        def continental(screen):
            screen.toggle_rank()

        def message(screen):
            screen.say("x" * 58)
        return (("the next opponent", lambda screen: None), ("the longest name, marked", opponent(TRINIDAD)),
                ("continental rank", continental), ("the performance shown", performance), ("a message", message))

    def test_the_team_info_screen_fits_in_every_state_at_every_size_and_is_on_the_grid(self):
        self.every_state_fits()

    def test_it_is_not_on_either_pending_list(self):
        self.not_pending("TeamInfoScreen", TeamInfoScreen)

    def test_its_panels_are_frames_and_the_original_heading_is_the_rows_over_the_list(self):
        window, screen = self.canonical(self.make)
        labels = [frame.label for frame in screen.findChildren(Frame)]
        self.assertEqual(sorted(labels), sorted(["team", "skills", "performance", "team tactics", "ranking", "line-up",
                                                  "characteristics", "player defaults", "countries"]))
        self.assertEqual(grid_check.cards(window), [])
        heading = [w for w in screen.findChildren(QLabel, "sub") if w.text() == "check out all the competitors"]
        self.assertEqual(len(heading), 1)
        self.assertLess(heading[0].y(), screen.countries_frame.y(), "over the list")

    def test_the_card_is_the_same_60_cells_as_s04s_and_the_list_the_same_29(self):
        window, screen = self.canonical(self.make)
        cell = cells.cell_w(screen)
        self.assertEqual(round(screen.card_view.width() / cell), CountryCard.COLS)
        self.assertEqual(round(screen.countries_frame.width() / cell), LIST_COLS)
        self.assertEqual(round((screen.countries_frame.x() - screen.card_view.x() - screen.card_view.width()) / cell), 1)

    def test_the_mark_is_in_the_second_cell_of_the_next_opponents_row_alone(self):
        window, screen = self.canonical(self.make)
        marks = screen.marks()
        self.assertEqual(sum(1 for mark in marks if mark), 1)
        self.assertIn(MARK, marks)
        row = screen.rows[marks.index(MARK)]
        self.assertEqual(row.cells[0].width() + cells.cell_w(screen) + row.cells[1].width(),
                         row.width(), "the name, a cell, the mark: the list's 29")

    def test_every_country_of_the_game_fits_the_cells_its_card_gives_it(self):
        window, screen = self.canonical(self.make)
        for number in range(1, 129):
            data = country_card(screen.model.state, number, screen.model.goaldat)
            screen.card_view.set_card(data)
            self.text_fits_its_cells(screen.card_view, f"country {number}")

    def test_the_bar_keeps_its_two_rows_for_each_enter_hint(self):
        window, screen = self.canonical(self.make)
        self.key_bar_is_two_rows(window, screen)
        screen.index = next(i for i, c in enumerate(screen.order) if c[1] == TRINIDAD)
        screen._show()
        self.relayout(window)
        self.assertEqual(screen.enter_text.text(), f"Fixtures of {TRINIDAD}")
        self.key_bar_is_two_rows(window, screen)

    def test_a_message_fits_its_two_rows(self):
        window, screen = self.canonical(self.make)
        screen.say("Nothing to say about this country: " + "x" * 20)
        self.assertLessEqual(len(screen.note.lines()), self.rows_of(screen.note))


@CAREER
class FixturesOnTheGrid(Base):
    """S11: the round (longer than the screen), a country's coming fixtures, each message it says and the states without a list."""
    EMPTY = ("no schedule", "stage complete")

    def make(self, window, country=None, back="desk"):
        model = played_round(career())   # round 2 is longer than the screen
        window.open_career(model)
        return window.push(FixturesScreen(window, model, country=country, back=back))

    def states(self):
        def last(screen):
            for _ in screen.items:
                screen.move(1)

        def longest_row(screen):
            # the longest names and kind a row has: fifteen characters before and after the v, the longest stage's word
            screen.items = [dict(row, first_name=TRINIDAD, second_name=TRINIDAD, kind_name=LONGEST_KIND) for row in screen.items]
            screen._show()

        def message(text):
            def put(screen):
                screen.message = text
                screen._show()
            return put

        def no_schedule(screen):
            screen.listing, screen.items = None, []
            screen._show()

        def stage_complete(screen):
            screen.items = []
            screen._show()
        return (("the round", lambda screen: None), ("the last row", last), ("the longest names and kind", longest_row),
                ("watch later", message(LATER_WATCH)), ("friendly later", message(LATER_FRIENDLY)), ("always watched", message(OWN_WATCHED)),
                ("no schedule", no_schedule), ("stage complete", stage_complete))

    def test_the_fixtures_screen_fits_in_every_state_at_every_size_and_is_on_the_grid(self):
        self.every_state_fits()

    def test_a_countrys_coming_fixtures_fit_too(self):
        for country, name in ((20, "Holland"), (next(c[0] for c in holland_countries() if c[1] == TRINIDAD), TRINIDAD)):
            with self.subTest(country=name):
                window = self.window()
                self.make(window, country=country, back="team info")
                for width, height in SIZES:
                    window.resize(width, height)
                    window.show()
                    for _ in range(3):
                        self.app.processEvents()
                    self.assertEqual(fixed_page.problems(window), [], f"{name} at {window.width()}x{window.height()}")
                canonical, screen = self.canonical(lambda w: self.make(w, country=country, back="team info"))
                self.assertIn(name, screen.heading())
                self.on_the_grid(canonical)

    def test_it_is_not_on_either_pending_list(self):
        self.not_pending("FixturesScreen", FixturesScreen)

    def test_its_panel_is_a_frame_with_the_heading_on_its_rule_and_the_columns_are_labels(self):
        window, screen = self.canonical(self.make)
        frames = screen.findChildren(Frame)
        self.assertEqual([frame.label for frame in frames], [screen.heading().lower()])
        self.assertEqual(frames[0].rule.text()[:8], "-fixture")
        self.assertEqual(grid_check.cards(window), [])
        header = [w for w in screen.findChildren(Clickable, "listRow") if w.index == -1][0]
        self.assertEqual(header.texts(), ["watch", "", "", "", "match", "at kick-off"])

    def test_it_shows_sixteen_rows_the_originals(self):
        """[confirmed: docs/original-game/images/fixtures-watch.png] the original's list is sixteen rows; S11 held fourteen at 24 px."""
        window, screen = self.canonical(self.make)
        self.assertEqual(VISIBLE, 16)
        self.assertEqual(len(screen.shown_rows()), 16)
        self.assertEqual(s11_fixtures.WIDTHS, (6, 16, 3, 16, 34, 15))
        self.assertEqual(sum(s11_fixtures.WIDTHS), theme.COLS, "across the 90 columns of the page")

    def test_a_row_is_a_row_of_cells_and_the_columns_stand_in_the_same_cells_on_each_row(self):
        window, screen = self.canonical(self.make)
        cell = cells.cell_w(screen)
        xs = {tuple(cell_.x() for cell_ in row.cells) for row in screen.rows}
        self.assertEqual(len(xs), 1, "every row's cells are at the same columns")
        for row in screen.rows:
            self.assertEqual([round(widget.width() / cell) for widget in row.cells], list(s11_fixtures.WIDTHS))
        self.assertEqual(round(screen.rows[0].width() / cell), theme.COLS)

    def test_the_count_the_note_and_what_enter_said_take_the_rows_they_have(self):
        window, screen = self.canonical(self.make)
        for message in (LATER_WATCH, LATER_FRIENDLY, OWN_WATCHED, "x" * 150):
            screen.message = message
            screen._show()
            self.assertLessEqual(len(screen.note.lines()), self.rows_of(screen.note), message)
        self.assertEqual(self.rows_of(screen.empty), 1)
        self.assertLessEqual(len("No coming fixtures: the stage is complete, and the next one is not reached yet (T170)."), theme.COLS)
        note = [w for w in screen.findChildren(CellPara) if w.text().startswith(s11_fixtures.NOTE[:10])][0]
        self.assertLessEqual(len(note.lines()), self.rows_of(note))

    def test_the_bar_keeps_its_two_rows_for_each_enter_hint(self):
        window, screen = self.canonical(self.make)
        self.key_bar_is_two_rows(window, screen)
        for step in range(3):
            screen.move(1)
            self.relayout(window)
            self.key_bar_is_two_rows(window, screen)


def holland_countries():
    return holland().countries()


if __name__ == "__main__":
    unittest.main()
