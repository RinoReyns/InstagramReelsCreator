import os
import sys
import time

import vlc
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from components.video_processing.fast_video_concat import FFmpegConcat
from utils.data_structures import Segment


class VideoPlayerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.segments = None
        self.total_duration = None
        self.current_segment_index = 0
        self.current_segment_offset = 0.0  # Time offset in current segment

        # VLC setup
        self.vlc_instance = vlc.Instance("--quiet")
        self.player = self.vlc_instance.media_player_new()

        # UI Elements
        self.video_frame = QWidget()
        palette = self.video_frame.palette()
        palette.setColor(QPalette.Window, Qt.black)
        self.video_frame.setAutoFillBackground(True)
        self.video_frame.setPalette(palette)
        self.video_frame.setFixedSize(int(1920 / 3), int(1080 / 3))
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignCenter)

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.open_video_btn = QPushButton("Open Video")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)

        controls = QHBoxLayout()
        controls.addWidget(self.open_video_btn)
        controls.addWidget(self.play_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)

        layout = QVBoxLayout()
        layout.addWidget(self.video_frame)
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.time_label)
        layout.addLayout(slider_layout)
        layout.addLayout(controls)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)

        # Connections
        self.play_button.clicked.connect(self.play)
        self.pause_button.clicked.connect(lambda: self.player.pause())
        self.stop_button.clicked.connect(self.stop)
        self.slider.sliderMoved.connect(self.seek)
        self.open_video_btn.clicked.connect(self.open_video_file)

        # Embed VLC into Qt widget
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform == "win32":
            self.player.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

        self.segment_media = None

    def _load_all_segment(self):
        self.segment_media = []
        print(self.segments)
        for seg in self.segments:
            media = self.vlc_instance.media_new(seg["path"])
            self.segment_media.append(media)

    def _load_segment(self, index):
        """Load the media for the given segment index"""
        if self.segment_media is None:
            segment = self.segments[index]
            media = self.vlc_instance.media_new(segment["path"])
        else:
            media = self.segment_media[index]
        self.player.set_media(media)
        self.current_segment_index = index

    def _get_media_duration(self, file_path, timeout=5):
        instance = vlc.Instance("--quiet")
        media = instance.media_new(file_path)

        # Start parsing
        media.parse_with_options(vlc.MediaParseFlag.local, timeout=0)

        # Wait for media to be parsed or timeout
        start_time = time.time()
        while not media.is_parsed():
            if time.time() - start_time > timeout:
                print("Timeout while parsing media.")
                return 0
            time.sleep(0.1)

        duration_ms = media.get_duration()
        if duration_ms <= 0:
            print("Duration not available or invalid.")
            return 0

        return duration_ms / 1000.0  # seconds

    def open_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.mov *.avi *.mkv)")
        if file_path:
            self.segments = [
                {
                    "path": file_path,
                    "start": 0.0,
                    "end": self._get_media_duration(file_path),
                }
            ]
            self.total_duration = sum(s["end"] - s["start"] for s in self.segments)

    def fast_preview(
        self,
        video_segments: None | list[Segment] = None,
        audio_segments: None | list[Segment] = None,
        text_segments: None | list[Segment] = None,
        output_folder: str = "",
    ):
        if video_segments is not None and len(video_segments) != 0:
            os.makedirs(output_folder, exist_ok=True)
            output_file = os.path.join(output_folder, "fast_preview.mkv")
            _, self.total_duration = FFmpegConcat().concat_segments(video_segments, output_file, audio_segments)
            self.segments = [
                {
                    "path": output_file,
                    "start": 0.0,
                    "end": self.total_duration,
                }
            ]
            self.stop()
            self.play()

    def play(self):
        if self.segments is not None and self.total_duration is not None:
            self._load_all_segment()
            self.seek(self.slider.value())
            self.timer.start()

    def stop(self):
        self.timer.stop()
        self.player.stop()
        self.slider.setValue(0)
        self.current_segment_index = 0
        self.current_segment_offset = 0.0
        self.segment_media = None

    def update_ui(self):
        if not self.player or not self.player.is_playing():
            return

        current_time = self.player.get_time() / 1000.0  # sec
        segment = self.segments[self.current_segment_index]

        # Check segment end
        if current_time >= segment["end"]:
            self._play_next_segment()
        else:
            global_time = self._get_global_time(self.current_segment_index, current_time)
            self.slider.setValue(int(global_time / self.total_duration * 1000))

            # Update time label
            self.time_label.setText(f"{self._format_time(global_time)} / {self._format_time(self.total_duration)}")

    def _play_next_segment(self):
        if self.current_segment_index + 1 < len(self.segments):
            self.current_segment_index += 1
            self._play_segment_from(self.segments[self.current_segment_index]["start"])
        else:
            self.stop()

    def _format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02}:{secs:02}"

    def _get_global_time(self, seg_idx, local_time):
        """Convert local segment time to global time"""
        offset = sum(s["end"] - s["start"] for s in self.segments[:seg_idx])
        return offset + (local_time - self.segments[seg_idx]["start"])

    def _get_segment_for_time(self, global_time):
        """Return (segment_index, time_in_segment) for a global time"""
        current_time = 0
        for idx, seg in enumerate(self.segments):
            seg_duration = seg["end"] - seg["start"]
            if current_time + seg_duration >= global_time:
                offset = global_time - current_time
                return idx, seg["start"] + offset
            current_time += seg_duration
        return len(self.segments) - 1, self.segments[-1]["end"]

    def _play_segment_from(self, time_in_segment):
        self._load_segment(self.current_segment_index)
        self.player.play()
        QTimer.singleShot(300, lambda: self.player.set_time(int(time_in_segment * 1000)))

    def seek(self, slider_value):
        global_time = (slider_value / 1000.0) * self.total_duration
        segment_index, local_time = self._get_segment_for_time(global_time)
        self.current_segment_index = segment_index
        self._play_segment_from(local_time)
