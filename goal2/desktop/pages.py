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
    self.new=QPushButton('New campaign');self.new.setObjectName('newCampaign')
    self.friendly=QPushButton('New standalone friendly');
    country_bar.addWidget(QLabel('Country'));country_bar.addWidget(self.country,1);header.addLayout(country_bar)
    layout=self.pages[0].content
    layout.addWidget(self.new);layout.addWidget(self.friendly)
    self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
    self.standings_dialog=None
    self.standings=QPushButton('Competition table');self.standings.setObjectName('showStandings')
    self.pages[3].content.addWidget(self.standings)
    layout=self.pages[1].content
    self.table=QTableWidget(20,7);self.table.setObjectName('squad')
    self.table.setHorizontalHeaderLabels(['XI','Player','Position','Ability','Energy','Confidence','Availability'])
    self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
    self.table.setTabKeyNavigation(False);self.table.setMinimumHeight(300);layout.addWidget(self.table)
    layout=self.pages[2].content
    pool_panel=QWidget();pool_layout=QVBoxLayout(pool_panel);self.pool_panel=pool_panel
    self.pool_summary=QLabel();self.pool_summary.setWordWrap(True);pool_layout.addWidget(self.pool_summary)
    filter_bar=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search reserve name')
    self.position=QComboBox();self.position.addItem('All position codes',None)
    for code in range(14):self.position.addItem(f'Position code {code}',code)
    filter_bar.addWidget(self.search,1);filter_bar.addWidget(self.position);pool_layout.addLayout(filter_bar)
    self.reserves=QTableWidget(0,7);self.reserves.setObjectName('reserves')
    self.reserves.setHorizontalHeaderLabels(['ID','Player','Position','Ability','Energy','Confidence','Availability'])
    self.reserves.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.reserves.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    self.reserves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.reserves.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
    pool_layout.addWidget(self.reserves,1)
    self.exchange=QPushButton('Exchange selected squad player and reserve');pool_layout.addWidget(self.exchange)
    self.reserves.setTabKeyNavigation(False);self.reserves.setMinimumHeight(300);layout.addWidget(pool_panel)
    layout=self.pages[1].content
    captain_bar=QHBoxLayout();captain_bar.addWidget(QLabel('Captain'));self.captain=QComboBox();self.captain.setObjectName('captain');captain_bar.addWidget(self.captain,1)
    self.confirm=QPushButton('Confirm management');self.confirm.setObjectName('confirm');self.cancel=QPushButton('Discard draft')
    captain_bar.addWidget(self.cancel);captain_bar.addWidget(self.confirm);layout.addLayout(captain_bar)
    self.tactics=[]
    tactics=QGridLayout()
    for index,(element,label) in enumerate(TACTICS):
        box=QCheckBox(label);box.setObjectName(f'tactic{element}')
        self.tactics.append((element,box));tactics.addWidget(box,index//2,index%2,Qt.AlignmentFlag.AlignLeft)
    layout.addLayout(tactics)
    layout=self.pages[4].content
    save_bar=QHBoxLayout();save_bar.addWidget(QLabel('Save file'));self.path=QLineEdit(str(model.save_path));self.path.setObjectName('savePath');save_bar.addWidget(self.path,1)
    self.save=QPushButton('Save');self.save.setObjectName('save');self.resume=QPushButton('Resume');self.resume.setObjectName('resume');save_bar.addWidget(self.save);save_bar.addWidget(self.resume);layout.addLayout(save_bar)
    layout=self.pages[3].content
    play_bar=QHBoxLayout();self.play=QPushButton('Play quick friendly');self.stop=QPushButton('Cancel match');self.stop.setEnabled(False)
    self.watch=QPushButton('Watch original friendly');self.watch.setObjectName('watchOriginal')
    play_bar.addWidget(self.play);play_bar.addWidget(self.watch);layout.addLayout(play_bar)
    half_bar=QHBoxLayout();self.half_out=QComboBox();self.half_in=QComboBox()
    self.substitute=QPushButton('Substitute');self.continue_match=QPushButton('Continue second half')
    half_bar.addWidget(QLabel('Off'));half_bar.addWidget(self.half_out);half_bar.addWidget(QLabel('On'));half_bar.addWidget(self.half_in)
    half_bar.addWidget(self.substitute);half_bar.addWidget(self.continue_match)
    for widget in (self.half_out,self.half_in,self.substitute,self.continue_match):widget.setEnabled(False)
    layout.addLayout(half_bar);self.half_preview=None
    self.result=QLabel();self.result.setWordWrap(True);self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.result)
    self.status=QLabel('Confirm management, then play a quick friendly or save.');self.status.setWordWrap(True);self.status.setObjectName('status');footer.addWidget(self.status,1);footer.addWidget(self.stop)
    for page in self.pages:page.content.addStretch()
    self.save_shortcut=QShortcut(QKeySequence('Ctrl+S'),self)
    self.save_shortcut.activated.connect(self.save.click)
    for widget in self.findChildren(QWidget):
        if isinstance(widget,(QPushButton,QComboBox,QLineEdit,QCheckBox)):
            if not widget.accessibleName():widget.setAccessibleName(widget.text() if hasattr(widget,'text') else widget.objectName())
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
