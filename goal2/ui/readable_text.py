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


from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLabel, QSizePolicy

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
    def sizeHint(self): return QSize(250,self.fontMetrics().height())
    def minimumSizeHint(self): return QSize(0,self.fontMetrics().height())
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
