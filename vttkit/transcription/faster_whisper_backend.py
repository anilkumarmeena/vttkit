"""Faster-Whisper backend adapter."""

from typing import Any, Iterable, Tuple

from .base import TranscriptionBackend


class FasterWhisperBackend(TranscriptionBackend):
    """Backend adapter for faster-whisper."""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        super().__init__(name="faster-whisper")
        from faster_whisper import WhisperModel

        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str, **kwargs: Any) -> Tuple[Iterable[Any], Any]:
        segments, info = self.model.transcribe(audio_path, **kwargs)
        return segments, info
