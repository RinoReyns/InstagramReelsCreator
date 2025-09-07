from components.gui_components.qt_timeline_base import BaseTimelineWidget
from utils.data_structures import TimelinesTypeEnum


class TextTimelineWidget(BaseTimelineWidget):
    def __init__(self):
        super().__init__()
        self.timeline_type = TimelinesTypeEnum.TEXT_TIMELINE.value
