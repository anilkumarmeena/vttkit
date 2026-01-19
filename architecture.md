# VTTKit Architecture

## Overview

VTTKit is a comprehensive Python library for downloading, parsing, merging, and processing WebVTT (VTT) subtitle files. It provides specialized support for YouTube videos and live streams, including HLS playlist handling and timestamp correction capabilities.

## Design Philosophy

1. **Modularity**: Each component has a single, well-defined responsibility
2. **Extensibility**: Easy to add new sources or processing capabilities
3. **Live Stream First**: Built with incremental updates and merging in mind
4. **YouTube Native**: Deep integration with YouTube's subtitle system via yt-dlp
5. **Word-Level Precision**: Extracts and preserves word-level timestamps for fine-grained control

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Public API Layer                      │
│  (VTTDownloader, VTTParser, VTTMerger, YouTubeClient)   │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                   Processing Layer                       │
│    (core.py, corrector.py, merger.py, parser.py)       │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                   Integration Layer                      │
│          (youtube/client.py, youtube/m3u8.py)           │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                    Data Models                           │
│                   (models.py)                            │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Data Models (`models.py`)

Defines the core data structures used throughout the package:

- **VTTWord**: Represents a word with its timestamp
- **VTTCue**: Represents a subtitle segment with word-level timestamps
- **VTTSegment**: Complete VTT document structure
- **DownloadConfig**: Configuration for download operations
- **M3U8Info**: M3U8 playlist metadata for timestamp correction

**Design Pattern**: Data Transfer Objects (DTOs) using Python dataclasses

### 2. Core Parsing (`core.py`)

The foundational VTT parsing engine that handles:

#### Key Functions:
- `timestamp_to_seconds()` / `seconds_to_timestamp()`: Bidirectional timestamp conversion
- `parse_vtt_content()`: Main parsing function that extracts cues and word-level timestamps
- `clean_vtt_content()`: Removes invalid entries and consecutive timestamps
- `split_long_cues()`: Breaks long subtitle segments into manageable chunks
- `build_cues_from_words()`: Reconstructs cues from word-level data

#### Parsing Algorithm:
1. **Header Extraction**: Parse WEBVTT header and metadata
2. **Cue Extraction**: Identify timestamp blocks and associated text
3. **Word-Level Parsing**: Extract timestamps from `<timestamp><c>text</c>` tags
4. **Syllable Grouping**: Group syllables into words based on spacing
5. **Timestamp Resolution**: Convert relative timestamps to absolute
6. **Cue Reconstruction**: Optionally rebuild cues from word data
7. **Duration Splitting**: Ensure cues don't exceed max duration

**Design Pattern**: Pipeline processing with functional composition

### 3. VTT Downloader (`downloader.py`)

Handles downloading VTT files from multiple sources:

#### Supported Sources:
- Direct HTTP/HTTPS URLs
- HLS playlists (M3U8)
- YouTube videos (via yt-dlp)
- YouTube live streams (with incremental updates)

#### Key Features:
- **Append Mode**: Merge new content with existing files (for live streams)
- **HLS Segment Handling**: Download and merge multiple M3U8 segments
- **Automatic Deduplication**: Prevent duplicate cues when merging
- **Stream ID Management**: Consistent naming for multi-download scenarios

#### Download Flow:
```
URL Input
    │
    ├─ YouTube URL? → YouTubeClient.download_subtitles()
    │                      │
    │                      └─ yt-dlp extraction → VTT URL
    │
    ├─ HLS Playlist? → download_vtt_segments_from_hls()
    │                      │
    │                      ├─ Parse M3U8 playlist
    │                      ├─ Download all segments
    │                      └─ Merge segments
    │
    └─ Direct URL → HTTP download
                        │
                        └─ Append mode? → Merge with existing
```

**Design Pattern**: Strategy pattern for different download sources

### 4. VTT Parser (`parser.py`)

Orchestrates the complete parsing pipeline from VTT to structured JSON:

#### Responsibilities:
- Load VTT files from disk
- Apply core parsing with configurable options
- Calculate and apply timestamp corrections
- Generate segments.json output format
- Track correction metadata

#### Output Format (segments.json):
```json
{
  "header": {
    "timestamp_correction": {
      "applied": true,
      "offset_seconds": 6170.0,
      "correction_method": "media_sequence",
      "media_sequence": 1234,
      "segment_duration": 5.0
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

**Design Pattern**: Facade pattern wrapping core functionality

### 5. VTT Merger (`merger.py`)

Provides merging and deduplication for incremental VTT updates:

#### Key Functions:
- `parse_vtt_cues()`: Extract cues from VTT content
- `deduplicate_cues()`: Remove duplicate cues based on timestamp + text
- `merge_vtt_content()`: Combine multiple VTT contents
- `format_vtt_from_cues()`: Reconstruct valid VTT from cues

#### Deduplication Strategy:
- Creates signature: `timestamp || text`
- Uses set-based lookup for O(1) duplicate detection
- Preserves order of first occurrence

**Design Pattern**: Builder pattern for incremental construction

### 6. Timestamp Corrector (`corrector.py`)

Handles timestamp offset calculation and application for live streams:

#### Why Timestamp Correction?

YouTube live streams provide VTT files with timestamps relative to the current segment, not the actual stream start time. The corrector uses M3U8 playlist metadata to calculate the true offset.

#### Correction Methods:
1. **Media Sequence**: `offset = media_sequence × segment_duration`
2. **Program Date Time**: Parse absolute timestamp from M3U8 (fallback)
3. **None**: No correction applied

#### VTTTimestampCorrector Class:
```python
corrector = VTTTimestampCorrector(m3u8_info)
corrected_cues = corrector.apply_to_cues(cues)
metadata = corrector.get_correction_metadata()
```

**Design Pattern**: Decorator pattern (adds offset to existing timestamps)

### 7. YouTube Integration (`youtube/`)

#### YouTubeClient (`youtube/client.py`)

Wrapper around yt-dlp for YouTube-specific operations:

- **download_subtitles()**: Extract VTT URL and download
- **extract_live_info()**: Get live stream metadata
- **is_live_active()**: Check if stream is currently live
- **refresh_vtt_url()**: Get updated VTT URL for live streams

#### M3U8 Utilities (`youtube/m3u8.py`)

Parse M3U8 playlists for timestamp correction:

- **extract_m3u8_info()**: Parse media sequence and segment duration
- **extract_m3u8_program_date_time()**: Extract absolute timestamps
- **is_m3u8_url()**: Validate M3U8 URLs

**Design Pattern**: Adapter pattern (adapts yt-dlp to VTTKit interface)

## Data Flow

### Standard Video Workflow

```
YouTube URL
    │
    ▼
YouTubeClient.download_subtitles()
    │
    ▼
VTT File (disk)
    │
    ▼
VTTParser.parse_to_segments()
    │
    ├─ core.parse_vtt_content()
    │       │
    │       ├─ Extract cues
    │       ├─ Parse word timestamps
    │       └─ Split long cues
    │
    └─ segments.json (output)
```

### Live Stream Workflow

```
YouTube Live URL
    │
    ▼
extract_m3u8_info() ─────────────┐
    │                            │
    ▼                            │
VTTDownloader.download()         │
    │                            │
    ├─ append_mode=True          │
    ├─ Merge with existing       │
    └─ VTT File (disk)           │
            │                    │
            ▼                    │
VTTParser.parse_to_segments()    │
    │                            │
    ├─ core.parse_vtt_content()  │
    │                            │
    ├─ VTTTimestampCorrector ◄───┘
    │       │
    │       └─ Apply offset
    │
    └─ segments.json (output)
```

## Key Design Decisions

### 1. Word-Level Timestamp Extraction

**Problem**: VTT files use syllable-level timestamps within `<c>` tags, but we need word-level granularity.

**Solution**: 
- Parse all `<timestamp><c>text</c>` pairs
- Group syllables by detecting spaces in tags
- Calculate middle timestamp for multi-syllable words
- Preserve word boundaries for accurate reconstruction

### 2. Incremental Live Stream Updates

**Problem**: Live streams continuously generate new VTT content that needs to be merged without duplication.

**Solution**:
- Append mode in downloader
- Signature-based deduplication (timestamp + text)
- Preserve existing file and merge new cues
- Rebuild cues from words to handle overlaps

### 3. Timestamp Correction Strategy

**Problem**: YouTube live VTT timestamps are relative to current segment, not stream start.

**Solution**:
- Extract M3U8 metadata (media sequence, segment duration)
- Calculate offset: `media_sequence × segment_duration`
- Apply offset to all timestamps after parsing
- Store correction metadata in output for auditing

### 4. Cue Duration Management

**Problem**: Some VTT cues can be very long (10+ seconds), making them hard to process.

**Solution**:
- Configurable `max_cue_duration` (default: 2.0 seconds)
- Split long cues at word boundaries
- Preserve word timestamps during splitting
- Option to rebuild all cues from word data

### 5. Clean Content Processing

**Problem**: VTT files can contain empty cues, consecutive timestamps, and invalid entries.

**Solution**:
- `clean_vtt_content()` function removes invalid patterns
- Filters timestamp lines and content lines
- Removes consecutive timestamps (empty cues)
- Reconstructs valid VTT structure

## Extension Points

### Adding New Download Sources

1. Implement source detection in `downloader.py`
2. Add download handler function
3. Return VTT content as string
4. Integrate with existing merge logic

### Adding New Correction Methods

1. Extend `calculate_timestamp_offset()` in `corrector.py`
2. Add new correction method identifier
3. Implement offset calculation logic
4. Update metadata tracking

### Custom Output Formats

1. Extend `VTTParser` class
2. Add new output method (e.g., `parse_to_srt()`)
3. Use existing parsed cue data
4. Format according to target specification

## Dependencies

### Core Dependencies
- **requests**: HTTP downloads
- **yt-dlp**: YouTube integration

### Optional Dependencies
- **pytest**: Testing framework
- **black**: Code formatting
- **mypy**: Type checking

## File Organization

```
vttkit/
├── __init__.py           # Public API exports
├── core.py               # Core parsing engine
├── corrector.py          # Timestamp correction
├── downloader.py         # Multi-source downloads
├── merger.py             # VTT merging & deduplication
├── models.py             # Data structures
├── parser.py             # Parsing orchestration
└── youtube/
    ├── __init__.py       # YouTube utilities export
    ├── client.py         # yt-dlp wrapper
    └── m3u8.py           # M3U8 parsing

examples/
├── basic_usage.py        # Simple download & parse
├── live_stream.py        # Live stream handling
├── merging_example.py    # Manual merging
└── youtube_download.py   # YouTube-specific examples
```

## Testing Strategy

### Unit Tests
- Core parsing functions (timestamp conversion, word extraction)
- Deduplication logic
- Timestamp correction calculations

### Integration Tests
- End-to-end download → parse → output
- Live stream merge scenarios
- YouTube URL handling

### Edge Cases
- Empty VTT files
- Malformed timestamps
- Very long cues
- Duplicate detection
- Offset validation

## Performance Considerations

1. **Memory Efficiency**: Stream-based processing where possible
2. **Deduplication**: O(1) lookup using set-based signatures
3. **File I/O**: Minimize disk reads/writes
4. **Network**: Reuse HTTP sessions, configurable timeouts
5. **Parsing**: Single-pass parsing with minimal backtracking

## Future Enhancements

### Potential Features
- [ ] SRT format support
- [ ] Real-time streaming API
- [ ] WebSocket support for live updates
- [ ] Multi-language subtitle handling
- [ ] Subtitle translation integration
- [ ] Advanced text cleaning (profanity filter, etc.)
- [ ] Subtitle synchronization tools
- [ ] Batch processing utilities

### Architectural Improvements
- [ ] Async/await support for downloads
- [ ] Plugin system for custom sources
- [ ] Caching layer for repeated downloads
- [ ] Configuration file support
- [ ] CLI tool with rich interface

## Troubleshooting Guide

### Common Issues

**Issue**: Timestamps are incorrect for live streams  
**Solution**: Ensure M3U8 info is passed to parser with correct media_sequence

**Issue**: Duplicate cues in merged output  
**Solution**: Use append_mode=True in downloader for automatic deduplication

**Issue**: Very long cues in output  
**Solution**: Adjust max_cue_duration parameter (default: 2.0s)

**Issue**: Missing word timestamps  
**Solution**: Enable rebuild_cues_from_words=True in parser

**Issue**: YouTube download fails  
**Solution**: Check yt-dlp version, consider using cookies file for authentication

## Contributing

When contributing to VTTKit:

1. **Follow the module structure**: Each component has a specific responsibility
2. **Maintain backward compatibility**: Public API changes require major version bump
3. **Add tests**: Unit tests for new functions, integration tests for workflows
4. **Document thoroughly**: Docstrings with examples for all public functions
5. **Type hints**: Use type annotations for better IDE support
6. **Logging**: Use appropriate log levels (debug, info, warning, error)

## License

MIT License - See LICENSE file for details.

---

**Version**: 0.1.0  
**Last Updated**: 2026-01-19  
**Maintainers**: VTTKit Contributors
