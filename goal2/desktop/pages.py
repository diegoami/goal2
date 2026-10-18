"""[designed: T74] Native page containers; the window retains all action ownership."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut,QKeySequence
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QScrollArea,QStackedWidget,QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)
from goal2.desktop.style import apply_style

DESTINATIONS=('Overview','Squad & tactics','National pool','Fixtures & results','Save / resume')

class ShellPage(QScrollArea):
    """[designed] One vertical content scroll region per destination."""
    def __init__(self,name,index):
        super().__init__();self.setObjectName(f'page{index+1}')
        self.setWidgetResizable(True);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        panel=QWidget();self.setWidget(panel);self.content=QVBoxLayout(panel)
        self.content.setContentsMargins(24,16,24,24);self.content.setSpacing(12)
        self.heading=QLabel(name);self.heading.setObjectName('pageHeading')
        self.heading.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.heading.setAccessibleName(name)
        self.content.addWidget(self.heading)

def compose(self,model,TACTICS):
    self.setWindowTitle('goal2 — Country management');self.resize(1050,780)
    root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
    layout.setContentsMargins(16,12,16,12);layout.setSpacing(12)
    header=QVBoxLayout();layout.addLayout(header)
    self.page_stack=QStackedWidget();self.page_stack.setObjectName('pageStack')
    self.pages=[ShellPage(name,i) for i,name in enumerate(DESTINATIONS)]
    self.navigation=[];self.navigation_shortcuts=[]
    nav=QHBoxLayout();nav.setSpacing(4);layout.addLayout(nav)
    for i,name in enumerate(DESTINATIONS):
        button=QPushButton(name.replace('&','&&'));button.setObjectName(f'nav{i+1}')
        button.setAccessibleName(name);button.setCheckable(True)
        button.clicked.connect(lambda checked=False,index=i:self.navigate(index))
        nav.addWidget(button);self.navigation.append(button);self.page_stack.addWidget(self.pages[i])
        shortcut=QShortcut(QKeySequence(f'Ctrl+{i+1}'),self)
        shortcut.activated.connect(lambda index=i:self.navigate(index));self.navigation_shortcuts.append(shortcut)
    layout.addWidget(self.page_stack,1)
    footer=QHBoxLayout();layout.addLayout(footer)
    self.title=QLabel();self.title.setObjectName('countryTitle')
    header.addWidget(self.title)
    self.context=QLabel();self.context.setObjectName('countryContext');header.addWidget(self.context)
    country_bar=QHBoxLayout();self.country=QComboBox();self.country.setObjectName('country')
    for number,name in model.view()['countries']:self.country.addItem(name,number)
    country_bar.addWidget(QLabel('Country'));country_bar.addWidget(self.country,1);header.addLayout(country_bar)
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
    order=[self.country,*self.navigation]
    for page in self.pages:
        order.append(page.heading)
        order.extend(w for w in page.findChildren(QWidget) if isinstance(w,(QPushButton,QComboBox,QLineEdit,QCheckBox,QTableWidget)))
    order.append(self.stop)
    for first,second in zip(order,order[1:]):QWidget.setTabOrder(first,second)
    apply_style(self);self.navigate(0)
