"""[designed: T74] Native page containers; the window retains all action ownership."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut,QKeySequence
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QStackedWidget,QPushButton,
 QComboBox,QTableWidget,QLineEdit,QCheckBox)
from goal2.desktop.style import apply_style

# [designed: T90; accepted vision #266] The accepted navigation's names for the five existing pages.
DESTINATIONS=('Country','Team','Pool','Fixtures & match','Save')

class ShellPage(QWidget):
    """[designed: T101, superseding T74's scroll region] One destination of the fixed page: its
    heading and content, and an optional action bar at the bottom. Nothing in it scrolls; a part
    that does not fit is a view of the page reached by a route (`views`)."""
    def set_footer(self,footer):
        """[designed: T76] A fixed action area below the content."""
        self.footer=footer;self.outer.addWidget(footer)

    def __init__(self,name,index):
        super().__init__();self.setObjectName(f'page{index+1}')
        self.outer=QVBoxLayout(self);self.outer.setContentsMargins(0,0,0,0);self.outer.setSpacing(0)
        panel=QWidget();panel.setObjectName('pageContent');self.outer.addWidget(panel,1)
        self.content=QVBoxLayout(panel)
        self.content.setContentsMargins(20,6,20,8);self.content.setSpacing(8)
        self.heading=QLabel(name);self.heading.setObjectName('pageHeading')
        self.heading.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.heading.setAccessibleName(name)
        self.content.addWidget(self.heading)
        # [designed: T101] The page's views (a QStackedWidget) and the function that shows one.
        self.views=None;self.escape=None

    def add_views(self,name,names):
        """[designed: T101] The page's views: a stack holding one widget per name, each with a
        vertical layout; the page's owner sets the stack's `show_view(i)`. Returns the stack and
        the views' layouts."""
        stack=QStackedWidget();stack.setObjectName(name);self.content.addWidget(stack,1)
        boxes=[]
        for view in names:
            widget=QWidget();widget.setObjectName(view);box=QVBoxLayout(widget)
            box.setContentsMargins(0,0,0,0);box.setSpacing(8);stack.addWidget(widget);boxes.append(box)
        self.views=stack
        return stack,boxes

    def keyPressEvent(self,event):
        """[designed: T101] Esc, not taken by a control, leaves a view for the page's first one.
        A key event (not a window shortcut) never takes Esc from a dialog or a drop-down."""
        if event.key()==Qt.Key.Key_Escape and self.escape is not None and self.escape():
            event.accept();return
        super().keyPressEvent(event)

    def widget(self):
        """The content panel (the former scroll region's widget)."""
        return self.outer.itemAt(0).widget()


def compose(self,model,TACTICS):
    """[designed: T90; accepted vision #266 screens 02/03] Top bar, retractable side bar, pages.
    [designed: T101] All of it is one fixed page of 1440x900, scaled to the window."""
    from PySide6.QtWidgets import QFrame
    self.setWindowTitle('goal2');self.resize(1440,900)
    root=QWidget();root.setObjectName('shellRoot');layout=QVBoxLayout(root)
    layout.setContentsMargins(8,8,8,8);layout.setSpacing(8)
    # Top bar, one row: GOAL2, the country, the career line and context, the next fixture.
    self.top_bar=QFrame();self.top_bar.setObjectName('topBar');top=QHBoxLayout(self.top_bar)
    top.setContentsMargins(14,6,14,6);top.setSpacing(20)
    brand=QLabel('GOAL2');brand.setObjectName('brand');top.addWidget(brand,0,Qt.AlignmentFlag.AlignVCenter)
    self.title=QLabel();self.title.setObjectName('countryTitle');self.title.setWordWrap(True)
    top.addWidget(self.title,2,Qt.AlignmentFlag.AlignVCenter)
    identity_text=QVBoxLayout();identity_text.setSpacing(2);top.addLayout(identity_text,3)
    self.career_line=QLabel();self.career_line.setObjectName('careerLine');self.career_line.setWordWrap(True);identity_text.addWidget(self.career_line)
    self.context=QLabel();self.context.setObjectName('countryContext');self.context.setWordWrap(True);identity_text.addWidget(self.context)
    next_text=QVBoxLayout();next_text.setSpacing(2);top.addLayout(next_text,3)
    self.next_line=QLabel();self.next_line.setObjectName('nextLine');self.next_line.setWordWrap(True);next_text.addWidget(self.next_line)
    self.next_detail=QLabel();self.next_detail.setObjectName('nextDetail');self.next_detail.setWordWrap(True);next_text.addWidget(self.next_detail)
    self.hide_top=QPushButton('[Top ^]');self.hide_top.setObjectName('hideTop');self.hide_top.setAccessibleName('Hide top bar')
    top.addWidget(self.hide_top,0,Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(self.top_bar)
    self.show_top=QPushButton('[v Top]');self.show_top.setObjectName('showTop');self.show_top.setAccessibleName('Show top bar')
    self.show_side=QPushButton('[Menu >]');self.show_side.setObjectName('showSide');self.show_side.setAccessibleName('Show side bar')
    # A retracted bar leaves its handle, so the pages keep the full width: [Menu >] sits at the
    # start of the top bar, or in one short row with [v Top] when the top bar is retracted too.
    self.top_layout=top;self.handles=QHBoxLayout();self.handles.setSpacing(8);layout.addLayout(self.handles)
    for handle in (self.show_side,self.show_top):handle.hide();self.handles.addWidget(handle)
    self.handles.addStretch(1)
    body=QHBoxLayout();body.setSpacing(8);layout.addLayout(body,1)
    # Side bar: the destinations, retractable.
    self.side_bar=QFrame();self.side_bar.setObjectName('sideBar');side=QVBoxLayout(self.side_bar)
    side.setContentsMargins(8,8,8,8);side.setSpacing(10)
    self.hide_side=QPushButton('[< Hide]');self.hide_side.setObjectName('hideSide');self.hide_side.setAccessibleName('Hide side bar')
    side.addWidget(self.hide_side)
    self.page_stack=QStackedWidget();self.page_stack.setObjectName('pageStack')
    self.pages=[ShellPage(name,i) for i,name in enumerate(DESTINATIONS)]
    self.navigation=[];self.navigation_shortcuts=[]
    for i,name in enumerate(DESTINATIONS):
        button=QPushButton(name.replace('&','&&'));button.setObjectName(f'nav{i+1}')
        button.setAccessibleName(name);button.setCheckable(True)
        button.clicked.connect(lambda checked=False,index=i:self.navigate(index))
        side.addWidget(button);self.navigation.append(button);self.page_stack.addWidget(self.pages[i])
        shortcut=QShortcut(QKeySequence(f'Ctrl+{i+1}'),self)
        shortcut.activated.connect(lambda index=i:self.navigate(index));self.navigation_shortcuts.append(shortcut)
    side.addStretch(1)
    hint=QLabel('F11: bars');hint.setObjectName('sideHint');side.addWidget(hint)
    body.addWidget(self.side_bar)
    main=QVBoxLayout();main.setSpacing(8);body.addLayout(main,1)
    main.addWidget(self.page_stack,1)
    footer=QHBoxLayout();main.addLayout(footer)
    from goal2.desktop.country_identity import CountryIdentity
    # [designed: T90] The neutral identity art stays available to assistive names, out of the header.
    self.identity_art=CountryIdentity(root);self.identity_art.hide()
    self.hide_top.clicked.connect(lambda:self.set_bars(top=False))
    self.show_top.clicked.connect(lambda:self.set_bars(top=True))
    self.hide_side.clicked.connect(lambda:self.set_bars(side=False))
    self.show_side.clicked.connect(lambda:self.set_bars(side=True))
    self.bars_shortcut=QShortcut(QKeySequence('F11'),self)
    # [designed: accepted #266 "F11: hide top + side bars"] Both showing: hide both; otherwise restore both.
    def toggle_bars():
        show=not (self.top_bar.isVisible() and self.side_bar.isVisible());self.set_bars(top=show,side=show)
    self.bars_shortcut.activated.connect(toggle_bars)
    from goal2.desktop import overview_page,squad_page,pool_page,fixtures_page,save_page
    for module in (overview_page,squad_page,pool_page,fixtures_page,save_page):module.build(self,model,TACTICS)
    self.status=QLabel('Confirm management, then play a quick friendly or save.');self.status.setWordWrap(True);self.status.setObjectName('status');footer.addWidget(self.status,1);footer.addWidget(self.stop)
    for page in self.pages:page.content.addStretch()
    self.save_shortcut=QShortcut(QKeySequence('Ctrl+S'),self)
    self.save_shortcut.activated.connect(self.save.click)
    for widget in [*self.findChildren(QWidget),*root.findChildren(QWidget)]:
        if isinstance(widget,(QPushButton,QComboBox,QLineEdit,QCheckBox)):
            if not widget.accessibleName():widget.setAccessibleName(widget.text() if hasattr(widget,'text') else widget.objectName())
    self.table.setAccessibleName('Squad');self.reserves.setAccessibleName('National pool reserves')
    self.country.setAccessibleName('Country');self.search.setAccessibleName('Search reserve name')
    self.position.setAccessibleName('Reserve position');self.half_out.setAccessibleName('Halftime outgoing player')
    self.half_in.setAccessibleName('Halftime incoming player')
    order=[*self.navigation]
    for page in self.pages:
        order.append(page.heading)
        order.extend(w for w in page.findChildren(QWidget) if isinstance(w,(QPushButton,QComboBox,QLineEdit,QCheckBox,QTableWidget)))
    order.append(self.stop)
    for first,second in zip(order,order[1:]):QWidget.setTabOrder(first,second)
    from goal2.desktop.fixed_page import FixedPage
    sheet=apply_style(self);self.setCentralWidget(FixedPage(root,sheet,self));self.navigate(0)
