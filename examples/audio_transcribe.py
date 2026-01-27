"""
Audio transcription example using faster-whisper backend.

Produces segments.json only (no VTT output).
"""

from vttkit import transcribe_to_segments_json


def main() -> None:
    audio_path = "local/audio.wav"  # Update to your audio file
    output_path = "local/audio_segments.json"

    result = transcribe_to_segments_json(
        audio_path=audio_path,
        output_file=output_path,
        model_name="base",
        language="en",
        max_segment_duration=2.0,
    )

    print(f"Segments saved to: {result['segments_path']}")
    print(f"Cues: {result['cues_count']}")


if __name__ == "__main__":
    main()
