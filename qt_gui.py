import os
import sys
import threading
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from components.audio_processing.dowload_music import DownloadThread
from components.audio_processing.play_audio import AudioThread
from components.gui_components.qt_text_timeline import TextTimelineWidget
from components.gui_components.qt_timeline_block import (
    AdjustableBlock,
    AudioAdjustableBlock,
)
from components.gui_components.qt_utils import get_header_text_label
from components.gui_components.qt_vertical_scroling_area import VerticalScrollArea
from components.gui_components.qt_video_timeline import VideoTimelineWidget
from components.gui_components.qt_waveform_item import WaveformItem
from components.video_processing.play_video import VideoPlayerUI
from main import create_instagram_reel, logger
from utils.data_structures import (
    FILE_NAME,
    INIT_AUDIO_LENGTH_S,
    MAX_VIDEO_DURATION,
    PIXELS_PER_SEC,
    TIMELINE_END,
    TIMELINE_START,
    DataTypeEnum,
    MediaClip,
    Segment,
    TimelinesTypeEnum,
    TransitionTypeEnum,
)
from utils.json_handler import pars_config, save_json_config


class InstagramReelCreatorGui(QWidget):
    DOWNLOAD_DIR = "download"
    AUDIO_SELECTOR_HEIGHT = 145

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instagram Reel Creator")
        self.setGeometry(750, 50, 1750, 1000)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # ===================== Video frame for VLC Video Player =======================
        self.video_frame = VideoPlayerUI()
        self.layout.addWidget(self.video_frame)
        # ===============================================================================

        # ================== Global Control Buttons =====================================
        self.load_config_btn = QPushButton("Load Timeline Config")
        self.save_config_btn = QPushButton("Save Timeline Config")
        self.load_config_btn.clicked.connect(self.load_config)
        self.save_config_btn.clicked.connect(self.save_config)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.load_config_btn)
        buttons_layout.addWidget(self.save_config_btn)
        self.layout.addLayout(buttons_layout)
        # ================================================================================

        self.scroll = VerticalScrollArea()
        self.blocks_configs = {}

        # ======================= Text Timeline View ===========================
        self.scroll.addWidget(get_header_text_label("Text Timeline"))
        self.text_timeline = TextTimelineWidget()
        self.scroll.addLayout(self.text_timeline.timeline_view_controls_layout)
        self.scroll.addWidget(self.text_timeline.timelineView)
        self.text_timeline.draw_text_time_grid(MAX_VIDEO_DURATION)
        # ========================================================================

        # ======================= Video Timeline View ===========================
        self.scroll.addWidget(get_header_text_label("Video Timeline:"))
        self.video_timeline = VideoTimelineWidget()
        self.scroll.addLayout(self.video_timeline.timeline_view_controls_layout)
        self.scroll.addLayout(self.video_timeline.timeline_view_work_dir_layout)
        self.scroll.addWidget(self.video_timeline.timelineView)
        self.video_timeline.draw_video_time_grid(MAX_VIDEO_DURATION)
        self.video_timeline.fast_preview_btn.clicked.connect(self.fast_preview)
        self.video_timeline.render_preview_btn.clicked.connect(self.render_preview)
        self.video_timeline.final_render_btn.clicked.connect(self.final_render)
        # ========================================================================

        # ======================= Audio Timeline View ============================
        self.loadAudioBtn = QPushButton("Load Audio")
        self.playAudioBtn = QPushButton("Play")
        self.pauseAudioBtn = QPushButton("Pause")
        self.stopAudioBtn = QPushButton("Stop")
        self.downloadAudioBtn = QPushButton("Download Audio from URL")
        self.audio_url_box = QLineEdit(self)

        self.audioTimelineView = QGraphicsView()
        self.audioTimelineScene = QGraphicsScene()
        self.audioTimelineView.setScene(self.audioTimelineScene)
        self.audioTimelineView.setFixedHeight(220)
        self.scroll.addWidget(get_header_text_label("Audio Timeline:"))
        audio_controls_layout = QHBoxLayout()
        audio_download_controls_layout = QHBoxLayout()
        audio_controls_layout.addWidget(self.loadAudioBtn)
        audio_controls_layout.addWidget(self.playAudioBtn)
        audio_controls_layout.addWidget(self.pauseAudioBtn)
        audio_controls_layout.addWidget(self.stopAudioBtn)
        self.scroll.addLayout(audio_controls_layout)
        audio_download_controls_layout.addWidget(self.downloadAudioBtn)
        audio_download_controls_layout.addWidget(self.audio_url_box)

        self.scroll.addLayout(audio_download_controls_layout)
        self.scroll.addWidget(self.audioTimelineView)
        self.layout.addWidget(self.scroll)
        self.draw_audio_time_grid(MAX_VIDEO_DURATION, self.AUDIO_SELECTOR_HEIGHT)
        self.loadAudioBtn.clicked.connect(self.load_audio_window)
        self.downloadAudioBtn.clicked.connect(self.download_audio)
        self.audio_thread = None
        # ========================================================================

        self.scroll.add_stretch()

    def load_audio_window(self):
        audio_path, _ = QFileDialog.getOpenFileName(self, "Open Audio File", "", "Audio Files (*.wav *.mp3)")
        self.load_external_audio(audio_path)

    def load_external_audio(self, audio_path, start=0, stop=INIT_AUDIO_LENGTH_S):
        if not audio_path:
            self.show_warning("None audio file was loaded.")
            return
        self.audio_path = Path(audio_path)
        self.audioTimelineScene.clear()
        height = 120
        waveform = WaveformItem(width=800, height=height)
        waveform.load_waveform(audio_path)
        self.audioTimelineScene.addItem(waveform)
        block_config = {
            FILE_NAME: audio_path,
            TIMELINE_START: start,
            TIMELINE_END: stop,
            "start": start,
            "end": stop,
            "type": DataTypeEnum.AUDIO,
        }
        # Add adjustable block for audio segment, full width initially

        audio_block = AudioAdjustableBlock(
            start * PIXELS_PER_SEC,
            5,
            INIT_AUDIO_LENGTH_S * PIXELS_PER_SEC,
            self.AUDIO_SELECTOR_HEIGHT,
            block_config=block_config,
        )
        self.audioTimelineScene.addItem(audio_block)
        self.draw_audio_time_grid(int(waveform.duration), self.AUDIO_SELECTOR_HEIGHT + 5)
        self.audio_thread = AudioThread(audio_path)

        self.playAudioBtn.clicked.connect(self.play_audio)
        self.pauseAudioBtn.clicked.connect(self.audio_thread.pause)
        self.stopAudioBtn.clicked.connect(self.audio_thread.stop_loop)
        self.audio_thread.looper.moveToThread(self.audio_thread)

    def show_warning(self, text):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Warning")
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def download_audio(self):
        if not self.audio_url_box.text():
            self.show_warning("Url to download is empty.")
            return
        # Setup progress dialog
        self.progress_dialog = QProgressDialog("Downloading...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Download Progress")
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.resize(400, 100)
        self.progress_dialog.show()

        # Start download thread
        self.thread = DownloadThread(self.audio_url_box.text(), self.DOWNLOAD_DIR)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.start()

        def on_finished():
            self.update_progress("Download completed!")
            self.progress_dialog.close()
            self.load_external_audio(self.thread.downloaded_file)

        self.thread.finished.connect(on_finished)

    def update_progress(self, text):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(text)

    def get_audio_item(self):
        for item in self.audioTimelineScene.items():
            if isinstance(item, AudioAdjustableBlock):
                return item.block_config
        return None

    def update_blocks_configs(self):
        for item in self.video_timeline.timelineView.items():
            if isinstance(item, AdjustableBlock):
                file_name = item.block_config[FILE_NAME]
                start = item.block_config["start"]
                end = item.block_config["end"]
                self.blocks_configs[file_name].start = start
                self.blocks_configs[file_name].end = end

        for item in self.audioTimelineScene.items():
            if isinstance(item, AudioAdjustableBlock):
                file_name = item.block_config[FILE_NAME]
                start = item.block_config["start"]
                end = item.block_config["end"]
                if file_name not in self.blocks_configs:
                    self.blocks_configs[file_name] = MediaClip(
                        start=start,
                        end=end,
                        transition=TransitionTypeEnum.NONE,
                        type=DataTypeEnum.AUDIO,
                        video_resampling=0,
                    )
                else:
                    self.blocks_configs[file_name].start = start
                    self.blocks_configs[file_name].end = end

        segments_video = []
        segments_audio = []
        for file, setting in self.blocks_configs.items():
            if setting.type != DataTypeEnum.AUDIO:
                segments_video.append(
                    Segment(
                        path=str(os.path.join(self.video_timeline.work_dir_box.text(), file)),
                        start=setting.start,
                        end=setting.end,
                    )
                )
            elif setting.type == DataTypeEnum.AUDIO:
                segments_audio.append(
                    Segment(
                        path=str(os.path.join(self.video_timeline.work_dir_box.text(), file)),
                        start=setting.start,
                        end=setting.end,
                    )
                )

        return segments_video, segments_audio

    def restart_audio_thread(self):
        # Stop existing thread if running
        if hasattr(self, "audio_thread") and self.audio_thread.isRunning():
            print("Stopping existing audio thread...")

            # Stop loop logic
            self.audio_thread.looper.stop_loop()
            self.audio_thread.quit()
            self.audio_thread.wait()
            self.audio_thread.start()

    def play_audio(self):
        if self.audio_thread is not None:
            params = self.get_audio_item()
            if params is not None:
                self.restart_audio_thread()
                self.audio_thread.finished.connect(self.audio_thread.stop_loop)
                self.audio_thread.start_loop(max(params[TIMELINE_START], 0), params[TIMELINE_END])

    def save_config(self):
        self.update_blocks_configs()
        config_path, _ = QFileDialog.getSaveFileName(self, "Save Config File", "", "JSON Files (*.json)")
        config = {timeline.value: {} for timeline in TimelinesTypeEnum}
        for name, element in self.blocks_configs.items():
            block_type = element.type

            if block_type == DataTypeEnum.AUDIO:
                timeline_type = TimelinesTypeEnum.AUDIO_TIMELINE
            elif block_type in [DataTypeEnum.VIDEO, DataTypeEnum.PHOTO]:
                timeline_type = TimelinesTypeEnum.VIDEO_TIMELINE
            elif block_type == DataTypeEnum.TEXT:
                timeline_type = TimelinesTypeEnum.TEXT_TIMELINE
            else:
                raise ValueError(f"{block_type} not supported")

            config[timeline_type][name] = element
        save_json_config(config, config_path)

    def load_config(self):
        config_path, _ = QFileDialog.getOpenFileName(self, "Open Config File", "", "JSON Files (*.json)")
        if not config_path:
            return
        if self.video_timeline.work_dir_box.text() == "":
            config_dir = os.path.dirname(config_path)
            self.video_timeline.work_dir_box.setText(config_dir)
        else:
            config_dir = self.video_timeline.work_dir_box.text()
        config_data = pars_config(config_path)

        self._load_audio_timeline(config_data)
        self.blocks_configs |= self.video_timeline.load_video_timeline(config_data, config_dir)
        # TODO:
        # add load text timeline

    def _load_audio_timeline(self, config):
        if not config.get(TimelinesTypeEnum.AUDIO_TIMELINE.value, None):
            logger.warning(f"Empty config for {TimelinesTypeEnum.AUDIO_TIMELINE.value}")
            return

        for file, settings in config[TimelinesTypeEnum.AUDIO_TIMELINE.value].items():
            self.load_external_audio(file, settings.start, settings.end)

    def fast_preview(self):
        video_segments, audio_segments = self.update_blocks_configs()
        self.video_frame.fast_preview(video_segments, os.path.abspath("preview"), audio_segments)

    def render_preview(self):
        self.update_blocks_configs()
        # TODO:
        # preview in one file
        self.run_main_script(True)

    def final_render(self):
        self.update_blocks_configs()
        self.run_main_script(False)

    def draw_audio_time_grid(self, max_seconds, height):
        for second in range(max_seconds + 1):
            x = 10 + second * PIXELS_PER_SEC
            self.audioTimelineScene.addLine(x, 0, x, height, Qt.gray)
            label = QGraphicsTextItem(f"{second}s")
            label.setPos(x + 2, height)
            self.audioTimelineScene.addItem(label)

    def run_main_script(self, preview: bool = False):
        # TODO:
        # add checks
        threading.Thread(target=self.execute_script, args=(preview,), daemon=True).start()

    def execute_script(self, preview):
        create_instagram_reel(self.blocks_configs, self.work_dir_box.text(), "test_output.mp4", preview)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Arial", 9)  # (family, point size)
    app.setFont(font)  # apply globally
    window = InstagramReelCreatorGui()
    window.show()
    sys.exit(app.exec_())
