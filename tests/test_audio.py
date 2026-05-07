from pathlib import Path

from voice_lab.audio import build_clip_path, ffmpeg_cut_command, ffmpeg_ogg_command


def test_build_clip_path_uses_character_emotion_and_source_stem():
    path = build_clip_path(Path("/tmp/root"), "Hero A", "기쁨", Path("my voice.mp3"))
    assert path == Path("/tmp/root/refs/hero_a/happy/my_voice_ref.wav")


def test_ffmpeg_cut_command_outputs_mono_32k_wav():
    command = ffmpeg_cut_command(Path("in.mp3"), Path("out.wav"), 87.0, 9.5)
    assert command[:2] == ["ffmpeg", "-y"]
    assert "-ss" in command and "87.0" in command
    assert "-t" in command and "9.5" in command
    assert command[-4:] == ["-ac", "1", "-ar", "32000", "out.wav"][-4:]


def test_ffmpeg_ogg_command_uses_vorbis_quality():
    command = ffmpeg_ogg_command(Path("in.wav"), Path("out.ogg"))
    assert command == ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", "in.wav", "-c:a", "libvorbis", "-q:a", "5", "out.ogg"]
