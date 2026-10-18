"""[designed: T79] Match reading surface; existing window callbacks own every action."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame,QVBoxLayout,QGridLayout,QLabel,QPushButton,QComboBox
from goal2.desktop.style import COLORS


def build(window, layout):
    panel=QFrame();panel.setObjectName('matchSurface');panel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    panel.setAccessibleName('Match presentation');body=QVBoxLayout(panel);body.setSpacing(8)
    window.match_surface=panel
    for attribute,name in (('match_provenance','matchProvenance'),('match_score','matchScore'),('match_progress','matchProgress')):
        label=QLabel();label.setObjectName(name);label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText);label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setAccessibleName({'matchProvenance':'Match provenance','matchScore':'Named match score','matchProgress':'Match progress'}[name])
        body.addWidget(label);setattr(window,attribute,label)
    c=COLORS
    panel.setStyleSheet(f'QFrame#matchSurface {{background:{c["panel"]};border:1px solid {c["divider"]};border-radius:8px;}}'
        f'QFrame#matchSurface:focus {{border:3px solid {c["focus"]};}}'
        f'QLabel#matchProvenance {{font-size:14px;color:{c["secondary"]};}}'
        'QLabel#matchScore {font-size:28px;font-weight:700;}'
        f'QLabel#matchProgress {{font-size:16px;color:{c["text"]};}}')
    window.play=QPushButton('Play quick friendly');window.play.setObjectName('playMatch')
    window.watch=QPushButton('Watch original friendly');window.watch.setObjectName('watchOriginal')
    # [designed] A vertical action group stays reachable at compact/high-DPI widths.
    body.addWidget(window.play);body.addWidget(window.watch)
    window.stop=QPushButton('Cancel match');window.stop.setObjectName('cancelMatch');window.stop.setEnabled(False)
    window.half_panel=QFrame();window.half_panel.setObjectName('halftimeDecision');half=QGridLayout(window.half_panel)
    heading=QLabel('Quick friendly · halftime decision');heading.setObjectName('cardHeading');half.addWidget(heading,0,0,1,2)
    window.half_out=QComboBox();window.half_in=QComboBox()
    window.substitute=QPushButton('Substitute');window.continue_match=QPushButton('Continue second half')
    half.addWidget(QLabel('Off'),1,0);half.addWidget(window.half_out,1,1)
    half.addWidget(QLabel('On'),2,0);half.addWidget(window.half_in,2,1)
    half.addWidget(window.substitute,3,0,1,2);half.addWidget(window.continue_match,4,0,1,2);half.setColumnStretch(1,1)
    for widget in (window.half_out,window.half_in,window.substitute,window.continue_match):widget.setEnabled(False)
    window.half_preview=None;body.addWidget(window.half_panel);layout.addWidget(panel)


def bind_keyboard(window):
    from PySide6.QtWidgets import QWidget
    QWidget.setTabOrder(window.standings,window.play)


def values(window):
    """[designed: T79] Read current authority, never reuse an old viewer after replacement."""
    from goal2.desktop.fixtures_page import snapshot
    display=window.display_model;state=display.state
    pending=state.campaign.next_fixture if state.campaign else None
    names=display.goaldat.country_names
    fixture=(names[pending.side_a]+' — '+names[pending.side_b]) if pending else 'Standalone friendly / no scheduled fixture'
    if window.preview is not None:
        return 'Country preview',fixture,'Return to the active country or explicitly start a new game.'
    if window.jobs.busy:
        half=window.jobs.halftime
        if half:
            a,b=half['teams'];x,y=half['score']
            return 'Quick simulation (rebuild setup)',f'{names[a]} {x} — {y} {names[b]}','Halftime · private decision. Continue second half or Cancel match; saving remains unavailable.'
        return 'Quick simulation (rebuild setup)',fixture,'Playing quick friendly… Cancel match preserves the committed game.'
    if window.competitive.busy:
        events=window.competitive.events
        if events:
            event=events[-1];a,b=pending.side_a,pending.side_b
            fixture=f'{names[a]} {event.score[0]} — {event.score[1]} {names[b]}'
        return 'Original engine — competitive',fixture,'Original competitive engine running. Cancel match remains available.'
    if window.watched.busy:
        d=window.watched.display
        if getattr(window.watched,'frames_enabled',False):
            pose=getattr(window,'_match_poses',{}).get(getattr(window.watched,'frame_ack',-1))
            if d.countries and pose is not None:
                fixture=f'{d.countries[0]} {pose["score"][0]} — {pose["score"][1]} {d.countries[1]}'
                progress=f'{pose["minute"]} min · rendered pitch sample. Cancel match remains available.'
            else:progress='Starting original friendly in Pygame… Waiting for the first rendered sample. Cancel match remains available.'
        elif d.countries and d.events:
            event=d.events[-1];fixture=f'{d.countries[0]} {event["score"][0]} — {event["score"][1]} {d.countries[1]}'
            progress=f'{event["minute"]} min · original engine running. Cancel match remains available.'
        else:progress='Starting original friendly in Pygame… Cancel match remains available.'
        return 'Original engine — friendly',fixture,progress
    if getattr(window.model,'match_pending',False):
        return 'Match in progress',fixture,'Waiting for the active match owner. Saving is unavailable.'
    last=state.last_match
    if last is not None:
        from goal2.game.watched_schema import watched
        data=snapshot(display)
        return ('Original engine' if watched(last) else 'Quick simulation (rebuild setup)'),data['score'],'Full time · '+data['stages']+' · Save / resume retains this completed game.'
    return 'No match played',fixture,'Choose an eligible play route below. Management edits must be confirmed first.'


def present(window):
    """[designed: T79] Pure widget updates; no engine start or management publication."""
    if not window.watched.busy or window.preview is not None:
        window._match_pose_token=None;window._match_poses={}
    provenance,score,progress=values(window)
    window.match_provenance.setText(provenance);window.match_score.setText(score);window.match_progress.setText(progress)


def observe(window):
    """[designed: T79] Remember only presentation fields until their existing flip ACK arrives."""
    controller=window.watched;token=controller.token
    if getattr(window,'_match_pose_token',None)!=token:
        window._match_pose_token=token;window._match_poses={}
    ack=getattr(controller,'frame_ack',-1)
    poses=getattr(window,'_match_poses',{})
    window._match_poses={k:v for k,v in poses.items() if k>=ack}
    if controller.display is not None:
        for frame in controller.display.frames:
            window._match_poses[frame['sequence']]={'minute':frame['minute'],'score':tuple(frame['score']),'watermark':frame['watermark']}
