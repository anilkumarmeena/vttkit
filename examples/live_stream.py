"""
Live stream processing example.

Demonstrates downloading and parsing VTT from a YouTube live stream
with timestamp correction and incremental merging.
"""

from vttkit import VTTDownloader, VTTParser
from vttkit.youtube import extract_m3u8_info

def main():
    # YouTube live stream URL
    live_url = "https://www.youtube.com/watch?v=LIVE_STREAM_ID"
    
    # VTT URL (extracted from YouTube)
    vtt_url = "https://example.com/live_stream.m3u8"
    
    # Initialize downloader and parser
    downloader = VTTDownloader()
    parser = VTTParser()
    
    # Extract M3U8 info for timestamp correction
    print("Extracting M3U8 metadata...")
    m3u8_info = extract_m3u8_info(vtt_url)
    print(f"Media sequence: {m3u8_info.get('media_sequence')}")
    print(f"Segment duration: {m3u8_info.get('segment_duration')}s")
    
    # Download live stream VTT (with merging for incremental updates)
    print("\nDownloading live stream VTT...")
    vtt_path = downloader.download(
        url=vtt_url,
        output_dir="/tmp/live_vtt",
        stream_id="live_stream",
        is_youtube=True,
        append_mode=True,  # Merge with existing file
        stream_url=live_url
    )
    print(f"Downloaded and merged to: {vtt_path}")
    
    # Parse with timestamp correction
    print("\nParsing with timestamp correction...")
    result = parser.parse_to_segments(
        vtt_file=vtt_path,
        output_file="live_segments.json",
        is_youtube=True,
        m3u8_info=m3u8_info
    )
    
    print(f"Parsed {result['cues_count']} cues")
    print(f"Timestamp offset applied: {result['offset_applied']}s")
    print(f"Correction method: {result['correction_method']}")
    print(f"Output saved to: {result['segments_path']}")

if __name__ == "__main__":
    main()
