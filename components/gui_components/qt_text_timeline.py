from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QWidget,
)

from utils.data_structures import PIXELS_PER_SEC


class TextTimelineWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.timelineView = QGraphicsView()
        self.timelineScene = QGraphicsScene()
        self.timelineView.setScene(self.timelineScene)
        self.timelineView.setFixedHeight(300)
        self.timeline_view_controls_layout = QHBoxLayout()

    def draw_text_time_grid(self, max_seconds):
        for second in range(max_seconds + 1):
            x = 10 + second * PIXELS_PER_SEC
            self.timelineScene.addLine(x, 0, x, 220, Qt.gray)
            label = QGraphicsTextItem(f"{second}s")
            label.setPos(x + 2, 220)
            self.timelineScene.addItem(label)
