"""[designed: T75] Displayed-country overview; the window owns every action."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame,QVBoxLayout,QGridLayout,QLabel,QPushButton,QWidget


def card(layout,title,name):
    panel=QFrame();panel.setObjectName('overviewCard');body=QVBoxLayout(panel)
    body.setContentsMargins(20,16,20,16);body.setSpacing(8)
    heading=QLabel(title);heading.setObjectName('cardHeading');body.addWidget(heading)
    text=QLabel();text.setObjectName(name);text.setWordWrap(True)
    text.setTextFormat(Qt.TextFormat.PlainText)
    text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    body.addWidget(text);layout.addWidget(panel)
    return text


def panel(title,name):
    """[designed: T91; accepted vision #266 screen 02] A red-titled framed panel of value lines."""
    frame=QFrame();frame.setObjectName('deskPanel');body=QVBoxLayout(frame)
    body.setContentsMargins(16,12,16,12);body.setSpacing(6)
    heading=QLabel(title);heading.setObjectName('deskHeading');body.addWidget(heading)
    text=QLabel();text.setObjectName(name);text.setWordWrap(True);text.setTextFormat(Qt.TextFormat.PlainText)
    text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);body.addWidget(text)
    return frame,body,text


def build(self,model,TACTICS):
    page=self.pages[0]
    from goal2.desktop.roster import RosterView
    from PySide6.QtWidgets import QHBoxLayout,QComboBox
    # [designed: T101] The Country page has three views on the fixed page: 0 the desk, 1 the
    # country card (Country card), 2 other games (Other games: browse another country, start a
    # new campaign or friendly, return to the active game). Esc returns to the desk.
    self.country_views,(desk_box,card_box,games_box)=page.add_views('countryViews',('countryDesk','countryCardView','countryGames'))
    self.country_views.show_view=lambda index:country_view(self,index)
    # [designed: T91; accepted vision #266 screen 02] Your country, next opponent and campaign;
    # the direct routes with the last result; the twenty. Three columns.
    # [designed: T101] Your country, opponent and campaign on the left; readiness, captain and the
    # last result beside them; the routes in a grid below both; the twenty on the right.
    desk=QHBoxLayout();desk.setSpacing(16);desk_box.addLayout(desk,1)
    work=QVBoxLayout();work.setSpacing(8);desk.addLayout(work,1)
    columns=QHBoxLayout();columns.setSpacing(16);work.addLayout(columns,1)
    routes=QGridLayout();routes.setSpacing(8);work.addLayout(routes)
    left=QVBoxLayout();left.setSpacing(10);holder=QWidget();holder.setLayout(left);columns.addWidget(holder,3)
    own,own_body,self.desk_own=panel('YOUR COUNTRY','deskOwn')
    self.overview_country_identity=QLabel();self.overview_country_identity.setObjectName('overviewCountry')
    self.overview_country_identity.setTextFormat(Qt.TextFormat.PlainText);self.overview_country_identity.setWordWrap(True)
    own_body.insertWidget(1,self.overview_country_identity);left.addWidget(own)
    opponent,opponent_body,self.desk_opponent=panel('NEXT OPPONENT','deskOpponent')
    self.overview_fixture=QLabel();self.overview_fixture.setObjectName('overviewFixture');self.overview_fixture.setWordWrap(True)
    self.overview_fixture.setTextFormat(Qt.TextFormat.PlainText);opponent_body.addWidget(self.overview_fixture);left.addWidget(opponent)
    campaign,_,self.desk_campaign=panel('YOUR CAMPAIGN','deskCampaign');left.addWidget(campaign)
    left.addStretch(1)
    middle=QVBoxLayout();middle.setSpacing(8);holder=QWidget();holder.setLayout(middle);columns.addWidget(holder,2)
    self.desk_routes=[]
    for text,name,index in (('Prepare match','deskPrepare',3),('Select squad','deskTeam',1),('Pool','deskPool',2),('Fixture list','deskFixtures',3)):
        button=QPushButton(text);button.setObjectName(name);button.setAccessibleName(text)
        button.clicked.connect(lambda checked=False,i=index:self.navigate(i));self.desk_routes.append(button)
    self.desk_routes[0].clicked.connect(lambda:self.fixtures_view(0))
    self.desk_routes[3].clicked.connect(lambda:self.fixtures_view(3))
    self.desk_card=QPushButton('Country card >');self.desk_card.setObjectName('deskCard')
    self.desk_card.setAccessibleName('Show the country card')
    self.desk_card.clicked.connect(lambda:country_view(self,1))
    self.desk_manager=QPushButton('Manager name');self.desk_manager.setObjectName('deskManager')
    self.desk_manager.setAccessibleName('Change the manager name');self.desk_manager.clicked.connect(self.rename_manager)
    self.desk_games=QPushButton('Other games >');self.desk_games.setObjectName('deskGames')
    self.desk_games.setAccessibleName('Browse another country or start another game')
    self.desk_games.clicked.connect(lambda:country_view(self,2))
    self.desk_readiness=QLabel();self.desk_readiness.setObjectName('deskReadiness');self.desk_readiness.setWordWrap(True);middle.addWidget(self.desk_readiness)
    self.desk_captain=QLabel();self.desk_captain.setObjectName('deskCaptain');self.desk_captain.setWordWrap(True);middle.addWidget(self.desk_captain)
    result,_,self.overview_result=panel('LAST RESULT','overviewResult');middle.addWidget(result)
    middle.addStretch(1)
    for number,button in enumerate((*self.desk_routes,self.desk_card,self.desk_manager,self.desk_games)):
        routes.addWidget(button,number//4,number%4)
    self.country_roster=RosterView('SQUAD',toggles=False);self.country_roster.setFixedWidth(320);self.country_roster.setAccessibleDescription('Enter: open this player on Team')
    desk.addWidget(self.country_roster,0,Qt.AlignmentFlag.AlignTop)
    # Enter on a player opens the Team page on him; the desk never changes the XI.
    self.country_roster.activated.connect(lambda row:(self.navigate(1),self.table.setCurrentCell(row,1)))
    self.summary=QLabel();self.summary.setObjectName('deskSummary');self.summary.setWordWrap(True);desk_box.addWidget(self.summary)
    # View 1: the T89 country card of the displayed country.
    from goal2.desktop.country_card import CountryCardView
    self.country_card_view=CountryCardView();card_box.addWidget(self.country_card_view,0,Qt.AlignmentFlag.AlignLeft)
    self.country_card_back=QPushButton('< Desk (Esc)');self.country_card_back.setObjectName('countryCardBack')
    self.country_card_back.setAccessibleName('Back to the desk');self.country_card_back.clicked.connect(lambda:country_view(self,0))
    card_box.addWidget(self.country_card_back,0,Qt.AlignmentFlag.AlignLeft);card_box.addStretch(1)
    # View 2: other games. [designed: T90] The browse selector is a Country-page control.
    title=QLabel('OTHER GAMES');title.setObjectName('deskHeading');games_box.addWidget(title)
    country_bar=QHBoxLayout();self.country=QComboBox();self.country.setObjectName('country')
    for number,name in model.view()['countries']:self.country.addItem(name,number)
    country_bar.addWidget(QLabel('Browse another country (preview only)'));country_bar.addWidget(self.country,1)
    games_box.addLayout(country_bar)
    self.overview_return=QPushButton('Return to active game');self.overview_return.setObjectName('returnActive')
    self.overview_return.clicked.connect(lambda:self.country.setCurrentIndex(self.country.findData(self.model.state.managed_country)))
    games_box.addWidget(self.overview_return)
    from goal2.desktop.model import START_YEARS
    # [designed: owner, 2026-10-20, T50] Draft only; New campaign reads it.
    self.start_year=QComboBox();self.start_year.setObjectName('startYear');self.start_year.setAccessibleName('Start year')
    for year,label in START_YEARS:self.start_year.addItem(label,year)
    year_bar=QHBoxLayout();year_bar.addWidget(QLabel('Start year'));year_bar.addWidget(self.start_year,1);games_box.addLayout(year_bar)
    self.new=QPushButton('New campaign');self.new.setObjectName('newCampaign')
    self.friendly=QPushButton('New standalone friendly');self.friendly.setObjectName('newFriendly')
    games_box.addWidget(self.new);games_box.addWidget(self.friendly)
    games_back=QPushButton('< Desk (Esc)');games_back.setObjectName('gamesBack');games_back.setAccessibleName('Back to the desk')
    games_back.clicked.connect(lambda:country_view(self,0));games_box.addWidget(games_back);games_box.addStretch(1)
    from PySide6.QtGui import QKeySequence,QShortcut
    self.country_escape=QShortcut(QKeySequence('Escape'),page)
    self.country_escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    self.country_escape.activated.connect(lambda:self.country_views.currentIndex()!=0 and country_view(self,0))


def country_view(self,index):
    """[designed: T101] Show Country view `index` (0 desk, 1 country card, 2 other games) with its
    first control focused; presentation only."""
    self.country_views.setCurrentIndex(index)
    if index==1:refresh_card(self)
    if self.page_stack.currentIndex()!=0:return
    target={0:self.desk_routes[0],1:self.country_card_back,2:self.country}[index]
    if not target.isEnabled():target=self.pages[0].heading
    target.setFocus(Qt.FocusReason.ShortcutFocusReason)


def ranks(display,country):
    """[confirmed: F007 via goal2.game.country_card] World rank, continent, rank within it."""
    from goal2.game.country_card import card
    c=card(display.state,country,display.goaldat)
    return c['world'],c['continent'],c['continental']


def refresh_card(self):
    from goal2.game.country_card import card
    display=self.display_model;state=display.state
    self.country_card_view.set_card(card(state,state.managed_country,display.goaldat))


def refresh(self,display,view):
    """[designed] Use the same displayed model as the roster, including previews."""
    from goal2.game.watched_schema import watched
    self.overview_country_identity.setText(view['country_name'])
    from goal2.desktop.fixtures_page import qualifying_text
    finished=display.state.campaign is not None and display.state.campaign.next_fixture is None
    self.overview_fixture.setText(view['fixture'] or ('Standalone friendly / no campaign fixture' if display.state.campaign is None else
        # [designed: T50] A finished stage names its outcome instead of an unsupported fixture.
        'Stage complete; the next stage is not available yet\n'+qualifying_text(display) if finished else 'No supported fixture'))
    match=display.state.last_match
    provenance=('Original engine' if watched(match) else 'Quick simulation (rebuild setup)') if match else 'No result yet'
    self.overview_result.setText(provenance+'\n'+display.result_text())
    state=display.state;names=display.goaldat.country_names
    world,continent,rank=ranks(display,state.managed_country)
    manager=display.summary()['manager'].split(' (')[0]
    self.desk_own.setText(f'Manager  {manager}\nWorld    {world:>3}\n{continent:<8} {rank:>3}')
    fixture=state.campaign.next_fixture if state.campaign else None
    if fixture is None:
        self.desk_opponent.setText('No scheduled opponent')
    else:
        opponent=fixture.side_b if fixture.side_a==state.managed_country else fixture.side_a
        world,continent,rank=ranks(display,opponent)
        self.desk_opponent.setText(f'{names[opponent].upper()}\nWorld    {world:>3}\n{continent:<8} {rank:>3}')
    summary=display.summary()
    lines=[summary['campaign'],'Next: '+summary['next']]
    qualifying=display.qualifying() if state.campaign is not None else None
    if qualifying:lines.append(qualifying['text'])
    self.desk_campaign.setText('\n'.join(lines))
    if self.country_views.currentIndex()==1:refresh_card(self)
    self.identity_art.setAccessibleName('Generic shirt and neutral decorative stripe for '+view['country_name'])
