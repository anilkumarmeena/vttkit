"""
Live stream processing example.

Demonstrates downloading and parsing VTT from a YouTube live stream
with timestamp correction and incremental merging.
"""

import logging

from vttkit import VTTDownloader, VTTParser
from vttkit.youtube import extract_m3u8_info, extract_youtube_live_info

# Configure logging to see vttkit internal logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # YouTube live stream URL
    live_url = "https://www.youtube.com/watch?v=raa4Pz1AP9s"
    
    # VTT URL (optional - will be auto-extracted from YouTube if not provided)
    vtt_url = None  # Set to None to auto-extract, or provide the M3U8 URL directly
    
    # Initialize downloader and parser
    downloader = VTTDownloader()
    parser = VTTParser()
    
    # Auto-extract VTT URL from YouTube if not provided
    if vtt_url is None:
        print("VTT URL not provided, extracting from YouTube...")
        try:
            live_info = extract_youtube_live_info(live_url)
            vtt_url = live_info.get('vtt_url')
            
            if vtt_url:
                print(f"Successfully extracted VTT URL from YouTube")
                print(f"Stream title: {live_info.get('title')}")
                print(f"Is live: {live_info.get('is_live')}")
            else:
                raise ValueError("No VTT URL found - captions may not be available for this stream")
        except Exception as e:
            print(f"Error extracting VTT URL from YouTube: {e}")
            print("Please provide the VTT URL manually or ensure the stream has captions enabled")
            return
    
    # Extract M3U8 info for timestamp correction
    print("\nExtracting M3U8 metadata...")
    m3u8_info = extract_m3u8_info(vtt_url)
    print(f"Media sequence: {m3u8_info.get('media_sequence')}")
    print(f"Segment duration: {m3u8_info.get('segment_duration')}s")
    
    # Download live stream VTT (with merging for incremental updates)
    print("\nDownloading live stream VTT...")
    vtt_path = downloader.download(
        url=vtt_url,
        output_dir="local/live_vtt",
        stream_id="live_stream",
        is_youtube=True,
        append_mode=True,  # Merge with existing file
        stream_url=live_url
    )
    print(f"Downloaded and merged to: {vtt_path}")
    
    # Set output path for segments in the same directory as VTT
    segments_output = vtt_path.replace('.vtt', '_segments.json')
    # Parse with timestamp correction
    print("\nParsing with timestamp correction...")
    result = parser.parse_to_segments(
        vtt_file=vtt_path,
        output_file=segments_output,
        is_youtube=True,
        m3u8_info=m3u8_info
    )
    
    print(f"Parsed {result['cues_count']} cues")
    print(f"Timestamp offset applied: {result['offset_applied']}s")
    print(f"Correction method: {result['correction_method']}")
    print(f"Output saved to: {result['segments_path']}")

if __name__ == "__main__":
    main()
