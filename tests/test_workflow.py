from pathlib import Path

from voice_lab.workflow import VoiceRequest, render_metadata


def test_render_metadata_contains_generic_voice_lab_fields():
    request = VoiceRequest(
        character="default",
        emotion="soft",
        line_id="line 001",
        text="hello",
        text_lang="en",
        prompt_text="reference hello",
        prompt_lang="en",
        source_audio=Path("/tmp/source.mp3"),
        ref_audio=Path("/tmp/ref.wav"),
        seed=7,
    )
    data = render_metadata(request, Path("/tmp/out.wav"), Path("/tmp/out.ogg"))
    assert data["character"] == "default"
    assert data["emotion"] == "soft"
    assert data["line_id"] == "line_001"
    assert data["text"] == "hello"
    assert data["seed"] == 7
    assert data["outputs"]["wav"] == "/tmp/out.wav"
