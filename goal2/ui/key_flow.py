"""[designed: owner #598] Wrap complete keyboard actions without shrinking their text."""
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QFrame, QLayout, QWidgetItem

class KeyFlow(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items=[]
    def addItem(self,item): self.items.append(item)
    def count(self): return len(self.items)
    def itemAt(self,index): return self.items[index] if 0<=index<len(self.items) else None
    def takeAt(self,index): return self.items.pop(index) if 0<=index<len(self.items) else None
    def insertWidget(self,index,widget):
        self.addChildWidget(widget)
        self.items.insert(max(0,index),QWidgetItem(widget))
        self.invalidate()
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self,width): return self.arrange(QRect(0,0,width,0),True)
    def setGeometry(self,rect):
        super().setGeometry(rect)
        self.arrange(rect,False)
    def minimumSize(self):
        size=QSize()
        for item in self.items: size=size.expandedTo(item.minimumSize())
        margins=self.contentsMargins()
        return size+QSize(margins.left()+margins.right(),margins.top()+margins.bottom())
    def sizeHint(self): return self.minimumSize()
    def arrange(self,rect,measure):
        margins=self.contentsMargins()
        area=rect.adjusted(margins.left(),margins.top(),-margins.right(),-margins.bottom())
        x,y,height=area.x(),area.y(),0
        for item in self.items:
            if item.isEmpty(): continue
            size=item.sizeHint()
            if x>area.x() and x+size.width()>area.right()+1:
                x=area.x();y+=height+self.spacing();height=0
            if not measure: item.setGeometry(QRect(x,y,min(size.width(),area.width()),size.height()))
            x+=size.width()+self.spacing();height=max(height,size.height())
        return y+height-rect.y()+margins.bottom()


class KeyBar(QFrame):
    def minimumSizeHint(self):
        return QSize(0,self.layout().heightForWidth(self.width())) if self.layout() else QSize(0,0)
    def sizeHint(self): return self.minimumSizeHint()
