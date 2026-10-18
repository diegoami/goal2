"""[designed: #182/T74] Shared football shell tokens; system fonts stay native."""
COLORS=dict(background='#081c18',panel='#102b25',raised='#1a3b32',text='#f5f2e8',
 secondary='#bbcfc5',paper='#f3efe2',ink='#17352c',accent='#c8f279',warning='#ffd17a',
 error='#ffb4a9',divider='#5a7c6e',focus='#ffe799')

def apply_style(window):
    c=COLORS
    title_size=32 if window.devicePixelRatioF()>1 else 40
    window.setStyleSheet(f"""
    QMainWindow, QDialog, QScrollArea, QScrollArea > QWidget > QWidget {{background:{c['background']};color:{c['text']};}}
    QWidget {{font-size:16px; color:{c['text']};}}
    QLabel#countryTitle {{font-size:{title_size}px;font-weight:700;}}
    QLabel#pageHeading {{font-size:24px;font-weight:600;padding:4px;}}
    QPushButton,QComboBox,QLineEdit,QCheckBox {{font-size:14px;min-height:40px;}}
    QPushButton,QComboBox,QLineEdit {{background:{c['panel']};border:1px solid {c['divider']};border-radius:4px;padding:0px 8px;}}
    QPushButton:checked {{background:{c['accent']};color:{c['ink']};font-weight:600;}}
    QPushButton:hover {{background:{c['raised']};}}
    QPushButton:checked:hover {{background:{c['accent']};color:{c['ink']};}}
    QPushButton:checked:focus {{border:3px solid {c['ink']};}}
    QPushButton:disabled,QComboBox:disabled,QLineEdit:disabled,QCheckBox:disabled {{color:{c['secondary']};background:{c['panel']};}}
    QPushButton:focus,QComboBox:focus,QLineEdit:focus,QCheckBox:focus,QTableWidget:focus,QLabel#pageHeading:focus {{border:3px solid {c['focus']};}}
    QComboBox QAbstractItemView {{background:{c['panel']};color:{c['text']};selection-background-color:{c['accent']};selection-color:{c['ink']};border:1px solid {c['divider']};}}
    QLineEdit {{selection-background-color:{c['accent']};selection-color:{c['ink']};}}
    QTableWidget {{font-size:14px;background:{c['paper']};color:{c['ink']};gridline-color:{c['divider']};selection-background-color:{c['accent']};selection-color:{c['ink']};}}
    QHeaderView::section {{background:{c['raised']};color:{c['text']};padding:8px;}}
    QScrollArea {{border:0;}}
    """)
