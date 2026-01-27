"""Transcription package with pluggable backends."""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from .base import build_segments_json
from .faster_whisper_backend import FasterWhisperBackend
from ..models import TranscribeConfig


@dataclass
class TranscriptionResult:
    """Result metadata from transcription."""

    segments_path: str
    cues_count: int
    backend: str
    model_name: str


def _get_backend(
    backend: str,
    model_name: str,
    device: str,
    compute_type: str,
) -> Any:
    if backend == "faster-whisper":
        return FasterWhisperBackend(
            model_name=model_name,
            device=device,
            compute_type=compute_type,
        )
    raise ValueError(f"Unsupported transcription backend: {backend}")


def transcribe_to_segments_json(
    audio_path: str,
    output_file: str = "segments.json",
    backend: str = "faster-whisper",
    model_name: str = "base",
    language: str = "en",
    device: str = "auto",
    compute_type: str = "default",
    max_segment_duration: float = 2.0,
    word_timestamps: bool = True,
    **backend_kwargs: Any,
) -> Dict[str, Any]:
    """
    Transcribe audio and write segments.json output.

    Args:
        audio_path: Path to input audio file.
        output_file: Path to write segments.json.
        backend: Transcription backend name (default: faster-whisper).
        model_name: Model name or path.
        language: Language code (e.g., "en").
        device: Device for backend model (e.g., "cpu", "cuda", "auto").
        compute_type: Backend compute type (backend-specific).
        max_segment_duration: Max duration per cue in seconds.
        word_timestamps: Request word-level timestamps from backend.
        **backend_kwargs: Extra kwargs passed to backend transcribe.

    Returns:
        Dictionary with result metadata (segments_path, cues_count, backend, model_name).
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    backend_impl = _get_backend(backend, model_name, device, compute_type)

    segments_iter, _info = backend_impl.transcribe(
        audio_path,
        language=language,
        word_timestamps=word_timestamps,
        **backend_kwargs,
    )

    segments_json = build_segments_json(
        segments_iter,
        language=language,
        max_segment_duration=max_segment_duration,
    )

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(segments_json, f, indent=2, ensure_ascii=False)

    return {
        "segments_path": output_file,
        "cues_count": len(segments_json.get("cues", [])),
        "backend": backend,
        "model_name": model_name,
    }


def transcribe_from_config(config: TranscribeConfig) -> Dict[str, Any]:
    """Transcribe audio using a TranscribeConfig object."""
    return transcribe_to_segments_json(
        audio_path=config.audio_path,
        output_file=config.output_file,
        backend=config.backend,
        model_name=config.model_name,
        language=config.language,
        device=config.device,
        compute_type=config.compute_type,
        max_segment_duration=config.max_segment_duration,
        word_timestamps=config.word_timestamps,
        **config.backend_kwargs,
    )
