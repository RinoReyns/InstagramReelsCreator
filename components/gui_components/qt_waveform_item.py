import numpy as np
import soundfile as sf
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QPen
from PyQt5.QtWidgets import QGraphicsItem

from utils.data_structures import PIXELS_PER_SEC


class WaveformItem(QGraphicsItem):
    def __init__(self, width=800, height=60):
        super().__init__()
        self.width = width
        self.height = height
        self.samples = None
        self.setFlag(QGraphicsItem.ItemClipsToShape, True)
        self.duration = 0

    def load_waveform(self, audio_path):
        try:
            self.samples, sr = sf.read(audio_path)
            self.samples = self.samples[:, 0]
            self.duration = len(self.samples) / sr
        except Exception as e:
            print(f"Error loading waveform: {e}")
            return np.array([])

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        if self.samples is None or self.samples.size == 0:
            return

        pen = QPen(Qt.blue)
        painter.setPen(pen)

        self.width = int(self.duration * PIXELS_PER_SEC)
        self.prepareGeometryChange()  # Notify Qt of geometry change

        mid_y = self.height / 2
        samples_per_pixel = len(self.samples) / self.width

        for x in range(self.width):
            idx = int(x * samples_per_pixel)
            if idx >= len(self.samples):
                break
            val = self.samples[idx]
            y = mid_y - val * (self.height / 2)
            painter.drawLine(QPointF(x, mid_y), QPointF(x, y))
