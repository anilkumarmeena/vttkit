"""
M3U8 playlist parsing utilities for VTTKit.

Provides functionality to extract timing information from HLS (M3U8) playlists,
particularly useful for YouTube live streams that require timestamp correction.
"""

import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


def extract_m3u8_info(m3u8_url: str, timeout: int = 30, verify_ssl: bool = False) -> Dict[str, any]:
    """
    Extract timing information from M3U8 playlist.
    
    Extracts:
    - PROGRAM-DATE-TIME: Wall-clock time for current segment
    - MEDIA-SEQUENCE: Segment number in the stream
    - EXTINF durations: Segment durations
    
    Args:
        m3u8_url: URL to M3U8 playlist
        timeout: Request timeout in seconds (default: 30)
        verify_ssl: Whether to verify SSL certificates (default: False for compatibility)
        
    Returns:
        Dictionary with program_time, media_sequence, and segment_duration
        
    Example:
        >>> info = extract_m3u8_info("https://example.com/playlist.m3u8")
        >>> print(info['media_sequence'], info['segment_duration'])
        1234 5.0
    """
    try:
        response = requests.get(m3u8_url, timeout=timeout, verify=verify_ssl)
        response.raise_for_status()
        
        program_time = None
        media_sequence = None
        segment_durations = []
        
        for line in response.text.split('\n'):
            line = line.strip()
            
            if line.startswith('#EXT-X-PROGRAM-DATE-TIME:'):
                program_time = line.split(':', 1)[1].strip()
                logger.debug(f"Found PROGRAM-DATE-TIME: {program_time}")
            
            elif line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                media_sequence = int(line.split(':', 1)[1].strip())
                logger.debug(f"Found MEDIA-SEQUENCE: {media_sequence}")
            
            elif line.startswith('#EXTINF:'):
                # Extract duration from #EXTINF:5.005, format
                duration_str = line.split(':', 1)[1].split(',')[0].strip()
                try:
                    segment_durations.append(float(duration_str))
                except ValueError:
                    pass
        
        # Calculate average segment duration
        avg_duration = sum(segment_durations) / len(segment_durations) if segment_durations else 5.0
        
        result = {
            'program_time': program_time,
            'media_sequence': media_sequence,
            'segment_duration': avg_duration,
        }
        
        logger.info(f"M3U8 info: sequence={media_sequence}, avg_duration={avg_duration:.3f}s")
        return result
        
    except Exception as e:
        logger.warning(f"Failed to extract M3U8 info: {str(e)}")
        return {
            'program_time': None,
            'media_sequence': None,
            'segment_duration': 5.0
        }


def extract_m3u8_program_date_time(m3u8_url: str) -> Optional[str]:
    """
    Extract PROGRAM-DATE-TIME from M3U8 playlist.
    
    This provides the wall-clock time for the stream segment, which can be used
    to calculate correct timestamps for live stream VTT files.
    
    Args:
        m3u8_url: URL to M3U8 playlist
        
    Returns:
        ISO 8601 datetime string from first PROGRAM-DATE-TIME tag, or None
        
    Example:
        >>> time_str = extract_m3u8_program_date_time("https://example.com/playlist.m3u8")
        >>> print(time_str)
        2024-01-15T10:30:00.000Z
    """
    info = extract_m3u8_info(m3u8_url)
    return info.get('program_time')


def is_m3u8_url(url: str) -> bool:
    """
    Check if a URL points to an M3U8 playlist.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be an M3U8 playlist, False otherwise
    """
    return url.lower().endswith('.m3u8') or '.m3u8?' in url.lower()
