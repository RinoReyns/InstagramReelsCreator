import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from components.gui_components.qt_timeline_block import AdjustableBlock
from main import logger
from utils.data_structures import (
    FILE_NAME,
    MAX_VIDEO_DURATION,
    PIXELS_PER_SEC,
    TIMELINE_END,
    TIMELINE_START,
    DataTypeEnum,
    TimelinesTypeEnum,
)
from utils.json_handler import media_clips_to_json


class VideoTimelineWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.render_preview_btn = QPushButton("Render Preview")
        self.fast_preview_btn = QPushButton("Fast Preview")
        self.load_config_btn = QPushButton("Load Timeline Config")
        self.save_config_btn = QPushButton("Save Timeline Config")
        self.final_render_btn = QPushButton("Final Render")
        self.work_dir_btn = QPushButton("Select Work Dir")
        self.work_dir_box = QLineEdit(self)

        self.timelineView = QGraphicsView()
        self.timelineScene = QGraphicsScene()
        self.timelineView.setScene(self.timelineScene)
        self.timelineView.setFixedHeight(300)

        self.timeline_view_controls_layout = QHBoxLayout()
        self.timeline_view_work_dir_layout = QHBoxLayout()
        self.timeline_view_controls_layout.addWidget(self.load_config_btn)
        self.timeline_view_controls_layout.addWidget(self.save_config_btn)
        self.timeline_view_controls_layout.addWidget(self.fast_preview_btn)
        self.timeline_view_controls_layout.addWidget(self.render_preview_btn)
        self.timeline_view_controls_layout.addWidget(self.final_render_btn)
        self.timeline_view_work_dir_layout.addWidget(self.work_dir_btn)
        self.timeline_view_work_dir_layout.addWidget(self.work_dir_box)

        # Connect buttons
        self.work_dir_btn.clicked.connect(self.get_work_dir)

    def draw_video_time_grid(self, max_seconds):
        for second in range(max_seconds + 1):
            x = 10 + second * PIXELS_PER_SEC
            self.timelineScene.addLine(x, 0, x, 220, Qt.gray)
            label = QGraphicsTextItem(f"{second}s")
            label.setPos(x + 2, 220)
            self.timelineScene.addItem(label)

    def get_work_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if folder:
            self.work_dir_box.setText(folder)

    def load_video_timeline(self, config_data, config_dir) -> dict:
        blocks_configs = {}
        self.timelineScene.clear()
        if not config_data.get(TimelinesTypeEnum.VIDEO_TIMELINE.value, None):
            logger.warning(f"Empty config for {TimelinesTypeEnum.VIDEO_TIMELINE.value}")
            return blocks_configs
        start = 0
        end = 0
        for file, settings in config_data[TimelinesTypeEnum.VIDEO_TIMELINE.value].items():
            try:
                duration = max(0, min(settings.end, MAX_VIDEO_DURATION)) - max(
                    0, min(settings.start, MAX_VIDEO_DURATION)
                )
                end += duration
                width = max((end - start) * PIXELS_PER_SEC, 10)
                x = 10 + start * PIXELS_PER_SEC

                if width <= 0:
                    logger.warning(f"Skipping {file} because width <= 0")
                    continue
                # TODO:
                # handle order change
                blocks_configs[file] = settings
                block_config_temp = media_clips_to_json({file: settings})
                block_config = {
                    FILE_NAME: file,
                    TIMELINE_START: start,
                    TIMELINE_END: end,
                    "duration": duration,
                    # add max duration of video to disable expanding for more
                    "type": DataTypeEnum.VIDEO,
                } | block_config_temp[file]

                block = AdjustableBlock(x, 10, width, 200, label="", block_config=block_config)
                self.timelineScene.addItem(block)
                full_path = os.path.join(config_dir, file)
                if not os.path.exists(full_path):
                    logger.warning(f"Warning: file not found {full_path}")
            except Exception as e:
                logger.error(f"Error processing {file}: {e}")
            start = end
        self.draw_video_time_grid(MAX_VIDEO_DURATION)
        return blocks_configs
