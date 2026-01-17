"""
YouTube client for VTTKit.

Provides YouTube-specific functionality using yt-dlp for subtitle extraction
and live stream information retrieval.
"""

import logging
import os
import re
from typing import Dict, Optional
from pathlib import Path

import yt_dlp

logger = logging.getLogger(__name__)


def is_youtube_url(url: str) -> bool:
    """
    Check if the provided URL is a valid YouTube URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is a valid YouTube URL, False otherwise
        
    Example:
        >>> is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        True
        >>> is_youtube_url("https://example.com/video")
        False
    """
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([^\s&]+)'
    return bool(re.match(youtube_regex, url))


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from a URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        YouTube video ID or None if not found
        
    Example:
        >>> extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        'dQw4w9WgXcQ'
    """
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([^\s&]+)'
    match = re.match(youtube_regex, url)
    return match.group(4) if match else None


class YouTubeClient:
    """
    Client for interacting with YouTube videos and live streams.
    
    Handles subtitle download, metadata extraction, and live stream information
    retrieval using yt-dlp.
    """
    
    def __init__(self, cookies_path: Optional[str] = None):
        """
        Initialize YouTube client.
        
        Args:
            cookies_path: Optional path to cookies file for authentication
        """
        self.cookies_path = cookies_path
    
    def _get_ydl_opts(self, **overrides) -> Dict:
        """
        Get default yt-dlp options with optional overrides.
        
        Args:
            **overrides: Options to override defaults
            
        Returns:
            Dictionary of yt-dlp options
        """
        opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
        }
        
        if self.cookies_path:
            opts['cookiefile'] = self.cookies_path
        
        opts.update(overrides)
        return opts
    
    def download_subtitles(self, url: str, output_dir: str) -> Optional[str]:
        """
        Download YouTube subtitles using yt-dlp.
        
        This properly handles authentication and signed URLs that expire.
        Returns the path to the downloaded VTT file.
        
        Args:
            url: YouTube video URL
            output_dir: Directory to save subtitles
            
        Returns:
            Path to downloaded VTT file, or None if no subtitles available
            
        Raises:
            ValueError: If URL is not a valid YouTube URL
            Exception: If download fails
        """
        if not is_youtube_url(url):
            raise ValueError(f"Invalid YouTube URL: {url}")
        
        video_id = extract_youtube_id(url)
        
        try:
            logger.info(f"Downloading subtitles for YouTube video: {video_id}")
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Configure yt-dlp to download only subtitles
            ydl_opts = self._get_ydl_opts(
                skip_download=True,
                writesubtitles=False,
                writeautomaticsub=True,
                subtitlesformat='vtt',
                subtitleslangs=['.*'],
                outtmpl=os.path.join(output_dir, f'{video_id}.%(ext)s'),
                quiet=False,
            )
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
            # Find the downloaded VTT file
            vtt_files = list(Path(output_dir).glob(f"{video_id}.*.vtt"))
            
            if vtt_files:
                vtt_path = str(vtt_files[0])
                logger.info(f"Successfully downloaded subtitles to: {vtt_path}")
                return vtt_path
            else:
                logger.warning(f"No VTT files found for {video_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download YouTube subtitles: {str(e)}")
            raise Exception(f"YouTube subtitle download failed: {str(e)}")
    
    def extract_live_info(self, url: str) -> Dict:
        """
        Extract live stream metadata including VTT subtitle URL using yt-dlp.
        
        Uses yt-dlp's extract_info with download=False to get stream metadata
        without downloading the video. Extracts subtitle URLs for live transcripts.
        
        Args:
            url: YouTube live stream URL
            
        Returns:
            Dictionary with stream information:
            - video_id: YouTube video ID
            - title: Stream title
            - is_live: Whether stream is currently live
            - vtt_url: URL to VTT subtitle file (if available)
            - description: Stream description
            - uploader: Channel name
            - duration: Video duration (if available)
            - view_count: View count (if available)
            
        Raises:
            ValueError: If URL is not a valid YouTube URL
            Exception: If extraction fails
        """
        if not is_youtube_url(url):
            raise ValueError(f"Invalid YouTube URL: {url}")
        
        video_id = extract_youtube_id(url)
        
        try:
            logger.info(f"Extracting live stream info for: {video_id}")
            
            # Configure yt-dlp options for info extraction only
            ydl_opts = self._get_ydl_opts(
                extract_flat=False,
                writesubtitles=True,
                writeautomaticsub=True,
                subtitlesformat='vtt',
                skip_download=True,
            )
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            # Extract VTT URL from subtitles
            vtt_url = None
            if info.get('subtitles') or info.get('automatic_captions'):
                # Try automatic captions first (live streams usually have these)
                captions = info.get('automatic_captions', {})
                if not captions:
                    captions = info.get('subtitles', {})
                
                # Look for any language with VTT format
                for lang, formats in captions.items():
                    for fmt in formats:
                        if fmt.get('ext') == 'vtt':
                            vtt_url = fmt.get('url')
                            logger.info(f"Found VTT URL for language '{lang}'")
                            break
                    if vtt_url:
                        break
            
            # Check if stream is live
            is_live = info.get('is_live', False)
            was_live = info.get('was_live', False)
            
            result = {
                'video_id': video_id,
                'title': info.get('title', f'Live Stream {video_id}'),
                'is_live': is_live,
                'was_live': was_live,
                'vtt_url': vtt_url,
                'description': info.get('description', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': info.get('duration'),
                'view_count': info.get('view_count'),
            }
            
            logger.info(
                f"Extracted info for {video_id}: "
                f"is_live={is_live}, has_vtt={vtt_url is not None}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract YouTube live info for {url}: {str(e)}")
            raise Exception(f"YouTube info extraction failed: {str(e)}")
    
    def is_live_active(self, url: str) -> bool:
        """
        Check if a YouTube stream is currently live.
        
        Args:
            url: YouTube stream URL
            
        Returns:
            True if stream is currently live, False otherwise
        """
        try:
            info = self.extract_live_info(url)
            return info.get('is_live', False)
        except Exception as e:
            logger.error(f"Failed to check YouTube live status: {str(e)}")
            # If we can't check, assume it's still live to avoid premature finalization
            logger.warning("Assuming stream is still live due to check failure")
            return True
    
    def refresh_vtt_url(self, url: str) -> Optional[str]:
        """
        Refresh VTT URL for a YouTube live stream.
        
        YouTube VTT URLs can expire or change during long live streams.
        This function fetches a fresh VTT URL.
        
        Args:
            url: YouTube stream URL
            
        Returns:
            Fresh VTT URL, or None if not available
        """
        try:
            logger.info(f"Refreshing VTT URL for YouTube stream")
            info = self.extract_live_info(url)
            vtt_url = info.get('vtt_url')
            
            if vtt_url:
                logger.info("VTT URL refreshed successfully")
            else:
                logger.warning("No VTT URL found during refresh")
            
            return vtt_url
            
        except Exception as e:
            logger.error(f"Failed to refresh VTT URL: {str(e)}")
            return None


# Convenience functions for backward compatibility
def download_youtube_subtitles(url: str, output_dir: str, cookies_path: Optional[str] = None) -> Optional[str]:
    """Download YouTube subtitles. Convenience function wrapping YouTubeClient."""
    client = YouTubeClient(cookies_path=cookies_path)
    return client.download_subtitles(url, output_dir)


def extract_youtube_live_info(url: str, cookies_path: Optional[str] = None) -> Dict:
    """Extract YouTube live stream info. Convenience function wrapping YouTubeClient."""
    client = YouTubeClient(cookies_path=cookies_path)
    return client.extract_live_info(url)


def refresh_youtube_vtt_url(url: str, cookies_path: Optional[str] = None) -> Optional[str]:
    """Refresh YouTube VTT URL. Convenience function wrapping YouTubeClient."""
    client = YouTubeClient(cookies_path=cookies_path)
    return client.refresh_vtt_url(url)
