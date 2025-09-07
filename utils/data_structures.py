from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from moviepy.video.io.VideoFileClip import VideoFileClip


class DataTypeEnum(StrEnum):
    VIDEO = 'video'
    PHOTO = 'photo'
    AUDIO = 'audio'
    TEXT = 'text'


class TransitionTypeEnum(StrEnum):
    NONE = 'none'
    ZOOM = 'zoom'
    SLIDE = 'slide'
    FADE = 'fade'
    SPIN = 'spin'


class TimelinesTypeEnum(StrEnum):
    AUDIO_TIMELINE = 'audio_timeline'
    VIDEO_TIMELINE = 'video_timeline'
    TEXT_TIMELINE = 'text_timeline'

    @classmethod
    def has_value(cls, value: str) -> bool:
        return value in {c.value for c in cls}

    @classmethod
    def has_name(cls, name: str) -> bool:
        return name.upper() in cls.__members__

@dataclass
class MediaClip:
    start: float
    end: float
    transition: TransitionTypeEnum
    type: DataTypeEnum  # 'video', 'image', 'audio'
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
