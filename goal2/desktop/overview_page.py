"""[designed: T75] Displayed-country overview; the window owns every action."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame,QVBoxLayout,QLabel,QPushButton


def card(layout,title,name):
    panel=QFrame();panel.setObjectName('overviewCard');body=QVBoxLayout(panel)
    body.setContentsMargins(20,16,20,16);body.setSpacing(8)
    heading=QLabel(title);heading.setObjectName('cardHeading');body.addWidget(heading)
    text=QLabel();text.setObjectName(name);text.setWordWrap(True)
    text.setTextFormat(Qt.TextFormat.PlainText)
    text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    body.addWidget(text);layout.addWidget(panel)
    return text


def build(self,model,TACTICS):
    layout=self.pages[0].content
    self.overview_country_identity=card(layout,'Selected country','overviewCountry')
    self.overview_fixture=card(layout,'Next fixture','overviewFixture')
    self.overview_result=card(layout,'Last result','overviewResult')
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
    self.identity_art.setAccessibleName('Generic shirt and neutral decorative stripe for '+view['country_name'])
