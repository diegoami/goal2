"""[designed: owner, 2026-10-22, #312; T101] One fixed page, scaled to the window.

Every screen is composed once for a page of 1440x900 logical pixels. The window scales that
page uniformly to fit, keeps its aspect and fills the margin black; nothing scrolls at any size,
and a small window shows everything smaller (as the pitch view does, `pygame_viewer.layout`).
[confirmed: `docs/original-game/images/*`] Every original screen is one 80x25 text page.

The way [designed: T101]: the page stays an ordinary tree of native Qt widgets, and the scale is
applied to the whole page. `FixedPage` is the window's central widget; it holds the page at
round(1440*s) x round(900*s), centred, where s = min(width/1440, height/900). Every length the
page is composed with is multiplied by s: the style sheet's pixel sizes (type, borders, padding,
minimum heights), the layouts' margins and spacings, the explicit widget sizes and table rows,
and the painted views (roster, cards), which draw in page coordinates through a scaled painter.
Native widgets keep native input: focus, the keyboard, the mouse, drop-downs, dialogs and the
accessibility tree see real widgets at their real place, so a drop-down opens at its scaled
position and a click lands where the widget is drawn. (A QGraphicsView holding the page would
scale it exactly too, but then the window's focus widget is the view, accessible geometry is the
off-screen proxy's, and drop-downs become scene items; see docs/desktop-management.md.)

[designed: owner, 2026-11-08, #667; T209] A page may be presented at 4:3, as DOSBox shows the original: `FixedPage(...,
stretch=1.2, text=32, aspect=(4, 3))` takes a logical page (the new window's is 1440x896, 90x28 cells of 16x32), scales every
horizontal length by s and every vertical one by 1.2*s, and keeps the page's rectangle 4:3 at any window size (letterboxed,
never re-flowed). A style
sheet cannot carry a font stretch, so the text is stretched in code: each widget has the taller pixel size and the narrower
`QFont` stretch that keeps a glyph one cell wide (`text_stretch`), and widgets inherit it. Without `stretch` (today's window,
goal2/desktop) the page is uniform, 1440x900, and nothing changes.

`problems(window)` is the no-scroll check every screen task uses: at the window's present size,
no scroll bar is visible, every visible widget lies inside the page, and no widget is clipped by
its parent or squeezed below the size its content needs.
"""
import re
from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QWidget, QLayout, QGridLayout, QBoxLayout, QScrollBar, QLabel,
                               QTableView, QAbstractScrollArea, QStackedWidget)

WIDTH, HEIGHT = 1440, 900
UNBOUNDED = 16777215
_PX = re.compile(r'(\d+(?:\.\d+)?)px')


def scale_of(widget):
    """The scale of the page `widget` is drawn on (1 for a widget outside a scaled window): the horizontal one."""
    window = widget.window() if widget is not None else None
    value = window.property('pageScale') if window is not None else None
    return float(value) if value else 1.0


def stretch_of(widget):
    """The vertical stretch of the page `widget` is drawn on (1.2 on the 4:3 page, 1 on a uniform one)."""
    window = widget.window() if widget is not None else None
    value = window.property('pageStretch') if window is not None else None
    return float(value) if value else 1.0


def scale_y_of(widget):
    """The vertical scale of the page `widget` is drawn on: the horizontal scale times the stretch."""
    return scale_of(widget) * stretch_of(widget)


def px(value, scale):
    """A page length at `scale`: rounded, and never 0 for a length that is not 0."""
    return 0 if not value else max(1, round(value * scale))


# The margin that gives a 3px focus border the room of a 2px border plus this margin: computed from
# the two rounded widths, so a focused control keeps its size at every scale.
FOCUS_MARGIN = '@focus-margin'


# [designed: T209] How a style sheet's pixel length scales on a stretched page: by the property it belongs to. A vertical
# property (a height, a top or bottom padding or margin or border) takes the vertical scale, the rest the horizontal one;
# `font-size` is the text's pixel size, which is vertical (the stretch narrows the glyph back, `text_stretch`). A box
# shorthand's values are taken in CSS order (top right bottom left); `border: 1px ...` has one width for four sides and
# takes the horizontal scale (a 1 to 3 px border differs by at most a pixel).
_DECL = re.compile(r'([\w-]+)(\s*:\s*)([^;{}]*)')
_VERTICAL = {'height', 'min-height', 'max-height', 'padding-top', 'padding-bottom', 'margin-top', 'margin-bottom',
             'border-top', 'border-bottom'}
_BOX = {'padding', 'margin'}


def scale_sheet(sheet, scale, stretch=1.0):
    """The style sheet with every pixel length multiplied by `scale` (the vertical ones also by `stretch`)."""
    if stretch == 1.0:
        sheet = _PX.sub(lambda m: f'{px(float(m.group(1)), scale)}px', sheet)
        return sheet.replace(FOCUS_MARGIN, f'{px(3, scale) - px(2, scale)}px')

    def lengths(value, factor):
        return _PX.sub(lambda m: f'{px(float(m.group(1)), factor)}px', value)

    def declaration(match):
        name, colon, value = match.group(1), match.group(2), match.group(3)
        if 'px' not in value:
            return match.group(0)
        if name == 'font-size' or name in _VERTICAL:
            return name + colon + lengths(value, scale * stretch)
        if name in _BOX:
            tokens = value.split()
            order = {1: (0, 0, 0, 0), 2: (0, 1, 0, 1), 3: (0, 1, 2, 1), 4: (0, 1, 2, 3)}.get(len(tokens))
            if order is None:
                return name + colon + lengths(value, scale)
            top, right, bottom, left = (tokens[i] for i in order)
            return (name + colon + ' '.join((lengths(top, scale * stretch), lengths(right, scale),
                                             lengths(bottom, scale * stretch), lengths(left, scale))))
        return name + colon + lengths(value, scale)

    sheet = _DECL.sub(declaration, sheet)
    return sheet.replace(FOCUS_MARGIN, f'{px(3, scale) - px(2, scale)}px')


def text_stretch(scale, stretch, text):
    """The `QFont` stretch, in percent, that keeps a glyph one cell wide on the stretched page: the font's advance is half
    its pixel size, the pixel size is `text` x `stretch` x `scale` rounded (a taller glyph), and the advance wanted is
    `text` / 2 x `scale`. [derived: confirmed 2026-11-09, pixel size 38 with stretch 83 gives advance 16 and height 39]"""
    height = max(1, round(text * stretch * scale))
    return max(1, round(100 * text * scale / height))


def set_stretch(root, percent):
    """Give the page's widgets the font stretch `percent`, after the style sheet is set. A style sheet cannot carry a
    stretch, and a widget keeps the stretch it was first given (its style sheet's font is resolved against its own, stale
    one), so a rescale sets it on each widget rather than on the page. [confirmed: measured, offscreen Qt: after
    `root.setFont`, a child kept 84 % when the page was set to 82 %] A widget made after the rescale (a key bar's items, a
    list's rows) starts from the application's font, so that carries the stretch too. [confirmed: the journey's
    FriendlyScreen key items had 84 % on a page that wanted 83 %, T209]"""
    app = QApplication.instance()
    if app is not None and app.font().stretch() != percent:
        font = app.font()
        font.setStretch(percent)
        app.setFont(font)
    for widget in [root, *root.findChildren(QWidget)]:
        font = widget.font()
        if font.stretch() != percent:
            font.setStretch(percent)
            widget.setFont(font)


def _own(widget):
    """Widgets the page composes (Qt's internal parts carry qt_ names and scale by their style)."""
    return not widget.objectName().startswith('qt_') and not widget.isWindow()


def record(root):
    """Remember the page lengths that the scale multiplies, as composed for 1440x900."""
    for layout in [root.layout(), *root.findChildren(QLayout)]:
        if layout is None or layout.property('pageMetrics') is not None:continue
        m = layout.contentsMargins()
        spacing = ((layout.horizontalSpacing(), layout.verticalSpacing()) if isinstance(layout, QGridLayout)
                   else (layout.spacing(), layout.spacing()))
        layout.setProperty('pageMetrics', [m.left(), m.top(), m.right(), m.bottom(), *spacing])
    for widget in root.findChildren(QWidget):
        if not _own(widget) or widget.property('pageSize') is not None:continue
        low, high = widget.minimumSize(), widget.maximumSize()
        if low != QSize(0, 0) or high != QSize(UNBOUNDED, UNBOUNDED):
            widget.setProperty('pageSize', [low.width(), low.height(), high.width(), high.height()])
        if isinstance(widget, QTableView) and widget.property('pageRow') is None:
            widget.setProperty('pageRow', widget.verticalHeader().defaultSectionSize())


def apply(root, scale, sheet, stretch=1.0, text=None):
    """Multiply every recorded length of the page by `scale` (vertical ones also by `stretch`) and restyle it.

    On a stretched page (`stretch` != 1, `text` the logical pixel size of its one text size) the page also sets the font
    stretch that keeps a glyph one cell wide (`set_stretch`)."""
    sy = scale * stretch
    for layout in [root.layout(), *root.findChildren(QLayout)]:
        metrics = layout.property('pageMetrics') if layout is not None else None
        if metrics is None:continue
        left, top, right, bottom, horizontal, vertical = metrics
        layout.setContentsMargins(px(left, scale), px(top, sy), px(right, scale), px(bottom, sy))
        if isinstance(layout, QGridLayout):
            if horizontal >= 0:layout.setHorizontalSpacing(px(horizontal, scale))
            if vertical >= 0:layout.setVerticalSpacing(px(vertical, sy))
        elif horizontal >= 0:
            down = isinstance(layout, QBoxLayout) and layout.direction() in (QBoxLayout.Direction.TopToBottom,
                                                                           QBoxLayout.Direction.BottomToTop)
            layout.setSpacing(px(horizontal, sy if down else scale))
    for widget in root.findChildren(QWidget):
        size = widget.property('pageSize')
        if size is not None:
            low_w, low_h, high_w, high_h = size
            widget.setMinimumSize(px(low_w, scale), px(low_h, sy))
            widget.setMaximumSize(UNBOUNDED if high_w == UNBOUNDED else px(high_w, scale),
                                  UNBOUNDED if high_h == UNBOUNDED else px(high_h, sy))
        row = widget.property('pageRow')
        if row is not None:widget.verticalHeader().setDefaultSectionSize(px(row, sy))
    root.setStyleSheet(scale_sheet(sheet, scale, stretch))
    if stretch != 1.0 and text:set_stretch(root, text_stretch(scale, stretch, text))
    # Every size hint follows the new type and lengths, hidden views included.
    for widget in root.findChildren(QWidget):
        widget.updateGeometry()
        if getattr(widget, 'page_painted', False):widget.update()
    for layout in [root.layout(), *root.findChildren(QLayout)]:
        if layout is not None:layout.invalidate()
    # A table's columns sized to their contents follow the new type.
    for table in root.findChildren(QTableView):
        table.resizeColumnsToContents()


class FixedPage(QWidget):
    """[designed: T101] The window's central widget: the page, scaled to fit and centred on black.

    [designed: T209] `logical` is the page's size in page pixels (1440x900 by default; the 4:3 window's is 1440x896).
    With `aspect` (4, 3) the page's rectangle is the largest whole-pixel 4:3 rectangle in the window, so it is 4:3 at any size
    and the window letterboxes the rest; its scale is the rectangle's width over the logical width, vertical lengths are
    multiplied by `stretch` (1.2) as well, and `text` is the logical pixel size of the one text size. The stretched content
    (896 x 1.2 = 1075.2 logical rows) is half a per cent shorter than the 4:3 rectangle (1080); the layout takes up the
    difference, never the cell."""

    def __init__(self, page, sheet, window, logical=(WIDTH, HEIGHT), stretch=1.0, text=None, aspect=None):
        super().__init__()
        self.setObjectName('fixedPage');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.page = page;self.sheet = sheet;self.window_ = window;self.scale = None
        self.logical = tuple(logical);self.stretch = stretch;self.text = text;self.aspect = aspect
        window.setProperty('pageStretch', stretch)
        page.setParent(self);record(page)
        self.fit()

    def sizeHint(self):
        return QSize(*self.page_size(*self.full_size())[:2])

    def full_size(self):
        """The window area at scale 1: the logical page, its height stretched, or the 4:3 rectangle round it."""
        if self.aspect is None:
            return round(self.logical[0]), round(self.logical[1] * self.stretch)
        return self.logical[0], round(self.logical[0] * self.aspect[1] / self.aspect[0])

    def page_size(self, width, height):
        """(page width, page height, scale) in an area of `width` x `height`."""
        if self.aspect is None:
            full_w, full_h = self.full_size()
            scale = min(width / full_w, height / full_h)
            return round(full_w * scale), round(full_h * scale), scale
        unit = max(1, min(width // self.aspect[0], height // self.aspect[1]))
        w, h = unit * self.aspect[0], unit * self.aspect[1]
        return w, h, w / self.logical[0]

    def minimumSizeHint(self):
        # Any window size is allowed: a small window shows the whole page smaller.
        return QSize(1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.fit()

    def fit(self):
        width, height = max(1, self.width()), max(1, self.height())
        w, h, scale = self.page_size(width, height)
        if self.scale is None or abs(scale - self.scale) > 1e-4:
            self.scale = scale;self.window_.setProperty('pageScale', scale)
            apply(self.page, scale, self.sheet, self.stretch, self.text)
        self.page.setGeometry((width - w) // 2, (height - h) // 2, w, h)
        # Settle the page's layout at once, so a page shown after a resize already has its geometry.
        from PySide6.QtCore import QCoreApplication, QEvent
        for _ in range(3):QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)

    def restyle(self, sheet):
        """A new style sheet for the page, at the present scale."""
        self.sheet = sheet;apply(self.page, self.scale, sheet, self.stretch, self.text)


def host(window):
    return window.centralWidget() if isinstance(window.centralWidget(), FixedPage) else None


def _name(widget):
    return widget.objectName() or widget.accessibleName() or type(widget).__name__


def problems(window):
    """[designed: T101] The no-scroll check at the window's present size; [] when it passes.

    No scroll bar is visible; every visible widget lies inside the page and inside its parent;
    no widget is squeezed below the size its content needs (a word-wrapped label is as tall as
    its text at its width); the page keeps its aspect and lies inside the window."""
    found = []
    frame = host(window)
    if frame is None:
        # A window without the fixed page is checked as it is, its central widget as the page.
        found.append('the window has no fixed page')
        page = window.centralWidget()
    else:
        page = frame.page
        scale = frame.scale
        if not frame.rect().contains(page.geometry()):
            found.append(f'page {page.geometry().getRect()} outside the window area {frame.rect().getRect()}')
        want_w, want_h, _ = frame.page_size(frame.width(), frame.height())
        if abs(page.width() - want_w) > 1 or abs(page.height() - want_h) > 1:
            found.append(f'page {page.width()}x{page.height()} is not {want_w}x{want_h} '
                         f'({frame.logical[0]}x{frame.logical[1]} at scale {scale:.4f}, stretch {frame.stretch})')
    bounds = page.rect()
    for widget in page.findChildren(QWidget):
        if widget.isWindow() or not widget.isVisible():continue
        name = _name(widget)
        if isinstance(widget, QScrollBar):
            found.append(f'scroll bar visible: {_name(widget.parentWidget().parentWidget() or widget)}')
            continue
        rect = QRect(widget.mapTo(page, QPoint(0, 0)), widget.size())
        if not bounds.contains(rect):
            found.append(f'{name} {rect.getRect()} outside the page {bounds.getRect()}')
        parent = widget.parentWidget()
        if parent is not None and parent is not page and not parent.rect().contains(widget.geometry()):
            found.append(f'{name} {widget.geometry().getRect()} clipped by {_name(parent)} {parent.rect().getRect()}')
        if not _own(widget) or widget.sizePolicy().horizontalPolicy() == widget.sizePolicy().Policy.Ignored:
            continue
        if isinstance(widget, QLabel) and widget.wordWrap():
            need = widget.heightForWidth(widget.width())
            if need > widget.height():
                found.append(f'{name} text needs {need} px, has {widget.height()}')
            continue
        if isinstance(widget, (QAbstractScrollArea, QStackedWidget)):continue
        hint = widget.minimumSizeHint()
        if hint.isValid() and (widget.width() < hint.width() or widget.height() < hint.height()):
            found.append(f'{name} {widget.width()}x{widget.height()} squeezed below {hint.width()}x{hint.height()}')
    return found
