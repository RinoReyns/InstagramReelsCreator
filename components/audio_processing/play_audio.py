from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
import vlc


class AudioLooper(QObject):
    finished = pyqtSignal()

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.start_time = 0
        self.end_time = 0
        self.running = False

        self.vlc_instance = vlc.Instance('--quiet')
        self.player = self.vlc_instance.media_player_new()
        self.media = self.vlc_instance.media_new(self.file_path)
        self.player.set_media(self.media)

        self._loop_timer = QTimer()
        self._loop_timer.setInterval(100)  # Check every 100ms
        self._loop_timer.timeout.connect(self._check_loop)

    @pyqtSlot(float, float)
    def start_loop(self, start_time, end_time):
        if self.running:
            self.stop_loop()

        self.start_time = start_time
        self.end_time = end_time
        self.running = True

        self.player.play()
        QTimer.singleShot(
            100, lambda: self.player.set_time(int(self.start_time * 1000))
        )
        self._loop_timer.start()

    def _check_loop(self):
        if not self.running:
            return
        current_ms = self.player.get_time()
        if current_ms >= int(self.end_time * 1000):
            self.player.set_time(int(self.start_time * 1000))

    @pyqtSlot()
    def stop_loop(self):
        self.running = False
        self._loop_timer.stop()
        if self.player.is_playing():
            self.player.stop()
        self.finished.emit()

    @pyqtSlot()
    def pause(self):
        if self.player.is_playing():
            self.player.pause()


class AudioThread(QThread):
    def __init__(self, file_path):
        super().__init__()
        self.looper = AudioLooper(file_path)

    def run(self):
        # Start Qt event loop for QTimer in AudioLooper
        self.exec_()

    def start_loop(self, start_time, end_time):
        self.looper.start_loop(start_time, end_time)

    def stop_loop(self):
        self.looper.stop_loop()

    def pause(self):
        self.looper.pause()
