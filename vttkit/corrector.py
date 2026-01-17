"""
Timestamp correction utilities for VTTKit.

Provides functionality to calculate and apply timestamp offsets for VTT files,
particularly useful for YouTube live streams where VTT timestamps need to be
corrected based on M3U8 playlist metadata.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

from .core import timestamp_to_seconds, seconds_to_timestamp

logger = logging.getLogger(__name__)


def calculate_timestamp_offset(m3u8_info: Optional[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Calculate timestamp offset from M3U8 playlist information.
    
    Uses media sequence number from M3U8 playlist to calculate the offset.
    Each segment represents a fixed duration of the stream.
    
    Args:
        m3u8_info: M3U8 info dict containing media_sequence and segment_duration
        
    Returns:
        Tuple of (offset_seconds, correction_method)
        
    Example:
        >>> m3u8_info = {'media_sequence': 1234, 'segment_duration': 5.0}
        >>> offset, method = calculate_timestamp_offset(m3u8_info)
        >>> print(f"{offset}s using {method}")
        6170.0s using media_sequence
    """
    try:
        if not m3u8_info:
            logger.warning("No M3U8 info provided, using original timestamps")
            return 0.0, "none"
        
        media_sequence = m3u8_info.get('media_sequence')
        segment_duration = m3u8_info.get('segment_duration', 5.0)
        
        # Use media sequence number to calculate offset
        if media_sequence is not None and segment_duration:
            # Calculate offset from media sequence number
            # Each segment represents segment_duration seconds of the stream
            offset_seconds = media_sequence * segment_duration
            
            logger.info(f"Media sequence: {media_sequence}")
            logger.info(f"Segment duration: {segment_duration:.3f}s")
            logger.info(f"Calculated offset from sequence: {offset_seconds:.3f}s ({offset_seconds/3600:.2f} hours)")
            
            # Validate offset is reasonable (not negative, not absurdly large)
            if offset_seconds < 0:
                logger.warning(f"Negative offset calculated: {offset_seconds}s, using 0")
                offset_seconds = 0
            elif offset_seconds > 86400:  # More than 24 hours
                logger.warning(f"Very large offset: {offset_seconds}s ({offset_seconds/3600:.1f} hours)")
            
            return offset_seconds, "media_sequence"
        
        else:
            logger.warning("No media sequence found in M3U8 info, using original timestamps")
            return 0.0, "none"
            
    except Exception as e:
        logger.warning(f"Failed to calculate timestamp offset: {str(e)}, using original timestamps")
        return 0.0, "none"


def add_seconds_to_timestamp(timestamp_str: str, offset_seconds: float) -> str:
    """
    Add seconds to a VTT timestamp string (HH:MM:SS.mmm format).
    
    Args:
        timestamp_str: VTT timestamp string
        offset_seconds: Seconds to add
        
    Returns:
        Adjusted timestamp string
        
    Example:
        >>> add_seconds_to_timestamp("00:05:30.000", 120)
        '00:07:30.000'
    """
    try:
        # Convert timestamp to seconds
        seconds = timestamp_to_seconds(timestamp_str)
        # Add offset
        new_seconds = seconds + offset_seconds
        # Convert back to timestamp format
        return seconds_to_timestamp(new_seconds)
    except Exception as e:
        logger.error(f"Failed to adjust timestamp {timestamp_str}: {str(e)}")
        return timestamp_str


def apply_offset_to_cues(cues: List[Dict[str, Any]], offset_seconds: float) -> List[Dict[str, Any]]:
    """
    Apply timestamp offset to all cues and their word-level timestamps.
    
    Args:
        cues: List of cue dictionaries from VTT parser
        offset_seconds: Seconds to add to all timestamps
        
    Returns:
        List of cues with adjusted timestamps
        
    Example:
        >>> cues = [{'start_time': '00:00:05.000', 'end_time': '00:00:07.000', 'text': 'Hello', 'words': []}]
        >>> adjusted = apply_offset_to_cues(cues, 120)
        >>> print(adjusted[0]['start_time'])
        '00:02:05.000'
    """
    if offset_seconds == 0:
        return cues
    
    logger.info(f"Applying timestamp offset to {len(cues)} cues: {offset_seconds:.3f}s ({offset_seconds/60:.1f} minutes)")
    
    adjusted_cues = []
    for cue in cues:
        adjusted_cue = cue.copy()
        
        # Adjust cue start and end times
        adjusted_cue['start_time'] = add_seconds_to_timestamp(cue['start_time'], offset_seconds)
        adjusted_cue['end_time'] = add_seconds_to_timestamp(cue['end_time'], offset_seconds)
        
        # Adjust word-level timestamps
        if 'words' in cue and cue['words']:
            adjusted_words = []
            for word in cue['words']:
                adjusted_word = word.copy()
                adjusted_word['time'] = add_seconds_to_timestamp(word['time'], offset_seconds)
                adjusted_words.append(adjusted_word)
            adjusted_cue['words'] = adjusted_words
        
        adjusted_cues.append(adjusted_cue)
    
    return adjusted_cues


def parse_timestamp_to_seconds(timestamp: str) -> float:
    """
    Parse a timestamp string into seconds.
    Supports both HH:MM:SS.mmm format and direct seconds format.
    
    This is a convenience wrapper around timestamp_to_seconds from core.
    
    Args:
        timestamp: The timestamp string (e.g., "00:05:30.500" or "330.5")
        
    Returns:
        The timestamp in seconds
        
    Example:
        >>> parse_timestamp_to_seconds("00:05:30.500")
        330.5
        >>> parse_timestamp_to_seconds("330.5")
        330.5
    """
    try:
        # Check if timestamp is already in seconds format (no colons)
        if ":" not in timestamp:
            return float(timestamp)
        
        # Use the core parser's function for HH:MM:SS.mmm format
        return timestamp_to_seconds(timestamp)
    except Exception as e:
        logger.error(f"Error parsing timestamp {timestamp}: {str(e)}")
        return 0.0


class VTTTimestampCorrector:
    """
    Class for handling VTT timestamp corrections.
    
    Provides methods to calculate offsets from M3U8 metadata and apply
    them to VTT cues, particularly useful for YouTube live streams.
    """
    
    def __init__(self, m3u8_info: Optional[Dict[str, Any]] = None):
        """
        Initialize corrector with optional M3U8 info.
        
        Args:
            m3u8_info: Optional M3U8 metadata dict
        """
        self.m3u8_info = m3u8_info
        self.offset_seconds = 0.0
        self.correction_method = "none"
        
        if m3u8_info:
            self.calculate_offset()
    
    def calculate_offset(self) -> float:
        """
        Calculate and store the timestamp offset.
        
        Returns:
            Calculated offset in seconds
        """
        self.offset_seconds, self.correction_method = calculate_timestamp_offset(self.m3u8_info)
        return self.offset_seconds
    
    def apply_to_cues(self, cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply calculated offset to cues.
        
        Args:
            cues: List of cue dictionaries
            
        Returns:
            List of cues with corrected timestamps
        """
        return apply_offset_to_cues(cues, self.offset_seconds)
    
    def get_correction_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the correction that was applied.
        
        Returns:
            Dictionary with correction information
        """
        return {
            'applied': self.offset_seconds > 0,
            'offset_seconds': self.offset_seconds,
            'media_sequence': self.m3u8_info.get('media_sequence') if self.m3u8_info else None,
            'segment_duration': self.m3u8_info.get('segment_duration') if self.m3u8_info else None,
            'program_time': self.m3u8_info.get('program_time') if self.m3u8_info else None,
            'correction_method': self.correction_method,
        }
