"""[designed: T74] Fixtures container for existing window-owned controls."""
from PySide6.QtCore import Qt
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
    self.result=card(half_box,'Goals and result details','resultDetails')
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
    from PySide6.QtGui import QKeySequence,QShortcut
    self.fixtures_escape=QShortcut(QKeySequence('Escape'),page)
    self.fixtures_escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    self.fixtures_escape.activated.connect(lambda:self.fixture_views.currentIndex()==3 and fixtures_view(self,0))


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
