from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QWidget


class VolumeBar(QWidget):
    def __init__(self):
        super().__init__()
        self.volume = 100
        self.setFixedHeight(30)
        self.setMaximumWidth(100)

    def setVolume(self, vol):
        self.volume = vol
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        bar_width = int((self.volume / 100) * (self.width() - 20))
        painter.setBrush(QColor(0, 150, 255))
        painter.drawRect(10, 10, bar_width, 10)
        painter.setPen(QColor(0, 0, 0))
        painter.drawRect(10, 10, self.width() - 20, 10)
