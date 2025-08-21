from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsTextItem

from components.gui_components.qt_resize_handle import ResizeHandle
from utils.data_structures import (
    PIXELS_PER_SEC,
    VisionDataTypeEnum,
    FILE_NAME,
    TIMELINE_START,
    TIMELINE_END,
)


class AdjustableBlock(QGraphicsRectItem):
    MIN_X = 0
    MAX_X = MIN_X + 90 * PIXELS_PER_SEC  # 90 seconds * 50 pixels/sec
    LABEL = (
        'File name:\n    {video_file}\n'
        'Timeline Pos:\n    start:{t_start}    \n    end:{t_end} '
        '\nFile Time:\n    start:{start}    \n    end:{end}'
    )
    BIAS_IN_S = 0.2

    def __init__(
        self,
        x,
        y,
        width,
        height,
        *,
        label='',
        color=QColor(100, 150, 200),
        block_config=None,
    ):
        # TODO:
        # emit signal to handle values manually
        super().__init__(0, 0, width, height)
        self.setBrush(QBrush(color))
        self.setFlags(
            QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemIsFocusable
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)
        self.setPos(x, y)
        self.handles_movable = True
        self.block_config = block_config

        # Text label
        self.text_label = QGraphicsTextItem(label, self)
        self.text_label.setDefaultTextColor(Qt.white)
        self.text_label.setPos(
            5, (height - self.text_label.boundingRect().height()) / 2
        )

        self.left_handle = ResizeHandle(self, 'left')
        self.right_handle = ResizeHandle(self, 'right')
        self._moving = False
        self._set_label()
        self.common_block_update()

        self._drag_start_x = 0


    def _set_label(self):
        if self.block_config is not None:
            if self.block_config['type'] == VisionDataTypeEnum.AUDIO:
                self.text_label.setPlainText(
                    self.LABEL.split('\nFile Time:')[0].format(
                        video_file=self.block_config[FILE_NAME],
                        t_start=self.block_config[TIMELINE_START],
                        t_end=self.block_config[TIMELINE_END],
                    )
                )

            else:
                self.text_label.setPlainText(
                    self.LABEL.format(
                        video_file=self.block_config[FILE_NAME],
                        t_start=self.block_config[TIMELINE_START],
                        t_end=self.block_config[TIMELINE_END],
                        start=self.block_config['start'],
                        end=self.block_config['end'],
                    )
                )

    def handler_move_update(self, handler_update='', delta_px=0):
        self.common_block_update()
        delta_in_s = delta_px/ PIXELS_PER_SEC

        if handler_update == 'left':
            self.block_config['start'] = round(self.block_config['start']  + delta_in_s, 2)
            self.block_config[TIMELINE_START] = round(self.block_config[TIMELINE_START] + delta_in_s, 2)
        else:
            self.block_config['end'] = round(self.block_config['end'] + delta_in_s, 2)
            self.block_config[TIMELINE_END] = round(self.block_config[TIMELINE_END] + delta_in_s, 2)

        self.block_config['duration'] = self.block_config['end'] - self.block_config['start']
        self._set_label()

    def common_block_update(self):
        # Handle positions
        self.left_handle.setPos(-self.left_handle.rect().width() / 2, 0)
        self.right_handle.setPos(
            self.rect().width() - self.right_handle.rect().width() / 2, 0
        )

        # Update label vertically
        self.text_label.setPos(
            5, (self.rect().height() - self.text_label.boundingRect().height()) / 2
        )

    def mousePressEvent(self, event):
        self._drag_start_x = event.scenePos().x()
        self._moving = True
        self.handles_movable = False  # Disable handle moves while dragging block
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._moving:
            delta = event.scenePos().x() - self._drag_start_x
            new_x = self.x() + delta
            new_x = max(self.MIN_X, min(new_x, self.MAX_X - self.rect().width()))

            self.setPos(QPointF(new_x, self.y()))
            self._drag_start_x = event.scenePos().x()
            if self.block_config is not None:
                delta_seconds = delta / PIXELS_PER_SEC

                # Clamp to prevent negative start time
                new_start = self.block_config[TIMELINE_START] + delta_seconds
                if new_start < 0:
                    delta_seconds = -self.block_config[TIMELINE_START]  # Only move to 0

                # Round delta and new values to 0.01 precision
                delta_seconds = round(delta_seconds, 2)

                self.block_config[TIMELINE_START] = round(
                    self.block_config[TIMELINE_START] + delta_seconds, 2
                )
                self.block_config[TIMELINE_END] = round(
                    self.block_config[TIMELINE_END] + delta_seconds, 2
                )

                if self.block_config[TIMELINE_START] < 0:
                    self.block_config[TIMELINE_START] = 0.0
                    self.block_config[TIMELINE_END] = round(
                        self.block_config['duration'], 2
                    )



                self.block_config[TIMELINE_START] = round(self.block_config[TIMELINE_START] + delta_seconds, 2)
                self.block_config[TIMELINE_END] = round(self.block_config[TIMELINE_END] + delta_seconds, 2)
                self._set_label()
            self.common_block_update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._moving = False
        self.handles_movable = True  # Re-enable handle moves
        self.setCursor(Qt.OpenHandCursor)
        self.common_block_update()
        super().mouseReleaseEvent(event)


class AudioAdjustableBlock(AdjustableBlock):
    # Inherit from your AdjustableBlock for resizing/moving behavior
    def __init__(
        self, x, y, width, height, color=QColor(200, 100, 150, 128), block_config=None
    ):
        super().__init__(x, y, width, height, color=color, block_config=block_config)
