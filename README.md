# Voice Lab

Generic local voice-generation lab for GPT-SoVITS.

The user-facing workflow is intentionally simple:

1. Upload/select a reference voice file.
2. Choose an emotion label.
3. Enter the line to speak.
4. Generate 1-5 candidates.
5. Listen and keep the best take.

Notes:

- GPT-SoVITS requires reference clips in the 3-10 second range. The UI can cut a clip from a longer audio file with `start_seconds` and `duration_seconds`.
- Emotion selection is used for organization and defaults. The generated emotion mostly comes from the reference voice tone, so choose a reference clip that already matches the desired emotion.
- Generated files are staged in `generated/`; approved/exported files can be copied later into a game project.

## Run

```bash
cd /home/jisub-lee/workspace/voice-lab
uv run --extra dev python app.py
```

Then open the printed local URL, usually:

```text
http://127.0.0.1:7860
```

## Current GPT-SoVITS wiring

GPT-SoVITS is fully owned by this project now. No symlinks to the old VN demo project are used.

- `references/GPT-SoVITS/` — moved GPT-SoVITS repository and model/config files
- `.venv-gpt-sovits/` — moved GPT-SoVITS Python virtualenv

The old locations under `/home/jisub-lee/workspace/vn-demo/` are intentionally removed so `voice-lab` is self-contained.
