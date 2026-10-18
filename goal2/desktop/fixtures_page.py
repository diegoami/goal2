"""[designed: T74] Fixtures container for existing window-owned controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit,QCheckBox)

def build(self,model,TACTICS):
    self.standings_dialog=None
    layout=self.pages[3].content
    self.fixture_next=card(layout,'Next fixture','fixtureNext')
    self.scoreboard=card(layout,'Last completed result','scoreboard')
    self.scoreboard.setStyleSheet('font-size: 22px; font-weight: 600;')
    self.result_stages=card(layout,'Match resolution','resultStages')
    self.standings=QPushButton('Competition table');self.standings.setObjectName('showStandings')
    self.pages[3].content.addWidget(self.standings)
    layout=self.pages[3].content
    play_bar=QHBoxLayout();self.play=QPushButton('Play quick friendly');self.stop=QPushButton('Cancel match');self.stop.setEnabled(False)
    self.watch=QPushButton('Watch original friendly');self.watch.setObjectName('watchOriginal')
    play_bar.addWidget(self.play);play_bar.addWidget(self.watch);layout.addLayout(play_bar)
    half_bar=QGridLayout();self.half_out=QComboBox();self.half_in=QComboBox()
    self.substitute=QPushButton('Substitute');self.continue_match=QPushButton('Continue second half')
    half_bar.addWidget(QLabel('Off'),0,0);half_bar.addWidget(self.half_out,0,1);half_bar.addWidget(self.substitute,0,2)
    half_bar.addWidget(QLabel('On'),1,0);half_bar.addWidget(self.half_in,1,1);half_bar.addWidget(self.continue_match,1,2)
    half_bar.setColumnStretch(1,1)
    for widget in (self.half_out,self.half_in,self.substitute,self.continue_match):widget.setEnabled(False)
    layout.addLayout(half_bar);self.half_preview=None
    self.result=card(layout,'Goals and result details','resultDetails')
    self.fixture_routes=QLabel();self.fixture_routes.setWordWrap(True);self.fixture_routes.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.fixture_routes)
    self.fixture_table=card(layout,'Standings snapshot','fixtureTable')


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
    self.fixture_next.setText(data['next']);self.scoreboard.setText(data['score'])
    self.result_stages.setText(data['stages']);self.result.setText(data['detail'])
    try:
        table=display.competition_table()
        self.fixture_table.setText('No complete opening group schedule' if table is None else
            'Current positions; qualification is provisional.\n'+
            '\n'.join(f"{r['rank']}. {r['name']}   P {r['played']}   GF {r['goals_for']}   GA {r['goals_against']}   GD {r['goal_difference']}   Pts {r['points']}" for r in table['rows']))
    except (ValueError,KeyError,IndexError) as exc:self.fixture_table.setText('Standings unavailable: '+str(exc))


def enabled(self,active):
    """[designed: T78; derived: T80/T50] Display existing routes; callbacks retain authority."""
    from goal2.engine.original_match.match import KINDS
    state=self.display_model.state;pending=state.campaign.next_fixture if state.campaign else None
    quick=state.campaign is None or (pending is not None and pending.kind==1)
    watch=pending is not None and pending.kind==1
    competitive=pending is not None and pending.kind!=1 and pending.kind in KINDS
    self.play.setEnabled(active and (quick or competitive));self.watch.setEnabled(active and watch)
    self.fixture_routes.setText(('Play: '+('quick friendly' if quick else 'original competitive') if quick or competitive else 'Play unavailable: unsupported pending fixture')+
        '\n'+('Watch: original friendly' if watch else 'Watch unavailable: scheduled friendlies only'))
