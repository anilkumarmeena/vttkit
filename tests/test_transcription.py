from vttkit.transcription.base import _split_long_segments, build_segments_json


def test_split_long_segments_without_words():
    segments = [{
        "start": 0.0,
        "end": 5.0,
        "text": "hello",
        "words": [],
    }]
    result = _split_long_segments(segments, max_duration=2.0)
    assert len(result) == 3
    assert abs(result[-1]["end"] - 5.0) < 1e-6


def test_split_long_segments_with_words():
    words = [
        {"word": "one", "start": 0.0, "end": 0.4},
        {"word": "two", "start": 0.9, "end": 1.3},
        {"word": "three", "start": 1.8, "end": 2.2},
        {"word": "four", "start": 2.7, "end": 3.1},
        {"word": "five", "start": 3.6, "end": 4.0},
    ]
    segments = [{
        "start": 0.0,
        "end": 4.0,
        "text": "one two three four five",
        "words": words,
    }]
    result = _split_long_segments(segments, max_duration=2.0)
    assert len(result) >= 2
    assert abs(result[-1]["end"] - 4.0) < 1e-6


def test_build_segments_json_schema():
    segments = [{
        "start": 0.0,
        "end": 1.0,
        "text": "hello world",
        "words": [
            {"word": "hello", "start": 0.0, "end": 0.4},
            {"word": "world", "start": 0.6, "end": 1.0},
        ],
    }]
    data = build_segments_json(segments, language="en", max_segment_duration=2.0)
    assert "header" in data
    assert data["header"]["language"] == "en"
    assert "cues" in data
    assert len(data["cues"]) == 1
    cue = data["cues"][0]
    assert set(cue.keys()) == {"start_time", "end_time", "text", "words"}
    assert cue["text"] == "hello world"
    assert len(cue["words"]) == 2
