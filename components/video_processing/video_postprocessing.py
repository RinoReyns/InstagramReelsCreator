import logging
import os
import shutil
import threading

from moviepy import AudioFileClip, VideoFileClip, concatenate_videoclips
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.VideoClip import ColorClip
from tqdm import tqdm

from components.video_processing.video_processing_utils import get_codec
from components.video_processing.video_transitions import VideoTransitions
from utils.data_structures import LoadedVideo

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")


class VideoPostProcessing:
    OUTPUT_FPS = 30
    PREVIEW_FOLDER = "preview"
    PREVIEW_FILE_TEMPLATE = "{index}_preview.mp4"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.video_transitions = VideoTransitions()

    @staticmethod
    def resize_and_center(clip: LoadedVideo, target_size=(1080, 1920)) -> LoadedVideo:
        target_w, target_h = target_size
        clip_w, clip_h = clip.clip.size
        clip_ar = clip_w / clip_h
        target_ar = target_w / target_h

        # Determine new size to preserve aspect ratio
        if clip_ar > target_ar:
            # Too wide, match width and scale height
            new_w = target_w
            new_h = int(target_w / clip_ar)
        else:
            # Too tall, match height and scale width
            new_h = target_h
            new_w = int(target_h * clip_ar)

        # Now actually resize the clip
        resized_clip = clip.clip.resized(new_size=(new_w, new_h))

        # Create a background (black)
        background = ColorClip(
            size=target_size,
            color=(
                0,
                0,
                0,
            ),
            duration=clip.clip.duration,
        )

        # Overlay the resized clip in the center of the background
        composed = CompositeVideoClip(
            [background, resized_clip.with_position("center")],
            size=target_size,
        )
        clip.clip = composed.with_duration(clip.clip.duration).with_audio(resized_clip.audio)
        return clip

    def apply_transitions(self, clips: list[LoadedVideo]):
        final_clip = clips[0].clip

        for i in range(1, len(clips)):
            transition = self.video_transitions.transitions[clips[i - 1].transition]
            final_clip = transition(final_clip, clips[i].clip, duration=1)
        return final_clip

    def render_clip(self, index, clip, codec, fps):
        output_file = os.path.join(self.PREVIEW_FOLDER, self.PREVIEW_FILE_TEMPLATE.format(index=f"0{index}"))
        clip.write_videofile(
            output_file,
            codec=codec,
            audio_codec="aac",
            threads=max(1, os.cpu_count() - 2),
            fps=fps,
            logger=None,  # bar
            preset="ultrafast",
        )
        clip.close()

    def preview(self, clips: list[LoadedVideo], audio_path="", audio_start=0):
        if os.path.exists(self.PREVIEW_FOLDER):
            shutil.rmtree(self.PREVIEW_FOLDER)
        os.makedirs(self.PREVIEW_FOLDER, exist_ok=True)
        codec = get_codec()
        threads = []

        # TODO:
        # use ProcessPool
        for index, c in enumerate(clips, 1):
            resized_clip = self.resize_and_center(c).clip
            thread = threading.Thread(
                target=self.render_clip,
                args=(index, resized_clip, codec, self.OUTPUT_FPS),
            )
            thread.start()
            threads.append(thread)

        # Optional: Wait for all threads to finish
        for thread in tqdm(threads, desc="Rendering previews"):
            thread.join()

        files = sorted(f for f in os.listdir(self.PREVIEW_FOLDER) if "preview" in f and f.endswith(".mp4"))
        files.sort(key=lambda x: int(x.split("_")[0]))
        if not files:
            raise Exception("No preview_*.mp4 files found!")

        clips = [VideoFileClip(os.path.join(self.PREVIEW_FOLDER, f)) for f in files]

        # === Concatenate videos ===
        final_video = concatenate_videoclips(clips, method="compose")
        # === Load and attach audio ===
        audio = AudioFileClip(audio_path).subclipped(
            start_time=audio_start, end_time=audio_start + final_video.duration
        )
        final_video = final_video.with_audio(audio)

        # === Export ===
        final_video.write_videofile(
            os.path.join(self.PREVIEW_FOLDER, "preview_fast.mp4"),
            codec=codec,
            audio_codec="aac",
            fps=self.OUTPUT_FPS,
            preset="ultrafast",
        )

        # === Cleanup ===
        for clip in clips:
            clip.close()
        audio.close()
        final_video.close()

    def final_render(self, output_path: str, clips: list[LoadedVideo], audio_path: str = "", audio_start=0):
        resized_clips_list = [self.resize_and_center(c) for c in clips]
        final_clip = self.apply_transitions(resized_clips_list)

        if audio_path:
            audio_clip = AudioFileClip(audio_path).subclipped(audio_start, audio_start + final_clip.duration)
            final_clip = final_clip.with_audio(audio_clip)
        final_clip.write_videofile(
            output_path,
            codec=get_codec(),
            audio_codec="aac",
            threads=os.cpu_count() - 2,
            fps=self.OUTPUT_FPS,
        )
        logging.info(f"Clip duration: {final_clip.duration}")
        # Close all clips to release resources
        final_clip.close()
        for clip in clips:
            clip.clip.close()
