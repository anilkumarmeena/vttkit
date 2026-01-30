"""
VTT content parsing and conversion utilities.

Provides core VTT parsing functionality for converting VTT format to structured
data with word-level timestamps. This module focuses on low-level VTT parsing
operations and includes all VTT-specific utility functions.
"""

import re
from itertools import groupby
from typing import Dict, List, Optional, Any, Tuple

from ..utils import timestamp_to_seconds, seconds_to_timestamp

# Constants
DEFAULT_MAX_CUE_DURATION = 2.0
TIMESTAMP_ALIGNMENT_TOLERANCE = 0.05  # seconds

# Pre-compiled regex patterns for performance
# Support any number of hour digits for live streams with large offsets
_TIMESTAMP_PATTERN = re.compile(r'(\d+:\d{2}:\d{2}\.\d{3}) --> (\d+:\d{2}:\d{2}\.\d{3})')
_CONTENT_PATTERN = re.compile(r'.*<\d+:\d{2}:\d{2}\.\d{3}>.*')
_TAG_PATTERN = re.compile(r'<(\d+:\d{2}:\d{2}\.\d{3})><c>([^<]*)</c>')
_CLEAN_TEXT_PATTERN = re.compile(r'<\d+:\d{2}:\d{2}\.\d{3}>|</?c>')


def _resolve_inner_timestamp(tag_timestamp: str, base_seconds: float) -> str:
    """
    Resolve cue-relative timestamps to absolute timestamps.
    
    Args:
        tag_timestamp: Relative timestamp within a cue
        base_seconds: Base time in seconds to add to
        
    Returns:
        Absolute timestamp string in HH:MM:SS.mmm format
    """
    tag_seconds = timestamp_to_seconds(tag_timestamp)
    return seconds_to_timestamp(base_seconds + tag_seconds)


def _calculate_middle_timestamp(syllable_list: List[Tuple[str, str]]) -> str:
    """
    Calculate middle timestamp from list of (timestamp, text) tuples.
    
    Args:
        syllable_list: List of (timestamp_str, text) tuples
        
    Returns:
        Middle timestamp as string in HH:MM:SS.mmm format
    """
    if not syllable_list:
        return "00:00:00.000"
    
    if len(syllable_list) == 1:
        return syllable_list[0][0]
    
    # Convert all timestamps to seconds
    timestamps_seconds = [timestamp_to_seconds(ts) for ts, _ in syllable_list]
    
    # Calculate middle (average of first and last)
    middle_seconds = (timestamps_seconds[0] + timestamps_seconds[-1]) / 2
    
    return seconds_to_timestamp(middle_seconds)


def clean_vtt_content(content: str) -> str:
    """
    Clean a VTT content by keeping only timestamp lines and formatted content lines.
    Removes consecutive timestamp entries and empty timestamp entries.
    
    Args:
        content: VTT file content as string
        
    Returns:
        Cleaned VTT content as string
        
    Raises:
        ValueError: If content is empty or invalid
    """
    if not content or not content.strip():
        raise ValueError("VTT content cannot be empty")
    
    # Split content into lines
    lines = content.strip().split('\n')
    
    # First pass: extract all timestamp and content lines using pre-compiled patterns
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if _TIMESTAMP_PATTERN.match(line) or _CONTENT_PATTERN.search(line):
            filtered_lines.append(line)
    
    # Second pass: remove consecutive timestamps and empty timestamp entries
    cleaned_lines = []
    i = 0
    while i < len(filtered_lines):
        current_line = filtered_lines[i]
        
        # If current line is a timestamp
        if _TIMESTAMP_PATTERN.match(current_line):
            # Check if there's a next line and it's not another timestamp
            if i+1 < len(filtered_lines) and not _TIMESTAMP_PATTERN.match(filtered_lines[i+1]):
                cleaned_lines.append(current_line)
                cleaned_lines.append(filtered_lines[i+1])
                i += 2
            else:
                # Skip this timestamp if next line is another timestamp or no next line exists
                i += 1
        else:
            # Non-timestamp line (shouldn't normally occur in this flow)
            i += 1
    
    # Format the output to be a valid VTT
    return "WEBVTT\n\n" + "\n\n".join([f"{cleaned_lines[i]}\n{cleaned_lines[i+1]}" for i in range(0, len(cleaned_lines), 2)])


def split_long_cues(cues: List[Dict[str, Any]], max_duration: float = DEFAULT_MAX_CUE_DURATION) -> List[Dict[str, Any]]:
    """
    Split cues that are longer than max_duration seconds.
    
    Args:
        cues: List of cue dictionaries
        max_duration: Maximum duration in seconds for each cue
        
    Returns:
        List of cues with long cues split into shorter ones
    """
    new_cues = []
    
    for cue in cues:
        start_time = timestamp_to_seconds(cue['start_time'])
        end_time = timestamp_to_seconds(cue['end_time'])
        duration = end_time - start_time
        
        # If cue is already short enough, keep it
        if duration <= max_duration:
            new_cues.append(cue)
            continue
        
        # Sort words by timestamp - cache the conversion in a dict
        word_times = {id(w): timestamp_to_seconds(w['time']) for w in cue['words']}
        words = sorted(cue['words'], key=lambda w: word_times[id(w)])
        
        # Group words by exact same timestamp
        word_groups = []
        for timestamp, group in groupby(words, key=lambda w: w['time']):
            word_group = list(group)
            timestamp_seconds = timestamp_to_seconds(timestamp)
            word_groups.append({
                'timestamp': timestamp,
                'timestamp_seconds': timestamp_seconds,
                'words': word_group
            })
        
        # If no words or just one group, split evenly
        if len(word_groups) <= 1:
            num_chunks = int(duration / max_duration) + (1 if duration % max_duration > 0 else 0)
            chunk_duration = duration / num_chunks
            
            for i in range(num_chunks):
                chunk_start = start_time + (i * chunk_duration)
                chunk_end = min(start_time + ((i + 1) * chunk_duration), end_time)
                
                # Create new cue
                # Use cached word_times for filtering
                chunk_words = [w for w in words if chunk_start <= word_times[id(w)] < chunk_end]
                new_cue = {
                    'start_time': seconds_to_timestamp(chunk_start),
                    'end_time': seconds_to_timestamp(chunk_end),
                    'text': cue['text'],
                    'words': chunk_words
                }
                new_cues.append(new_cue)
        else:
            # Group words into chunks of max_duration, keeping same-timestamp words together
            current_chunk_word_groups = []
            current_chunk_words = []
            current_chunk_start = start_time
            last_word_end = start_time
            current_chunk_duration = 0
            
            for i, group in enumerate(word_groups):
                group_time = group['timestamp_seconds']
                group_words = group['words']
                
                # Calculate end time for this group
                if i < len(word_groups) - 1:
                    next_group_time = word_groups[i+1]['timestamp_seconds']
                    group_end = next_group_time
                else:
                    # Last group ends at the cue end time
                    group_end = end_time
                
                group_duration = group_end - group_time
                potential_chunk_duration = (group_end - current_chunk_start)
                
                # Check if adding this group would exceed max_duration and we have already added some words
                if potential_chunk_duration > max_duration and current_chunk_words:
                    # Create a new cue with current chunk
                    chunk_words = [w for group in current_chunk_word_groups for w in group['words']]
                    chunk_text = " ".join([w['word'] for w in chunk_words])
                    
                    new_cue = {
                        'start_time': seconds_to_timestamp(current_chunk_start),
                        'end_time': seconds_to_timestamp(last_word_end),
                        'text': chunk_text,
                        'words': chunk_words
                    }
                    new_cues.append(new_cue)
                    
                    # Start a new chunk with this group
                    current_chunk_word_groups = []
                    current_chunk_words = []
                    current_chunk_start = group_time
                    current_chunk_duration = 0
                
                # Add the current group to the chunk
                current_chunk_word_groups.append(group)
                current_chunk_words.extend(group_words)
                last_word_end = group_end
                current_chunk_duration = last_word_end - current_chunk_start
            
            # Add the final chunk if it has words
            if current_chunk_words:
                chunk_text = " ".join([w['word'] for w in current_chunk_words])
                
                new_cue = {
                    'start_time': seconds_to_timestamp(current_chunk_start),
                    'end_time': cue['end_time'],
                    'text': chunk_text,
                    'words': current_chunk_words
                }
                new_cues.append(new_cue)
    
    return new_cues


def build_cues_from_words(words: List[Dict[str, Any]], max_cue_duration: float = DEFAULT_MAX_CUE_DURATION) -> List[Dict[str, Any]]:
    """
    Build cues from a word-level list using a max duration window.
    
    Args:
        words: List of word dictionaries with 'word' and 'time' keys
        max_cue_duration: Maximum duration in seconds for each cue
        
    Returns:
        List of cue dictionaries built from words
    """
    if not words:
        return []

    # Cache timestamp conversions and sort with stable index
    word_times = [(timestamp_to_seconds(w["time"]), i, w) for i, w in enumerate(words)]
    word_times.sort(key=lambda item: (item[0], item[1]))

    cues = []
    current_words = []
    segment_start = None
    segment_end = None

    for word_time, _, word in word_times:
        if segment_start is None:
            segment_start = word_time
            segment_end = word_time
            current_words = [word]
            continue

        if word_time - segment_start > max_cue_duration:
            cues.append({
                "start_time": seconds_to_timestamp(segment_start),
                "end_time": seconds_to_timestamp(segment_end),
                "text": " ".join([w["word"] for w in current_words]).strip(),
                "words": current_words,
            })
            current_words = [word]
            segment_start = word_time
            segment_end = word_time
        else:
            current_words.append(word)
            segment_end = word_time

    if current_words:
        cues.append({
            "start_time": seconds_to_timestamp(segment_start),
            "end_time": seconds_to_timestamp(segment_end),
            "text": " ".join([w["word"] for w in current_words]).strip(),
            "words": current_words,
        })

    return cues


def _extract_header(header_lines: List[str]) -> Dict[str, str]:
    """
    Extract header metadata from VTT header lines.
    
    Args:
        header_lines: List of header lines (after WEBVTT)
        
    Returns:
        Dictionary of header key-value pairs
    """
    header = {}
    for line in header_lines[1:]:  # Skip "WEBVTT" line
        if ': ' in line:
            key, value = line.split(': ', 1)
            header[key] = value
    return header


def _clean_text(text: str) -> str:
    """
    Remove all VTT formatting tags from text.
    
    Args:
        text: Text with VTT tags
        
    Returns:
        Clean text without tags
    """
    return _CLEAN_TEXT_PATTERN.sub('', text)


def _parse_word_timestamps(
    text_content: str,
    cue_start_seconds: float,
    cue_end_seconds: float,
    start_time: str,
    rebuild_cues_from_words: bool,
    has_emitted_words: bool,
    previous_words: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, str]]:
    """
    Extract word-level timestamps from VTT text content.
    
    Args:
        text_content: VTT text with timestamp tags
        cue_start_seconds: Cue start time in seconds
        cue_end_seconds: Cue end time in seconds
        start_time: Cue start timestamp string
        rebuild_cues_from_words: Whether rebuilding cues from words
        has_emitted_words: Whether words have been emitted previously
        previous_words: Previously emitted words for overlap trimming when rebuilding
        
    Returns:
        List of word dictionaries with 'word' and 'time' keys
    """
    words_with_timestamps = []
    syllables_in_word = []
    matches = list(_TAG_PATTERN.finditer(text_content))

    def _trim_duplicate_prefix(prefix_tokens: List[str], keep_last_token: bool) -> List[str]:
        if not prefix_tokens or not previous_words:
            return prefix_tokens

        previous_tokens = [w["word"] for w in previous_words if "word" in w]
        if not previous_tokens:
            return prefix_tokens

        max_overlap = min(len(prefix_tokens), len(previous_tokens))
        if keep_last_token and max_overlap == len(prefix_tokens):
            max_overlap = len(prefix_tokens) - 1

        overlap = 0
        for size in range(max_overlap, 0, -1):
            if previous_tokens[-size:] == prefix_tokens[:size]:
                overlap = size
                break

        if overlap:
            return prefix_tokens[overlap:]

        return prefix_tokens
    
    def finalize_word():
        if not syllables_in_word:
            return
        word_text = ''.join([s[1] for s in syllables_in_word]).strip()
        if word_text:
            middle_timestamp = _calculate_middle_timestamp(syllables_in_word)
            words_with_timestamps.append({
                "word": word_text,
                "time": middle_timestamp
            })
    
    inner_base_seconds = cue_start_seconds
    if matches:
        first_tag_text = matches[0].group(2)
        first_tag_seconds = timestamp_to_seconds(matches[0].group(1))
        
        if rebuild_cues_from_words:
            # Align the first inner timestamp to the cue start for incremental updates
            inner_base_seconds = cue_start_seconds - first_tag_seconds
        else:
            cue_duration = max(0.0, cue_end_seconds - cue_start_seconds)
            if first_tag_seconds > cue_duration + TIMESTAMP_ALIGNMENT_TOLERANCE:
                inner_base_seconds = cue_start_seconds - first_tag_seconds
        
        text_before_first_tag = text_content[:matches[0].start()]
        text_before_first_tag = text_before_first_tag.replace("\n", " ").rstrip()
        
        if text_before_first_tag:
            prefix_tokens = text_before_first_tag.split()
            if prefix_tokens:
                if rebuild_cues_from_words and has_emitted_words:
                    prefix_tokens = _trim_duplicate_prefix(
                        prefix_tokens,
                        keep_last_token=not first_tag_text.startswith(' ')
                    )
                if first_tag_text.startswith(' '):
                    for word in prefix_tokens:
                        words_with_timestamps.append({
                            "word": word,
                            "time": start_time
                        })
                else:
                    if len(prefix_tokens) > 1:
                        for word in prefix_tokens[:-1]:
                            words_with_timestamps.append({
                                "word": word,
                                "time": start_time
                            })
                    if prefix_tokens:
                        syllables_in_word = [(start_time, prefix_tokens[-1])]
        
        # Process all timestamp + text pairs
        for match in matches:
            timestamp = match.group(1)
            text = match.group(2)
            resolved_timestamp = _resolve_inner_timestamp(
                timestamp,
                inner_base_seconds,
            )
            
            has_leading_space = text.startswith(' ')
            has_trailing_space = text.endswith(' ')
            
            if has_leading_space:
                finalize_word()
                syllables_in_word = []
                text = text.lstrip()
            
            if text:
                syllables_in_word.append((resolved_timestamp, text))
            
            if has_trailing_space:
                finalize_word()
                syllables_in_word = []
        
        # Add the last word if exists
        finalize_word()
    
    # Fallback: if no words extracted, split clean text by spaces
    if not words_with_timestamps:
        clean_text = _clean_text(text_content)
        for word in clean_text.strip().split():
            words_with_timestamps.append({
                "word": word,
                "time": start_time
            })
    
    return words_with_timestamps


def parse_vtt_content(
    vtt_content: str,
    max_cue_duration: float = DEFAULT_MAX_CUE_DURATION,
    clean_content: bool = True,
    rebuild_cues_from_words: bool = False
) -> Dict[str, Any]:
    """
    Parse VTT content and ensure cues are under max_cue_duration seconds.
    
    Args:
        vtt_content: VTT file content as string
        max_cue_duration: Maximum duration in seconds for each cue
        clean_content: Whether to clean VTT content before parsing
        rebuild_cues_from_words: If True, cues are rebuilt from word-level timestamps
        
    Returns:
        Dictionary with 'header' and 'cues' keys
        
    Raises:
        ValueError: If VTT content is empty or invalid format
    """
    # Validate input
    if not vtt_content or not vtt_content.strip():
        raise ValueError("VTT content cannot be empty")
    
    if not vtt_content.strip().startswith("WEBVTT"):
        raise ValueError("Invalid VTT format: must start with 'WEBVTT'")
    
    # Clean the VTT content if requested
    if clean_content:
        vtt_content = clean_vtt_content(vtt_content)
    
    # Split the content by empty lines to separate header and cues
    blocks = vtt_content.strip().split("\n\n")
    
    # Extract header using helper function
    header_lines = blocks[0].split("\n")
    header = _extract_header(header_lines)
    
    # Extract cues
    cues = []
    all_words = []
    has_emitted_words = False
    
    for block in blocks[1:]:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
            
        # Extract timestamp line
        timestamp_line = lines[0]
        
        # Check if the first line is a timestamp, otherwise it's an identifier
        timestamp_match = _TIMESTAMP_PATTERN.search(timestamp_line)
        
        if timestamp_match:
            timestamp_index = 0
        else:
            # The first line is an identifier, the second line has the timestamp
            timestamp_index = 1
            if len(lines) > 1:
                timestamp_line = lines[1]
                timestamp_match = _TIMESTAMP_PATTERN.search(timestamp_line)
        
        if not timestamp_match:
            continue
            
        start_time = timestamp_match.group(1)
        end_time = timestamp_match.group(2)
        cue_start_seconds = timestamp_to_seconds(start_time)
        cue_end_seconds = timestamp_to_seconds(end_time)
        
        # Extract text content
        text_lines = lines[timestamp_index+1:]
        text_content = ' '.join(text_lines)
        
        # Extract word-level timestamps using helper function
        words_with_timestamps = _parse_word_timestamps(
            text_content,
            cue_start_seconds,
            cue_end_seconds,
            start_time,
            rebuild_cues_from_words,
            has_emitted_words,
            previous_words=all_words if rebuild_cues_from_words else None
        )

        if words_with_timestamps:
            has_emitted_words = True
                
        # Clean text (remove all tags)
        clean_text = _clean_text(text_content)
        
        if rebuild_cues_from_words:
            all_words.extend(words_with_timestamps)
        else:
            cue = {
                'start_time': start_time,
                'end_time': end_time,
                'text': clean_text,
                'words': words_with_timestamps
            }
            cues.append(cue)
    
    # Split long cues into shorter ones if needed
    if rebuild_cues_from_words:
        final_cues = build_cues_from_words(all_words, max_cue_duration)
    else:
        final_cues = split_long_cues(cues, max_cue_duration)
    
    return {
        'header': header,
        'cues': final_cues
    }


def format_transcript_with_timestamps(cues: List[Dict[str, Any]]) -> str:
    """
    Format transcript with human-readable timestamps in [HH:MM:SS] format.
    
    Args:
        cues: List of cue dictionaries from parsed VTT
        
    Returns:
        Formatted transcript as a string with one line per cue
    """
    formatted_lines = []
    for cue in cues:
        start_time = timestamp_to_seconds(cue["start_time"])
        hours, remainder = divmod(start_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        timestamp = f"[{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}]"
        formatted_lines.append(f"{timestamp} {cue['text'].strip()}")
    return "\n".join(formatted_lines)


def parse_vtt(vtt_file_path: str, max_cue_duration: float = DEFAULT_MAX_CUE_DURATION) -> Tuple[str, Dict[str, Any]]:
    """
    Parse a VTT file and return both the formatted transcript and the structured data.
    
    Args:
        vtt_file_path: Path to the VTT file
        max_cue_duration: Maximum duration in seconds for each subtitle segment
        
    Returns:
        A tuple of (formatted transcript string, structured VTT data)
        
    Raises:
        FileNotFoundError: If VTT file does not exist
        ValueError: If VTT file is empty or invalid format
    """
    with open(vtt_file_path, 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    result = parse_vtt_content(vtt_content, max_cue_duration)
    return format_transcript_with_timestamps(result["cues"]), result
