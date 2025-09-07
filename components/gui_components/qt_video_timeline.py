from PyQt5.QtWidgets import QPushButton

from components.gui_components.qt_timeline_base import BaseTimelineWidget
from components.gui_components.qt_timeline_block import AdjustableBlock
from utils.data_structures import FILE_NAME, TimelinesTypeEnum


class VideoTimelineWidget(BaseTimelineWidget):
    def __init__(self):
        super().__init__()
        self.render_preview_btn = QPushButton("Render Preview")
        self.fast_preview_btn = QPushButton("Fast Preview")
        self.final_render_btn = QPushButton("Final Render")

        self.timeline_view_controls_layout.addWidget(self.fast_preview_btn)
        self.timeline_view_controls_layout.addWidget(self.render_preview_btn)
        self.timeline_view_controls_layout.addWidget(self.final_render_btn)
        self.timeline_type = TimelinesTypeEnum.VIDEO_TIMELINE.value

    def update_blocks_configs(self, blocks_configs) -> dict:
        for item in self.timelineView.items():
            if isinstance(item, AdjustableBlock):
                file_name = item.block_config[FILE_NAME]
                start = item.block_config["start"]
                end = item.block_config["end"]
                blocks_configs[file_name].start = start
                blocks_configs[file_name].end = end
        return blocks_configs
