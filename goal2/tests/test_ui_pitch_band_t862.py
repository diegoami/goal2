"""[designed: owner, 2026-11-25 and 2026-11-27, #862] S17 and S18 drawn as the original draws its pitch screen.

The claims it protects, each against the original's captures (docs/original-game/images):
- **The top band** (t156-045-kick-off.png, t156-066-injury-and-booking.png, match-commentary.png, e031-shootout-start.png):
  the score box names the home side in light red and the away side in white, each with dash leaders, `versus` between them,
  and each side's goals boxed on its own row; the frame of the kind of match holds the last three events; the minute is
  large blocky digits at the right, line-art and not type.
- **No dead region** above the key line: the pitch and the commentary reach the body's last row, and the rows over the key
  line carry ink across the pitch.
- **The key line** reads as the original's (`↑↓ display ↔ speed»»»»»» R result Space commentary F9 ♫ Esc bench`), the speed's
  chevrons in its caption.
- **S18's stops sit on the key line** (t156-067-substitution-opportunity.png, t156-149-opponent-substitution.png,
  t156-175-replay-prompt.png): across the foot of the screen, never over the pitch's field or the top band; a notice is a grey
  label with a magenta key hint, a question is cyan; the mouse answers them as the keys do.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them.
"""
import unittest

from goal2.tests import requires
from goal2.tests import test_ui_desk_t164
from goal2.tests.test_ui_grid_screens_t211 import Base as GridBase
from goal2.tests import test_ui_grid_screens_t212 as t212

requires.require(modules=("PySide6",))

from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from goal2.ui import cells, theme  # noqa: E402
from goal2.ui.frame import Frame  # noqa: E402


def tearDownModule():
    test_ui_desk_t164.tearDownModule()


def colour_of(widget):
    return widget.palette().color(widget.foregroundRole()).name()


def rect_in(screen, widget, rect=None):
    rect = widget.rect() if rect is None else rect
    return QRect(widget.mapTo(screen, rect.topLeft()), rect.size())


def events(*texts, minute=12):
    return [{"kind": "commentary", "minute": minute, "score": [0, 1], "data": {"text": text}} for text in texts]


@t212.PITCH
class PitchBand(GridBase):
    make = t212.PitchOnTheGrid.make
    names = None   # the fixture's countries and kind (t212's `make` reads them)
    kind = None

    def screen(self):
        window, screen = self.canonical(self.make)
        self.window_ = window
        return screen

    # The top band.
    def test_the_score_box_names_home_in_light_red_and_away_in_white_with_dash_leaders_and_versus(self):
        """[derived: t156-045 (Norway at home), match-commentary.png (Italy, whose kit is blue, at home),
        e031-shootout-start.png (Belgium at home): the home name is light red and the away name white whatever the kits]"""
        from goal2.ui.pitch import HOME, side_colour
        from goal2.ui.s17_pitch import SIDE_COLS
        screen = self.screen()
        names = screen.controller.display.countries
        self.assertEqual(screen.home.text(), names[HOME] + "-" * (SIDE_COLS - len(names[HOME])))
        self.assertEqual(screen.away.text(), names[1 - HOME] + "-" * (SIDE_COLS - len(names[1 - HOME])))
        self.assertEqual(colour_of(screen.home), theme.TITLE_BANNER)
        self.assertEqual(colour_of(screen.away), theme.TEXT_BRIGHT)
        self.assertNotEqual(side_colour(1 - HOME, screen.kits), theme.TEXT_BRIGHT,
                            "the fixture's away kit is not white, so the name's white is not its kit")
        self.assertEqual(screen.versus.text(), "versus")
        home, versus, away = (rect_in(screen, w) for w in (screen.home, screen.versus, screen.away))
        row = cells.row_px(screen)
        self.assertEqual((versus.y() - home.y(), away.y() - versus.y()), (row, row))
        digits = [rect_in(screen, label.parentWidget()) for label in screen.goals]
        self.assertEqual([d.y() for d in digits], [home.y(), away.y()], "each side's goals on its own row")

    def test_the_frame_of_the_kind_of_match_holds_the_last_three_events(self):
        screen = self.screen()
        shown = events("Bratseth wins the toss", "Nilsen to take kick off", "FOUL by Nilsen", "Nilsen BOOKED")
        screen.controller.shown = lambda: shown
        screen.refresh()
        self.assertEqual([w.text() for w in screen.recent], ["Nilsen to take kick off", "FOUL by Nilsen", "Nilsen BOOKED"])
        two = events("Bratseth wins the toss", "Nilsen to take kick off")
        screen.controller.shown = lambda: two
        screen.refresh()
        self.assertEqual([w.text() for w in screen.recent], ["Bratseth wins the toss", "Nilsen to take kick off", ""],
                         "from the first row, as t156-045-kick-off.png")
        frame = next(f for f in screen.findChildren(Frame) if f.label == screen.controller.display.kind.lower())
        self.assertEqual(round(frame.height() / cells.row_px(screen)), 4, "the rule and three events")

    def test_the_minute_is_large_line_art_digits_at_the_right(self):
        from goal2.ui.s17_pitch import HEAD_ROWS
        screen = self.screen()
        clock = screen.clock
        self.assertEqual(clock.findChildren(QLabel), [], "line-art, not type")
        self.assertNotIsInstance(clock, QLabel)
        for minute, shown in ((0, ""), (8, "8"), (17, "17"), (105, "105")):
            screen.controller.frame_or_event = lambda m=minute: (m, [0, 0])
            screen.refresh()
            self.assertEqual(clock.digits(), shown)
        page = self.window_.page
        right = clock.mapTo(page, QPoint(clock.width(), 0)).x()
        self.assertEqual(right, page.width(), "at the right of the band")
        self.assertEqual(round(clock.height() / cells.row_px(screen)), HEAD_ROWS, "as tall as the band")
        screen.controller.frame_or_event = lambda: (17, [0, 0])
        screen.refresh()
        image = clock.grab().toImage()
        ink = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())}
        self.assertIn(theme.HEADING, ink, "cyan digits")

    # No dead region.
    def test_the_pitch_and_the_commentary_reach_the_foot_and_the_foot_has_ink_across_the_pitch(self):
        screen = self.screen()
        body = rect_in(screen, screen.area)
        pitch = rect_in(screen, screen.pitch)
        frame = next(f for f in screen.findChildren(Frame) if f.label == "commentary")
        row = cells.row_px(screen)
        # rows are whole pixels from the top: what is left under the last row is the page's 4:3 slack, less than a row
        self.assertLess(body.bottom() - pitch.bottom(), row, "the pitch reaches the body's last row")
        self.assertEqual(rect_in(screen, frame).bottom(), pitch.bottom(), "the commentary reaches it too")
        from goal2.ui.s17_pitch import REQUESTED
        screen.controller.note = REQUESTED
        screen.refresh()
        self.relayout(self.window_)
        self.assertTrue(screen.note.isVisibleTo(screen))
        self.assertTrue(rect_in(screen, frame).contains(rect_in(screen, screen.note)), "what the bench said is in the commentary")
        screen.controller.note = ""
        screen.refresh()
        self.relayout(self.window_)
        image = screen.grab().toImage()
        quarter = pitch.width() // 4
        for part in range(4):
            with self.subTest(quarter=part):
                found = any(image.pixelColor(x, y).name() != theme.GROUND
                            for x in range(pitch.x() + part * quarter, pitch.x() + (part + 1) * quarter)
                            for y in range(pitch.bottom() - 2 * row + 1, pitch.bottom() + 1))
                self.assertTrue(found, "ink in the rows over the key line")

    def test_the_field_keeps_its_proportions(self):
        """The field is drawn at the size it had in 18 rows; the rows the pitch gains are surround."""
        from goal2.ui.s17_pitch import FIELD_ROWS
        screen = self.screen()
        row = cells.row_px(screen)
        drawing = screen.pitch.drawing()
        self.assertEqual(drawing.height(), FIELD_ROWS * row)
        self.assertEqual(drawing.width(), screen.pitch.width())
        self.assertAlmostEqual(screen.pitch.scale_y(), FIELD_ROWS * row / 560, places=3)

    # The key line.
    def test_the_key_line_reads_as_the_originals_with_the_speed_in_its_caption(self):
        screen = self.screen()
        markers = screen.controller.display.speed_markers()
        texts = screen.key_texts()
        for expected in ((("↑", "↓"), "display"), (("↔",), "speed" + markers), (("R",), "result"),
                         (("Space",), "commentary"), (("F9",), "♫"), (("Esc",), "bench")):
            self.assertIn(expected, texts)
        screen.step_speed(-1)
        slower = screen.controller.display.speed_markers()
        self.assertNotEqual(slower, markers)
        self.assertIn((("↔",), "speed" + slower), screen.key_texts())
        drawn = [w.text() for w in screen.key_bar.findChildren(QLabel, "keyLabel")]
        self.assertIn("speed" + slower, drawn, "the bar redraws the caption")
        frame = next(f for f in screen.findChildren(Frame) if f.label == "commentary")
        self.assertFalse(any("Speed" in w.text() or "marks:" in w.text() for w in frame.findChildren(QLabel)),
                         "the speed and marks are no longer in the commentary")

    # The stops.
    def stops(self, screen):
        from goal2.ui.s18_stop import ACTION_REPLAY, NOTICE_OPPONENT, NOTICE_SHOOTOUT, SHOOTOUT, YES_NO
        return (
            ("question", lambda: screen.show_stop("replay", ACTION_REPLAY, "", lambda key: None, dict(YES_NO))),
            ("opponent", lambda: screen.show_stop(NOTICE_OPPONENT, "SUBSTITUTION Leonharsen on for Nilsen",
                                                  "Norway: Norway 0 - 1 Holland, 30′. Press any key: play on.", lambda key: None)),
            ("shootout", lambda: screen.show_stop(NOTICE_SHOOTOUT, SHOOTOUT, "The match ends level: the penalty shoot-out follows.",
                                                  lambda key: None)),
            ("opportunity", lambda: t212.PitchOnTheGrid.opportunity(self, screen)),
            ("keeper", lambda: t212.PitchOnTheGrid.opportunity(self, screen, True, 3)),
        )

    def test_a_stop_sits_on_the_key_line_and_leaves_the_field_and_the_band_in_view(self):
        screen = self.screen()
        self.addCleanup(screen.stop_box.cancel)
        row = cells.row_px(screen)
        for name, put in self.stops(screen):
            with self.subTest(stop=name):
                screen.stop_box.cancel()
                put()
                self.relayout(self.window_)
                box = rect_in(screen, screen.stop_box)
                self.assertTrue(screen.stop_box.open)
                self.assertEqual((box.x(), box.width()), (0, screen.width()), "across the screen")
                self.assertEqual(box.bottom(), screen.rect().bottom(), "at its foot")
                self.assertLessEqual(box.y(), rect_in(screen, screen.key_bar).y(), "over the key line")
                self.assertIn(box.height(), [cells.span_px(screen, rows) for rows in range(2, 6)], "whole rows, as the key line's")
                field = rect_in(screen, screen.pitch, screen.pitch.field())
                self.assertFalse(box.intersects(field), "the field stays in view")
                self.assertFalse(box.intersects(rect_in(screen, screen.score_head)), "the band stays in view")
        screen.stop_box.cancel()

    def test_a_notice_is_a_grey_label_with_a_magenta_hint_and_a_question_is_cyan(self):
        from goal2.ui.s18_stop import ANY_KEY
        screen = self.screen()
        self.addCleanup(screen.stop_box.cancel)
        stops = dict(self.stops(screen))
        box = screen.stop_box
        stops["opponent"]()
        self.assertEqual(box.texts()[0], "SUBSTITUTION Leonharsen on for Nilsen", "the headline is whole")
        self.assertEqual(box.label.text(), "SUBSTITUTION")
        self.assertIn("#aaaaaa", box.label.styleSheet().lower(), "a grey label")
        self.assertEqual(colour_of(box.label), "#000000")
        self.assertEqual(box.rest.text(), "Leonharsen on for Nilsen")
        self.assertEqual(colour_of(box.rest), theme.HEADING)
        self.assertEqual(box.key_hint.text(), ANY_KEY)
        self.assertEqual(colour_of(box.key_hint), theme.KEY_HINT)
        box.cancel()
        stops["question"]()
        self.assertEqual(colour_of(box.headline), theme.HEADING, "a question is cyan")
        self.assertEqual(colour_of(box.key_hint), theme.HEADING)

    def test_the_mouse_answers_a_stop_as_the_keys_do(self):
        from goal2.ui.s18_stop import YES_NO
        screen = self.screen()
        self.addCleanup(screen.stop_box.cancel)
        box = screen.stop_box
        answers = []
        screen.show_stop("opponent", "SUBSTITUTION A on for B", "", answers.append)
        self.relayout(self.window_)
        QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=box.rect().center())
        self.assertEqual(answers, [Qt.Key.Key_Return])
        self.assertFalse(box.open)
        screen.show_stop("replay", "Do you want an action replay?", "", answers.append, dict(YES_NO))
        self.relayout(self.window_)
        QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=box.rect().center())
        self.assertTrue(box.open, "a click beside the answers answers nothing")
        item = box.answer_items[Qt.Key.Key_N]
        QTest.mouseClick(item, Qt.MouseButton.LeftButton, pos=item.rect().center())
        self.assertEqual(answers, [Qt.Key.Key_Return, Qt.Key.Key_N])
        self.assertFalse(box.open)


if __name__ == "__main__":
    unittest.main()
