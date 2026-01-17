"""
Data models for VTTKit.

Defines the core data structures used throughout the package.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class VTTWord:
    """Represents a word with its timestamp in a VTT cue."""
    word: str
    time: str  # HH:MM:SS.mmm format


@dataclass
class VTTCue:
    """Represents a VTT cue (subtitle segment) with word-level timestamps."""
    start_time: str  # HH:MM:SS.mmm
    end_time: str    # HH:MM:SS.mmm
    text: str
    words: List[VTTWord] = field(default_factory=list)


@dataclass
class VTTSegment:
    """Represents a complete VTT document structure."""
    header: Dict[str, Any] = field(default_factory=dict)
    cues: List[VTTCue] = field(default_factory=list)


@dataclass
class DownloadConfig:
    """Configuration for VTT download operations."""
    url: str
    output_dir: str
    stream_id: Optional[str] = None
    is_youtube: bool = False
    append_mode: bool = False
    stream_url: Optional[str] = None  # Original stream URL for YouTube


@dataclass
class M3U8Info:
    """M3U8 playlist metadata for timestamp correction."""
    program_time: Optional[str] = None
    media_sequence: Optional[int] = None
    segment_duration: float = 5.0
