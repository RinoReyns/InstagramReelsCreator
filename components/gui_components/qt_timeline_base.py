import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QWidget,
)

from components.gui_components.qt_timeline_block import AdjustableBlock
from utils.data_structures import (
    FILE_NAME,
    MAX_VIDEO_DURATION,
    PIXELS_PER_SEC,
    TIMELINE_END,
    TIMELINE_START,
    TimelinesTypeEnum,
)
from utils.json_handler import media_clips_to_json
from utils.utils import check_if_file_exists

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")
logger = logging.getLogger(__name__)


class BaseTimelineWidget(QWidget):
    MAX_HEIGHT = 280

    def __init__(self):
        super().__init__()
        self.timelineView = QGraphicsView()
        self.timelineScene = QGraphicsScene()
        self.timelineView.setScene(self.timelineScene)
        self.timelineView.setFixedHeight(self.MAX_HEIGHT)
        self.timeline_view_controls_layout = QHBoxLayout()
        self.timeline_type = None

    def draw_time_grid(self, max_seconds):
        for second in range(max_seconds + 1):
            x = 10 + second * PIXELS_PER_SEC
            self.timelineScene.addLine(x, 0, x, self.MAX_HEIGHT - 80, Qt.gray)
            label = QGraphicsTextItem(f"{second}s")
            label.setPos(x + 2, self.MAX_HEIGHT - 80)
            self.timelineScene.addItem(label)

    def load_timeline(self, config_data, config_dir="") -> dict:
        blocks_configs = {}
        self.timelineScene.clear()
        if not config_data.get(self.timeline_type, None):
            logger.warning(f"Empty config for {self.timeline_type}")
            self.draw_time_grid(MAX_VIDEO_DURATION)
            return blocks_configs

        start = 0
        end = 0
        for file, settings in config_data[self.timeline_type].items():
            try:
                duration = max(0, min(settings.end, MAX_VIDEO_DURATION)) - max(
                    0, min(settings.start, MAX_VIDEO_DURATION)
                )
                end += duration
                width = max((end - start) * PIXELS_PER_SEC, 10)

                if width <= 0:
                    logger.warning(f"Skipping {file} because width <= 0")
                    continue
                # TODO:
                # handle order change
                blocks_configs[file] = settings
                block_config_temp = media_clips_to_json({file: settings})

                block_config = {
                    FILE_NAME: file,
                    TIMELINE_START: start
                    if self.timeline_type == TimelinesTypeEnum.VIDEO_TIMELINE.value
                    else settings.start,
                    TIMELINE_END: end if self.timeline_type == TimelinesTypeEnum.VIDEO_TIMELINE.value else settings.end,
                    "duration": duration,
                    # add max duration of video to disable expanding for more
                } | block_config_temp[file]

                x = 10 + block_config[TIMELINE_START] * PIXELS_PER_SEC
                block = AdjustableBlock(x, 10, width, self.MAX_HEIGHT - 100, label="", block_config=block_config)
                self.timelineScene.addItem(block)
                check_if_file_exists(config_dir, file)
            except Exception as e:
                logger.error(f"Error processing {file}: {e}")
            start = end
        self.draw_time_grid(MAX_VIDEO_DURATION)
        return blocks_configs

    def update_blocks_configs(self, blocks_config) -> dict:
        raise NotImplementedError
