import os
import tempfile
from typing import List, Optional
from PyQt5.QtCore import QProcess

from utils.data_structures import Segment


class FFmpegConcat:
    def __init__(self):
        self.proc = None

    def _run_ffmpeg(self, args: List[str]) -> bool:
        proc = QProcess()
        proc.start('ffmpeg', args)
        proc.waitForFinished(-1)
        success = proc.exitCode() == 0
        if not success:
            print('FFmpeg failed:', bytes(proc.readAllStandardError()).decode())
        return success

    def concat_segments(
        self,
        video_segments: List[Segment],
        out_path: str,
        audio_segments: Optional[List[Segment]] = None,
    ) -> tuple[bool, float]:
        """
        Concatenate video segments and optional audio segments (with same trim info).
        """
        # TODO:
        # add logger
        # add threads for preparing videos
        if not video_segments:
            print('No video segments provided')
            return False, 0.0

        tmp_dir = tempfile.mkdtemp()
        tmp_video_files = []
        tmp_audio_files = []

        # Step 1: trim video segments into MKV
        duration = 0.0
        for i, seg in enumerate(video_segments):
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
            print('Trimming video:', ' '.join(['ffmpeg'] + args))
            if not self._run_ffmpeg(args):
                return False, 0.0
            tmp_video_files.append(tmp_file)
            duration += seg.end - seg.start

        # Step 2: concatenate video parts
        video_list_path = os.path.join(tmp_dir, 'video_list.txt')
        with open(video_list_path, 'w', encoding='utf-8') as f:
            for tmp in tmp_video_files:
                f.write(f"file '{os.path.abspath(tmp)}'\n")
        concat_video = os.path.join(tmp_dir, 'concat_video.mkv')
        args = ['-hide_banner', '-y', '-f', 'concat', '-safe', '0', '-i', video_list_path, '-c', 'copy', concat_video]
        print('Concatenating video:', ' '.join(['ffmpeg'] + args))
        if not self._run_ffmpeg(args):
            return False, 0.0

        # Step 3: if audio segments provided, trim and concatenate audio
        final_audio = None
        if audio_segments:
            for i, seg in enumerate(audio_segments):
                tmp_file = os.path.join(tmp_dir, f"audio_part_{i}.mkv")
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
                print('Trimming audio:', ' '.join(['ffmpeg'] + args))
                if not self._run_ffmpeg(args):
                    return False, 0.0
                tmp_audio_files.append(tmp_file)

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
            print('Concatenating audio:', ' '.join(['ffmpeg'] + args))
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
            print('Muxing final video + audio:', ' '.join(['ffmpeg'] + args))
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

        print(f"✅ Final video with optional trimmed audio: {out_path}")
        return True, duration
