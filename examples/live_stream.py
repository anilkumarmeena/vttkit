"""
Live stream processing example.

Demonstrates downloading and processing VTT from a YouTube live stream with
complete pipeline including word-level timestamp enrichment.

Pipeline:
1. Download VTT → _current.vtt
2. Apply timestamp correction (YouTube live streams)
3. Enrich with word-level timestamps (optional)
4. Merge into main VTT file with deduplication
"""

import logging

from vttkit import VTTDownloader, VTTParser, YouTubeClient
from vttkit.youtube import extract_m3u8_info

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
    
    # Enable word-level timestamp enrichment (NEW feature)
    # Set to True to automatically add estimated word timestamps to VTT files
    enrich_word_timestamps = True
    
    # Initialize clients
    downloader = VTTDownloader()
    parser = VTTParser()
    youtube_client = YouTubeClient()
    
    # Auto-extract VTT URL from YouTube if not provided
    if vtt_url is None:
        print("VTT URL not provided, extracting from YouTube...")
        try:
            live_info = youtube_client.extract_live_info(live_url)
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
    
    # Download live stream VTT with complete processing pipeline
    print("\nDownloading live stream VTT...")
    print(f"Word timestamp enrichment: {'ENABLED' if enrich_word_timestamps else 'DISABLED'}")
    
    vtt_path = downloader.download(
        url=vtt_url,
        output_dir="local/live_vtt",
        stream_id="live_stream",
        is_youtube=True,
        append_mode=True,  # Transform and merge into main VTT file
        stream_url=live_url,
        m3u8_info=m3u8_info,  # Pass M3U8 info for timestamp correction
        enrich_word_timestamps=enrich_word_timestamps  # NEW: Add word-level timestamps
    )
    print(f"Downloaded to: {vtt_path}")
    
    # Show sample of word-level timestamps if enrichment was enabled
    if enrich_word_timestamps:
        print("\n" + "="*70)
        print("Sample of VTT with word-level timestamps:")
        print("="*70)
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Show first few cues
            sample_lines = 0
            for line in lines:
                print(line.rstrip())
                sample_lines += 1
                if sample_lines >= 15:  # Show first 15 lines
                    break
        print("="*70)
    
    # Parse the merged VTT file (timestamps already corrected during download)
    print("\nParsing merged VTT file...")
    segments_output = vtt_path.replace('.vtt', '_segments.json')
    result = parser.parse_to_segments(
        vtt_file=vtt_path,
        output_file=segments_output,
        is_youtube=True,
        m3u8_info=m3u8_info
    )
    
    print(f"\nParsing results:")
    print(f"  ✓ Parsed {result['cues_count']} cues")
    print(f"  ✓ Output saved to: {result['segments_path']}")
    
    print("\n" + "="*70)
    print("Complete processing pipeline executed successfully!")
    print("="*70)
    print("\nPipeline steps:")
    print("  1. ✓ Downloaded VTT from YouTube live stream")
    print("  2. ✓ Applied timestamp correction using M3U8 metadata")
    if enrich_word_timestamps:
        print("  3. ✓ Enriched with word-level timestamps (syllable-based)")
    else:
        print("  3. ⊗ Word enrichment skipped (set enrich_word_timestamps=True to enable)")
    print("  4. ✓ Merged with existing VTT (deduplication)")
    print("  5. ✓ Parsed to segments.json format")
    print("="*70)

if __name__ == "__main__":
    main()
