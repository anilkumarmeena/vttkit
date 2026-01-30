"""
YouTube download example.

Demonstrates downloading and parsing subtitles from a YouTube video.
"""

import logging

from vttkit import VTTDownloader, VTTParser

# Configure logging to see vttkit internal logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # YouTube video URL
    youtube_url = "https://www.youtube.com/watch?v=eSPJsnYY6_4"
    
    # Initialize downloader and parser
    downloader = VTTDownloader()
    parser = VTTParser()
    
    # Download YouTube subtitles
    # Note: is_youtube and stream_url are now optional - YouTube URLs are auto-detected
    print(f"Downloading subtitles from YouTube...")
    vtt_path = downloader.download(
        url=youtube_url,
        output_dir="local/youtube_vtt",
        # is_youtube=True,  # Optional - auto-detected from URL
        # stream_url=youtube_url  # Optional - auto-detected from URL
    )
    print(f"Downloaded to: {vtt_path}")
    
    # Parse to segments.json
    print("\nParsing VTT file...")
    result = parser.parse_to_segments(
        vtt_file=vtt_path,
        output_file="youtube_segments.json"
    )
    
    print(f"Parsed {result['cues_count']} cues")
    print(f"Output saved to: {result['segments_path']}")

if __name__ == "__main__":
    main()
