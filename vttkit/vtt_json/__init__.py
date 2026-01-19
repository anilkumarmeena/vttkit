"""
VTT to JSON conversion package.

Provides functionality for parsing VTT files and converting them to structured
JSON/dictionary format with word-level timestamps. Includes support for YouTube
live stream timestamp correction and segments.json output format.
"""

from .converter import (
    parse_vtt_content,
    parse_vtt,
    format_transcript_with_timestamps,
)

from .parser import VTTParser

__all__ = [
    # Core conversion functions
    "parse_vtt_content",
    "parse_vtt",
    "format_transcript_with_timestamps",
    
    # Parser class
    "VTTParser",
]
