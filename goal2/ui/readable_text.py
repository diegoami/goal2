"""[designed: owner #598] A bounded recent transcript containing only complete wrapped entries."""
from PySide6.QtCore import QRect, Qt

def recent_text(lines,metrics,width,height,maximum=15):
    kept=[]
    for text in reversed(lines[-maximum:]):
        trial=[text]+kept
        value="\n".join(trial)
        bounds=metrics.boundingRect(QRect(0,0,max(1,width-2),100000),int(Qt.TextFlag.TextWordWrap),value)
        if bounds.height()>max(0,height-2):break
        kept=trial
    return "\n".join(kept)


import textwrap

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLabel, QSizePolicy

from goal2.ui import cells


def recent_cells(lines,columns,rows,maximum=15):
    """[designed: T212] `recent_text` in cells: the newest of `lines` (at most `maximum`), each wrapped at `columns` characters
    (as `cells.CellPara` wraps), as many whole entries as fit in `rows` rows, oldest first, one entry to a line of the text."""
    kept,used=[],0
    for text in reversed(lines[-maximum:]):
        need=len(textwrap.wrap(text,max(1,columns),drop_whitespace=True) or [""])
        if used+need>rows:break
        kept.insert(0,text);used+=need
    return "\n".join(kept)

class Excerpt(QLabel):
    """[designed: owner #598] One-line header preview; the full entry stays in commentary."""
    def __init__(self):
        super().__init__()
        self._full_text=''
        self.setObjectName('value')
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
    def setText(self,text):
        self._full_text=text
        self._fit()
    # [designed: T212] a row of the cell, not the font's line box (a pixel taller at some sizes): the preview is one row on the grid
    def sizeHint(self): return QSize(250,cells.row_px(self))
    def minimumSizeHint(self): return QSize(0,cells.row_px(self))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._fit()
    def changeEvent(self,event):
        super().changeEvent(event)
        self._fit()
    def _fit(self):
        if not hasattr(self,'_full_text'): return
        shown=self.fontMetrics().elidedText(self._full_text,Qt.TextElideMode.ElideRight,max(0,self.width()))
        if QLabel.text(self)!=shown: QLabel.setText(self,shown)
