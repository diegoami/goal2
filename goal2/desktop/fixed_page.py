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

`problems(window)` is the no-scroll check every screen task uses: at the window's present size,
no scroll bar is visible, every visible widget lies inside the page, and no widget is clipped by
its parent or squeezed below the size its content needs.
"""
import re
from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import (QWidget, QLayout, QGridLayout, QBoxLayout, QScrollBar, QLabel,
                               QTableView, QAbstractScrollArea, QStackedWidget)

WIDTH, HEIGHT = 1440, 900
UNBOUNDED = 16777215
_PX = re.compile(r'(\d+(?:\.\d+)?)px')


def scale_of(widget):
    """The scale of the page `widget` is drawn on (1 for a widget outside a scaled window)."""
    window = widget.window() if widget is not None else None
    value = window.property('pageScale') if window is not None else None
    return float(value) if value else 1.0


def px(value, scale):
    """A page length at `scale`: rounded, and never 0 for a length that is not 0."""
    return 0 if not value else max(1, round(value * scale))


# The margin that gives a 3px focus border the room of a 2px border plus this margin: computed from
# the two rounded widths, so a focused control keeps its size at every scale.
FOCUS_MARGIN = '@focus-margin'


def scale_sheet(sheet, scale):
    """The style sheet with every pixel length multiplied by `scale`."""
    sheet = _PX.sub(lambda m: f'{px(float(m.group(1)), scale)}px', sheet)
    return sheet.replace(FOCUS_MARGIN, f'{px(3, scale) - px(2, scale)}px')


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


def apply(root, scale, sheet):
    """Multiply every recorded length of the page by `scale` and restyle it."""
    for layout in [root.layout(), *root.findChildren(QLayout)]:
        metrics = layout.property('pageMetrics') if layout is not None else None
        if metrics is None:continue
        left, top, right, bottom, horizontal, vertical = metrics
        layout.setContentsMargins(px(left, scale), px(top, scale), px(right, scale), px(bottom, scale))
        if isinstance(layout, QGridLayout):
            if horizontal >= 0:layout.setHorizontalSpacing(px(horizontal, scale))
            if vertical >= 0:layout.setVerticalSpacing(px(vertical, scale))
        elif horizontal >= 0:
            layout.setSpacing(px(horizontal, scale))
    for widget in root.findChildren(QWidget):
        size = widget.property('pageSize')
        if size is not None:
            low_w, low_h, high_w, high_h = size
            widget.setMinimumSize(px(low_w, scale), px(low_h, scale))
            widget.setMaximumSize(UNBOUNDED if high_w == UNBOUNDED else px(high_w, scale),
                                  UNBOUNDED if high_h == UNBOUNDED else px(high_h, scale))
        row = widget.property('pageRow')
        if row is not None:widget.verticalHeader().setDefaultSectionSize(px(row, scale))
    root.setStyleSheet(scale_sheet(sheet, scale))
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
    """[designed: T101] The window's central widget: the page, scaled to fit and centred on black."""

    def __init__(self, page, sheet, window):
        super().__init__()
        self.setObjectName('fixedPage');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.page = page;self.sheet = sheet;self.window_ = window;self.scale = None
        page.setParent(self);record(page)
        self.fit()

    def sizeHint(self):
        return QSize(WIDTH, HEIGHT)

    def minimumSizeHint(self):
        # Any window size is allowed: a small window shows the whole page smaller.
        return QSize(1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.fit()

    def fit(self):
        width, height = max(1, self.width()), max(1, self.height())
        scale = min(width / WIDTH, height / HEIGHT)
        if self.scale is None or abs(scale - self.scale) > 1e-4:
            self.scale = scale;self.window_.setProperty('pageScale', scale)
            apply(self.page, scale, self.sheet)
        w, h = round(WIDTH * scale), round(HEIGHT * scale)
        self.page.setGeometry((width - w) // 2, (height - h) // 2, w, h)
        # Settle the page's layout at once, so a page shown after a resize already has its geometry.
        from PySide6.QtCore import QCoreApplication, QEvent
        for _ in range(3):QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)

    def restyle(self, sheet):
        """A new style sheet for the page, at the present scale."""
        self.sheet = sheet;apply(self.page, self.scale, sheet)


def host(window):
    return window.centralWidget() if isinstance(window.centralWidget(), FixedPage) else None


def _name(widget):
    return widget.objectName() or widget.accessibleName() or type(widget).__name__


def problems(window):
    """[designed: T101] The no-scroll check at the window's present size; [] when it passes.

    No scroll bar is visible; every visible widget lies inside the page and inside its parent;
    no widget is squeezed below the size its content needs (a word-wrapped label is as tall as
    its text at its width); the page keeps the 1440x900 aspect and lies inside the window."""
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
        if abs(page.width() - WIDTH * scale) > 1 or abs(page.height() - HEIGHT * scale) > 1:
            found.append(f'page {page.width()}x{page.height()} is not 1440x900 at scale {scale:.4f}')
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
