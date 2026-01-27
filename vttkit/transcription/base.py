"""
Shared transcription utilities and backend interface.

Defines common helpers for converting backend segments into the VTTKit
segments.json structure and a minimal backend protocol.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..utils import seconds_to_timestamp


@dataclass
class TranscriptionBackend:
    """Base backend interface for transcription engines."""
    name: str

    def transcribe(self, audio_path: str, **kwargs: Any) -> Tuple[Iterable[Any], Any]:
        raise NotImplementedError


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _format_timestamp(seconds: float) -> str:
    return seconds_to_timestamp(seconds)


def _normalize_segments(raw_segments: Iterable[Any]) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    for segment in raw_segments:
        start = _get_attr(segment, "start", 0.0)
        end = _get_attr(segment, "end", 0.0)
        text = (_get_attr(segment, "text", "") or "").strip()
        words_raw = _get_attr(segment, "words", None)
        words: List[Dict[str, Any]] = []
        if words_raw:
            for word in words_raw:
                word_text = (_get_attr(word, "word", "") or "").strip()
                word_start = _get_attr(word, "start", None)
                word_end = _get_attr(word, "end", None)
                if word_text and word_start is not None:
                    words.append({
                        "word": word_text,
                        "start": float(word_start),
                        "end": float(word_end) if word_end is not None else None,
                    })
        segments.append({
            "start": float(start),
            "end": float(end),
            "text": text,
            "words": words,
        })
    return segments


def _group_words_by_start(words: List[Dict[str, Any]], precision: int = 3) -> List[List[Dict[str, Any]]]:
    if not words:
        return []
    words_sorted = sorted(words, key=lambda w: w["start"])
    grouped: List[List[Dict[str, Any]]] = []
    current_group: List[Dict[str, Any]] = []
    current_key = None

    for word in words_sorted:
        key = round(word["start"], precision)
        if current_key is None or key != current_key:
            if current_group:
                grouped.append(current_group)
            current_group = [word]
            current_key = key
        else:
            current_group.append(word)

    if current_group:
        grouped.append(current_group)

    return grouped


def _estimate_group_end(group: List[Dict[str, Any]], next_start: Optional[float]) -> float:
    last_word = group[-1]
    last_end = last_word.get("end")
    if last_end is not None:
        return float(last_end)
    if next_start is not None:
        return float(next_start)
    return float(last_word["start"]) + 0.3


def _split_long_segments(segments: List[Dict[str, Any]], max_duration: float) -> List[Dict[str, Any]]:
    if max_duration <= 0:
        return segments

    new_segments: List[Dict[str, Any]] = []

    for segment in segments:
        start_time = segment["start"]
        end_time = segment["end"]
        duration = end_time - start_time
        words = segment.get("words", [])

        if duration <= max_duration:
            new_segments.append(segment)
            continue

        if not words:
            num_chunks = int(duration / max_duration) + (1 if duration % max_duration > 0 else 0)
            chunk_duration = duration / num_chunks if num_chunks else duration
            for i in range(num_chunks):
                chunk_start = start_time + (i * chunk_duration)
                chunk_end = min(start_time + ((i + 1) * chunk_duration), end_time)
                new_segments.append({
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": segment["text"],
                    "words": [],
                })
            continue

        word_groups = _group_words_by_start(words)
        current_chunk_words: List[Dict[str, Any]] = []
        current_chunk_start = start_time
        current_chunk_text_parts: List[str] = []
        last_word_end = start_time

        for idx, group in enumerate(word_groups):
            next_start = None
            if idx < len(word_groups) - 1:
                next_start = word_groups[idx + 1][0]["start"]

            group_start = group[0]["start"]
            group_end = _estimate_group_end(group, next_start)

            potential_duration = group_end - current_chunk_start
            if potential_duration > max_duration and current_chunk_words:
                chunk_text = " ".join(w["word"] for w in current_chunk_words)
                new_segments.append({
                    "start": current_chunk_start,
                    "end": last_word_end,
                    "text": chunk_text,
                    "words": current_chunk_words,
                })
                current_chunk_words = []
                current_chunk_text_parts = []
                current_chunk_start = group_start

            current_chunk_words.extend(group)
            current_chunk_text_parts.extend(w["word"] for w in group)
            last_word_end = group_end

        if current_chunk_words:
            final_end = max(end_time, last_word_end)
            chunk_text = " ".join(current_chunk_text_parts)
            new_segments.append({
                "start": current_chunk_start,
                "end": final_end,
                "text": chunk_text,
                "words": current_chunk_words,
            })

    return new_segments


def _segments_to_cues(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cues: List[Dict[str, Any]] = []
    for segment in segments:
        start_time = _format_timestamp(segment["start"])
        end_time = _format_timestamp(segment["end"])
        text = (segment.get("text") or "").strip()
        words_data = []
        for word in segment.get("words", []) or []:
            word_text = (word.get("word") or "").strip()
            word_start = word.get("start")
            if word_text and word_start is not None:
                words_data.append({
                    "word": word_text,
                    "time": _format_timestamp(float(word_start)),
                })
        cues.append({
            "start_time": start_time,
            "end_time": end_time,
            "text": text,
            "words": words_data,
        })
    return cues


def build_segments_json(
    segments: Iterable[Any],
    language: str,
    max_segment_duration: float
) -> Dict[str, Any]:
    normalized = _normalize_segments(segments)
    processed = _split_long_segments(normalized, max_segment_duration)
    cues = _segments_to_cues(processed)
    header = {
        "kind": "captions",
        "language": language,
    }
    return {
        "header": header,
        "cues": cues,
    }
