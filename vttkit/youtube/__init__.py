"""
YouTube module for VTTKit.

Provides YouTube-specific functionality including subtitle download
and M3U8 playlist parsing.
"""

from .client import (
    YouTubeClient,
    is_youtube_url,
    extract_youtube_id,
)

from .m3u8 import (
    extract_m3u8_info,
    extract_m3u8_program_date_time,
    is_m3u8_url,
)

__all__ = [
    'YouTubeClient',
    'is_youtube_url',
    'extract_youtube_id',
    'extract_m3u8_info',
    'extract_m3u8_program_date_time',
    'is_m3u8_url',
]
