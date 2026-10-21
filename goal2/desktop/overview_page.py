"""[designed: T75] Displayed-country overview; the window owns every action."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame,QVBoxLayout,QLabel,QPushButton,QWidget


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
    layout=self.pages[0].content
    from goal2.desktop.roster import Columns,RosterView
    # [designed: T91; accepted vision #266 screen 02] Your country, next opponent and campaign;
    # the direct routes; the twenty. Three columns when wide, stacked when narrow.
    desk=Columns(1000);desk.setObjectName('countryDesk');layout.insertWidget(1,desk)
    left=QVBoxLayout();left.setSpacing(12);holder=QWidget();holder.setLayout(left);desk.box.addWidget(holder,3)
    own,own_body,self.desk_own=panel('YOUR COUNTRY','deskOwn')
    self.overview_country_identity=QLabel();self.overview_country_identity.setObjectName('overviewCountry')
    self.overview_country_identity.setTextFormat(Qt.TextFormat.PlainText);self.overview_country_identity.setWordWrap(True)
    own_body.insertWidget(1,self.overview_country_identity);left.addWidget(own)
    opponent,opponent_body,self.desk_opponent=panel('NEXT OPPONENT','deskOpponent')
    self.overview_fixture=QLabel();self.overview_fixture.setObjectName('overviewFixture');self.overview_fixture.setWordWrap(True)
    self.overview_fixture.setTextFormat(Qt.TextFormat.PlainText);opponent_body.addWidget(self.overview_fixture);left.addWidget(opponent)
    campaign,_,self.desk_campaign=panel('YOUR CAMPAIGN','deskCampaign');left.addWidget(campaign)
    result,_,self.overview_result=panel('LAST RESULT','overviewResult');left.addWidget(result)
    left.addStretch(1)
    middle=QVBoxLayout();middle.setSpacing(12);holder=QWidget();holder.setLayout(middle);desk.box.addWidget(holder,2)
    self.desk_routes=[]
    for text,name,index in (('Prepare match','deskPrepare',3),('Select squad','deskTeam',1),('Pool','deskPool',2),('Fixture list','deskFixtures',3)):
        button=QPushButton(text);button.setObjectName(name);button.setAccessibleName(text)
        button.clicked.connect(lambda checked=False,i=index:self.navigate(i));middle.addWidget(button);self.desk_routes.append(button)
    self.desk_card=QPushButton('Country card');self.desk_card.setObjectName('deskCard');self.desk_card.setCheckable(True)
    self.desk_card.setAccessibleName('Show the country card');middle.addWidget(self.desk_card)
    self.desk_manager=QPushButton('Manager name');self.desk_manager.setObjectName('deskManager')
    self.desk_manager.setAccessibleName('Change the manager name');self.desk_manager.clicked.connect(self.rename_manager)
    middle.addWidget(self.desk_manager)
    self.desk_readiness=QLabel();self.desk_readiness.setObjectName('deskReadiness');self.desk_readiness.setWordWrap(True);middle.addWidget(self.desk_readiness)
    self.desk_captain=QLabel();self.desk_captain.setObjectName('deskCaptain');self.desk_captain.setWordWrap(True);middle.addWidget(self.desk_captain)
    middle.addStretch(1)
    self.country_roster=RosterView('SQUAD',toggles=False);self.country_roster.setFixedWidth(320);self.country_roster.setAccessibleDescription('Enter: open this player on Team')
    desk.box.addWidget(self.country_roster,2,Qt.AlignmentFlag.AlignTop)
    # Enter on a player opens the Team page on him; the desk never changes the XI.
    self.country_roster.activated.connect(lambda row:(self.navigate(1),self.table.setCurrentCell(row,1)))
    from goal2.desktop.country_card import CountryCardView
    self.country_card_view=CountryCardView();self.country_card_view.hide();layout.insertWidget(2,self.country_card_view)
    self.desk_card.toggled.connect(lambda shown:(self.country_card_view.setVisible(shown),shown and refresh_card(self)))
    self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
    self.overview_return=QPushButton('Return to active game');self.overview_return.setObjectName('returnActive')
    self.overview_return.clicked.connect(lambda:self.country.setCurrentIndex(self.country.findData(self.model.state.managed_country)))
    layout.addWidget(self.overview_return)
    from PySide6.QtWidgets import QComboBox
    from goal2.desktop.model import START_YEARS
    # [designed: owner, 2026-10-20, T50] Draft only; New campaign reads it.
    self.start_year=QComboBox();self.start_year.setObjectName('startYear');self.start_year.setAccessibleName('Start year')
    for year,label in START_YEARS:self.start_year.addItem(label,year)
    layout.addWidget(QLabel('Start year'));layout.addWidget(self.start_year)
    self.new=QPushButton('New campaign');self.new.setObjectName('newCampaign')
    self.friendly=QPushButton('New standalone friendly');self.friendly.setObjectName('newFriendly')
    layout.addWidget(self.new);layout.addWidget(self.friendly)


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
    if self.desk_card.isChecked():refresh_card(self)
    self.identity_art.setAccessibleName('Generic shirt and neutral decorative stripe for '+view['country_name'])
