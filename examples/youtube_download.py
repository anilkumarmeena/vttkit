"""
YouTube download example.

Demonstrates downloading and parsing subtitles from a YouTube video.
"""

from vttkit import VTTDownloader, VTTParser

def main():
    # YouTube video URL
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Initialize downloader and parser
    downloader = VTTDownloader()
    parser = VTTParser()
    
    # Download YouTube subtitles
    print(f"Downloading subtitles from YouTube...")
    vtt_path = downloader.download(
        url=youtube_url,
        output_dir="local/youtube_vtt",
        is_youtube=True,
        stream_url=youtube_url  # Required for yt-dlp
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
