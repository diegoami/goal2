"""[designed: T90; accepted vision #266 render.py palette] The original-style shell tokens
(body sizes stay at T74's until T91 recomposes the pages for larger type):
black screens, large monospaced type, strong functional colours. Token names are kept from
T74 (#182) so every surface and check reads the same keys."""
COLORS=dict(background='#000000',panel='#000000',raised='#1a1a1a',text='#eeeeee',
 secondary='#aaaaaa',paper='#000000',ink='#000000',accent='#aaaaaa',warning='#ffff55',
 error='#ff5555',divider='#55ffff',focus='#ffff55',
 # [designed: accepted #266] the functional colours.
 cyan='#55ffff',red='#ff5555',yellow='#ffff55',green='#55ff55',magenta='#ff55ff',gold='#ffbb33')
FONT="'DejaVu Sans Mono','Consolas','Courier New',monospace"
# [designed: #278, found by the Windows workflow] The game ships its monospace font: Windows has no
# DejaVu Sans Mono, and its fallbacks have other metrics, so the shell's minimum size outgrew the
# 900x700 target. DejaVu fonts (fonts/LICENSE: Bitstream Vera, free to redistribute) are bundled.
from pathlib import Path
FONT_FILES=tuple(Path(__file__).with_name('fonts')/name for name in ('DejaVuSansMono.ttf','DejaVuSansMono-Bold.ttf'))
_LOADED=[]


def load_fonts():
    """Register the bundled fonts with Qt once per process; returns their font ids."""
    if not _LOADED:
        from PySide6.QtGui import QFontDatabase
        _LOADED.extend(QFontDatabase.addApplicationFont(str(path)) for path in FONT_FILES)
    return list(_LOADED)


def apply_style(window):
    load_fonts();c=COLORS
    window.setStyleSheet(f"""
    QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget, QWidget#shellRoot, QStackedWidget {{background:{c['background']};color:{c['text']};}}
    QWidget {{font-family:{FONT};font-size:16px;color:{c['text']};}}
    QFrame#topBar, QFrame#sideBar {{border:2px solid {c['cyan']};background:{c['background']};}}
    QLabel#brand {{font-size:34px;font-weight:700;color:{c['cyan']};}}
    QLabel#countryTitle {{font-size:34px;font-weight:700;color:{c['yellow']};}}
    QLabel#careerLine, QLabel#countryContext {{font-size:20px;color:{c['text']};}}
    QLabel#nextLine {{font-size:26px;font-weight:700;color:{c['cyan']};}}
    QLabel#nextDetail {{font-size:20px;color:{c['text']};}}
    QLabel#sideHint {{color:{c['magenta']};font-size:16px;}}
    QLabel#pageHeading {{font-size:26px;font-weight:700;color:{c['red']};padding:4px;}}
    QPushButton,QComboBox,QLineEdit,QCheckBox {{font-size:14px;min-height:40px;}}
    QPushButton {{background:{c['background']};color:{c['cyan']};border:2px solid {c['cyan']};padding:0px 12px;font-weight:700;text-align:left;}}
    QComboBox,QLineEdit {{background:{c['background']};color:{c['green']};border:2px solid {c['cyan']};padding:0px 8px;}}
    QFrame#sideBar QPushButton {{border:0;font-size:22px;}}
    QPushButton:checked {{background:{c['accent']};color:{c['ink']};}}
    QPushButton:hover {{background:{c['raised']};}}
    QPushButton:checked:hover {{background:{c['accent']};color:{c['ink']};}}
    QPushButton:checked:focus {{border:3px solid {c['focus']};}}
    QPushButton:disabled,QComboBox:disabled,QLineEdit:disabled,QCheckBox:disabled {{color:#777777;border-color:#555555;}}
    QPushButton:focus,QComboBox:focus,QLineEdit:focus,QCheckBox:focus,QTableWidget:focus,QLabel#pageHeading:focus {{border:3px solid {c['focus']};}}
    QComboBox QAbstractItemView {{background:{c['background']};color:{c['text']};selection-background-color:{c['accent']};selection-color:{c['ink']};border:1px solid {c['cyan']};}}
    QLineEdit {{selection-background-color:{c['accent']};selection-color:{c['ink']};}}
    QCheckBox {{color:{c['text']};}}
    QTableWidget {{font-size:14px;background:{c['paper']};color:{c['text']};gridline-color:#444444;selection-background-color:{c['accent']};selection-color:{c['ink']};border:2px solid {c['cyan']};}}
    QHeaderView {{background:{c['background']};}}
    QHeaderView::section {{background:{c['background']};color:{c['gold']};padding:8px;border:0;border-bottom:1px solid {c['cyan']};font-weight:700;}}
    QTableCornerButton::section {{background:{c['background']};border:0;}}
    QFrame#overviewCard {{background:{c['background']};border:2px solid {c['red']};}}
    QLabel#cardHeading {{font-size:14px;color:{c['red']};font-weight:700;}}
    QFrame#deskPanel {{background:{c['background']};border:2px solid {c['red']};}}
    QLabel#deskHeading {{font-size:20px;color:{c['red']};font-weight:700;}}
    QLabel#deskOwn, QLabel#deskOpponent {{font-size:22px;color:{c['text']};}}
    QLabel#deskCampaign {{font-size:20px;color:{c['yellow']};}}
    QLabel#deskReadiness {{font-size:22px;color:{c['green']};font-weight:700;}}
    QLabel#resultTitle {{font-size:30px;color:{c['red']};font-weight:700;}}
    QLabel#resultSubtitle {{font-size:22px;color:{c['gold']};font-weight:700;}}
    QFrame#resultPanel {{background:{c['background']};border:2px solid {c['cyan']};}}
    QLabel#resultHeading {{font-size:20px;color:{c['cyan']};font-weight:700;}}
    QLabel#resultScorersA, QLabel#resultScorersB {{font-size:20px;color:{c['yellow']};}}
    QLabel#resultStatistics {{font-size:18px;color:{c['green']};}}
    QLabel#resultMotm {{font-size:26px;color:{c['yellow']};font-weight:700;}}
    QLabel#resultNote {{font-size:14px;color:{c['magenta']};}}
    QPushButton#resultContinue, QPushButton#resultRound {{font-size:20px;padding:8px 16px;}}
    QLabel#prepTitle {{font-size:28px;color:{c['red']};font-weight:700;}}
    QFrame#playPanel {{background:{c['background']};border:2px solid {c['red']};}}
    QLabel#prepHeading {{font-size:20px;color:{c['red']};font-weight:700;}}
    QLabel#prepQuick, QLabel#prepWatch {{font-size:18px;color:{c['text']};}}
    QLabel#prepSpeedHeading {{font-size:20px;color:{c['yellow']};font-weight:700;}}
    QLabel#prepNote {{font-size:14px;color:{c['magenta']};}}
    QPushButton#speedSlow:checked, QPushButton#speedNormal:checked, QPushButton#speedFast:checked {{background:{c['accent']};color:{c['ink']};}}
    QPushButton#deskPrepare {{font-size:20px;text-align:left;padding:8px 12px;}}
    QLabel#poolCardCaption {{font-size:20px;color:{c['yellow']};font-weight:700;}}
    QLabel#deskCaptain {{font-size:20px;color:{c['yellow']};}}
    QPushButton#deskTeam, QPushButton#deskPool, QPushButton#deskFixtures, QPushButton#deskCard, QPushButton#deskManager {{font-size:20px;text-align:left;padding:8px 12px;}}
    QLabel#overviewCountry {{font-size:24px;font-weight:700;color:{c['yellow']};}}
    QLabel#overviewFixture,QLabel#overviewResult {{font-size:20px;font-weight:600;color:{c['green']};}}
    QLabel#lineupBoard,QLabel#benchBoard,QLabel#playerDetail {{background:{c['background']};border:2px solid {c['cyan']};padding:16px;}}
    QLabel#tacticsTitle {{font-size:26px;font-weight:700;color:{c['red']};}}
    QFrame#tacticsTeam {{background:{c['background']};border:2px solid {c['gold']};}}
    QFrame#tacticsDefaults {{background:{c['background']};border:2px solid {c['red']};}}
    QLabel#tacticsHeading {{font-size:20px;font-weight:700;color:{c['gold']};}}
    QLabel#tacticsDefaultsHeading {{font-size:20px;font-weight:700;color:{c['red']};}}
    QLabel#tacticsManager, QLabel#captainLabel {{font-size:20px;color:{c['yellow']};}}
    QComboBox#captain {{font-size:20px;color:{c['yellow']};}}
    QFrame#tacticsTeam QLabel#lineupBoard, QFrame#tacticsTeam QLabel#benchBoard {{border:0;padding:4px 0px;font-size:18px;color:{c['green']};}}
    QPushButton[tacticRow="true"] {{font-size:20px;min-height:44px;border:0;}}
    QLabel#tacticsHint {{color:{c['magenta']};font-size:16px;}}
    QPushButton#teamPool, QPushButton#teamTableRoute, QPushButton#teamTacticsRoute, QPushButton#renamePlayer, QPushButton#confirmPlan, QPushButton#discardPlan, QPushButton#tableBack {{font-size:20px;padding:4px 12px;}}
    QTableWidget#squad {{font-weight:700;gridline-color:#333333;}}
    QTableWidget#squad::indicator {{width:18px;height:18px;}}
    QTableWidget#squad::indicator:unchecked {{background:{c['background']};border:2px solid {c['red']};}}
    QTableWidget#squad::indicator:checked {{background:{c['green']};border:2px solid {c['green']};}}
    QTableWidget#squad::indicator:disabled {{background:{c['background']};border:2px dotted #777777;}}
    QTableWidget#squad::indicator:checked:disabled {{background:#777777;border:2px solid #777777;}}
    QLabel#squadSummary {{font-size:18px;color:{c['yellow']};}}
    QWidget#draftBar {{background:{c['background']};border-top:2px solid {c['cyan']};}}
    QLabel#draftState {{color:{c['warning']};font-size:14px;font-weight:700;}}
    QWidget#draftBar QPushButton {{border:3px solid {c['cyan']};}}
    QWidget#draftBar QPushButton:focus {{border:3px solid {c['focus']};}}
    QLabel#status {{color:{c['magenta']};}}
    QScrollArea {{border:0;}}
    QScrollBar:vertical {{background:{c['background']};width:14px;border:1px solid {c['cyan']};}}
    QScrollBar:horizontal {{background:{c['background']};height:14px;border:1px solid {c['cyan']};}}
    QScrollBar::handle {{background:{c['accent']};min-width:24px;min-height:24px;}}
    QScrollBar::add-line, QScrollBar::sub-line {{width:0;height:0;}}
    QScrollBar::add-page, QScrollBar::sub-page {{background:none;}}
    QMenuBar, QMenu {{background:{c['background']};color:{c['cyan']};}}
    QMenuBar::item:selected, QMenu::item:selected {{background:{c['accent']};color:{c['ink']};}}
    QMessageBox, QInputDialog {{background:{c['background']};}}
    QMessageBox QLabel, QInputDialog QLabel {{color:{c['text']};font-size:20px;}}
    """)
