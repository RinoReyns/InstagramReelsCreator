import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from PyQt5.QtCore import QProcess

from utils.data_structures import DataTypeEnum, Segment

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
# TODO:
# add threads and move to the main processing lib

class FFmpegConcat:
    def __init__(self):
        self.proc = None
        self.logger = logging.getLogger(__name__)

    def _run_ffmpeg(self, args: List[str]) -> bool:
        proc = QProcess()
        proc.start('ffmpeg', args)
        proc.waitForFinished(-1)
        success = proc.exitCode() == 0
        if not success:
            self.logger.error(f'FFmpeg failed: {bytes(proc.readAllStandardError()).decode()}')
        return success

    def process_video_segment(self, tmp_dir, i, seg):
        tmp_file = os.path.join(tmp_dir, f"video_part_{i}.mkv")
        args = [
            '-hide_banner',
            '-y',
            '-ss',
            str(seg.start),
            '-to',
            str(seg.end),
            '-i',
            seg.path,
            '-c',
            'copy',
            tmp_file,
        ]
        self.logger.info('Trimming video: ' + ' '.join(['ffmpeg'] + args))
        if not self._run_ffmpeg(args):
            return None, 0.0
        return i, tmp_file, seg.end - seg.start, DataTypeEnum.VIDEO

    def process_audio_segment(self, tmp_dir, i, seg):
        tmp_file = os.path.join(tmp_dir, f"audio_part_{i}.mkv")
        args = [
            '-hide_banner', '-y',
            '-ss', str(seg.start),
            '-to', str(seg.end),
            '-i', seg.path,
            '-c', 'copy',
            tmp_file,
        ]
        self.logger.info(f"Trimming audio segment {i}: " + ' '.join(['ffmpeg'] + args))
        if not self._run_ffmpeg(args):
            return i, None, None, DataTypeEnum.AUDIO
        return i, tmp_file, None, DataTypeEnum.AUDIO

    def concat_segments(
        self,
        video_segments: List[Segment],
        out_path: str,
        audio_segments: Optional[List[Segment]] = None,
    ) -> tuple[bool, float]:
        """
        Concatenate video segments and optional audio segments (with same trim info).
        """
        if not video_segments:
            self.logger.error('No video segments provided')
            return False, 0.0

        tmp_dir = tempfile.mkdtemp()
        tmp_audio_files = [None] * len(audio_segments)
        tmp_video_files = [None] * len(video_segments)

        # Step 1: trim video segments into MKV
        duration = 0.0

        # Run trimming in parallel threads
        with ThreadPoolExecutor(max_workers=os.cpu_count() - 2 or 1) as executor:
            futures = {executor.submit(self.process_video_segment, tmp_dir, i, seg): i for i, seg in enumerate(video_segments)}
            if audio_segments:
                futures |= {executor.submit(self.process_audio_segment, tmp_dir, i, seg): i for i, seg in
                           enumerate(audio_segments, start=len(futures))}
            for future in as_completed(futures):
                i, tmp_data, seg_duration, data_type = future.result()
                if tmp_data is None:
                    self.logger.error(f"Trimming failed on segment {i}")
                    return False, 0.0
                if data_type == DataTypeEnum.VIDEO:
                    tmp_video_files[i] = tmp_data
                    duration += seg_duration
                elif data_type == DataTypeEnum.AUDIO:
                    tmp_audio_files[i - len(tmp_video_files)] = tmp_data

        self.logger.info(f"All audio and video segments trimmed. Total duration of clip: {duration:.2f}s")

        # Step 2: concatenate video parts
        video_list_path = os.path.join(tmp_dir, 'video_list.txt')
        with open(video_list_path, 'w', encoding='utf-8') as f:
            for tmp in tmp_video_files:
                f.write(f"file '{os.path.abspath(tmp)}'\n")
        concat_video = os.path.join(tmp_dir, 'concat_video.mkv')
        args = ['-hide_banner', '-y', '-f', 'concat', '-safe', '0', '-i', video_list_path, '-c', 'copy', concat_video]
        self.logger.info(f'Concatenating video: {' '.join(['ffmpeg'] + args)}', )
        if not self._run_ffmpeg(args):
            return False, 0.0

        # Step 3: if audio segments provided, trim and concatenate audio
        final_audio = None
        if audio_segments:
            audio_list_path = os.path.join(tmp_dir, 'audio_list.txt')
            with open(audio_list_path, 'w', encoding='utf-8') as f:
                for tmp in tmp_audio_files:
                    f.write(f"file '{os.path.abspath(tmp)}'\n")

            final_audio = os.path.join(tmp_dir, 'concat_audio.mkv')
            args = [
                '-hide_banner',
                '-y',
                '-f',
                'concat',
                '-safe',
                '0',
                '-i',
                audio_list_path,
                '-c',
                'copy',
                final_audio,
            ]
            self.logger.info(f'Concatenating audio: {' '.join(['ffmpeg'] + args)}')
            if not self._run_ffmpeg(args):
                return False, 0.0

        # Step 4: mux video + audio into final output
        if final_audio:
            args = [
                '-hide_banner',
                '-y',
                '-i',
                concat_video,
                '-i',
                final_audio,
                '-c:v',
                'copy',
                '-c:a',
                'copy',
                '-map',
                '0:v:0',
                '-map',
                '1:a:0',
                out_path,
            ]
            self.logger.info(f'Muxing final video + audio: {' '.join(['ffmpeg'] + args)}', )
            if not self._run_ffmpeg(args):
                return False, duration
        else:
            os.rename(concat_video, out_path)

        # Step 5: cleanup temp files
        for tmp in (
            tmp_video_files
            + tmp_audio_files
            + [
                video_list_path,
                audio_list_path if audio_segments else '',
                concat_video,
                final_audio if final_audio else '',
            ]
        ):
            try:
                if tmp and os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

        self.logger.info(f"✅ Final video with optional trimmed audio: {out_path}")
        return True, duration
