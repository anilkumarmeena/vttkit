"""
Shared utility functions for VTTKit.

Provides common utilities used across multiple modules, primarily
timestamp conversion functions and word-level timestamp estimation.
"""

import re
from typing import List, Dict, Optional, Tuple


def timestamp_to_seconds(timestamp: str) -> float:
    """
    Convert HH:MM:SS.mmm format to seconds.
    
    Args:
        timestamp: Timestamp string in HH:MM:SS.mmm format
        
    Returns:
        Time in seconds as float
        
    Example:
        >>> timestamp_to_seconds("00:01:30.500")
        90.5
    """
    h, m, s = timestamp.split(':')
    seconds = int(h) * 3600 + int(m) * 60 + float(s)
    return seconds


def seconds_to_timestamp(seconds: float) -> str:
    """
    Convert seconds to HH:MM:SS.mmm format.
    
    Args:
        seconds: Time in seconds as float
        
    Returns:
        Timestamp string in HH:MM:SS.mmm format
        
    Example:
        >>> seconds_to_timestamp(90.5)
        '00:01:30.500'
    """
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d}.{milliseconds:03d}"


def estimate_word_timestamps(cue_start: str, cue_end: str, text: str) -> List[Dict[str, str]]:
    """
    Estimate word-level timestamps based on syllable count and word length.
    
    Uses syllable counting for more accurate time distribution. Falls back to
    character counting if syllable library is unavailable or encounters errors.
    
    Algorithm:
    1. Split text into words
    2. Count syllables per word (or use character count as fallback)
    3. Detect punctuation and add pause weights
    4. Calculate baseline duration (150ms per word minimum)
    5. Distribute remaining time proportionally based on syllable/character count
    
    Args:
        cue_start: Start timestamp in HH:MM:SS.mmm format
        cue_end: End timestamp in HH:MM:SS.mmm format
        text: Text content to split into words
        
    Returns:
        List of dictionaries with 'word' and 'time' keys
        
    Example:
        >>> estimate_word_timestamps("00:00:00.000", "00:00:03.000", "preparing to activate")
        [
            {"word": "preparing", "time": "00:00:00.000"},
            {"word": "to", "time": "00:00:01.243"},
            {"word": "activate", "time": "00:00:01.757"}
        ]
    """
    # Import syllables library with fallback
    try:
        import syllables
        use_syllables = True
    except ImportError:
        use_syllables = False
    
    # Split into words
    words = text.split()
    if not words:
        return []
    
    # Calculate total duration
    start_sec = timestamp_to_seconds(cue_start)
    end_sec = timestamp_to_seconds(cue_end)
    total_duration = end_sec - start_sec
    
    # Edge case: single word
    if len(words) == 1:
        return [{"word": words[0], "time": cue_start}]
    
    # Calculate weights for each word
    word_weights = []
    pause_weights = []
    
    for word in words:
        # Clean word for syllable/character counting (remove punctuation)
        clean_word = word.strip('.,!?;:\'"')
        
        # Count syllables or characters
        if use_syllables and clean_word:
            try:
                syllable_count = syllables.estimate(clean_word)
                # Ensure at least 1 syllable
                weight = max(1, syllable_count)
            except Exception:
                # Fallback to character count
                weight = max(1, len(clean_word))
        else:
            # Fallback to character count
            weight = max(1, len(clean_word))
        
        word_weights.append(weight)
        
        # Detect punctuation for pause weights
        pause = 0.0
        if word.endswith((',', ';')):
            pause = 0.1  # 100ms for comma/semicolon
        elif word.endswith(('.', '!', '?')):
            pause = 0.2  # 200ms for sentence-ending punctuation
        pause_weights.append(pause)
    
    # Calculate time distribution
    baseline_per_word = 0.15  # 150ms minimum per word
    total_baseline = baseline_per_word * len(words)
    total_pauses = sum(pause_weights)
    total_weight = sum(word_weights)
    
    # Remaining time to distribute proportionally
    remaining_time = total_duration - total_baseline - total_pauses
    
    # Edge case: if duration is too short, distribute evenly
    if remaining_time < 0:
        remaining_time = 0
    
    # Generate timestamps for each word
    result = []
    current_time = start_sec
    
    for i, (word, weight, pause) in enumerate(zip(words, word_weights, pause_weights)):
        # Calculate word duration
        if total_weight > 0:
            proportional_time = (weight / total_weight) * remaining_time
            word_duration = baseline_per_word + proportional_time
        else:
            word_duration = baseline_per_word
        
        # Add pause after word
        word_duration += pause
        
        # Ensure last word ends exactly at cue_end
        if i == len(words) - 1:
            word_duration = end_sec - current_time
        
        # Create word timestamp entry
        word_timestamp = seconds_to_timestamp(current_time)
        result.append({
            "word": word,
            "time": word_timestamp
        })
        
        current_time += word_duration
    
    return result


def _estimate_word_duration(word: str) -> float:
    """
    Estimate speaking duration based on character count.
    Uses ~5.5 chars/second (165 WPM average speaking rate).
    
    Args:
        word: The word text
        
    Returns:
        Duration in seconds, clamped between 0.2s - 1.5s
    """
    CHARS_PER_SECOND = 5.5
    MIN_DURATION = 0.2
    MAX_DURATION = 1.5
    
    duration = len(word) / CHARS_PER_SECOND
    return max(MIN_DURATION, min(MAX_DURATION, duration))


def _normalize_word_timings(words: List[Dict[str, str]], start_time: str) -> List[Dict[str, str]]:
    """
    Normalize word timestamps to ensure proper spacing.
    
    Fixes:
    - Identical timestamps → adds word-length-based spacing
    - Backwards timestamps → enforces chronological order
    
    Args:
        words: List of word dicts with 'word' and 'time' keys
        start_time: Cue start time to use as minimum
        
    Returns:
        Normalized list of words with corrected timestamps
    """
    if not words:
        return words
    
    normalized = []
    last_time_seconds = timestamp_to_seconds(start_time)
    
    for word in words:
        word_time_seconds = timestamp_to_seconds(word['time'])
        
        # If word is at/before last time, push it forward
        if word_time_seconds <= last_time_seconds:
            if normalized:
                # Use previous word's estimated duration as spacing
                prev_duration = _estimate_word_duration(normalized[-1]['word'])
                word_time_seconds = last_time_seconds + prev_duration
            else:
                word_time_seconds = last_time_seconds
        
        normalized.append({
            'word': word['word'],
            'time': seconds_to_timestamp(word_time_seconds)
        })
        last_time_seconds = word_time_seconds
    
    return normalized


def _calculate_cue_end_time(words: List[Dict[str, str]], provided_end_time: str) -> str:
    """
    Calculate proper cue end time based on last word + its duration.
    Ensures last word has time to display before cue ends.
    
    Args:
        words: Normalized list of words
        provided_end_time: Original end time from JSON
        
    Returns:
        Calculated end time (last word time + 80% of word duration)
    """
    if not words:
        return provided_end_time
    
    last_word = words[-1]
    last_word_time = timestamp_to_seconds(last_word['time'])
    last_word_duration = _estimate_word_duration(last_word['word'])
    
    # Add 80% of word duration as buffer
    calculated_end = last_word_time + (last_word_duration * 0.8)
    
    # Use whichever is larger
    provided_end = timestamp_to_seconds(provided_end_time)
    final_end = max(calculated_end, provided_end)
    
    return seconds_to_timestamp(final_end)


def format_cue_with_word_timestamps(start_time: str, end_time: str, words: List[Dict[str, str]]) -> Tuple[str, str]:
    """
    Format a cue with word-level timestamps into VTT format.
    Normalizes word timings and calculates proper end_time based on word lengths.
    
    Args:
        start_time: Cue start timestamp
        end_time: Cue end timestamp (may be adjusted based on word durations)
        words: List of word dictionaries with 'word' and 'time' keys
        
    Returns:
        Tuple of (formatted_vtt_content, corrected_end_time)
        - formatted_vtt_content: VTT cue content with two lines:
          Line 1: Word-level timestamps with <timestamp><c>word</c> tags
          Line 2: Plain text sentence for fallback/readability
        - corrected_end_time: Adjusted end time ensuring last word has display time
        
    Example:
        >>> words = [
        ...     {"word": "preparing", "time": "00:00:00.000"},
        ...     {"word": "to", "time": "00:00:01.243"},
        ...     {"word": "activate", "time": "00:00:01.757"}
        ... ]
        >>> content, end = format_cue_with_word_timestamps("00:00:00.000", "00:00:03.000", words)
        >>> # content: 'preparing<00:00:01.243><c> to</c><00:00:01.757><c> activate</c>\\npreparing to activate'
        >>> # end: adjusted timestamp based on word durations
    """
    if not words:
        return ("", end_time)
    
    # Step 1: Normalize word timings to fix identical/overlapping timestamps
    normalized_words = _normalize_word_timings(words, start_time)
    
    # Step 2: Calculate proper end time based on last word + its duration
    corrected_end_time = _calculate_cue_end_time(normalized_words, end_time)
    
    # Step 3: Format VTT content (existing logic with normalized words)
    # Build word-level timestamp line and collect plain words
    # Format: first_word<timestamp2><c> word2</c><timestamp3><c> word3</c>
    # Space appears AFTER <c> tag (before the word text inside the tag)
    formatted_parts = []
    plain_words = []
    
    for i, word in enumerate(normalized_words):
        timestamp = word["time"]
        word_text = word["word"]
        plain_words.append(word_text)
        
        if i == 0:
            # First word: just the plain text (no tags)
            formatted_parts.append(word_text)
        else:
            # Subsequent words: <timestamp><c> word</c> (space INSIDE <c> tag)
            formatted_parts.append(f"<{timestamp}><c> {word_text}</c>")
    
    # Join without spaces since spaces are inside <c> tags
    word_timestamp_line = "".join(formatted_parts)
    plain_text_line = " ".join(plain_words)
    content = f"{word_timestamp_line}\n{plain_text_line}"
    
    return (content, corrected_end_time)


def enrich_vtt_content_with_word_timestamps(vtt_content: str) -> str:
    """
    Enrich VTT content string by adding estimated word-level timestamps to cues that lack them.
    
    String-based version that operates directly on VTT content without file I/O.
    Detects cues without word-level timestamps, estimates timestamps using syllable-based
    distribution, and returns enriched VTT content with <timestamp><c>word</c> tags.
    
    Args:
        vtt_content: VTT content as string
        
    Returns:
        Enriched VTT content string with word-level timestamps
        
    Example:
        >>> content = "WEBVTT\\n\\n00:00:01.000 --> 00:00:03.000\\nHello world"
        >>> enriched = enrich_vtt_content_with_word_timestamps(content)
        >>> "Hello<" in enriched  # First word is plain text
        True
        >>> "<c> world</c>" in enriched  # Subsequent words have <c> tags with leading space
        True
    """
    # Split into blocks (header + cues)
    blocks = vtt_content.strip().split('\n\n')
    
    # Pattern to match VTT cue timestamps
    timestamp_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
    # Pattern to detect existing word timestamps
    word_timestamp_pattern = re.compile(r'<\d{2}:\d{2}:\d{2}\.\d{3}><c>')
    
    enriched_blocks = []
    
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        
        # Check if this is the header block (starts with WEBVTT or contains metadata)
        if lines[0].startswith('WEBVTT') or lines[0].startswith('X-TIMESTAMP-MAP') or lines[0].startswith('Kind:') or lines[0].startswith('Language:'):
            enriched_blocks.append(block)
            continue
        
        # Try to find timestamp line
        timestamp_line_idx = None
        timestamp_match = None
        
        for i, line in enumerate(lines):
            match = timestamp_pattern.search(line)
            if match:
                timestamp_line_idx = i
                timestamp_match = match
                break
        
        # If no timestamp found, keep block as-is
        if timestamp_match is None:
            enriched_blocks.append(block)
            continue
        
        start_time = timestamp_match.group(1)
        end_time = timestamp_match.group(2)
        
        # Get text content (everything after timestamp line)
        text_lines = lines[timestamp_line_idx + 1:]
        text_content = ' '.join(text_lines)
        
        # Check if already has word timestamps
        if word_timestamp_pattern.search(text_content):
            # Already has word timestamps, keep as-is
            enriched_blocks.append(block)
            continue
        
        # Clean text (remove any existing tags)
        clean_text = re.sub(r'<[^>]+>', '', text_content)
        clean_text = clean_text.strip()
        
        if not clean_text:
            # Empty text, keep as-is
            enriched_blocks.append(block)
            continue
        
        # Estimate word timestamps
        words = estimate_word_timestamps(start_time, end_time, clean_text)
        
        # Format with word timestamps and get corrected end time
        enriched_text, corrected_end_time = format_cue_with_word_timestamps(start_time, end_time, words)
        
        # Rebuild the block with enriched content and corrected timestamp
        new_block_lines = lines[:timestamp_line_idx]  # Keep identifier (if any)
        # Update timestamp line with corrected end time
        timestamp_line = lines[timestamp_line_idx]
        corrected_timestamp_line = timestamp_line.replace(end_time, corrected_end_time)
        new_block_lines.append(corrected_timestamp_line)
        new_block_lines.append(enriched_text)
        enriched_blocks.append('\n'.join(new_block_lines))
    
    # Build enriched VTT content
    enriched_content = '\n\n'.join(enriched_blocks)
    if not enriched_content.endswith('\n'):
        enriched_content += '\n'
    
    return enriched_content


def enrich_vtt_with_word_timestamps(
    input_vtt_path: str,
    output_vtt_path: Optional[str] = None
) -> Dict[str, int]:
    """
    Enrich a VTT file by adding estimated word-level timestamps to cues that lack them.
    
    Reads a VTT file, detects cues without word-level timestamps, estimates timestamps
    using syllable-based distribution, and writes an enriched VTT file with
    <timestamp><c>word</c> tags.
    
    Args:
        input_vtt_path: Path to input VTT file
        output_vtt_path: Path to output VTT file (defaults to input_vtt_path if None)
        
    Returns:
        Dictionary with statistics:
            - cues_processed: Total number of cues processed
            - cues_enriched: Number of cues that were enriched with word timestamps
            - cues_skipped: Number of cues that already had word timestamps
            
    Example:
        >>> result = enrich_vtt_with_word_timestamps(
        ...     "input.vtt",
        ...     "output_enriched.vtt"
        ... )
        >>> print(f"Enriched {result['cues_enriched']} cues")
    """
    if output_vtt_path is None:
        output_vtt_path = input_vtt_path
    
    # Read input VTT file
    with open(input_vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Use string-based enrichment
    enriched_content = enrich_vtt_content_with_word_timestamps(content)
    
    # Calculate statistics for backward compatibility
    timestamp_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
    word_timestamp_pattern = re.compile(r'<\d{2}:\d{2}:\d{2}\.\d{3}><c>')
    
    original_blocks = content.strip().split('\n\n')
    enriched_blocks = enriched_content.strip().split('\n\n')
    
    cues_processed = 0
    cues_enriched = 0
    cues_skipped = 0
    
    for orig_block, enr_block in zip(original_blocks, enriched_blocks):
        if timestamp_pattern.search(orig_block):
            cues_processed += 1
            if word_timestamp_pattern.search(orig_block):
                cues_skipped += 1
            elif word_timestamp_pattern.search(enr_block):
                cues_enriched += 1
    
    # Write enriched VTT
    with open(output_vtt_path, 'w', encoding='utf-8') as f:
        f.write(enriched_content)
    
    return {
        "cues_processed": cues_processed,
        "cues_enriched": cues_enriched,
        "cues_skipped": cues_skipped
    }
