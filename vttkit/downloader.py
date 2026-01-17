"""
VTT downloader for VTTKit.

Handles downloading VTT files from various sources including direct HTTP URLs,
HLS playlists (M3U8), and YouTube streams. Supports incremental downloads
for live streams with merging and deduplication.
"""

import logging
import os
from typing import Optional
from pathlib import Path

import requests

from .merger import merge_vtt_content
from .youtube import YouTubeClient, is_youtube_url
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


def download_vtt_segments_from_hls(playlist_url: str, timeout: int = 30) -> str:
    """
    Download and merge VTT segments from HLS playlist.
    
    YouTube live streams provide captions as HLS playlists (M3U8) that reference
    multiple VTT segment files. This function downloads all segments and merges them.
    
    Args:
        playlist_url: URL to HLS playlist (M3U8)
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        Merged VTT content as string
        
    Raises:
        Exception: If download or parsing fails
    """
    try:
        logger.info("Detected HLS playlist format, downloading segments...")
        
        # Download the playlist
        response = requests.get(playlist_url, timeout=timeout)
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
                seg_response = requests.get(segment_url, timeout=timeout)
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
    
    Supports incremental downloads for live streams with automatic merging.
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
        timeout: int = 30
    ) -> str:
        """
        Download VTT file from URL and save to local filesystem.
        
        For YouTube streams, uses yt-dlp to properly handle authentication.
        For other streams, downloads directly from URL.
        Supports incremental appending for live streams to build complete transcript.
        
        Args:
            url: URL to download VTT file from (can be direct VTT or M3U8 playlist)
            output_dir: Directory to save the VTT file
            stream_id: Stream ID for naming the local file (default: generated from URL)
            is_youtube: Whether this is a YouTube stream
            append_mode: If True, append new content to existing file (for live streams)
            stream_url: Original stream URL (for YouTube streams, used for yt-dlp)
            timeout: Request timeout in seconds (default: 30)
            
        Returns:
            Local file path where VTT was saved
            
        Raises:
            Exception: If download or save fails
        """
        try:
            # Prepare local directory and file path
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate stream_id if not provided
            if not stream_id:
                stream_id = Path(url).stem or "downloaded"
            
            local_path = os.path.join(output_dir, f"{stream_id}.vtt")
            
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
                        
                        # Clean up temp download if different from target
                        if downloaded_vtt != local_path:
                            try:
                                # Copy to target location
                                with open(local_path, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                                # Remove temp file
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
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                
                new_content = response.text
                
                # Check if this is an HLS playlist
                if is_hls_playlist(new_content):
                    logger.info("Detected HLS playlist format, attempting segment download")
                    new_content = download_vtt_segments_from_hls(url, timeout=timeout)
            
            # Handle append mode for live streams
            if append_mode and os.path.exists(local_path):
                logger.info("Append mode: merging with existing VTT file")
                merged_content = merge_vtt_content(local_path, new_content)
                final_content = merged_content
            else:
                # First download or non-append mode: use new content as-is
                if os.path.exists(local_path):
                    logger.info("Overwrite mode: replacing existing VTT file")
                else:
                    logger.info("First download: creating new VTT file")
                final_content = new_content
            
            # Save final content to local file
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            logger.info(f"VTT saved successfully to: {local_path}")
            return local_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download VTT from {url[:100] if url else 'N/A'}: {str(e)}")
            raise Exception(f"VTT download failed: {str(e)}")
        except IOError as e:
            logger.error(f"Failed to save VTT to {local_path}: {str(e)}")
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


# Convenience function for backward compatibility
def download_vtt(
    url: str,
    output_dir: str,
    stream_id: Optional[str] = None,
    is_youtube: bool = False,
    append_mode: bool = False,
    stream_url: Optional[str] = None,
    youtube_cookies_path: Optional[str] = None
) -> str:
    """
    Download VTT file. Convenience function wrapping VTTDownloader.
    
    See VTTDownloader.download() for parameter documentation.
    """
    downloader = VTTDownloader(youtube_cookies_path=youtube_cookies_path)
    return downloader.download(
        url=url,
        output_dir=output_dir,
        stream_id=stream_id,
        is_youtube=is_youtube,
        append_mode=append_mode,
        stream_url=stream_url
    )
