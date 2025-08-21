import os
import sys
import threading

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QHBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsTextItem,
    QLineEdit,
    QProgressDialog,
    QMessageBox,
)

from components.gui_components.qt_timeline_block import (
    AdjustableBlock,
    AudioAdjustableBlock,
)
from components.audio_processing.play_audio import AudioThread
from components.video_processing.play_video import VideoPlayerUI
from utils.json_handler import media_clips_to_json, pars_config
from utils.data_structures import (
    VisionDataTypeEnum,
    FILE_NAME,
    TIMELINE_START,
    TIMELINE_END, MediaClip,INIT_AUDIO_LENGTH_S
)

from components.gui_components.qt_waveform_item import WaveformItem
from utils.data_structures import PIXELS_PER_SEC, MAX_VIDEO_DURATION, TransitionTypeEnum
from main import create_instagram_reel, logger

from components.audio_processing.dowload_music import DownloadThread
from utils.data_structures import Segment

class VideoTimelineApp(QWidget):
    DOWNLOAD_DIR = 'download'

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Instagram Reel Creator')
        self.setGeometry(750, 50, 1750, 1000)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Video frame for VLC
        self.video_frame = VideoPlayerUI()
        self.layout.addWidget(self.video_frame)

        # Timeline view
        self.render_preview_btn = QPushButton('Render Preview')
        self.fast_preview_btn = QPushButton('Fast Preview')
        self.load_config_btn = QPushButton('Load Timeline Config')
        self.save_config_btn = QPushButton('Save Timeline Config')
        self.final_render_btn = QPushButton('Final Render')
        self.work_dir_btn = QPushButton('Select Work Dir')
        self.work_dir_box = QLineEdit(self)

        self.timelineView = QGraphicsView()
        self.timelineScene = QGraphicsScene()
        self.timelineView.setScene(self.timelineScene)
        self.timelineView.setFixedHeight(300)

        timeline_view_controls_layout = QHBoxLayout()
        timeline_view_work_dir_layout = QHBoxLayout()
        timeline_view_controls_layout.addWidget(self.load_config_btn)
        timeline_view_controls_layout.addWidget(self.save_config_btn)
        timeline_view_controls_layout.addWidget(self.fast_preview_btn)
        timeline_view_controls_layout.addWidget(self.render_preview_btn)
        timeline_view_controls_layout.addWidget(self.final_render_btn)
        timeline_view_work_dir_layout.addWidget(self.work_dir_btn)
        timeline_view_work_dir_layout.addWidget(self.work_dir_box)
        self.layout.addLayout(timeline_view_controls_layout)
        self.layout.addLayout(timeline_view_work_dir_layout)
        self.layout.addWidget(self.timelineView)
        self.draw_video_time_grid(90)
        self.blocks_configs = {}

        # Connect buttons
        self.load_config_btn.clicked.connect(self.load_config)
        self.fast_preview_btn.clicked.connect(self.fast_preview)
        self.work_dir_btn.clicked.connect(self.get_work_dir)
        self.render_preview_btn.clicked.connect(self.render_preview)
        self.final_render_btn.clicked.connect(self.final_render)
        self.blocks = []

        # Audio Timeline
        self.loadAudioBtn = QPushButton('Load Audio')
        self.playAudioBtn = QPushButton('Play')
        self.pauseAudioBtn = QPushButton('Pause')
        self.stopAudioBtn = QPushButton('Stop')
        self.downloadAudioBtn = QPushButton('Download Audio from URL')
        self.audio_url_box = QLineEdit(self)

        self.audioTimelineView = QGraphicsView()
        self.audioTimelineScene = QGraphicsScene()
        self.audioTimelineView.setScene(self.audioTimelineScene)
        self.audioTimelineView.setFixedHeight(200)
        self.layout.addWidget(QLabel('Audio Timeline:'))
        audio_controls_layout = QHBoxLayout()
        audio_download_controls_layout = QHBoxLayout()
        audio_controls_layout.addWidget(self.loadAudioBtn)
        audio_controls_layout.addWidget(self.playAudioBtn)
        audio_controls_layout.addWidget(self.pauseAudioBtn)
        audio_controls_layout.addWidget(self.stopAudioBtn)
        self.layout.addLayout(audio_controls_layout)
        audio_download_controls_layout.addWidget(self.downloadAudioBtn)
        audio_download_controls_layout.addWidget(self.audio_url_box)

        self.layout.addLayout(audio_download_controls_layout)
        self.layout.addWidget(self.audioTimelineView)
        self.draw_audio_time_grid(MAX_VIDEO_DURATION)
        self.loadAudioBtn.clicked.connect(self.load_audio_window)
        self.downloadAudioBtn.clicked.connect(self.download_audio)
        self.audio_thread = None

    def load_audio_window(self):
        audio_path, _ = QFileDialog.getOpenFileName(
            self, 'Open Audio File', '', 'Audio Files (*.wav *.mp3)'
        )
        self.load_external_audio(audio_path)

    def load_external_audio(self, audio_path):
        if not audio_path:
            self.show_warning('None audio file was loaded.')
            return
        self.audio_path = audio_path
        self.audioTimelineScene.clear()
        height = 120
        waveform = WaveformItem(width=800, height=height)
        waveform.load_waveform(audio_path)
        self.audioTimelineScene.addItem(waveform)
        block_config = {
            FILE_NAME: audio_path,
            TIMELINE_START: 0,
            TIMELINE_END: INIT_AUDIO_LENGTH_S,
            'start': 0,
            'end': INIT_AUDIO_LENGTH_S,
            'type': VisionDataTypeEnum.AUDIO,
        }
        # Add adjustable block for audio segment, full width initially
        audio_block = AudioAdjustableBlock(
            0, 5, INIT_AUDIO_LENGTH_S*PIXELS_PER_SEC, 115, block_config=block_config
        )
        self.audioTimelineScene.addItem(audio_block)
        self.draw_audio_time_grid(int(waveform.duration))
        self.audio_thread = AudioThread(audio_path)

        self.playAudioBtn.clicked.connect(self.play_audio)
        self.pauseAudioBtn.clicked.connect(self.audio_thread.pause)
        self.stopAudioBtn.clicked.connect(self.audio_thread.stop_loop)
        self.audio_thread.looper.moveToThread(self.audio_thread)

    def show_warning(self, text):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)  # Use Critical for errors
        msg.setWindowTitle('Warning')
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def download_audio(self):
        if not self.audio_url_box.text():
            self.show_warning('Url to download is empty.')
            return
        # Setup progress dialog
        self.progress_dialog = QProgressDialog('Downloading...', 'Cancel', 0, 0, self)
        self.progress_dialog.setWindowTitle('Download Progress')
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.resize(400, 100)
        self.progress_dialog.show()


        # Start download thread
        self.thread = DownloadThread(self.audio_url_box.text(), self.DOWNLOAD_DIR)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.start()

        def on_finished():
            self.update_progress('Download completed!')
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
        for item in self.timelineView.items():
            if isinstance(item, AdjustableBlock):
                file_name = item.block_config[FILE_NAME]
                start = item.block_config['start']
                end = item.block_config['end']
                self.blocks_configs[file_name].start = start
                self.blocks_configs[file_name].end = end

        for item in self.audioTimelineScene.items():
            if isinstance(item, AudioAdjustableBlock):
                file_name = item.block_config[FILE_NAME]
                start = item.block_config['start']
                end = item.block_config['end']
                if file_name not in self.blocks_configs:
                    self.blocks_configs[file_name] = MediaClip(start=start,
                                                               end=end,
                                                               transition=TransitionTypeEnum.NONE,
                                                               type=VisionDataTypeEnum.AUDIO,
                                                               video_resampling=0)
                else:
                    self.blocks_configs[file_name].start = start
                    self.blocks_configs[file_name].end = end

        segments_video = []
        segments_audio = []
        for file, setting in self.blocks_configs.items():
            if setting.type != VisionDataTypeEnum.AUDIO:
                segments_video.append(
                    Segment(path=str(os.path.join(self.work_dir_box.text(), file)),
                            start=setting.start,
                            end=setting.end)
                )
            elif setting.type == VisionDataTypeEnum.AUDIO:
                segments_audio.append(
                    Segment(path=str(os.path.join(self.work_dir_box.text(), file)),
                            start=setting.start,
                            end=setting.end)
                )


        return segments_video, segments_audio

    def restart_audio_thread(self):
        # Stop existing thread if running
        if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
            print('Stopping existing audio thread...')

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
                self.audio_thread.start_loop(
                    max(params[TIMELINE_START], 0), params[TIMELINE_END]
                )

    def load_config(self):
        config_path, _ = QFileDialog.getOpenFileName(
            self, 'Open Config File', '', 'JSON Files (*.json)'
        )
        if not config_path:
            return
        if self.work_dir_box.text() == '':
            config_dir = os.path.dirname(config_path)
            self.work_dir_box.setText(config_dir)
        else:
            config_dir = self.work_dir_box.text()
        config_data = pars_config(config_path)

        self.video_clips = {}
        self.timelineScene.clear()
        start = 0
        end = 0
        for video_file, settings in config_data.items():
            if settings.type == VisionDataTypeEnum.AUDIO:
                continue
            try:
                duration = max(0, min(settings.end, MAX_VIDEO_DURATION)) - max(
                    0, min(settings.start, MAX_VIDEO_DURATION)
                )
                end += duration
                width = max((end - start) * PIXELS_PER_SEC, 10)
                x = 10 + start * PIXELS_PER_SEC

                if width <= 0:
                    logger.warning(f"Skipping {video_file} because width <= 0")
                    continue
                # TODO:
                # handle order change
                self.blocks_configs[video_file] = settings
                block_config_temp = media_clips_to_json({video_file: settings})
                block_config = {
                    FILE_NAME: video_file,
                    TIMELINE_START: start,
                    TIMELINE_END: end,
                    'duration': duration,
                    # add max duration of video to disable expanding for more
                    'type': VisionDataTypeEnum.VIDEO,
                } | block_config_temp[video_file]

                block = AdjustableBlock(
                    x, 10, width, 200, label='', block_config=block_config
                )
                self.timelineScene.addItem(block)
                full_path = os.path.join(config_dir, video_file)
                if not os.path.exists(full_path):
                    print(f"Warning: file not found {full_path}")
                self.video_clips[full_path] = settings
            except Exception as e:
                print(f"Error processing {video_file}: {e}")
            start = end
        self.draw_video_time_grid(MAX_VIDEO_DURATION)

    def fast_preview(self):
        video_segments, audio_segments = self.update_blocks_configs()
        self.video_frame.fast_preview(video_segments, os.path.abspath('preview') ,audio_segments)
        #self.play_audio()

    def render_preview(self):
        self.update_blocks_configs()
        # TODO:
        # preview in one file
        self.run_main_script(True)

    def final_render(self):
        self.update_blocks_configs()
        self.run_main_script(False)

    def get_work_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            'Select Folder',
            '',
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if folder:
            self.work_dir_box.setText(folder)

    def draw_video_time_grid(self, max_seconds):
        for second in range(max_seconds + 1):
            x = 10 + second * PIXELS_PER_SEC
            self.timelineScene.addLine(x, 0, x, 220, Qt.gray)
            label = QGraphicsTextItem(f"{second}s")
            label.setPos(x + 2, 220)
            self.timelineScene.addItem(label)

    def draw_audio_time_grid(self, max_seconds):
        for second in range(max_seconds + 1):
            x = 10 + second * PIXELS_PER_SEC
            self.audioTimelineScene.addLine(x, 0, x, 120, Qt.gray)
            label = QGraphicsTextItem(f"{second}s")
            label.setPos(x + 2, 120)
            self.audioTimelineScene.addItem(label)

    def run_main_script(self, preview: bool = False):
        # TODO:
        # add checks
        threading.Thread(
            target=self.execute_script, args=(preview,), daemon=True
        ).start()

    def execute_script(self, preview):
        create_instagram_reel(
            self.blocks_configs, self.work_dir_box.text(), 'test_output.mp4', preview
        )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont('Arial', 9)  # (family, point size)
    app.setFont(font)  # apply globally
    window = VideoTimelineApp()
    window.show()
    sys.exit(app.exec_())
