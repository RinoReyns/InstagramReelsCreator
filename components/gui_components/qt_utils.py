from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel


def get_header_text_label(text):
    text_label = QLabel(text)
    font = QFont()
    font.setPointSize(12)
    font.setBold(True)
    font.setUnderline(True)
    text_label.setFont(font)
    return text_label
