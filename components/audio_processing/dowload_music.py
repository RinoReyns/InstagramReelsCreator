import yt_dlp
import os

from PyQt5.QtCore import QThread, pyqtSignal

def download_audio_as_wav(url, output_dir, progress_callback=None):
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
        'prefer_ffmpeg': True,
        'keepvideo': True,
        'quiet': False,
        'progress_hooks': [progress_callback] if progress_callback else []
    }

    def hook(d):
        if progress_callback:
            progress_callback(d)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)  # get info first
        filename = ydl.prepare_filename(info_dict)  # full path where it will be saved
        ydl.download([url])

    return f"{filename.split('.')[0]}.wav"


class DownloadThread(QThread):
    progress_signal = pyqtSignal(str)

    def __init__(self, url, download_dir):
        super().__init__()
        self.url = url
        self.download_dir = download_dir
        self.downloaded_file = ""

    def run(self):
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '').strip()
                self.progress_signal.emit(f"Downloading: {percent}")
            elif d['status'] == 'finished':
                self.progress_signal.emit(f"Finished: {d['filename']}")

        self.downloaded_file = download_audio_as_wav(self.url, self.download_dir, progress_callback=progress_hook)
