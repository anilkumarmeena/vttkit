"""
Shared utility functions for VTTKit.

Provides common utilities used across multiple modules, primarily
timestamp conversion functions.
"""


def timestamp_to_seconds(timestamp: str) -> float:
    """
    Convert HH:MM:SS.mmm format to seconds.
    
    Args:
        timestamp: Timestamp string in HH:MM:SS.mmm format
        
    Returns:
        Time in seconds as float
        
    Example:
        >>> timestamp_to_seconds("00:01:30.500")
        90.5
    """
    h, m, s = timestamp.split(':')
    seconds = int(h) * 3600 + int(m) * 60 + float(s)
    return seconds


def seconds_to_timestamp(seconds: float) -> str:
    """
    Convert seconds to HH:MM:SS.mmm format.
    
    Args:
        seconds: Time in seconds as float
        
    Returns:
        Timestamp string in HH:MM:SS.mmm format
        
    Example:
        >>> seconds_to_timestamp(90.5)
        '00:01:30.500'
    """
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d}.{milliseconds:03d}"
