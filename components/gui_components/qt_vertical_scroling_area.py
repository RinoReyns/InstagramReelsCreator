from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollArea, QVBoxLayout, QWidget


class VerticalScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)

        # content widget that actually holds your items
        content = QWidget()
        self.vbox = QVBoxLayout(content)
        self.vbox.setContentsMargins(8, 8, 8, 8)
        self.vbox.setSpacing(8)

        # make the scroll area resize its content width to match
        self.setWidgetResizable(True)
        self.setWidget(content)

        # only vertical scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # optional: better look on high-DPI
        self.setAlignment(Qt.AlignTop)

    def addLayout(self, layer):
        self.vbox.addLayout(layer)

    def addWidget(self, w):
        self.vbox.addWidget(w)

    def add_stretch(self):
        self.vbox.addStretch(1)
