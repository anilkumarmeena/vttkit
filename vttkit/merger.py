"""
VTT merging and deduplication utilities for VTTKit.

Provides functionality to merge multiple VTT files, particularly useful for
live streams where VTT content is downloaded incrementally and needs to be
combined without duplication.
"""

import logging
import os
from typing import List, Dict, Set

logger = logging.getLogger(__name__)


def parse_vtt_cues(vtt_content: str) -> List[Dict[str, str]]:
    """
    Parse VTT content and extract individual cues.
    
    Args:
        vtt_content: VTT file content as string
        
    Returns:
        List of cue dictionaries with 'timestamp', 'text', and 'raw' fields
        
    Example:
        >>> content = "WEBVTT\\n\\n00:00:01.000 --> 00:00:03.000\\nHello world"
        >>> cues = parse_vtt_cues(content)
        >>> print(len(cues))
        1
    """
    cues = []
    lines = vtt_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip WEBVTT header and empty lines
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or not line:
            i += 1
            continue
        
        # Check if line contains timestamp (cue timing)
        if '-->' in line:
            timestamp_line = line
            text_lines = []
            raw_lines = [timestamp_line]
            
            # Collect all text lines for this cue
            i += 1
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                raw_lines.append(lines[i].strip())
                i += 1
            
            if text_lines:
                # Preserve multi-line format (e.g., word timestamps + plain text)
                # Use newline to join lines, maintaining dual format
                cues.append({
                    'timestamp': timestamp_line,
                    'text': '\n'.join(text_lines),  # Changed from ' '.join to '\n'.join
                    'raw': '\n'.join(raw_lines)
                })
        else:
            # Skip cue numbers or other metadata
            i += 1
    
    return cues


def deduplicate_cues(existing_cues: List[Dict[str, str]], new_cues: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Deduplicate cues based on timestamp and text content.
    
    Args:
        existing_cues: List of existing cues
        new_cues: List of new cues to add
        
    Returns:
        List of unique new cues that don't exist in existing_cues
        
    Example:
        >>> existing = [{'timestamp': '00:00:01.000 --> 00:00:02.000', 'text': 'Hello'}]
        >>> new = [{'timestamp': '00:00:01.000 --> 00:00:02.000', 'text': 'Hello'},
        ...        {'timestamp': '00:00:03.000 --> 00:00:04.000', 'text': 'World'}]
        >>> unique = deduplicate_cues(existing, new)
        >>> len(unique)
        1
    """
    # Create a set of existing cue signatures (timestamp + text)
    existing_signatures: Set[str] = set()
    for cue in existing_cues:
        signature = f"{cue['timestamp']}||{cue['text']}"
        existing_signatures.add(signature)
    
    # Filter out duplicates from new cues
    unique_new_cues = []
    for cue in new_cues:
        signature = f"{cue['timestamp']}||{cue['text']}"
        if signature not in existing_signatures:
            unique_new_cues.append(cue)
            existing_signatures.add(signature)  # Add to set to avoid duplicates within new_cues
    
    return unique_new_cues


def merge_vtt_content(existing_vtt_path: str, new_vtt_content: str, new_vtt_offset_seconds: float = 0.0) -> str:
    """
    Merge new VTT content with existing VTT file, deduplicating cues.
    
    Maintains proper VTT format with single WEBVTT header and sequential cue numbering.
    
    NOTE: In the optimized pipeline, timestamp corrections should be applied to new_vtt_content
    BEFORE calling this function. The new_vtt_offset_seconds parameter is kept for backward
    compatibility but should typically be 0.0 in the new flow.
    
    Args:
        existing_vtt_path: Path to existing VTT file
        new_vtt_content: New VTT content to append (should already have corrected timestamps)
        new_vtt_offset_seconds: Optional timestamp offset to apply (default: 0.0, use only for legacy support)
        
    Returns:
        Merged VTT content as string
        
    Example:
        >>> # Assuming existing.vtt has some content
        >>> new_content = "WEBVTT\\n\\n00:00:05.000 --> 00:00:07.000\\nNew text"
        >>> merged = merge_vtt_content("existing.vtt", new_content)
        >>> "WEBVTT" in merged
        True
    """
    # Apply timestamp offset to new content if specified (legacy support)
    if new_vtt_offset_seconds > 0:
        from .corrector import apply_offset_to_vtt_content
        logger.info(f"Applying timestamp offset to new VTT content before merge: {new_vtt_offset_seconds:.3f}s")
        new_vtt_content = apply_offset_to_vtt_content(new_vtt_content, new_vtt_offset_seconds)
    
    # Read existing content if file exists
    existing_cues = []
    if os.path.exists(existing_vtt_path):
        try:
            with open(existing_vtt_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
                existing_cues = parse_vtt_cues(existing_content)
                logger.info(f"Found {len(existing_cues)} existing cues in VTT file")
        except Exception as e:
            logger.warning(f"Failed to read existing VTT file: {str(e)}, will create new file")
    
    # Parse new cues (now with corrected timestamps if offset was applied)
    new_cues = parse_vtt_cues(new_vtt_content)
    logger.info(f"Parsed {len(new_cues)} new cues from download")
    
    # Deduplicate
    unique_new_cues = deduplicate_cues(existing_cues, new_cues)
    logger.info(f"Found {len(unique_new_cues)} unique new cues to append")
    
    # Combine all cues
    all_cues = existing_cues + unique_new_cues
    
    # Build merged VTT content using format function (preserves multi-line content)
    merged_content = format_vtt_from_cues(all_cues)
    
    logger.info(f"Merged VTT file now contains {len(all_cues)} total cues")
    return merged_content


def format_vtt_from_cues(cues: List[Dict[str, str]]) -> str:
    """
    Format a list of cues into valid VTT content.
    
    Preserves multi-line cue content (e.g., word timestamps + plain text).
    
    Args:
        cues: List of cue dictionaries
        
    Returns:
        Formatted VTT content as string
        
    Example:
        >>> cues = [{'timestamp': '00:00:01.000 --> 00:00:02.000', 'text': 'Hello'}]
        >>> vtt = format_vtt_from_cues(cues)
        >>> vtt.startswith('WEBVTT')
        True
    """
    content = "WEBVTT\n\n"
    
    for idx, cue in enumerate(cues, start=1):
        content += f"{idx}\n"
        content += f"{cue['timestamp']}\n"
        # Preserve multi-line text (word timestamps + plain text)
        content += f"{cue['text']}\n\n"
    
    return content


class VTTMerger:
    """
    Class for merging VTT files with deduplication.
    
    Useful for live streams where VTT content is downloaded incrementally
    and needs to be combined into a single file.
    """
    
    def __init__(self):
        """Initialize VTT merger."""
        self.cues: List[Dict[str, str]] = []
    
    def add_from_file(self, vtt_path: str) -> int:
        """
        Add cues from a VTT file.
        
        Args:
            vtt_path: Path to VTT file
            
        Returns:
            Number of unique cues added
        """
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_cues = parse_vtt_cues(content)
            unique_cues = deduplicate_cues(self.cues, new_cues)
            self.cues.extend(unique_cues)
            
            logger.info(f"Added {len(unique_cues)} unique cues from {vtt_path}")
            return len(unique_cues)
            
        except Exception as e:
            logger.error(f"Failed to add cues from {vtt_path}: {str(e)}")
            raise
    
    def add_from_content(self, vtt_content: str) -> int:
        """
        Add cues from VTT content string.
        
        Args:
            vtt_content: VTT content as string
            
        Returns:
            Number of unique cues added
        """
        new_cues = parse_vtt_cues(vtt_content)
        unique_cues = deduplicate_cues(self.cues, new_cues)
        self.cues.extend(unique_cues)
        
        logger.info(f"Added {len(unique_cues)} unique cues from content")
        return len(unique_cues)
    
    def get_merged_content(self) -> str:
        """
        Get the merged VTT content.
        
        Returns:
            Formatted VTT content with all merged cues
        """
        return format_vtt_from_cues(self.cues)
    
    def save(self, output_path: str) -> None:
        """
        Save merged VTT content to file.
        
        Args:
            output_path: Path to save the merged VTT file
        """
        content = self.get_merged_content()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved merged VTT with {len(self.cues)} cues to {output_path}")
    
    def clear(self) -> None:
        """Clear all stored cues."""
        self.cues = []
    
    def get_cue_count(self) -> int:
        """Get the number of cues currently stored."""
        return len(self.cues)
