"""
Basic VTTKit usage example.

Demonstrates downloading and parsing a VTT file from a direct URL.
"""

from vttkit import VTTDownloader, VTTParser

def main():
    # Initialize downloader and parser
    downloader = VTTDownloader()
    parser = VTTParser()
    
    # Download VTT file
    print("Downloading VTT file...")
    vtt_path = downloader.download(
        url="https://example.com/subtitles.vtt",
        output_dir="/tmp/vtt"
    )
    print(f"Downloaded to: {vtt_path}")
    
    # Parse to segments.json
    print("\nParsing VTT file...")
    result = parser.parse_to_segments(
        vtt_file=vtt_path,
        output_file="segments.json"
    )
    
    print(f"Parsed {result['cues_count']} cues")
    print(f"Output saved to: {result['segments_path']}")

if __name__ == "__main__":
    main()
