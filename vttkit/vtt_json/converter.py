"""
VTT content parsing and conversion utilities.

Provides core VTT parsing functionality for converting VTT format to structured
data with word-level timestamps. This module focuses on low-level VTT parsing
operations and includes all VTT-specific utility functions.
"""

import re
from itertools import groupby

from ..utils import timestamp_to_seconds, seconds_to_timestamp


def resolve_inner_timestamp(tag_timestamp: str, base_seconds: float) -> str:
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


def calculate_middle_timestamp(syllable_list):
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
    """
    # Regular expressions to match timestamp lines and content lines with formatting
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}')
    content_pattern = re.compile(r'.*<\d{2}:\d{2}:\d{2}\.\d{3}>.*')
    
    # Split content into lines
    lines = content.strip().split('\n')
    
    # First pass: extract all timestamp and content lines
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if timestamp_pattern.match(line) or content_pattern.search(line):
            filtered_lines.append(line)
    
    # Second pass: remove consecutive timestamps and empty timestamp entries
    cleaned_lines = []
    i = 0
    while i < len(filtered_lines):
        current_line = filtered_lines[i]
        
        # If current line is a timestamp
        if timestamp_pattern.match(current_line):
            # Check if there's a next line and it's not another timestamp
            if i+1 < len(filtered_lines) and not timestamp_pattern.match(filtered_lines[i+1]):
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


def split_long_cues(cues, max_duration=2.0):
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
        
        # Sort words by timestamp
        words = sorted(cue['words'], key=lambda w: timestamp_to_seconds(w['time']))
        
        # Group words by exact same timestamp
        word_groups = []
        for timestamp, group in groupby(words, key=lambda w: w['time']):
            word_group = list(group)
            word_groups.append({
                'timestamp': timestamp,
                'timestamp_seconds': timestamp_to_seconds(timestamp),
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
                new_cue = {
                    'start_time': seconds_to_timestamp(chunk_start),
                    'end_time': seconds_to_timestamp(chunk_end),
                    'text': cue['text'],
                    'words': [w for w in words if timestamp_to_seconds(w['time']) >= chunk_start and 
                              timestamp_to_seconds(w['time']) < chunk_end]
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


def build_cues_from_words(words, max_cue_duration=2.0):
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

    indexed_words = list(enumerate(words))
    indexed_words.sort(key=lambda item: (timestamp_to_seconds(item[1]["time"]), item[0]))

    cues = []
    current_words = []
    segment_start = None
    segment_end = None

    for _, word in indexed_words:
        word_time = timestamp_to_seconds(word["time"])
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


def parse_vtt_content(vtt_content, max_cue_duration=2.0, clean_content=True, rebuild_cues_from_words=False):
    """Parse VTT content and ensure cues are under max_cue_duration seconds.

    If rebuild_cues_from_words is True, cues are rebuilt from word-level timestamps.
    """
    # Clean the VTT content if requested
    if clean_content:
        vtt_content = clean_vtt_content(vtt_content)
    
    # Split the content by empty lines to separate header and cues
    blocks = vtt_content.strip().split("\n\n")
    
    # Extract header
    header = {}
    header_lines = blocks[0].split("\n")
    # First line is always WEBVTT
    for line in header_lines[1:]:
        if ': ' in line:
            key, value = line.split(': ', 1)
            header[key] = value
    
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
        timestamp_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})'
        timestamp_match = re.search(timestamp_pattern, timestamp_line)
        
        if timestamp_match:
            timestamp_index = 0
        else:
            # The first line is an identifier, the second line has the timestamp
            timestamp_index = 1
            timestamp_line = lines[1]
            timestamp_match = re.search(timestamp_pattern, timestamp_line)
        
        if not timestamp_match:
            continue
            
        start_time = timestamp_match.group(1)
        end_time = timestamp_match.group(2)
        cue_start_seconds = timestamp_to_seconds(start_time)
        cue_end_seconds = timestamp_to_seconds(end_time)
        
        # Extract text content
        text_lines = lines[timestamp_index+1:]
        text_content = ' '.join(text_lines)
        
        # Extract word-level timestamps by grouping syllables
        # Word boundaries are detected by spaces in <c> tags

        # Pattern to match timestamp and text in <c> tags
        # Matches: <HH:MM:SS.mmm><c>text</c>
        pattern = r'<(\d{2}:\d{2}:\d{2}\.\d{3})><c>([^<]*)</c>'

        words_with_timestamps = []
        syllables_in_word = []
        matches = list(re.finditer(pattern, text_content))

        def finalize_word():
            if not syllables_in_word:
                return
            word_text = ''.join([s[1] for s in syllables_in_word]).strip()
            if word_text:
                middle_timestamp = calculate_middle_timestamp(syllables_in_word)
                words_with_timestamps.append({
                    "word": word_text,
                    "time": middle_timestamp
                })

        inner_base_seconds = cue_start_seconds
        if matches:
            first_tag_text = matches[0].group(2)
            first_tag_seconds = timestamp_to_seconds(matches[0].group(1))
            if rebuild_cues_from_words:
                # Align the first inner timestamp to the cue start for incremental updates.
                inner_base_seconds = cue_start_seconds - first_tag_seconds
            else:
                cue_duration = max(0.0, cue_end_seconds - cue_start_seconds)
                if first_tag_seconds > cue_duration + 0.05:
                    inner_base_seconds = cue_start_seconds - first_tag_seconds

            text_before_first_tag = text_content[:matches[0].start()]
            text_before_first_tag = text_before_first_tag.replace("\n", " ").rstrip()
            include_prefix_words = not rebuild_cues_from_words or not has_emitted_words

            if text_before_first_tag:
                prefix_tokens = text_before_first_tag.split()
                if prefix_tokens:
                    if first_tag_text.startswith(' '):
                        if include_prefix_words:
                            for word in prefix_tokens:
                                words_with_timestamps.append({
                                    "word": word,
                                    "time": start_time
                                })
                    else:
                        if include_prefix_words and len(prefix_tokens) > 1:
                            for word in prefix_tokens[:-1]:
                                words_with_timestamps.append({
                                    "word": word,
                                    "time": start_time
                                })
                        syllables_in_word = [(start_time, prefix_tokens[-1])]

            # Process all timestamp + text pairs
            for match in matches:
                timestamp = match.group(1)
                text = match.group(2)
                resolved_timestamp = resolve_inner_timestamp(
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
            syllables_in_word = []
        
        # Fallback: if no words extracted, split clean text by spaces
        if not words_with_timestamps:
            clean_text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', text_content)
            clean_text = re.sub(r'<c>(.*?)</c>', r'\1', clean_text)
            for word in clean_text.strip().split():
                words_with_timestamps.append({
                    "word": word,
                    "time": start_time
                })

        if words_with_timestamps:
            has_emitted_words = True
                
        # Clean text (remove all tags)
        clean_text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', text_content)
        clean_text = re.sub(r'<c>(.*?)</c>', r'\1', clean_text)
        
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


def format_transcript_with_timestamps(cues):
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


def parse_vtt(vtt_file_path, max_cue_duration=2.0):
    """
    Parse a VTT file and return both the formatted transcript and the structured data.
    
    Args:
        vtt_file_path: Path to the VTT file
        max_cue_duration: Maximum duration in seconds for each subtitle segment
        
    Returns:
        A tuple of (formatted transcript string, structured VTT data)
    """
    with open(vtt_file_path, 'r', encoding='utf-8') as f:
        vtt_content = f.read()
    result = parse_vtt_content(vtt_content, max_cue_duration)
    return format_transcript_with_timestamps(result["cues"]), result
