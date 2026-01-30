"""
VTT downloader for VTTKit.

Handles downloading VTT files from various sources including direct HTTP URLs,
HLS playlists (M3U8), and YouTube streams. Downloads are saved to _current.vtt files,
with optional timestamp correction and merging to main VTT files when using append mode.
"""

import logging
import os
from typing import Optional
from pathlib import Path

import requests

from .youtube import YouTubeClient, is_youtube_url, extract_youtube_id
from .models import DownloadConfig

logger = logging.getLogger(__name__)


def is_hls_playlist(content: str) -> bool:
    """
    Check if content is an HLS playlist (M3U8 format).
    
    Args:
        content: Content to check
        
    Returns:
        True if content is HLS playlist, False otherwise
    """
    return content.strip().startswith('#EXTM3U')


def download_vtt_segments_from_hls(playlist_url: str, timeout: int = 30, verify_ssl: bool = False) -> str:
    """
    Download and merge VTT segments from HLS playlist.
    
    YouTube live streams provide captions as HLS playlists (M3U8) that reference
    multiple VTT segment files. This function downloads all segments and merges them.
    
    Args:
        playlist_url: URL to HLS playlist (M3U8)
        timeout: Request timeout in seconds (default: 30)
        verify_ssl: Whether to verify SSL certificates (default: False for compatibility)
        
    Returns:
        Merged VTT content as string
        
    Raises:
        Exception: If download or parsing fails
    """
    try:
        logger.info("Detected HLS playlist format, downloading segments...")
        
        # Download the playlist
        response = requests.get(playlist_url, timeout=timeout, verify=verify_ssl)
        response.raise_for_status()
        playlist_content = response.text
        
        # Extract segment URLs from playlist
        segment_urls = []
        for line in playlist_content.split('\n'):
            line = line.strip()
            # Skip comments and metadata
            if line and not line.startswith('#'):
                # If it's a relative URL, make it absolute
                if line.startswith('http'):
                    segment_urls.append(line)
                else:
                    # Construct absolute URL from playlist base URL
                    base_url = playlist_url.rsplit('/', 1)[0]
                    segment_urls.append(f"{base_url}/{line}")
        
        logger.info(f"Found {len(segment_urls)} VTT segments in playlist")
        
        # Download and merge all segments
        merged_vtt = "WEBVTT\n\n"
        cue_counter = 1
        
        for i, segment_url in enumerate(segment_urls):
            try:
                logger.debug(f"Downloading segment {i+1}/{len(segment_urls)}")
                seg_response = requests.get(segment_url, timeout=timeout, verify=verify_ssl)
                seg_response.raise_for_status()
                segment_content = seg_response.text
                
                # Parse segment and extract cues (skip WEBVTT header)
                lines = segment_content.split('\n')
                in_cue = False
                
                for line in lines:
                    # Skip WEBVTT header and metadata
                    if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                        continue
                    
                    # Check if line is a timestamp
                    if '-->' in line:
                        in_cue = True
                        # Add cue number
                        merged_vtt += f"{cue_counter}\n"
                        merged_vtt += f"{line}\n"
                        cue_counter += 1
                    elif in_cue:
                        if line.strip():
                            merged_vtt += f"{line}\n"
                        else:
                            # Empty line marks end of cue
                            merged_vtt += "\n"
                            in_cue = False
                
                # Add separator between segments
                if i < len(segment_urls) - 1:
                    merged_vtt += "\n"
                    
            except Exception as e:
                logger.warning(f"Failed to download segment {i+1}: {str(e)}, continuing...")
                continue
        
        logger.info(f"Successfully merged {len(segment_urls)} VTT segments")
        return merged_vtt
        
    except Exception as e:
        logger.error(f"Failed to download HLS segments: {str(e)}")
        raise Exception(f"HLS segment download failed: {str(e)}")


class VTTDownloader:
    """
    VTT downloader supporting multiple sources.
    
    Can download from:
    - Direct HTTP/HTTPS VTT URLs
    - HLS playlists (M3U8)
    - YouTube videos and live streams
    
    Downloads are saved to {stream_id}_current.vtt files.
    With append_mode enabled, also transforms and merges into {stream_id}.vtt.
    """
    
    def __init__(self, youtube_cookies_path: Optional[str] = None):
        """
        Initialize VTT downloader.
        
        Args:
            youtube_cookies_path: Optional path to cookies file for YouTube authentication
        """
        self.youtube_client = YouTubeClient(cookies_path=youtube_cookies_path)
    
    def download(
        self,
        url: str,
        output_dir: str,
        stream_id: Optional[str] = None,
        is_youtube: bool = False,
        append_mode: bool = False,
        stream_url: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = False,
        m3u8_info: Optional[dict] = None,
        enrich_word_timestamps: bool = False
    ) -> str:
        """
        Download VTT file from URL and save to local filesystem.
        
        For YouTube streams, uses yt-dlp to properly handle authentication.
        For other streams, downloads directly from URL.
        
        The downloaded content is always saved to {stream_id}_current.vtt.
        If append_mode is True, the content is also transformed (timestamp corrected)
        and merged into {stream_id}.vtt with deduplication.
        
        Args:
            url: URL to download VTT file from (can be direct VTT or M3U8 playlist)
            output_dir: Directory to save the VTT file
            stream_id: Stream ID for naming the local file (default: generated from URL)
            is_youtube: Whether this is a YouTube stream
            append_mode: If True, applies timestamp corrections and merges into main VTT file
            stream_url: Original stream URL (for YouTube streams, used for yt-dlp)
            timeout: Request timeout in seconds (default: 30)
            verify_ssl: Whether to verify SSL certificates (default: False for compatibility)
            m3u8_info: M3U8 metadata for timestamp correction (used when append_mode=True)
            enrich_word_timestamps: If True, adds estimated word-level timestamps to cues (default: False)
            
        Returns:
            Local file path where VTT was saved:
            - {stream_id}_current.vtt if append_mode=False
            - {stream_id}.vtt if append_mode=True
            
        Raises:
            Exception: If download or save fails
        """
        try:
            # Prepare local directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Auto-detect YouTube URLs
            if not is_youtube and is_youtube_url(url):
                logger.info(f"Auto-detected YouTube URL: {url}")
                is_youtube = True
                if not stream_url:
                    stream_url = url
            
            # Generate stream_id if not provided
            if not stream_id:
                # For YouTube videos, extract video ID for better naming
                if is_youtube and stream_url:
                    video_id = extract_youtube_id(stream_url)
                    if video_id:
                        stream_id = video_id
                    else:
                        stream_id = Path(url).stem or "downloaded"
                else:
                    stream_id = Path(url).stem or "downloaded"
            
            # Download new content
            new_content = None
            
            # For YouTube streams, use yt-dlp to download subtitles
            if is_youtube and stream_url:
                logger.info(f"Using yt-dlp to download YouTube subtitles")
                
                try:
                    # Download subtitles using yt-dlp
                    downloaded_vtt = self.youtube_client.download_subtitles(stream_url, output_dir)
                    
                    if downloaded_vtt and os.path.exists(downloaded_vtt):
                        # Read the downloaded content
                        with open(downloaded_vtt, 'r', encoding='utf-8') as f:
                            new_content = f.read()
                        
                        # Clean up temp download file
                        try:
                            os.remove(downloaded_vtt)
                        except:
                            pass
                        
                        logger.info(f"Successfully downloaded YouTube subtitles")
                    else:
                        logger.warning("yt-dlp did not download subtitles, falling back to direct download")
                        
                except Exception as e:
                    logger.warning(f"yt-dlp subtitle download failed: {str(e)}, falling back to direct download")
            
            # Fallback: Direct download for non-YouTube or if yt-dlp fails
            if new_content is None:
                logger.info(f"Downloading VTT from: {url[:100]}...")
                
                # Make HTTP request with timeout
                response = requests.get(url, timeout=timeout, verify=verify_ssl)
                response.raise_for_status()
                
                new_content = response.text
                
                # Check if this is an HLS playlist
                if is_hls_playlist(new_content):
                    logger.info("Detected HLS playlist format, attempting segment download")
                    new_content = download_vtt_segments_from_hls(url, timeout=timeout, verify_ssl=verify_ssl)
            
            # Step 1: Save the original downloaded VTT to _current.vtt (for reference/debugging)
            current_path = os.path.join(output_dir, f"{stream_id}_current.vtt")
            with open(current_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"Original VTT saved to: {current_path}")
            
            # Handle append mode: transform and merge into main VTT file
            if append_mode:
                main_path = os.path.join(output_dir, f"{stream_id}.vtt")
                
                # Step 2: Apply timestamp correction (if YouTube with m3u8_info)
                corrected_content = new_content
                if is_youtube and m3u8_info:
                    from .corrector import calculate_timestamp_offset, apply_offset_to_vtt_content
                    offset_seconds, correction_method = calculate_timestamp_offset(m3u8_info)
                    logger.info(f"Calculated timestamp offset: {offset_seconds:.3f}s using {correction_method}")
                    corrected_content = apply_offset_to_vtt_content(new_content, offset_seconds)
                    logger.info("Applied timestamp correction to content")
                
                # Step 3: Add word-level timestamps (if requested)
                timestamped_content = corrected_content
                if enrich_word_timestamps:
                    from .utils import enrich_vtt_content_with_word_timestamps
                    logger.info("Enriching VTT with estimated word-level timestamps")
                    try:
                        timestamped_content = enrich_vtt_content_with_word_timestamps(corrected_content)
                        logger.info("Successfully enriched content with word-level timestamps")
                    except Exception as e:
                        logger.warning(f"Failed to enrich word timestamps: {str(e)}, continuing with corrected content")
                        timestamped_content = corrected_content
                
                # Step 4: Save intermediate timestamped file (corrected + word timestamps)
                timestamped_path = os.path.join(output_dir, f"{stream_id}_current_timestamped.vtt")
                with open(timestamped_path, 'w', encoding='utf-8') as f:
                    f.write(timestamped_content)
                logger.info(f"Timestamped VTT saved to: {timestamped_path}")
                
                # Step 5: Merge into main VTT file (no offset needed - already applied)
                from .merger import merge_vtt_content
                logger.info("Merging timestamped content into main VTT file")
                merged_content = merge_vtt_content(main_path, timestamped_content, new_vtt_offset_seconds=0.0)
                
                # Save merged content to main VTT file
                with open(main_path, 'w', encoding='utf-8') as f:
                    f.write(merged_content)
                logger.info(f"Merged VTT saved to: {main_path}")
                
                return main_path
            
            return current_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download VTT from {url[:100] if url else 'N/A'}: {str(e)}")
            raise Exception(f"VTT download failed: {str(e)}")
        except IOError as e:
            logger.error(f"Failed to save VTT: {str(e)}")
            raise Exception(f"VTT save failed: {str(e)}")
    
    def download_from_config(self, config: DownloadConfig) -> str:
        """
        Download VTT using a DownloadConfig object.
        
        Args:
            config: DownloadConfig object with download parameters
            
        Returns:
            Local file path where VTT was saved
        """
        return self.download(
            url=config.url,
            output_dir=config.output_dir,
            stream_id=config.stream_id,
            is_youtube=config.is_youtube,
            append_mode=config.append_mode,
            stream_url=config.stream_url,
        )
    
    def get_vtt_path(self, output_dir: str, stream_id: str) -> str:
        """
        Get the local path where VTT file would be stored.
        
        Args:
            output_dir: Output directory
            stream_id: Stream ID
            
        Returns:
            Expected local file path for VTT
        """
        return os.path.join(output_dir, f"{stream_id}.vtt")
    
    def vtt_exists(self, output_dir: str, stream_id: str) -> bool:
        """
        Check if VTT file already exists locally.
        
        Args:
            output_dir: Output directory
            stream_id: Stream ID
            
        Returns:
            True if VTT file exists, False otherwise
        """
        vtt_path = self.get_vtt_path(output_dir, stream_id)
        return os.path.exists(vtt_path)
