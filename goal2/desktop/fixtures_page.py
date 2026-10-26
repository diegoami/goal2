"""[designed: T74] Fixtures container for existing window-owned controls."""
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    self.standings_dialog=None
    page=self.pages[3]
    # [designed: T101] The Fixtures & match page has four views on the fixed page: 0 the match
    # preparation, 1 the full-time result, 2 half time (the substitution), 3 the fixture list (the
    # next fixture, the last result, the standings and the qualifying). A finished match opens the
    # result; a half-time pause opens half time; Fixture list and Esc are the routes.
    self.fixture_views,(prep_box,result_box,half_box,list_box)=page.add_views('fixtureViews',
        ('matchPreparationView','matchResultView','halfTimeView','fixtureListView'))
    self.fixture_views.show_view=lambda index:fixtures_view(self,index)
    self.fixtures_view=lambda index:fixtures_view(self,index)
    self.play=QPushButton('Play quick friendly');self.stop=QPushButton('Cancel match');self.stop.setEnabled(False)
    self.watch=QPushButton('Watch original friendly');self.watch.setObjectName('watchOriginal')
    self.standings=QPushButton('Competition table');self.standings.setObjectName('showStandings')
    preparation(self,prep_box)
    result_section(self,result_box)
    # View 2: half time.
    self.half_title=QLabel('HALF TIME');self.half_title.setObjectName('prepTitle');half_box.addWidget(self.half_title)
    half_bar=QGridLayout();self.half_out=QComboBox();self.half_in=QComboBox()
    self.substitute=QPushButton('Substitute');self.continue_match=QPushButton('Continue second half')
    half_bar.addWidget(QLabel('Off'),0,0);half_bar.addWidget(self.half_out,0,1);half_bar.addWidget(self.substitute,0,2)
    half_bar.addWidget(QLabel('On'),1,0);half_bar.addWidget(self.half_in,1,1);half_bar.addWidget(self.continue_match,1,2)
    half_bar.setColumnStretch(1,1)
    for widget in (self.half_out,self.half_in,self.substitute,self.continue_match):widget.setEnabled(False)
    half_box.addLayout(half_bar);self.half_preview=None
    half_box.addStretch(1)
    # View 3: the fixture list, in two columns.
    title=QLabel('FIXTURE LIST');title.setObjectName('prepTitle');list_box.addWidget(title)
    columns=QHBoxLayout();columns.setSpacing(16);list_box.addLayout(columns)
    left=QVBoxLayout();left.setSpacing(8);columns.addLayout(left,1)
    right=QVBoxLayout();right.setSpacing(8);columns.addLayout(right,1)
    self.fixture_next=card(left,'Next fixture','fixtureNext')
    self.scoreboard=card(left,'Last completed result','scoreboard')
    self.scoreboard.setStyleSheet('font-size: 22px; font-weight: 600;')
    self.result_stages=card(left,'Match resolution','resultStages')
    self.result=card(left,'Goals and result details','resultDetails')
    self.fixture_routes=QLabel();self.fixture_routes.setObjectName('fixtureRoutes');self.fixture_routes.setWordWrap(True);self.fixture_routes.setTextFormat(Qt.TextFormat.PlainText);left.addWidget(self.fixture_routes)
    left.addStretch(1)
    self.fixture_table=card(right,'Standings snapshot','fixtureTable')
    self.qualifying=card(right,'Continental qualifying','continentalQualifying')
    right.addStretch(1)
    routes=QHBoxLayout();list_box.addLayout(routes)
    self.fixture_list_back=QPushButton('< Match (Esc)');self.fixture_list_back.setObjectName('fixtureListBack');self.fixture_list_back.setAccessibleName('Back to the match preparation')
    self.fixture_list_back.clicked.connect(lambda:fixtures_view(self,0))
    for button in (self.standings,self.fixture_list_back):routes.addWidget(button)
    routes.addStretch(1);list_box.addStretch(1)
    def escape():
        if self.fixture_views.currentIndex()==3:
            fixtures_view(self,0);return True
        return False
    page.escape=escape



def fixtures_view(self,index):
    """[designed: T101] Show Fixtures view `index` (0 preparation, 1 result, 2 half time, 3 the
    fixture list) with its first control focused; presentation only."""
    self.fixture_views.setCurrentIndex(index)
    if self.page_stack.currentIndex()!=3:return
    target={0:self.play,1:self.result_continue,2:self.half_out,3:self.fixture_list_back}[index]
    if not target.isEnabled():target=self.pages[3].heading
    target.setFocus(Qt.FocusReason.ShortcutFocusReason)


from goal2.desktop.match_view import SPEEDS


def preparation(self,layout):
    """[designed: T95; accepted vision #266 screen 05] Both elevens with their formations beside
    the Play panel: Quick and Watch explained next to their existing buttons, and the speed."""
    from PySide6.QtWidgets import QFrame,QButtonGroup
    from goal2.desktop.roster import RosterView
    self.prep_title=QLabel();self.prep_title.setObjectName('prepTitle');self.prep_title.setWordWrap(True)
    layout.addWidget(self.prep_title)
    columns=QWidget();columns.setObjectName('matchPreparation');columns.box=QHBoxLayout(columns)
    columns.box.setContentsMargins(0,0,0,0);columns.box.setSpacing(16);layout.addWidget(columns)
    self.lineup_own=RosterView('XI',toggles=False,capacity=11,marks=False)
    self.lineup_other=RosterView('XI',toggles=False,capacity=11,marks=False)
    for view in (self.lineup_own,self.lineup_other):
        view.setFixedWidth(320);columns.box.addWidget(view,0,Qt.AlignmentFlag.AlignTop)
    panel=QFrame();panel.setObjectName('playPanel');body=QVBoxLayout(panel);body.setSpacing(8)
    columns.box.addWidget(panel,1,Qt.AlignmentFlag.AlignTop)
    def text(value,name):
        label=QLabel(value);label.setObjectName(name);label.setWordWrap(True);body.addWidget(label);return label
    text('PLAY','prepHeading')
    text('QUICK RESULT\nNo pitch; the result arrives at once. A half-time decision may pause it.','prepQuick')
    body.addWidget(self.play)
    text('WATCH MATCH\nFollow the original on the pitch, in its own window. Friendlies only.','prepWatch')
    body.addWidget(self.watch)
    text('SPEED (watching; Left/Right change it during the match)','prepSpeedHeading')
    row=QGridLayout();body.addLayout(row)
    self.speed_group=QButtonGroup(panel);self.speed_group.setExclusive(True);self.speed_buttons=[]
    for name,rate in SPEEDS:
        button=QPushButton(name);button.setObjectName('speed'+name);button.setCheckable(True)
        button.setAccessibleName(f'Watch speed {name}, {rate} samples per second')
        self.speed_group.addButton(button,rate);row.addWidget(button,len(self.speed_buttons)//3,len(self.speed_buttons)%3)  # two rows of three
        self.speed_buttons.append(button)
    self.speed_group.button(60).setChecked(True)
    self.prep_note=text('','prepNote')
    routes=QHBoxLayout();body.addLayout(routes)
    self.fixture_list_route=QPushButton('Fixture list >');self.fixture_list_route.setObjectName('fixtureListRoute')
    self.fixture_list_route.setAccessibleName('Show the fixture list and standings')
    self.fixture_list_route.clicked.connect(lambda:fixtures_view(self,3));routes.addWidget(self.fixture_list_route)
    self.half_route=QPushButton('Half time >');self.half_route.setObjectName('halfTimeRoute');self.half_route.setAccessibleName('Show half time')
    self.half_route.clicked.connect(lambda:fixtures_view(self,2));routes.addWidget(self.half_route)
    layout.addStretch(1)


def result_section(self,layout):
    """[designed: T97; accepted vision #266 screen 08] Full time: score, half-time, each side's
    scorers, the original's statistics and man of the match; Continue and Round results."""
    from PySide6.QtWidgets import QFrame
    self.result_open=False
    self.result_box=QWidget();self.result_box.setObjectName('resultSection');box=QVBoxLayout(self.result_box)
    box.setContentsMargins(0,0,0,0);box.setSpacing(10);layout.addWidget(self.result_box);layout.addStretch(1)
    self.result_title=QLabel();self.result_title.setObjectName('resultTitle');self.result_title.setWordWrap(True);box.addWidget(self.result_title)
    self.result_subtitle=QLabel();self.result_subtitle.setObjectName('resultSubtitle');self.result_subtitle.setWordWrap(True);box.addWidget(self.result_subtitle)
    columns=QWidget();columns.box=QHBoxLayout(columns);columns.box.setContentsMargins(0,0,0,0);columns.box.setSpacing(16)
    box.addWidget(columns);self.result_panels=[]
    for name in ('resultScorersA','resultStatistics','resultScorersB'):
        panel=QFrame();panel.setObjectName('resultPanel');body=QVBoxLayout(panel)
        heading=QLabel();heading.setObjectName('resultHeading');body.addWidget(heading)
        text=QLabel();text.setObjectName(name);text.setWordWrap(True);text.setTextFormat(Qt.TextFormat.PlainText)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);body.addWidget(text);body.addStretch(1)
        columns.box.addWidget(panel,2 if name=='resultStatistics' else 1);self.result_panels.append((heading,text))
    self.result_motm=QLabel();self.result_motm.setObjectName('resultMotm');self.result_motm.setWordWrap(True);box.addWidget(self.result_motm)
    actions=QHBoxLayout();box.addLayout(actions)
    self.result_continue=QPushButton('Continue');self.result_continue.setObjectName('resultContinue')
    self.result_round=QPushButton('Round results');self.result_round.setObjectName('resultRound')
    for button in (self.result_continue,self.result_round):actions.addWidget(button)
    actions.addStretch(1)
    self.result_note=QLabel();self.result_note.setObjectName('resultNote');self.result_note.setWordWrap(True);box.addWidget(self.result_note)
    self.result_continue.clicked.connect(lambda:continue_after_result(self))
    self.result_round.clicked.connect(self.show_standings)
    self.result_box.hide()


def open_result(self):
    """[designed: T97] A match has just finished: show its result first, Continue focused."""
    self.result_open=True;refresh_result(self);self.navigate(3);fixtures_view(self,1)
    self.result_continue.setFocus()


def continue_after_result(self):
    """[designed: T97; accepted screen 09] Continue: back to the Country desk and the next fixture."""
    self.result_open=False;refresh_result(self);self.fixture_views.setCurrentIndex(0);self.navigate(0)
    self.desk_routes[0].setFocus()


def refresh_result(self):
    from goal2.game.match_report import report,NOT_RECORDED
    display=self.display_model
    value=report(display.state.last_match,display.goaldat) if self.result_open and self.preview is None else None
    self.result_box.setVisible(value is not None)
    if value is None:return
    a,b=value['teams'];score=value['score']
    self.result_title.setText(f'FULL TIME / {a.upper()} {score[0]} - {score[1]} {b.upper()}')
    half=value['half_time']
    self.result_subtitle.setText(f"{value['kind'].upper()} / HALF TIME "+(f'{half[0]} : {half[1]}' if half else NOT_RECORDED.upper())+f" / {value['engine']}")
    for (heading,text),side,team in ((self.result_panels[0],0,a),(self.result_panels[2],1,b)):
        heading.setText(f'{team.upper()} SCORERS')
        text.setText('\n'.join(f'{name}  {minute}′' for name,minute in value['scorers'][side]) or 'No goals')
    heading,text=self.result_panels[1]
    heading.setText(f'STATISTICS / {a[:3].upper()} : {b[:3].upper()}')
    if value['statistics'] is None:
        text.setText(NOT_RECORDED+': the quick simulation keeps the score and goals only.')
    else:
        rows=[f'{label:<14}{x:>3} : {y}' for label,(x,y) in value['statistics']]
        rows+=['',f"Bars (raw)    {value['bars'][0][0]}:{value['bars'][0][1]}  {value['bars'][1][0]}:{value['bars'][1][1]}",'Meaning unverified']
        stages=value['stages']
        if stages:
            for key,label in (('regulation','Regulation'),('extra_time','Extra time'),('penalties','Penalties')):
                if stages[key] is not None:rows.append(f'{label:<14}{stages[key][0]:>3} : {stages[key][1]}')
        text.setText('\n'.join(rows))
    self.result_motm.setText('MAN OF THE MATCH: '+(value['man_of_the_match'] or NOT_RECORDED))
    subs=[f'{off} > {on} {minute}′' for team,off,on,minute in value['substitutions']]
    self.result_note.setText(' / '.join(subs) if subs else 'No substitutions recorded')


def playback_rate(self):
    """The chosen watched playback rate, read afresh for each started match."""
    return self.speed_group.checkedId()


def refresh_preparation(self):
    """[designed: T95] The draft's eleven (what will play once confirmed) and the opponent's
    stored eleven [confirmed: F024: the computer corrects it by bench swaps at kickoff]."""
    from goal2.game import roles
    from goal2.desktop.squad_page import roster_rows
    display=self.display_model;state=display.state;names=display.goaldat.country_names
    codes,lines=roles.tables(state)
    def formation(words):
        positions=[state.players[w][6] for w in words]
        return '-'.join(str(sum(1 for p in positions if p<14 and lines[p]==line)) for line in (1,2,3))
    rows=display.view()['players'];selected=self.selected_ids();captain=self.captain.currentData()
    own=[r for r in roster_rows(self,rows,selected,captain) if r[4]]
    self.lineup_own.set_rows(own);self.lineup_own.caption=f'{names[state.managed_country].upper()} / {formation(selected)}'
    fixture=state.campaign.next_fixture if state.campaign else None
    if fixture is None:
        self.prep_title.setText('QUICK FRIENDLY' if state.campaign is None else 'NO FIXTURE SCHEDULED')
        self.lineup_other.setVisible(False);self.lineup_other.set_rows([])
    else:
        other=fixture.side_b if fixture.side_a==state.managed_country else fixture.side_a
        kind='Friendly' if fixture.kind==1 else 'Qualifier'
        self.prep_title.setText(f'{names[fixture.side_a].upper()} v {names[fixture.side_b].upper()} / {kind.upper()}')
        record=state.countries[other];words=[int.from_bytes(record[2*i:2*i+2],'little') for i in range(11)]
        goaldat=display.goaldat
        def name(word):
            initial=goaldat.player_initials[word] if word<len(goaldat.player_initials) else ''
            return (initial+' ' if initial else '')+goaldat.player_names[word]
        other_rows=[(w,name(w),*roles.role(state,state.players[w][6],cache=(codes,lines)),True,False) for w in words]
        self.lineup_other.setVisible(True);self.lineup_other.set_rows(other_rows)
        self.lineup_other.caption=f'{names[other].upper()} / {formation(words)}'
    dirty=self.draft()!=(state.starting_eleven,state.captain,state.country_tactics)
    self.prep_note.setText(('Unconfirmed changes: confirm them on Team before Start. ' if dirty else '')+
                           'Quick and Watch may differ. The opponent may swap injured players at kickoff.')


def card(layout,title,name):
    """[designed: T78] Wrapped plain text stays selectable inside the page scroll area."""
    from PySide6.QtWidgets import QFrame
    panel=QFrame();panel.setObjectName('overviewCard');body=QVBoxLayout(panel)
    heading=QLabel(title);heading.setObjectName('cardHeading');body.addWidget(heading)
    label=QLabel();label.setObjectName(name);label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    body.addWidget(label);layout.addWidget(panel)
    return label


def snapshot(display,view=None):
    """[designed: T78] Pure presentation boundary; malformed copies cannot publish state.
    [derived: T51] Source A/B order and normal goals exclude shootout kicks.
    """
    from goal2.game.watched_schema import watched,validate_result,resolution,COMPETITIVE_SCHEMA
    state=display.state;match=state.last_match
    fixture=state.campaign.next_fixture if state.campaign else None
    next_text=((display.goaldat.country_names[fixture.side_a]+' — '+display.goaldat.country_names[fixture.side_b])
               if fixture else ('Standalone friendly / no campaign fixture' if state.campaign is None else 'No pending fixture'))
    result=dict(next=next_text,score='No match played',stages='No completed result',detail='No result yet\nNo match played',error=False)
    if match is None:return result
    try:
        detail=display.result_text()
        original=watched(match)
        provenance='Original engine' if original else 'Quick simulation (rebuild setup)'
        stages=[]
        if original:
            competitive=match.get('schema')==COMPETITIVE_SCHEMA
            validate_result(match.get('original'),competitive=competitive)
            raw=match['original']
            if match['teams']!=[raw['first'],raw['second']] or match['score']!=list(raw['score']) or match['goals']!=raw['goals']:
                raise ValueError('Result envelope differs from original result')
            if competitive:
                resolved=resolution(raw)
                for key,label in (('regulation','Regulation'),('extra_time','Extra time'),('penalties','Penalties')):
                    pair=resolved[key]
                    if pair is not None:stages.append(f'{label}: {pair[0]} — {pair[1]}')
                winner=resolved['winner']
                stages.append('Draw' if winner==2 else 'Winner: '+display.goaldat.country_names[match['teams'][winner]])
        a,b=match['teams'];x,y=match['score']
        result.update(score=f'{display.goaldat.country_names[a]} {x} — {y} {display.goaldat.country_names[b]}',
                      stages='\n'.join(stages) if stages else 'Full time',detail=provenance+'\n'+detail)
    except (ValueError,KeyError,IndexError,TypeError) as exc:
        result.update(score='Result unavailable',stages='Invalid saved result',detail=str(exc),error=True)
    return result


def refresh(self,display,view):
    """[designed: T78] All cards follow the displayed country, including fresh previews."""
    data=snapshot(display,view)
    refresh_result(self)
    self.fixture_next.setText(data['next']);self.scoreboard.setText(data['score'])
    self.result_stages.setText(data['stages']);self.result.setText(data['detail'])
    try:
        table=display.competition_table()
        self.fixture_table.setText('No complete opening group schedule' if table is None else
            'Current positions; qualification is provisional.\n'+
            '\n'.join(f"{r['rank']}. {r['name']}   P {r['played']}   GF {r['goals_for']}   GA {r['goals_against']}   GD {r['goal_difference']}   Pts {r['points']}" for r in table['rows']))
    except (ValueError,KeyError,IndexError) as exc:self.fixture_table.setText('Standings unavailable: '+str(exc))
    self.qualifying.setText(qualifying_text(display))


from goal2.desktop.model import CONTINENTS


def qualifying_text(display):
    """[designed: T50] The managed stage-2 status; the 32 finalists once every fixture is played."""
    try:
        view=display.qualifying()
    except (ValueError,KeyError,IndexError) as exc:return 'Qualifying unavailable: '+str(exc)
    if view is None:return 'No continental qualifying stage in this campaign'
    lines=[f"{CONTINENTS[view['continent']]}, group {view['group']}",view['text']]
    if view['qualifiers'] is not None:
        lines.append('Continental finalists (group winners):')
        lines+=[f"{CONTINENTS[c]}: "+', '.join(names) for c,names in view['qualifiers'].items()]
    return '\n'.join(lines)


def enabled(self,active):
    """[designed: T78; derived: T80/T50] Display existing routes; callbacks retain authority."""
    from goal2.engine.original_match.match import KINDS
    state=self.display_model.state;pending=state.campaign.next_fixture if state.campaign else None
    quick=state.campaign is None or (pending is not None and pending.kind==1)
    watch=pending is not None and pending.kind==1
    competitive=pending is not None and pending.kind!=1 and pending.kind in KINDS
    self.play.setEnabled(active and (quick or competitive));self.watch.setEnabled(active and watch)
    # [designed: T50] A finished stage is not an unsupported fixture: the finals builder is T52's.
    finished=state.campaign is not None and pending is None
    self.fixture_routes.setText(('Play: '+('quick friendly' if quick else 'original competitive') if quick or competitive else
        'Play unavailable: this stage is complete; the next stage is not available yet' if finished else 'Play unavailable: unsupported pending fixture')+
        '\n'+('Watch: original friendly' if watch else 'Watch unavailable: scheduled friendlies only'))


# -- the core route (T105) ------------------------------------------------------------------------------------
# [designed: owner, 2026-10-22, #321; T105] Over the core the Fixtures & match page shows the original's fixture
# list (000E:0000: the fixtures from the current one on, sixteen rows at a time, the managed fixtures ticked) and
# its tournament (1771:958D: the group table and the group's fixtures) [confirmed: the screens' text in
# goal2/tests/test_core_desktop_t105.py], read through the CoreModel only. Up and Down scroll the list or change the
# group: presentation only, no key reaches the original.
FIXTURE_ROWS = 16


class _ScrollBoard:
    """Mixin for a TextBoard whose lines are a window over `items`, moved by Up/Down/PgUp/PgDn/Home/End."""

    def keyPressEvent(self, event):
        steps = {Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1, Qt.Key.Key_PageDown: self.page_step,
                 Qt.Key.Key_PageUp: -self.page_step, Qt.Key.Key_Home: -10 ** 6, Qt.Key.Key_End: 10 ** 6}
        if event.key() in steps:
            self.move(steps[event.key()]);event.accept();return
        super().keyPressEvent(event)


def _fixture_line(row, managed):
    from goal2.desktop.player_card import CYAN, GOLD, GREEN, MAGENTA, WHITE
    score = f"{row['score'][0]:>2}v{row['score'][1]:<2}" if row['played'] else '  v  '
    def colour(country):
        return WHITE if country in managed else CYAN
    return [(f"{row['first_name']:>15} ", colour(row['first'])), (score, GOLD),
            (f" {row['second_name']:<15}  ", colour(row['second'])),
            (f"{row['kind_name']:<12}", GREEN if row['kind'] == 1 else GOLD), (' √' if row['mark'] else '  ', MAGENTA)]


def build_core(self, model):
    from goal2.desktop.core_window import TextBoard
    page = self.pages[3]
    routes = QHBoxLayout();routes.setSpacing(8);page.content.addLayout(routes)
    self.core_fixture_route = QPushButton('fixture list');self.core_fixture_route.setObjectName('coreFixtureRoute')
    self.core_tournament_route = QPushButton('tournament');self.core_tournament_route.setObjectName('coreTournamentRoute')
    for button in (self.core_fixture_route, self.core_tournament_route):routes.addWidget(button)
    self.core_show_match = QPushButton('SHOW MATCH (F8)');self.core_show_match.setObjectName('coreShowMatch')
    self.core_show_match.setMinimumHeight(44);self.core_show_match.setShortcut('F8')
    self.core_show_match.setAccessibleName('Show the match window')
    self.core_show_match.setToolTip('No match window is available')
    self.core_show_match.setEnabled(False)
    self.core_show_match.clicked.connect(lambda:self.core_round.show_match())
    routes.addWidget(self.core_show_match)
    routes.addStretch(1)
    self.fixture_views, (list_box, tournament_box) = page.add_views('fixtureViews', ('coreFixtureListView', 'coreTournamentView'))
    self.fixture_views.show_view = lambda index: core_fixtures_view(self, index)
    self.fixtures_view = lambda index: core_fixtures_view(self, index)
    self.core_fixture_route.clicked.connect(lambda: core_fixtures_view(self, 0))
    self.core_tournament_route.clicked.connect(lambda: core_fixtures_view(self, 1))

    class FixtureBoard(_ScrollBoard, TextBoard):
        page_step = FIXTURE_ROWS

        def move(board, step):
            board.offset = max(0, min(max(0, len(board.items) - FIXTURE_ROWS), board.offset + step))
            board.show_window()

        def show_window(board):
            board.set_lines([_fixture_line(r, board.managed) for r in board.items[board.offset:board.offset + FIXTURE_ROWS]])
    self.core_fixture_board = FixtureBoard('FIXTURES AND RESULTS', 54, FIXTURE_ROWS, 'coreFixtureBoard', 17)
    self.core_fixture_board.items = [];self.core_fixture_board.offset = 0;self.core_fixture_board.managed = ()
    self.core_fixture_board.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    list_box.addWidget(self.core_fixture_board, 0, Qt.AlignmentFlag.AlignLeft)
    self.core_fixture_hint = QLabel();self.core_fixture_hint.setObjectName('prepNote');self.core_fixture_hint.setWordWrap(True)
    list_box.addWidget(self.core_fixture_hint);list_box.addStretch(1)

    class GroupBoard(_ScrollBoard, TextBoard):
        page_step = 1

        def move(board, step):
            if board.groups:
                board.offset = max(0, min(len(board.groups) - 1, board.offset + step))
            board.show_window()

        def show_window(board):
            from goal2.desktop.player_card import GOLD, GREEN, WHITE, CYAN
            if not board.groups:
                board.set_lines([[(board.empty, CYAN)]]);return
            g = board.groups[board.offset]
            lines = [[(f"Group {g['group']:<9}", GOLD), ('  P  W  D  L   F   A   T', GOLD)]]
            for r in g['rows']:
                lines.append([(f"{r['name']:<15}", WHITE if r['country'] in board.managed else CYAN),
                              (f"{r['played']:>3}{r['won']:>3}{r['drawn']:>3}{r['lost']:>3}"
                               f"{r['for']:>4}{r['against']:>4}{r['points']:>4}", GREEN)])
            lines.append([])
            lines += [_fixture_line(f, board.managed) for f in g['fixtures']]
            if board.top_scorers:
                lines += [[], [('TOP SCORERS', GOLD)]]
                lines += [[(f"{i+1}) {r['name']:<14} {r['goals']:>3}", WHITE)]
                          for i,r in enumerate(board.top_scorers)]
            board.set_lines(lines)
    self.core_group_board = GroupBoard('TOURNAMENT', 54, 18, 'coreGroupBoard', 17)
    self.core_group_board.groups = [];self.core_group_board.offset = 0;self.core_group_board.managed = ()
    self.core_group_board.empty = ''
    self.core_group_board.top_scorers = []
    self.core_group_board.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    self.core_tournament_title = QLabel();self.core_tournament_title.setObjectName('prepTitle')
    tournament_box.addWidget(self.core_tournament_title)
    from PySide6.QtWidgets import QStackedWidget
    from goal2.desktop.bracket_page import BracketBoard
    self.core_tournament_content = QStackedWidget()
    self.core_tournament_content.addWidget(self.core_group_board)
    self.core_bracket_board = BracketBoard('coreBracketBoard');self.core_bracket_board.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    self.core_tournament_content.addWidget(self.core_bracket_board)
    tournament_box.addWidget(self.core_tournament_content, 1)
    self.core_tournament_hint = QLabel('Up/Down: group');self.core_tournament_hint.setObjectName('prepNote')
    tournament_box.addWidget(self.core_tournament_hint)

    def escape():
        if self.fixture_views.currentIndex() == ROUND_VIEW:
            return self.core_round.escape()
        if self.fixture_views.currentIndex() != 0:
            core_fixtures_view(self, 0);return True
        return False
    page.escape = escape
    self.core_round = CoreRound(self)


def core_fixtures_view(self, index):
    """[designed: T105] Show Fixtures view `index` (0 the fixture list, 1 the tournament); presentation only."""
    for button in (self.core_fixture_route, self.core_tournament_route):button.setVisible(True)
    self.fixture_views.setCurrentIndex(index)
    if hasattr(self, 'core_round'):self.core_round.holder.updateGeometry()
    if self.page_stack.currentIndex() == 3:
        (self.core_fixture_board if index == 0 else self.core_tournament_content.currentWidget()).setFocus(Qt.FocusReason.ShortcutFocusReason)


def refresh_core(self, model):
    desk = model.desk()
    managed = tuple(m['country'] for m in desk['managers'])
    listing = model.fixture_list()
    board = self.core_fixture_board
    board.items, board.managed = listing['rows'], managed
    board.offset = 0;board.show_window()
    self.core_fixture_hint.setText(f"{len(listing['rows'])} fixtures from number {listing['first']}; "
                                   'Up/Down/PgUp/PgDn scroll; √ marks your fixtures')
    view = model.tournament()
    competition = 'WORLD CUP' if view['class'] and view['display'] != 'qualifying' else view['continent'].upper()
    self.core_tournament_title.setText(f"{competition} / {view['display'].upper()}")
    group = self.core_group_board
    group.managed = managed;group.groups = view['groups'] or []
    group.top_scorers = view.get('top_scorers', [])
    group.empty = ('' if view['groups'] is not None else
                   f"The {view['display']} display is not read over the core yet (stage {view['stage']}).")
    own = [i for i, g in enumerate(group.groups) if any(r['country'] == desk['team']['country'] for r in g['rows'])]
    group.offset = own[0] if own else 0
    group.show_window()
    if view.get('bracket') is not None:
        self.core_bracket_board.set_view(view['bracket'], managed)
        self.core_tournament_content.setCurrentIndex(1);self.core_tournament_hint.hide()
    else:
        self.core_tournament_content.setCurrentIndex(0);self.core_tournament_hint.show()


# -- the round over the core (T108) -----------------------------------------------------------------------------
# [designed: owner, 2026-10-22, #308, #331; decision 7] Play next game on the core route is the original's round, run
# as background jobs (CoreJobs), each step by the original's own keys (goal2/core/driver.py): the round's other
# fixtures and their results, the captain, the first half as the original's quick result, the half-time board and
# bench, the second half, the full-time board, the table and the bulletins, back to the manager menu. The page stops
# the player only where the original asks the manager: the captain, the half-time menu (play on, or the bench), and an
# eleven the original refuses before the kick-off (its message, and SELECT YOUR TEAM to fix it). The screens the
# original only shows ("hit any key") come as goal2 pages, one at a time, Next or Enter for the next. The pitch view
# over the core is G14b; the page says so.
ROUND_VIEW = 2
RESULT_ROWS = 18


def _board_lines(view, title):
    from goal2.desktop.player_card import CYAN, GOLD, GREEN, WHITE
    lines = [[(title, GOLD)], [(f"{view['names'][0]:>15} ", WHITE), (f"{view['score'][0]:>2} - {view['score'][1]:<2}", GOLD),
                               (f" {view['names'][1]:<15}", WHITE)], []]
    for side in (0, 1):
        for s in view['scorers'][side]:
            mark = f" {s['mark']}" if s['mark'] else ''
            lines.append([(f"{view['names'][side][:15]:<15} ", CYAN), (f"{s['name']:<14}", WHITE),
                          (f"{s['minute']:>3}'{mark}", GREEN)])
    if not any(view['scorers']):
        lines.append([('No goals', CYAN)])
    if view.get('man_of_the_match'):
        lines += [[], [('MAN OF THE MATCH  ', GOLD), (view['man_of_the_match'], WHITE)]]
    return lines


def _page_lines(kind, view, managed):
    """A page the round passed, as lines of a TextBoard, in the original's structure."""
    from goal2.desktop.player_card import CYAN, GOLD, WHITE
    if kind == 'round-results':
        return [[('THE ROUND\'S RESULTS', GOLD)]] + [_fixture_line(r, managed) for r in view['rows']][-RESULT_ROWS + 1:]
    if kind == 'fixture-result':
        return [[('RESULT', GOLD)], _fixture_line(view, managed)]
    if kind in ('match-board', 'match-summary'):
        return _board_lines(view, 'FULL TIME')
    if kind == 'tournament-table':
        country = next((m for m in managed), None)
        groups = [g for g in (view['groups'] or []) if g['number']==view.get('selected_group')]
        if not groups:
            groups = [g for g in (view['groups'] or []) if any(r['country'] == country for r in g['rows'])]
        if not groups:groups = (view['groups'] or [])[:1]
        lines = []
        for g in groups[:1]:
            lines.append([(f"Group {g['group']:<9}", GOLD), ('  P  W  D  L   F   A   T', GOLD)])
            for r in g['rows']:
                lines.append([(f"{r['name']:<15}", WHITE if r['country'] in managed else CYAN),
                              (f"{r['played']:>3}{r['won']:>3}{r['drawn']:>3}{r['lost']:>3}"
                               f"{r['for']:>4}{r['against']:>4}{r['points']:>4}", WHITE)])
            if view['display']=='finals':
                lines.append([]);lines += [_fixture_line(f,managed) for f in g['fixtures']]
        if view.get('top_scorers'):
            lines += [[], [('TOP SCORERS', GOLD)]]
            lines += [[(f"{i+1}) {r['name']:<14} {r['goals']:>3}", WHITE)]
                      for i,r in enumerate(view['top_scorers'])]
        return lines or [[('The table', GOLD)]]
    return []


PAGE_TITLES = {'round-results': "THE ROUND'S RESULTS", 'fixture-result': 'RESULT', 'match-board': 'RESULT AND SUMMARY',
               'match-summary': 'RESULT AND SUMMARY', 'tournament-table': 'THE TABLE', 'bulletin': 'THE SOCCER BULLETIN',
               'championship-bracket': 'CHAMPIONSHIP'}


class _RoundHolder(QWidget):
    """[designed: T108] The round's view counts towards the page's size only while it is shown: a stacked view's
    minimum is otherwise the largest of its views, and the fixture list and tournament would need the bench's room."""

    def __init__(self, stack):
        super().__init__();self.stack = stack

    def _shown(self):
        return self.stack.currentWidget() is self

    def sizeHint(self):
        return super().sizeHint() if self._shown() else QSize(0, 0)

    def minimumSizeHint(self):
        return super().minimumSizeHint() if self._shown() else QSize(0, 0)


class _RoundNext(QPushButton):
    """[designed: T115] The focused page action accepts the advertised Enter as well as Space."""

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click();event.accept()
        else:
            super().keyPressEvent(event)


class CoreRound:
    """[designed: T108] The round's views on the Fixtures & match page over the core: 0 the captain, 1 the bench
    (bench_page.CoreBench), 2 a page the round passed."""

    def __init__(self, window):
        from PySide6.QtWidgets import QStackedWidget
        from goal2.desktop.core_window import TextBoard
        from goal2.desktop.roster import RosterView
        from goal2.desktop.bench_page import CoreBench
        self.window = window;self.state = None;self.queue = [];self.after = None;self.first_page = 0
        stack = window.fixture_views
        holder = _RoundHolder(stack);holder.setObjectName('coreRoundView');box = QVBoxLayout(holder)
        box.setContentsMargins(0, 0, 0, 0);box.setSpacing(8);stack.addWidget(holder)
        assert stack.indexOf(holder) == ROUND_VIEW
        self.holder = holder
        self.pitch_note = QLabel('Watch the match in the pitch window, or take the original\'s quick result.')
        self.pitch_note.setObjectName('prepNote');self.pitch_note.setWordWrap(True)
        box.addWidget(self.pitch_note)
        self.views = QStackedWidget();self.views.setObjectName('coreRoundViews');box.addWidget(self.views, 1)
        # 0: the captain (CC7B's list: the eleven), with the original's own choice
        captain = QWidget();captain.setObjectName('coreCaptainView');row = QHBoxLayout(captain);row.setSpacing(16)
        left = QVBoxLayout();left.setSpacing(10);row.addLayout(left, 1)
        self.captain_title = QLabel('CAPTAIN');self.captain_title.setObjectName('prepTitle');left.addWidget(self.captain_title)
        self.captain_note = QLabel();self.captain_note.setObjectName('prepNote');self.captain_note.setWordWrap(True)
        left.addWidget(self.captain_note)
        self.refusal = QLabel();self.refusal.setObjectName('benchMessage');self.refusal.setWordWrap(True)
        left.addWidget(self.refusal)
        self.kick_off = QPushButton('Kick off: the selected player captains (Enter)');self.kick_off.setObjectName('coreKickOff')
        self.kick_off.clicked.connect(self.kick_off_selected);left.addWidget(self.kick_off)
        self.computer = QPushButton("Kick off: the original's own captain (C)");self.computer.setObjectName('coreCaptainC')
        self.computer.clicked.connect(lambda: self.start_kick_off(None));left.addWidget(self.computer)
        self.players = QPushButton('Players: select your team >');self.players.setObjectName('corePreMatchPlayers')
        self.players.clicked.connect(self.show_pre_match);left.addWidget(self.players)
        self.watch = QPushButton('Watch this match');self.watch.setObjectName('coreWatch');self.watch.setCheckable(True)
        self.watch.setChecked(True)  # [designed: owner demo feedback, 2026-10-23, T116]
        left.addWidget(self.watch)
        left.addStretch(1)
        self.captain_roster = RosterView('CAPTAIN', toggles=False, grouped=False, marks=False, capacity=11)
        self.captain_roster.setObjectName('coreCaptainRoster');self.captain_roster.setFixedWidth(320)
        self.captain_roster.activated.connect(lambda r: self.kick_off_selected())
        row.addWidget(self.captain_roster, 0, Qt.AlignmentFlag.AlignTop)
        self.views.addWidget(captain)
        # 1: the bench
        self.bench = CoreBench(window, self.views)
        # 2: a page the round passed
        page = QWidget();page.setObjectName('coreRoundPage');pbox = QVBoxLayout(page);pbox.setSpacing(8)
        self.page_count = QLabel();self.page_count.setObjectName('prepNote');pbox.addWidget(self.page_count)
        from goal2.desktop.bulletin_page import BulletinColumns
        self.page_content = QStackedWidget();pbox.addWidget(self.page_content, 1)
        board_holder = QWidget();board_box = QVBoxLayout(board_holder);board_box.setContentsMargins(0, 0, 0, 0)
        self.page_board = TextBoard('RESULT', 56, RESULT_ROWS, 'coreRoundBoard', 17)
        board_box.addWidget(self.page_board, 0, Qt.AlignmentFlag.AlignLeft);board_box.addStretch(1)
        self.page_content.addWidget(board_holder)
        self.bulletin_columns = BulletinColumns('THE SOCCER BULLETIN');self.page_content.addWidget(self.bulletin_columns)
        from goal2.desktop.bracket_page import BracketBoard
        self.round_bracket_board = BracketBoard('coreRoundBracket');self.page_content.addWidget(self.round_bracket_board)
        self.page_next = _RoundNext('Next > (Enter)');self.page_next.setObjectName('coreRoundNext')
        self.page_next.clicked.connect(self.next_page);pbox.addWidget(self.page_next)
        self.views.addWidget(page)
        # 3: the managed side's substitution notice at a stoppage
        notice = QWidget();notice.setObjectName('coreNoticeView');nbox = QVBoxLayout(notice);nbox.setSpacing(10)
        title = QLabel('SUBSTITUTION OPPORTUNITY');title.setObjectName('prepTitle');nbox.addWidget(title)
        self.notice_note = QLabel();self.notice_note.setObjectName('prepNote');self.notice_note.setWordWrap(True)
        nbox.addWidget(self.notice_note)
        self.notice_bench = QPushButton('Players: the bench (any key) >');self.notice_bench.setObjectName('coreNoticeBench')
        self.notice_bench.clicked.connect(lambda: self.window.run_core('notice', True));nbox.addWidget(self.notice_bench)
        self.notice_pass = QPushButton('Play on: let it pass (no key)');self.notice_pass.setObjectName('coreNoticePass')
        self.notice_pass.clicked.connect(lambda: self.window.run_core('notice', False));nbox.addWidget(self.notice_pass)
        nbox.addStretch(1);self.views.addWidget(notice)
        # [designed: T109] The existing pygame pitch owns the live picture; Qt keeps a resumable wait on close.
        live = QWidget();lbox = QVBoxLayout(live)
        self.live_note = QLabel('The match is in the pitch window. Enter there opens the bench.')
        self.live_note.setObjectName('prepNote');self.live_note.setWordWrap(True);lbox.addWidget(self.live_note)
        self.resume_watch = QPushButton('Resume watching');self.resume_watch.clicked.connect(self.resume_viewer)
        lbox.addWidget(self.resume_watch);lbox.addStretch(1);self.views.addWidget(live)
        summary = QWidget();sbox = QVBoxLayout(summary)
        self.summary_note = QLabel('Save the match summary?');self.summary_note.setObjectName('prepTitle')
        sbox.addWidget(self.summary_note)
        self.summary_board = TextBoard('MATCH SUMMARY', 56, RESULT_ROWS, 'coreSummaryBoard', 17)
        sbox.addWidget(self.summary_board, 0, Qt.AlignmentFlag.AlignLeft)
        self.export_summary = QPushButton('Save summary…');self.export_summary.clicked.connect(self.save_summary)
        sbox.addWidget(self.export_summary)
        self.skip_summary = QPushButton('Continue without saving (N)')
        self.skip_summary.clicked.connect(lambda: self.window.run_core('summary_done'));sbox.addWidget(self.skip_summary)
        sbox.addStretch(1);self.views.addWidget(summary)
        # [designed: T118; confirmed: 0791:9B93] The original orders every available XI player.
        order = QWidget();obox = QVBoxLayout(order);obox.setSpacing(8)
        self.shootout_title = QLabel();self.shootout_title.setObjectName('prepTitle');obox.addWidget(self.shootout_title)
        self.shootout_hint = QLabel('Choose each available player in order. Esc undoes the last pick.')
        self.shootout_hint.setObjectName('prepNote');self.shootout_hint.setWordWrap(True);obox.addWidget(self.shootout_hint)
        columns = QHBoxLayout();columns.setSpacing(8);obox.addLayout(columns)
        left = QVBoxLayout();columns.addLayout(left)
        self.shootout_roster = RosterView('SHOOTOUT XI',toggles=False,grouped=False,marks=False,capacity=11)
        self.shootout_roster.setFixedWidth(300);left.addWidget(self.shootout_roster)
        self.shootout_pick = _RoundNext('Select player (Enter)');left.addWidget(self.shootout_pick)
        self.shootout_undo = QPushButton('Undo last pick (Esc)');left.addWidget(self.shootout_undo)
        left.addStretch(1)
        from goal2.desktop.player_card import PlayerCardView
        self.shootout_card = PlayerCardView(compact=True);columns.addWidget(self.shootout_card)
        obox.addStretch(1);self.views.addWidget(order)
        self.shootout_pick.clicked.connect(self.pick_shootout)
        self.shootout_undo.clicked.connect(lambda: self.window.run_core('shootout_undo'))
        self.shootout_roster.activated.connect(lambda r: self.pick_shootout())
        self.shootout_roster.current_changed.connect(lambda r: self.refresh_shootout_card())
        from PySide6.QtCore import QTimer
        self.viewer = None
        self.watch_suspended = False
        self.pending_inputs = []
        self.pending_stop = None
        from goal2.desktop.core_takers import TakerPages
        self.takers=TakerPages(self)
        self.viewer_timer = QTimer(window);self.viewer_timer.setInterval(2);self.viewer_timer.timeout.connect(self.poll_viewer)
        self.buttons = [self.kick_off, self.computer, self.players, self.page_next, self.bench.play, self.notice_bench,
                        self.notice_pass, self.watch, self.export_summary, self.skip_summary, self.resume_watch,
                        self.bench.position_next,self.bench.position_club,self.bench.roster]
        self.buttons += [self.shootout_pick,self.shootout_undo,self.shootout_roster]
        self.buttons += self.takers.controls

    # -- the steps --------------------------------------------------------------------------------------------
    def show(self, index):
        w = self.window
        if w.page_stack.currentIndex() != 3:w.navigate(3)
        # [designed: T108] the fixture list's routes wait while the round is shown; the bench needs the page's height
        for button in (w.core_fixture_route, w.core_tournament_route):button.setVisible(False)
        self.pitch_note.setVisible(index not in (1,6,self.takers.choice_index,self.takers.preview_index))
        # [designed: T114 review R1] QStackedWidget includes hidden children's hints: only the player page
        # needs this row, so it must not enlarge the captain/progress pages before or after an offer.
        self.bench.position_row.setVisible(index==1 and self.bench.positions_offered())
        w.fixture_views.setCurrentIndex(ROUND_VIEW);self.views.setCurrentIndex(index);self.holder.updateGeometry()
        focus = {0: self.captain_roster, 1: self.bench.roster, 2: self.page_next, 3: self.notice_bench,
                 4: self.resume_watch, 5: self.export_summary, 6: self.shootout_roster,
                 self.takers.choice_index:self.takers.roster,self.takers.preview_index:self.takers.back}[index]
        focus.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def start(self):
        """Play next game: the round's start, as a job."""
        self.viewer_timer.stop()
        if self.viewer is not None:
            self.viewer.close();self.viewer = None
        self.watch_suspended = False
        self.pending_inputs = []
        self.window.run_core('round_start')
        self.show_waiting('The original plays the round…')

    def show_waiting(self, text):
        """[designed: T110] A new step shows its progress board, including after a bulletin."""
        self.page_content.setCurrentIndex(0)
        self.page_count.setText(text);self.page_board.set_lines([]);self.show(2)

    def finished(self, name, answer):
        """A round step's job ended: show the stop the original is at (CoreModel.round_state's `stop`)."""
        kind, value = answer
        if kind != 'done':
            self.bench.message = value;self.bench.refresh();return
        state = self.state = value
        self.refresh_match_button()
        if name == 'round_start':self.first_page = 0
        if state['stop'] != 'live' and self.viewer is not None:
            if state.get('commentary') and self.viewer.display.frame is not None:
                self.viewer.pose(self.viewer.display.frame, state['commentary'])
                self.pending_stop = (name, ('done', dict(state, commentary=[])))
                return
            self.viewer.decision('half_time' if state['stop'] == 'half-time' else state['stop'])
        if name == 'round_position':
            self.bench.message = (f"The original refused: {state['position_refused']}" if state['position_refused']
                                  else f"Last refusal: {state['refused']}. Play checks again." if state['refused']
                                  else 'Position set by the original. Play checks the eleven.')
            mode=self.bench.mode
            self.bench.offer(state,mode)
            words=sum((list(x) for x in self.bench.words()),[])
            if state['position_player'] in words:self.bench.roster.set_current(words.index(state['position_player']))
            self.show(1);return
        if name == 'substitute':
            made = state['substitution']
            self.bench.message = ('Made by the original' if made['made'] else
                                  f"The original refused: {made['refused']}" if made['refused'] else 'Not made')
        elif name == 'prematch_swap':
            self.bench.message = 'Moved by the original'
            self.bench.offer(state, 'pre_match');self.show(1);return
        elif state['refused']:
            self.bench.message = f"The original refused: {state['refused']}"
        else:
            self.bench.message = ''
        stop = state['stop']
        if stop == 'shootout-announcement':
            self.queue = list(state['pages'][self.first_page:]);self.after = 'shootout-announcement'
            self.first_page = len(state['pages']);self.next_page()
        elif stop == 'shootout-order':
            self.show_shootout_order(state)
        elif stop in ('taker','taker-pitch'):
            self.first_page = len(state['pages'])
            self.takers.offer(state)
        elif stop == 'round-paused':
            self.queue = list(state['pages'][self.first_page:]);self.after = 'round-paused'
            self.first_page = len(state['pages']);self.next_page()
        elif stop in ('bulletin-achievement','bulletin-congratulations'):
            self.queue = list(state['pages'][self.first_page:]);self.after = stop
            self.first_page = len(state['pages']);self.next_page()
        elif stop == 'captain':
            if name in ('round_start', 'round_continue'):
                self.queue = list(state['pages'][self.first_page:]);self.after = 'captain';self.first_page = len(state['pages'])
                self.next_page()
            else:
                self.show_captain()
        elif stop in ('half-time', 'extra-time-start', 'extra-time-half', 'stoppage', 'pause'):
            self.first_page = len(state['pages'])
            self.bench.offer(state, 'half_time' if stop in ('half-time','extra-time-start','extra-time-half') else stop);self.show(1)
        elif stop == 'notice':
            self.first_page = len(state['pages']);self.show_notice(state)
        elif stop == 'full-time':              # [T108 review, R1] the round's end goes on, as on a resume
            self.window.run_core('finish')
        elif stop == 'live':
            # [designed: T116] An existing live page needs a new pose, not another geometry/focus transition.
            if self.views.currentIndex()!=4:self.show(4)
            try:
                if not self.watch_suspended:self.resume_viewer()
            except (OSError, ValueError) as exc:
                self.stop_viewer(str(exc))
        elif stop == 'summary-save':
            self.summary_board.set_lines(_board_lines(state['board'], 'FULL TIME'))
            self.show(5)
        else:
            self.queue = list(state['pages'][self.first_page:]);self.after = 'menu';self.next_page()

    def show_notice(self, state):
        """[confirmed: code/seg_0791_13.asm 7FCF] the managed side's notice: a key opens the match menu (the bench),
        none (or Esc) lets it pass; the players the original marks are read from its status words (1771:42BC)."""
        notice = state['notice']
        # [confirmed: code/seg_0791_13.asm 8062-80A9] it is offered at each stoppage while a substitution is asked for
        # (DS:9B40); letting it pass does not clear that
        self.notice_note.setText('The original offers a substitution: ' + (', '.join(
            f"{p['name']} {p['readiness']}" for p in notice['players']) or 'press any key for the bench')
            + '. Let it pass and the original asks again at each stoppage, until a substitution is made.')
        self.show(3)

    def show_shootout_order(self, state):
        from goal2.desktop.core_roles import role_code
        order=state['order'];self.state=state
        self.shootout_roster.unavailable={i for i,p in enumerate(order['players']) if not p['available']}
        self.shootout_title.setText(f"SHOOTOUT ORDER / {order['name'].upper()} / {len(order['picks'])} OF {order['needed']}")
        self.shootout_roster.set_rows([(p['player'],
            (f"{p['rank']:2}. " if p['rank'] else '    ')+p['name'],role_code(p),p['line'],True,False)
            for p in order['players']],order['slot']-1)
        self.show(6);self.refresh_shootout_card()

    def refresh_shootout_card(self):
        if self.window.core_jobs.busy or self.state is None or self.state['stop']!='shootout-order':return
        from goal2.desktop.player_card import core_card
        row=self.shootout_roster.current
        players=self.state['order']['players']
        if 0<=row<len(players):
            self.shootout_card.set_card(core_card(self.window.model.card(players[row]['player'])))
        self.refresh_shootout_controls()

    def refresh_shootout_controls(self):
        active=self.state is not None and self.state['stop']=='shootout-order' and not self.window.core_jobs.busy
        players=self.state['order']['players'] if active else []
        row=self.shootout_roster.current
        choice=players[row] if 0<=row<len(players) else None
        self.shootout_pick.setEnabled(bool(choice and choice['available'] and choice['rank'] is None))
        self.shootout_undo.setEnabled(bool(active and self.state['order']['picks']))

    def pick_shootout(self):
        if not self.shootout_pick.isEnabled() or self.window.core_jobs.busy:return
        player=self.state['order']['players'][self.shootout_roster.current]['player']
        self.window.run_core('shootout_pick',player)

    def show_captain(self):
        from goal2.desktop.core_roles import role_code
        state = self.window.model.round_state();self.state = state
        choice = state['captain']
        rows = [(r['player'], r['name'], role_code(r), r['line'], True, r['player'] == choice['captain'])
                for r in choice['eleven']]
        self.captain_roster.caption = choice['name'].upper()
        current = next((i for i, r in enumerate(rows) if r[5]), 0)
        self.captain_roster.set_rows(rows, current)
        self.captain_title.setText(f"CAPTAIN / {choice['name'].upper()}")
        self.captain_note.setText('Up/Down: the player who captains; Enter: kick off with him. C: the original '
                                  'picks its own (its best leader). Choose Watch for the pitch, '
                                  'or leave it off for the original\'s quick result.')
        self.refusal.setText(f"Last original refusal: {state['refused']}. Play checks again." if state['refused'] else '')
        self.show(0)

    def show_pre_match(self):
        state = self.window.model.round_state()
        self.bench.message = '';self.bench.offer(state, 'pre_match');self.show(1)

    def kick_off_selected(self):
        rows = self.captain_roster.rows
        if rows and 0 <= self.captain_roster.current < len(rows):
            self.start_kick_off(rows[self.captain_roster.current][0])

    def start_kick_off(self, captain):
        if self.window.core_jobs.busy:return
        self.watch_suspended = False
        if self.window.run_core('kick_off', captain, self.watch.isChecked()):
            self.show_waiting('The original plays the first half…')

    def start_play_on(self):
        """Play on at half time: the second half and the round's last screens, as a job."""
        if self.window.core_jobs.busy:return
        self.first_page = len(self.window.model.driver.pages)
        if self.window.run_core('play_on'):
            self.show_waiting('The original plays the second half…')

    def resume_viewer(self):
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.core_roles import pitch_identity
        if self.state is None or self.state['stop'] != 'live' or self.window.core_jobs.busy:return
        if self.viewer is None:
            self.viewer = CoreViewer(pitch_identity(self.window.model.state, self.state['identity']))
        self.watch_suspended = False
        self.viewer.pose(self.state['pitch'], self.state['commentary'], self.state.get('speed'))
        self.resume_watch.hide()
        self.live_note.setText('The match is in the pitch window. Enter there opens the bench.')
        self.viewer_timer.start()
        self.refresh_match_button()

    def refresh_match_button(self):
        """[designed: T138] Navigation stays outside the disabled game-action list."""
        button = self.window.core_show_match
        existing = (self.viewer is not None and not self.viewer.closed
                    and self.viewer.process is not None and self.viewer.process.poll() is None)
        resumable = bool(self.state and self.state['stop'] in ('live','taker-pitch')
                         and not self.window.core_jobs.busy)
        button.setEnabled(existing or resumable)
        button.setText('SHOW MATCH (F8)' if existing or not resumable else 'RESUME MATCH WINDOW (F8)')
        button.setShortcut('F8')  # QAbstractButton.setText replaces its shortcut.
        button.setToolTip('Bring the existing match window forward' if existing else
                          'Resume watching from the current original stop' if resumable else
                          'No match window is available')

    def show_match(self):
        """[designed: owner #430] Focus the owned viewer, or explicitly resume its live stop."""
        try:
            if (self.viewer is not None and not self.viewer.closed
                    and self.viewer.process is not None and self.viewer.process.poll() is None):
                self.viewer.show_window()
            elif self.state and self.state['stop'] in ('live','taker-pitch') and not self.window.core_jobs.busy:
                if self.viewer is not None:
                    self.viewer.close();self.viewer = None
                if self.state['stop']=='taker-pitch':self.show_taker_pitch(self.state)
                else:self.resume_viewer()
                if self.viewer is None:return False
                self.viewer.show_window()
            else:
                self.refresh_match_button();return False
        except (OSError, ValueError) as exc:
            self.window.status.setText(f'Cannot show match window: {exc}')
            self.refresh_match_button();return False
        self.window.status.setText('Match window requested; Enter in the pitch opens the bench.')
        self.refresh_match_button();return True

    def stop_viewer(self, message):
        self.viewer_timer.stop()
        self.watch_suspended = True
        if self.viewer is not None:
            self.viewer.close();self.viewer = None
        self.live_note.setText(message + '. The original waits here; resume watching or save the core.')
        self.resume_watch.setEnabled(True)
        self.resume_watch.show()
        if self.state and self.state['stop']=='taker-pitch':
            self.takers.preview_note.setText(message+'. The original still waits; return to choices or show the pitch again.')
            self.takers.refresh_controls()
        if self.pending_stop is not None:
            pending, self.pending_stop = self.pending_stop, None
            self.finished(*pending)
        self.refresh_match_button()

    def poll_viewer(self):
        if self.viewer is None:return
        # [designed: T116] The current bounded worker step already owns the core. SDL retains ordered input;
        # re-reading/hashing its unchanged status while that step runs only competes with emulation.
        if self.window.core_jobs.busy:return
        try:
            request = self.viewer.poll()
            if request in ('bench','left','right'):
                from goal2.core.screens import RETURN, LEFT, RIGHT
                if len(self.pending_inputs)>=64:raise ValueError('Core input queue overflow')
                self.pending_inputs.append({'bench':RETURN,'left':LEFT,'right':RIGHT}[request])
            if self.viewer.closed:
                self.stop_viewer('The pitch window was closed');return
            if self.pending_stop is not None and self.viewer.drained:
                pending, self.pending_stop = self.pending_stop, None
                self.finished(*pending)
                return
            self.takers.refresh_controls()
            if (self.state and self.state['stop'] in ('taker','taker-pitch') and self.viewer.drained
                    and self.pending_inputs and not self.window.core_jobs.busy):
                if self.window.run_core('taker_key',self.pending_inputs[0]):
                    self.pending_inputs.pop(0)
                return
            if (self.state and self.state['stop'] == 'live' and self.viewer.drained
                    and not self.window.core_jobs.busy):
                key = self.pending_inputs[0] if self.pending_inputs else None
                if self.window.run_core('live_step', key) and self.pending_inputs:
                    self.pending_inputs.pop(0)
        except (OSError, ValueError) as exc:
            self.stop_viewer(str(exc))

    def save_summary(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self.window, 'Save match summary', 'match-summary.txt', 'Text (*.txt)')
        if not path:return
        try:
            self.window.model.export_summary(path)
        except (OSError, ValueError) as exc:
            self.window.status.setText(str(exc));return
        self.window.run_core('summary_done')

    def show_taker_pitch(self,state):
        """[designed:T120] A frozen existing SDL renderer; no live_step while CF3A reads its dismissal key."""
        from goal2.desktop.core_viewer import CoreViewer
        from goal2.desktop.core_roles import pitch_identity
        if self.window.core_jobs.busy:
            return
        try:
            if self.viewer is None:
                self.viewer = CoreViewer(pitch_identity(self.window.model.state, state['identity']))
            if self.viewer.display.frame_sequence >= 0 and not self.viewer.drained:
                self.takers.preview_note.setText('The pitch is being displayed…')
                return
            self.viewer.pose(state['pitch'],state.get('commentary',[]),state['speed'])
            self.viewer_timer.start()  # the manager's blocking read freezes the core, not an invented match tick
            self.takers.preview_note.setText('The original waits. Enter in the pitch window or Return here goes back to the selector.')
        except (OSError,ValueError) as exc:
            self.stop_viewer(str(exc))
        self.takers.refresh_controls()
        self.refresh_match_button()

    def next_page(self):
        if self.window.core_jobs.busy:return
        managed = tuple(m['country'] for m in self.window.model.desk()['managers'])
        if self.after in ('round-continue','shootout-begin') and not self.queue:
            action='round_continue' if self.after=='round-continue' else 'shootout_start'
            if self.window.run_core(action):
                self.after = None;self.show_waiting('The original continues the round…')
            return
        self.page_next.setText('Next > (Enter)')
        if self.queue:
            kind, view = self.queue.pop(0)
            self.page_board.title = PAGE_TITLES.get(kind, kind.upper())
            # [designed: T110] A bulletin keeps its three original columns; it is never flattened or sliced.
            if kind == 'bulletin':
                self.bulletin_columns.set_content(view);self.page_content.setCurrentIndex(1)
                self.page_board.set_lines([])
            elif kind == 'championship-bracket':
                self.round_bracket_board.set_view(view, managed);self.page_content.setCurrentIndex(2)
                self.page_board.set_lines([])
            else:
                self.page_board.set_lines(_page_lines(kind, view, managed));self.page_content.setCurrentIndex(0)
            self.page_count.setText(f"{PAGE_TITLES.get(kind, kind)}: {len(self.queue)} more")
            self.shown = (kind, view);self.show(2);return
        if self.after == 'shootout-announcement':
            self.page_board.title='PENALTY SHOOTOUT'
            # [designed: T118] Report the current guest score without assuming its preceding phase.
            self.page_board.set_lines(_board_lines(self.state['board'],'MATCH SCORE'))
            self.page_content.setCurrentIndex(0);self.page_count.setText(self.state['message'])
            self.page_next.setText('Choose shootout order (Enter)')
            self.after='shootout-begin';self.show(2)
        elif self.after == 'round-paused':
            self.page_board.title = "THE ROUND'S RESULTS"
            self.page_board.set_lines(_page_lines('round-results',self.state['results'],managed))
            self.page_content.setCurrentIndex(0)
            self.page_count.setText(self.state['message'])
            self.page_next.setText('Continue (Enter)')
            self.after = 'round-continue';self.show(2)
        elif self.after in ('bulletin-achievement','bulletin-congratulations'):
            # [designed: #395] Keep the guest frozen until the player's Continue.
            self.bulletin_columns.set_content(self.state['bulletin']);self.page_content.setCurrentIndex(1)
            self.page_board.set_lines([]);self.page_count.setText('')
            self.page_next.setText('Continue (Enter)')
            self.after = 'round-continue';self.show(2)
        elif self.after == 'captain':
            self.after = None;self.show_captain()
        else:
            self.after = None;core_fixtures_view(self.window, 0);self.window.navigate(0)

    def escape(self):
        if self.views.currentIndex() in (self.takers.choice_index,self.takers.preview_index):
            self.takers.key(27)
            return True
        if self.views.currentIndex()==6:
            if self.shootout_undo.isEnabled():self.shootout_undo.click()
            return True
        if self.views.currentIndex() == 1:
            return self.bench.escape()
        return False
