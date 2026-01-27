# VTTKit

**Complete VTT (WebVTT) Processing Toolkit with YouTube Support**

VTTKit is a Python library for downloading, parsing, merging, and processing WebVTT subtitle files. It includes full support for YouTube videos and live streams, HLS playlist handling, and timestamp correction for live streams.

## Features

✅ **Download VTT** from HTTP URLs, HLS playlists (M3U8), and YouTube  
✅ **Parse VTT** with word-level timestamps  
✅ **Merge VTT** files incrementally (perfect for live streams)  
✅ **Correct timestamps** for YouTube live streams using M3U8 metadata  
✅ **Output segments.json** format with structured cues and word-level data  
✅ **YouTube integration** with yt-dlp (full support)  
✅ **Transcribe audio** to segments.json using faster-whisper  

## Installation

```bash
pip install vttkit
```

For development installation:
```bash
git clone https://github.com/vttkit/vttkit.git
cd vttkit
pip install -e .
```

## Quick Start

### Enable Logging (Optional)

VTTKit uses Python's standard logging module. To see internal logs, configure logging in your script:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Download and Parse a VTT File

```python
from vttkit import VTTDownloader, VTTParser

# Download VTT from URL
downloader = VTTDownloader()
vtt_path = downloader.download(
    url="https://example.com/subtitles.vtt",
    output_dir="local/vtt"
)

# Parse to segments.json
parser = VTTParser()
result = parser.parse_to_segments(
    vtt_file=vtt_path,
    output_file="segments.json"
)

print(f"Parsed {result['cues_count']} cues")
```

### YouTube Video Subtitles

```python
from vttkit import VTTDownloader, VTTParser

# Download from YouTube
downloader = VTTDownloader()
vtt_path = downloader.download(
    url="https://youtube.com/watch?v=VIDEO_ID",
    output_dir="local/vtt",
    is_youtube=True,
    stream_url="https://youtube.com/watch?v=VIDEO_ID"
)

# Parse
parser = VTTParser()
result = parser.parse_to_segments(vtt_path, "segments.json")
```

### YouTube Live Stream (with timestamp correction)

```python
from vttkit import VTTDownloader, VTTParser
from vttkit.youtube import extract_m3u8_info

# Get M3U8 info for timestamp correction
m3u8_info = extract_m3u8_info("https://example.com/playlist.m3u8")

# Download live stream VTT (with merging)
downloader = VTTDownloader()
vtt_path = downloader.download(
    url="https://youtube.com/watch?v=LIVE_ID",
    output_dir="local/live",
    is_youtube=True,
    append_mode=True,  # Merge with existing
    stream_url="https://youtube.com/watch?v=LIVE_ID"
)

# Parse with timestamp correction
parser = VTTParser()
result = parser.parse_to_segments(
    vtt_file=vtt_path,
    output_file="segments.json",
    is_youtube=True,
    m3u8_info=m3u8_info
)

print(f"Applied {result['offset_applied']}s offset using {result['correction_method']}")
```

### Audio Transcription (faster-whisper)

```python
from vttkit import transcribe_to_segments_json

result = transcribe_to_segments_json(
    audio_path="local/audio.wav",
    output_file="segments.json",
    model_name="base",
    language="en",
    max_segment_duration=2.0
)

print(f"Transcribed {result['cues_count']} cues")
```

### Merge Multiple VTT Files

```python
from vttkit import VTTMerger

merger = VTTMerger()

# Add multiple VTT files
merger.add_from_file("part1.vtt")
merger.add_from_file("part2.vtt")
merger.add_from_file("part3.vtt")

# Save merged result
merger.save("merged.vtt")
print(f"Merged {merger.get_cue_count()} cues")
```

## API Reference

### VTTDownloader

Downloads VTT files from various sources.

```python
downloader = VTTDownloader(youtube_cookies_path=None)

vtt_path = downloader.download(
    url: str,                      # VTT URL or YouTube URL
    output_dir: str,               # Where to save
    stream_id: Optional[str],      # Custom ID for naming
    is_youtube: bool = False,      # Use yt-dlp for YouTube
    append_mode: bool = False,     # Merge with existing (for live streams)
    stream_url: Optional[str],     # Original YouTube URL
    timeout: int = 30              # Request timeout
)
```

### VTTParser

Parses VTT files to segments.json format.

```python
parser = VTTParser()

result = parser.parse_to_segments(
    vtt_file: str,                         # Input VTT file
    output_file: str = "segments.json",    # Output file
    m3u8_info: Optional[Dict] = None,      # For timestamp correction
    is_youtube: bool = False,              # Enable YouTube corrections
    max_cue_duration: float = 2.0,         # Max cue length in seconds
    clean_content: bool = True,            # Clean VTT content
    rebuild_cues_from_words: bool = True   # Rebuild from word data
)
```

### VTTMerger

Merges multiple VTT files with deduplication.

```python
merger = VTTMerger()

merger.add_from_file(vtt_path: str)         # Add from file
merger.add_from_content(vtt_content: str)   # Add from string
merger.save(output_path: str)               # Save merged VTT
merged = merger.get_merged_content()        # Get as string
```

### VTTTimestampCorrector

Corrects timestamps for live streams.

```python
from vttkit import VTTTimestampCorrector

corrector = VTTTimestampCorrector(m3u8_info)
corrected_cues = corrector.apply_to_cues(cues)
metadata = corrector.get_correction_metadata()
```

### YouTube Client

```python
from vttkit.youtube import YouTubeClient

client = YouTubeClient(cookies_path=None)

# Download subtitles
vtt_path = client.download_subtitles(url, output_dir)

# Get stream info
info = client.extract_live_info(url)

# Check if live
is_live = client.is_live_active(url)

# Refresh VTT URL
new_url = client.refresh_vtt_url(url)
```

## Core Functions

VTTKit also exports core parsing functions for direct use:

```python
from vttkit import (
    parse_vtt_content,              # Parse VTT string
    timestamp_to_seconds,           # Convert timestamp to float
    seconds_to_timestamp,           # Convert float to timestamp
    format_transcript_with_timestamps,  # Format for reading
)
```

## Output Format

The `segments.json` format includes:

```json
{
  "header": {
    "timestamp_correction": {
      "applied": true,
      "offset_seconds": 6170.0,
      "correction_method": "media_sequence"
    }
  },
  "cues": [
    {
      "start_time": "01:42:50.000",
      "end_time": "01:42:52.000",
      "text": "Hello world",
      "words": [
        {"word": "Hello", "time": "01:42:50.000"},
        {"word": "world", "time": "01:42:51.000"}
      ]
    }
  ]
}
```

## Requirements

- Python >= 3.8
- requests >= 2.28.0
- yt-dlp >= 2023.0.0

## Development

```bash
# Clone repository
git clone https://github.com/vttkit/vttkit.git
cd vttkit

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black vttkit/

# Type checking
mypy vttkit/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Credits

Originally extracted from the short-generator project to provide a standalone, reusable VTT processing library.
