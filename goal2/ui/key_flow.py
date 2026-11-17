"""[designed: owner #598] Wrap complete keyboard actions without shrinking their text."""
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QFrame, QLayout, QWidgetItem

class KeyFlow(QLayout):
    # [designed: T211] On the grid the rows touch (`line_spacing` 0 where the keys are a cell apart) and the keys sit on the
    # bar's bottom rows (`bottom`), so a bar of fewer rows than it was given leaves its empty rows above.
    line_spacing=None
    bottom=False
    rows=0   # the rows the bar always has, on the grid
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
    def heightForWidth(self,width):
        height=self.arrange(QRect(0,0,width,0),True)
        if self.rows and self.parentWidget() is not None:
            from goal2.ui import cells
            height=max(height,cells.span_px(self.parentWidget(),self.rows))
        return height
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
        gap=self.spacing() if self.line_spacing is None else self.line_spacing
        if self.bottom and not measure:
            used=self.arrange(rect,True)-margins.top()-margins.bottom()
            area.moveTop(area.y()+max(0,area.height()-used))
        x,y,height=area.x(),area.y(),0
        for item in self.items:
            if item.isEmpty(): continue
            size=item.sizeHint()
            if x>area.x() and x+size.width()>area.right()+1:
                x=area.x();y+=height+gap;height=0
            if not measure: item.setGeometry(QRect(x,y,min(size.width(),area.width()),size.height()))
            x+=size.width()+self.spacing();height=max(height,size.height())
        return y+height-rect.y()+margins.bottom()


class KeyBar(QFrame):
    def minimumSizeHint(self):
        return QSize(0,self.layout().heightForWidth(self.width())) if self.layout() else QSize(0,0)
    def sizeHint(self): return self.minimumSizeHint()
