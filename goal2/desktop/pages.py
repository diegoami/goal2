"""[designed: T74] Native page containers; the window retains all action ownership."""
from PySide6.QtCore import Qt,QEvent
from PySide6.QtGui import QShortcut,QKeySequence
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QScrollArea,QStackedWidget,QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)
from goal2.desktop.style import apply_style

# [designed: T90; accepted vision #266] The accepted navigation's names for the five existing pages.
DESTINATIONS=('Country','Team','Pool','Fixtures & match','Save')

class ShellPage(QScrollArea):
    """[designed] One vertical content scroll region per destination."""
    def set_footer(self,footer):
        """[designed: T76] Reserve a fixed action area outside content scrolling."""
        self.footer=footer;footer.setParent(self);footer.show();self.place_footer()

    def place_footer(self):
        if not hasattr(self,'footer'):return
        height=self.footer.sizeHint().height()
        self.setViewportMargins(0,0,0,height)
        self.footer.setGeometry(0,self.height()-height,self.viewport().width(),height);self.footer.raise_()

    def viewportEvent(self,event):
        result=super().viewportEvent(event)
        if event.type()==QEvent.Type.Resize and hasattr(self,'footer'):
            self.footer.resize(self.viewport().width(),self.footer.height())
        return result

    def resizeEvent(self,event):
        super().resizeEvent(event);self.place_footer()

    def __init__(self,name,index):
        super().__init__();self.setObjectName(f'page{index+1}')
        self.setWidgetResizable(True);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        panel=QWidget();self.setWidget(panel);self.content=QVBoxLayout(panel)
        self.content.setContentsMargins(24,16,24,24);self.content.setSpacing(12)
        self.heading=QLabel(name);self.heading.setObjectName('pageHeading')
        self.heading.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.heading.setAccessibleName(name)
        self.content.addWidget(self.heading)

def compose(self,model,TACTICS):
    """[designed: T90; accepted vision #266 screens 02/03] Top bar, retractable side bar, pages."""
    from PySide6.QtWidgets import QFrame
    self.setWindowTitle('goal2');self.resize(1440,900)
    root=QWidget();root.setObjectName('shellRoot');self.setCentralWidget(root);layout=QVBoxLayout(root)
    layout.setContentsMargins(8,8,8,8);layout.setSpacing(8)
    # Top bar: GOAL2, the country and its context, the career line, the next fixture.
    self.top_bar=QFrame();self.top_bar.setObjectName('topBar');top=QHBoxLayout(self.top_bar)
    top.setContentsMargins(16,8,16,8);top.setSpacing(24)
    brand=QLabel('GOAL2');brand.setObjectName('brand');top.addWidget(brand,0,Qt.AlignmentFlag.AlignTop)
    identity_text=QVBoxLayout();top.addLayout(identity_text,2)
    self.title=QLabel();self.title.setObjectName('countryTitle');self.title.setWordWrap(True)
    identity_text.addWidget(self.title)
    self.career_line=QLabel();self.career_line.setObjectName('careerLine');self.career_line.setWordWrap(True);identity_text.addWidget(self.career_line)
    self.context=QLabel();self.context.setObjectName('countryContext');self.context.setWordWrap(True);identity_text.addWidget(self.context)
    next_text=QVBoxLayout();top.addLayout(next_text,2)
    self.next_line=QLabel();self.next_line.setObjectName('nextLine');self.next_line.setWordWrap(True);next_text.addWidget(self.next_line)
    self.next_detail=QLabel();self.next_detail.setObjectName('nextDetail');self.next_detail.setWordWrap(True);next_text.addWidget(self.next_detail)
    self.hide_top=QPushButton('[Top ^]');self.hide_top.setObjectName('hideTop');self.hide_top.setAccessibleName('Hide top bar')
    top.addWidget(self.hide_top,0,Qt.AlignmentFlag.AlignTop)
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
    # The country browse selector is a Country-page control now, not part of the header.
    country_bar=QHBoxLayout();self.country=QComboBox();self.country.setObjectName('country')
    for number,name in model.view()['countries']:self.country.addItem(name,number)
    country_bar.addWidget(QLabel('Browse another country (preview only)'));country_bar.addWidget(self.country,1)
    self.pages[0].content.addLayout(country_bar)
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
    for widget in self.findChildren(QWidget):
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
    apply_style(self);self.navigate(0)
