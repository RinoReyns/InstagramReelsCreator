from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from moviepy.video.io.VideoFileClip import VideoFileClip


class VisionDataTypeEnum(StrEnum):
    VIDEO = 'video'
    PHOTO = 'photo'
    AUDIO = 'audio'


class TransitionTypeEnum(StrEnum):
    NONE = 'none'
    ZOOM = 'zoom'
    SLIDE = 'slide'
    FADE = 'fade'
    SPIN = 'spin'


@dataclass
class MediaClip:
    start: float
    end: float
    transition: TransitionTypeEnum
    type: VisionDataTypeEnum  # 'video', 'image', 'audio'
    video_resampling: int


@dataclass
class LoadedVideo:
    clip: VideoFileClip = None
    transition: TransitionTypeEnum = None


INSTAGRAM_RESOLUTION = (1080, 1920)
PIXELS_PER_SEC = 50
INIT_AUDIO_LENGTH_S = 10
MAX_VIDEO_DURATION = 90
FILE_NAME = 'name'
TIMELINE_START = 'timeline_start'
TIMELINE_END = 'timeline_end'


@dataclass
class Segment:
    path: str
    start: float
    end: float
