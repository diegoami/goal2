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
    card_row=QHBoxLayout();card_row.setSpacing(16);card_box.addLayout(card_row)
    self.country_card_view=CountryCardView();card_row.addWidget(self.country_card_view,0,Qt.AlignmentFlag.AlignTop)
    self.country_card_back=QPushButton('< Desk (Esc)');self.country_card_back.setObjectName('countryCardBack')
    self.country_card_back.setAccessibleName('Back to the desk');self.country_card_back.clicked.connect(lambda:country_view(self,0))
    card_row.addWidget(self.country_card_back,0,Qt.AlignmentFlag.AlignTop);card_row.addStretch(1);card_box.addStretch(1)
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
    def escape():
        if self.country_views.currentIndex()!=0:
            country_view(self,0);return True
        return False
    page.escape=escape



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


# -- the core route (T105) ------------------------------------------------------------------------------------
# [designed: owner, 2026-10-22, #321; T105] Over the core the Country page is the original's manager menu
# [confirmed: `docs/original-game/images/manager-menu.png`]: the name and rating, the team with its world and
# continent rankings, the next opponents with theirs and the fixture's kind, the managers 1-6, the menu's routes and
# the squad strip; its second view is the history (1771:1D5C) in the original's boxes. Everything is read through
# the CoreModel (goal2/core/views.py); nothing here touches the Python route's state.
# [T107] team info and select squad open the Team page (its team tactics and its squad). [T108] play next game runs
# the original's round (fixtures_page.CoreRound).
CORE_ROUTES = (('team info', 'coreTeamInfo', None), ('fixture list', 'coreFixtureList', None),
               ('tournament', 'coreTournament', None), ('history', 'coreHistory', None),
               ('select squad', 'coreSelectSquad', None), ('play next game', 'corePlay', None))


def build_core(self, model):
    from PySide6.QtWidgets import QHBoxLayout
    from goal2.desktop.roster import RosterView
    from goal2.desktop.core_window import TextBoard
    from goal2.desktop.core_model import DISABLED, DISABLED_TEXT
    page = self.pages[0]
    self.country_views, (desk_box, history_box) = page.add_views('countryViews', ('coreDesk', 'coreHistoryView'))
    self.country_views.show_view = lambda index: core_country_view(self, index)
    desk = QHBoxLayout();desk.setSpacing(16);desk_box.addLayout(desk)
    left = QVBoxLayout();left.setSpacing(10);desk.addLayout(left, 3)
    frame, _, self.core_name = panel('NAME / RATING', 'coreName');left.addWidget(frame)
    frame, body, self.core_team = panel('TEAM', 'deskOwn')
    self.core_team_name = QLabel();self.core_team_name.setObjectName('overviewCountry');body.insertWidget(1, self.core_team_name)
    left.addWidget(frame)
    frame, body, self.core_opponent = panel('NEXT OPPONENTS', 'deskOpponent')
    self.core_opponent_name = QLabel();self.core_opponent_name.setObjectName('overviewCountry')
    body.insertWidget(1, self.core_opponent_name)
    self.core_fixture_kind = QLabel();self.core_fixture_kind.setObjectName('deskCampaign');body.addWidget(self.core_fixture_kind)
    left.addWidget(frame);left.addStretch(1)
    middle = QVBoxLayout();middle.setSpacing(8);desk.addLayout(middle, 2)
    self.core_managers = TextBoard('MANAGERS', 18, 6, 'coreManagers', 17);middle.addWidget(self.core_managers)
    self.core_routes = {}
    for text, name, waits in CORE_ROUTES:
        label = text if waits is None else f'{text} · {DISABLED[waits]}'
        button = QPushButton(label);button.setObjectName(name);button.setAccessibleName(label)
        if waits is not None:
            button.setEnabled(False);button.setToolTip(DISABLED_TEXT[waits]);button.setAccessibleDescription(DISABLED_TEXT[waits])
        middle.addWidget(button);self.core_routes[text] = button
    self.core_routes['fixture list'].clicked.connect(lambda: (self.navigate(3), self.fixtures_view(0)))
    self.core_routes['tournament'].clicked.connect(lambda: (self.navigate(3), self.fixtures_view(1)))
    self.core_routes['history'].clicked.connect(lambda: core_country_view(self, 1))
    self.core_routes['team info'].clicked.connect(lambda: (self.navigate(1), self.team_views.show_view(1)))
    self.core_routes['select squad'].clicked.connect(lambda: (self.navigate(1), self.team_views.show_view(0)))
    self.core_routes['play next game'].clicked.connect(lambda: self.core_round.start())
    middle.addStretch(1)
    self.country_roster = RosterView('SQUAD', toggles=False, grouped=True, marks=False)
    self.country_roster.setFixedWidth(320);desk.addWidget(self.country_roster, 0, Qt.AlignmentFlag.AlignTop)
    # View 1: the history, in the original's boxes.
    top = QHBoxLayout();top.setSpacing(12);history_box.addLayout(top)
    self.core_statistics = TextBoard('STATISTICS', 46, 6, 'coreStatistics');top.addWidget(self.core_statistics)
    self.core_successes = TextBoard('SUCCESSES', 20, 3, 'coreSuccesses');top.addWidget(self.core_successes)
    top.addStretch(1)
    middle_row = QHBoxLayout();middle_row.setSpacing(12);history_box.addLayout(middle_row)
    self.core_results = TextBoard('RESULTS', 38, 10, 'coreResults');middle_row.addWidget(self.core_results)
    self.core_scorers = TextBoard('TOP SCORERS', 20, 10, 'coreTopScorers');middle_row.addWidget(self.core_scorers)
    self.core_caps = TextBoard('TOP CAPS', 20, 10, 'coreTopCaps');middle_row.addWidget(self.core_caps)
    middle_row.addStretch(1)
    bottom = QHBoxLayout();bottom.setSpacing(12);history_box.addLayout(bottom)
    self.core_records = TextBoard('RECORDS', 58, 3, 'coreRecords');bottom.addWidget(self.core_records)
    self.core_history_back = QPushButton('< Desk (Esc)');self.core_history_back.setObjectName('coreHistoryBack')
    self.core_history_back.clicked.connect(lambda: core_country_view(self, 0))
    bottom.addWidget(self.core_history_back, 0, Qt.AlignmentFlag.AlignTop);bottom.addStretch(1)
    history_box.addStretch(1)

    def escape():
        if self.country_views.currentIndex() != 0:
            core_country_view(self, 0);return True
        return False
    page.escape = escape


def core_country_view(self, index):
    """[designed: T105] Show Country view `index` (0 the desk, 1 the history); presentation only."""
    if self.page_stack.currentIndex() != 0:self.navigate(0)
    self.country_views.setCurrentIndex(index)
    (self.core_routes['fixture list'] if index == 0 else self.core_history_back).setFocus(Qt.FocusReason.ShortcutFocusReason)


def refresh_core(self, model, desk=None):
    from goal2.desktop.player_card import CYAN, GOLD, GREEN, WHITE, YELLOW
    from goal2.desktop.core_roles import role_code
    desk = model.desk() if desk is None else desk
    self.core_name.setText(f"{desk['manager']}\nrating  {desk['rating']}")
    team = desk['team']
    self.core_team_name.setText(team['name'])
    self.core_team.setText(f"World  : {team['world_rank']:>3}\n{team['continent']:<7}: {team['continent_rank']:>3}")
    opponent = desk['opponent']
    if opponent is None:
        self.core_opponent_name.setText('—');self.core_opponent.setText('No fixture');self.core_fixture_kind.setText('')
    else:
        self.core_opponent_name.setText(opponent['name'])
        self.core_opponent.setText(f"World  : {opponent['world_rank']:>3}\n"
                                   f"{opponent['continent']:<7}: {opponent['continent_rank']:>3}")
        self.core_fixture_kind.setText(desk['fixture_kind'])
    names = {m['number']: m['name'] for m in desk['managers']}
    self.core_managers.set_lines([[(f'{n} ', GOLD), (names.get(n, ''), WHITE if n == desk['manager_number'] else CYAN)]
                                  for n in range(1, 7)])
    # [designed: owner, 2026-10-21, #283; goal2/game/roles.py] the left-hand positions in lower case.
    rows = [(p['player'], p['name'], role_code(p), p['line'], i < 11, False)
            for i, p in enumerate(desk['squad'])]
    self.country_roster.set_rows(rows);self.country_roster.caption = team['name'].upper()
    history = model.history()
    stats = history['statistics']
    head = [('                     home    away    all', GOLD)]
    sub = [('                     now top now top now top', GOLD)]
    self.core_statistics.set_lines([head, sub] + [[(f'{name:<20}', GOLD), (' '.join(f'{v:>3}' for v in values), GREEN)]
                                                  for name, values in stats.items()])
    s = history['successes']
    self.core_successes.set_lines([[('    1st 2nd 3rd 4th', GOLD)],
                                   [('WC  ', GOLD), (' '.join(f'{v:>3}' for v in s['world_cup']), GREEN)],
                                   [('CH  ', GOLD), (' '.join(f'{v:>3}' for v in s['championship']), GREEN)]])
    self.core_results.set_lines([[(r['season'] + ' ', YELLOW), (f"{r['competition']:<3}", CYAN),
                                  (f"{r['won']:>3}{r['drawn']:>3}{r['lost']:>3}{r['for']:>3}{r['against']:>3} ", GREEN),
                                  (r['best'], WHITE)] for r in history['results']] or [[('no results yet', CYAN)]])
    for board, rows in ((self.core_scorers, history['top_scorers']), (self.core_caps, history['top_caps'])):
        board.set_lines([[(f"{r['name']:<15}", YELLOW), (f"{r['count']:>4}", GREEN)] for r in rows] or [[('none yet', CYAN)]])
    lines = []
    for where in ('home', 'away', 'neutral'):
        line = [(f'{where:<8}', GOLD)]
        for what in ('wins', 'defeats'):
            r = history['records'][what][where]
            text = '—' if r is None else ((f"{r['score'][0]}v{r['score'][1]} " if r['score'] else '') + ', '.join(r['opponents']))
            line.append((f'{what[:-1] if what == "wins" else "defeat"}: {text:<16} ', GREEN if what == 'wins' else YELLOW))
        lines.append(line)
    self.core_records.set_lines(lines)
