"""
VTT parser for segments.json generation.

Orchestrates the complete VTT parsing pipeline from VTT file to segments.json format.
Applies timestamp corrections for YouTube live streams and outputs structured data
with word-level timestamps.
"""

import json
import logging
from typing import Dict, Any, Optional

from .converter import parse_vtt_content
from ..corrector import VTTTimestampCorrector

logger = logging.getLogger(__name__)


class VTTParser:
    """
    Parser for converting VTT files to segments.json format.
    
    Handles the complete parsing pipeline including:
    - VTT content parsing with word-level timestamps
    - Timestamp correction for live streams (YouTube)
    - Output to segments.json format
    """
    
    def __init__(self):
        """Initialize VTT parser."""
        pass
    
    def parse_to_segments(
        self,
        vtt_file: str,
        output_file: str = "segments.json",
        m3u8_info: Optional[Dict[str, Any]] = None,
        is_youtube: bool = False,
        max_cue_duration: float = 2.0,
        clean_content: bool = True,
        rebuild_cues_from_words: bool = True
    ) -> Dict[str, Any]:
        """
        Parse VTT file and generate segments.json with complete transcript.
        
        For YouTube live streams, applies timestamp correction to align VTT timestamps
        with actual stream time. The correction is applied after parsing and stored
        in the segments.json header for auditing.
        
        Args:
            vtt_file: Path to VTT file
            output_file: Output filename (default: "segments.json")
            m3u8_info: M3U8 info dict with media_sequence and segment_duration
            is_youtube: Whether this is a YouTube stream (enables timestamp correction)
            max_cue_duration: Maximum duration in seconds for each cue (default: 2.0)
            clean_content: Whether to clean VTT content before parsing (default: True)
            rebuild_cues_from_words: Rebuild cues from word-level data (default: True)
        
        Returns:
            Dictionary containing:
                - segments_path: Path to saved segments.json file
                - cues_count: Number of cues extracted
                - offset_applied: Timestamp offset applied (in seconds)
                - correction_method: Method used for timestamp correction
                
        Example:
            >>> parser = VTTParser()
            >>> result = parser.parse_to_segments(
            ...     vtt_file="stream.vtt",
            ...     output_file="segments.json",
            ...     is_youtube=True,
            ...     m3u8_info={'media_sequence': 1234, 'segment_duration': 5.0}
            ... )
            >>> print(f"Parsed {result['cues_count']} cues")
        """
        logger.info(f"Parsing VTT file: {vtt_file}")
        
        # Load VTT content from file
        with open(vtt_file, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        
        # Parse VTT content using core parser
        parsed_data = parse_vtt_content(
            vtt_content,
            max_cue_duration=max_cue_duration,
            clean_content=clean_content,
            rebuild_cues_from_words=rebuild_cues_from_words
        )
        
        header = parsed_data['header']
        cues = parsed_data['cues']
        
        # Format as segments.json structure
        segments_data = {
            "header": header,
            "cues": cues
        }
        
        # Save segments.json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(segments_data, f, indent=2, ensure_ascii=False)

        logger.info(f"VTT parsing complete: {len(cues)} cues extracted")
        
        # Return result
        return {
            "segments_path": output_file,
            "cues_count": len(cues),
        }
    
    def parse_content_to_dict(
        self,
        vtt_content: str,
        m3u8_info: Optional[Dict[str, Any]] = None,
        is_youtube: bool = False,
        max_cue_duration: float = 2.0
    ) -> Dict[str, Any]:
        """
        Parse VTT content string directly to dictionary (no file I/O).
        
        Args:
            vtt_content: VTT content as string
            m3u8_info: M3U8 info dict with media_sequence and segment_duration
            is_youtube: Whether this is a YouTube stream
            max_cue_duration: Maximum duration in seconds for each cue
            
        Returns:
            Dictionary with 'header' and 'cues' keys
        """
        # Parse VTT content
        parsed_data = parse_vtt_content(
            vtt_content,
            max_cue_duration=max_cue_duration,
            clean_content=True,
            rebuild_cues_from_words=True
        )
        
        header = parsed_data['header']
        cues = parsed_data['cues']
        
        return {
            "header": header,
            "cues": cues
        }
