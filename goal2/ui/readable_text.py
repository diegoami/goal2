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
