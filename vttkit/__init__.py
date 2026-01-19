"""
VTTKit - Complete VTT (WebVTT) Processing Toolkit

A comprehensive library for downloading, parsing, merging, and processing
VTT subtitle files with full YouTube support.

Features:
- Download VTT from HTTP URLs, HLS playlists (M3U8), and YouTube
- Parse VTT with word-level timestamps
- Merge VTT files incrementally (for live streams)
- Correct timestamps for YouTube live streams
- Output structured segments.json format

Example usage:
    >>> from vttkit import VTTDownloader, VTTParser
    >>> 
    >>> # Download VTT
    >>> downloader = VTTDownloader()
    >>> vtt_path = downloader.download(
    ...     url="https://youtube.com/watch?v=VIDEO_ID",
    ...     output_dir="local/vtt",
    ...     is_youtube=True
    ... )
    >>> 
    >>> # Parse to segments.json
    >>> parser = VTTParser()
    >>> result = parser.parse_to_segments(
    ...     vtt_file=vtt_path,
    ...     output_file="segments.json"
    ... )
"""

import logging

__version__ = "0.1.0"
__author__ = "VTTKit Contributors"
__license__ = "MIT"

# Add NullHandler to prevent "No handler found" warnings
# Users should configure logging in their application if they want to see logs
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Core parsing functions
from .core import (
    parse_vtt_content,
    parse_vtt,
    timestamp_to_seconds,
    seconds_to_timestamp,
    format_transcript_with_timestamps,
    clean_vtt_content,
    split_long_cues,
    build_cues_from_words,
)

# Main classes
from .downloader import VTTDownloader, download_vtt, is_hls_playlist, download_vtt_segments_from_hls
from .parser import VTTParser, parse_vtt_to_segments
from .merger import VTTMerger, parse_vtt_cues, deduplicate_cues, merge_vtt_content, format_vtt_from_cues
from .corrector import (
    VTTTimestampCorrector,
    calculate_timestamp_offset,
    add_seconds_to_timestamp,
    apply_offset_to_cues,
    parse_timestamp_to_seconds,
)

# Data models
from .models import VTTCue, VTTWord, VTTSegment, DownloadConfig, M3U8Info

# YouTube utilities
from .youtube import (
    is_youtube_url,
    extract_youtube_id,
    download_youtube_subtitles,
    extract_youtube_live_info,
    refresh_youtube_vtt_url,
    extract_m3u8_info,
    extract_m3u8_program_date_time,
    is_m3u8_url,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    
    # Core parsing functions
    "parse_vtt_content",
    "parse_vtt",
    "timestamp_to_seconds",
    "seconds_to_timestamp",
    "format_transcript_with_timestamps",
    "clean_vtt_content",
    "split_long_cues",
    "build_cues_from_words",
    
    # Main classes
    "VTTDownloader",
    "VTTParser",
    "VTTMerger",
    "VTTTimestampCorrector",
    
    # Convenience functions
    "download_vtt",
    "parse_vtt_to_segments",
    "parse_vtt_cues",
    "deduplicate_cues",
    "merge_vtt_content",
    "format_vtt_from_cues",
    "is_hls_playlist",
    "download_vtt_segments_from_hls",
    "calculate_timestamp_offset",
    "add_seconds_to_timestamp",
    "apply_offset_to_cues",
    "parse_timestamp_to_seconds",
    
    # Models
    "VTTCue",
    "VTTWord",
    "VTTSegment",
    "DownloadConfig",
    "M3U8Info",
    
    # YouTube utilities
    "is_youtube_url",
    "extract_youtube_id",
    "download_youtube_subtitles",
    "extract_youtube_live_info",
    "refresh_youtube_vtt_url",
    "extract_m3u8_info",
    "extract_m3u8_program_date_time",
    "is_m3u8_url",
]
