from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem


class ResizeHandle(QGraphicsRectItem):
    def __init__(self, parent_block, position):
        super().__init__(0, 0, 6, parent_block.rect().height())
        self.parent_block = parent_block
        self.position = position  # 'left' or 'right'
        color = Qt.red if position == 'left' else Qt.green
        self.setBrush(QBrush(color))
        self.setCursor(Qt.SizeHorCursor)
        self.setZValue(1)
        self.setParentItem(parent_block)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        self._handling_change = False

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            if not self.parent_block.handles_movable:
                # Ignore any handle move attempts
                return QPointF(0, 0)
        if change == QGraphicsItem.ItemPositionChange and not self._handling_change:
            self._handling_change = True
            dx = value.x()
            if dx is None:
                self._handling_change = False
                return super().itemChange(change, value)

            if self.position == 'left':
                # Calculate proposed new position and width
                new_x = self.parent_block.x() + dx
                new_width = self.parent_block.rect().width() - dx

                # Clamp new_x so it never goes less than MIN_X
                if new_x < self.parent_block.MIN_X:
                    dx = self.parent_block.MIN_X - self.parent_block.x()
                    new_x = self.parent_block.MIN_X
                    new_width = self.parent_block.rect().width() - dx

                # Minimum width check
                if new_width < 10:
                    new_width = 10
                    new_x = self.parent_block.x() + (
                        self.parent_block.rect().width() - 10
                    )

                # Apply new size and position
                self.parent_block.setRect(
                    0, 0, new_width, self.parent_block.rect().height()
                )
                self.parent_block.setPos(QPointF(new_x, self.parent_block.y()))

            elif self.position == 'right':
                new_width = dx
                max_right = self.parent_block.MAX_X
                right_edge = self.parent_block.x() + new_width

                # Clamp right edge so it doesn't go beyond MAX_X
                if right_edge > max_right:
                    new_width = max_right - self.parent_block.x()

                # Minimum width check
                if new_width < 10:
                    new_width = 10

                self.parent_block.setRect(
                    0, 0, new_width, self.parent_block.rect().height()
                )

            self.parent_block.updateHandles()
            # Prevent handle from moving independently
            return QPointF(0, 0)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        self._drag_start_x = event.scenePos().x()
        self.setCursor(Qt.SizeHorCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        delta = event.scenePos().x() - self._drag_start_x
        self._drag_start_x = event.scenePos().x()

        if self.position == 'left':
            # Calculate new size and position
            new_x = self.parent_block.x() + delta
            new_width = self.parent_block.rect().width() - delta

            # Clamp new_x and new_width properly
            if new_x < self.parent_block.MIN_X:
                new_x = self.parent_block.MIN_X
                new_width = self.parent_block.rect().width() + (
                    self.parent_block.x() - new_x
                )
            if new_width < 10:
                new_width = 10
                new_x = self.parent_block.x() + (self.parent_block.rect().width() - 10)

            self.parent_block.setRect(
                0, 0, new_width, self.parent_block.rect().height()
            )
            self.parent_block.setPos(QPointF(new_x, self.parent_block.y()))

        elif self.position == 'right':
            new_width = self.parent_block.rect().width() + delta
            max_right = self.parent_block.MAX_X

            if self.parent_block.x() + new_width > max_right:
                new_width = max_right - self.parent_block.x()
            if new_width < 10:
                new_width = 10

            self.parent_block.setRect(
                0, 0, new_width, self.parent_block.rect().height()
            )

        self.parent_block.updateHandles()
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.SizeHorCursor)
        event.accept()
