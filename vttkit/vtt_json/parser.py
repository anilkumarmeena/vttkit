"""
VTT parser for segments.json generation.

Orchestrates the complete VTT parsing pipeline from VTT file to segments.json format.
Outputs structured data with word-level timestamps.
"""

import json
import logging
from typing import Dict, Any

from .converter import parse_vtt_content, DEFAULT_MAX_CUE_DURATION

logger = logging.getLogger(__name__)


class VTTParser:
    """
    Parser for converting VTT files to segments.json format.
    
    Handles the complete parsing pipeline including:
    - VTT content parsing with word-level timestamps
    - Output to segments.json format
    """
    
    def parse_to_segments(
        self,
        vtt_file: str,
        output_file: str = "segments.json",
        max_cue_duration: float = DEFAULT_MAX_CUE_DURATION,
        clean_content: bool = True,
        rebuild_cues_from_words: bool = True
    ) -> Dict[str, Any]:
        """
        Parse VTT file and generate segments.json with complete transcript.
        
        Args:
            vtt_file: Path to VTT file
            output_file: Output filename (default: "segments.json")
            max_cue_duration: Maximum duration in seconds for each cue
            clean_content: Whether to clean VTT content before parsing (default: True)
            rebuild_cues_from_words: Rebuild cues from word-level data (default: True)
        
        Returns:
            Dictionary containing:
                - segments_path: Path to saved segments.json file
                - cues_count: Number of cues extracted
                
        Raises:
            FileNotFoundError: If VTT file does not exist
            ValueError: If VTT file is empty or invalid format
                
        Example:
            >>> parser = VTTParser()
            >>> result = parser.parse_to_segments(
            ...     vtt_file="stream.vtt",
            ...     output_file="segments.json"
            ... )
            >>> print(f"Parsed {result['cues_count']} cues")
        """
        logger.info(f"Parsing VTT file: {vtt_file}")
        
        # Load VTT content from file
        with open(vtt_file, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        
        # Parse VTT content using core parser
        parsed_data = parse_vtt_content(
            vtt_content,
            max_cue_duration=max_cue_duration,
            clean_content=clean_content,
            rebuild_cues_from_words=rebuild_cues_from_words
        )
        
        header = parsed_data['header']
        cues = parsed_data['cues']
        
        # Format as segments.json structure
        segments_data = {
            "header": header,
            "cues": cues
        }
        
        # Save segments.json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(segments_data, f, indent=2, ensure_ascii=False)

        logger.info(f"VTT parsing complete: {len(cues)} cues extracted")
        
        # Return result
        return {
            "segments_path": output_file,
            "cues_count": len(cues),
        }
    
    def parse_content_to_dict(
        self,
        vtt_content: str,
        max_cue_duration: float = DEFAULT_MAX_CUE_DURATION,
        clean_content: bool = True,
        rebuild_cues_from_words: bool = True
    ) -> Dict[str, Any]:
        """
        Parse VTT content string directly to dictionary (no file I/O).
        
        Args:
            vtt_content: VTT content as string
            max_cue_duration: Maximum duration in seconds for each cue
            clean_content: Whether to clean VTT content before parsing
            rebuild_cues_from_words: Rebuild cues from word-level data
            
        Returns:
            Dictionary with 'header' and 'cues' keys
            
        Raises:
            ValueError: If VTT content is empty or invalid format
        """
        # Parse VTT content
        parsed_data = parse_vtt_content(
            vtt_content,
            max_cue_duration=max_cue_duration,
            clean_content=clean_content,
            rebuild_cues_from_words=rebuild_cues_from_words
        )
        
        return {
            "header": parsed_data['header'],
            "cues": parsed_data['cues']
        }
