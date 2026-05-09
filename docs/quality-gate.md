# Voice quality gate

Voice Lab separates generation from quality verification. Generated audio is never assumed to be production-ready just because GPT-SoVITS returned a file.

## Modes

`pick-best` supports two quality modes.

```text
balanced  Rank candidates and return the best available take.
strict    Rank candidates, but mark the winner as failing if residual mechanical risk is too high.
```

Use `balanced` for exploration and debugging. Use `strict` before presenting a candidate as production/listening-ready. In balanced mode, `quality_pass` only means no strict failure was evaluated; production automation should require `quality_mode == "strict"` and `quality_pass == true`.

## Recommended production command

```bash
uv run voice-lab pick-best \
  --input-dir generated/default/ch01_001 \
  --anchor /path/to/clean_anchor.ogg \
  --target-text "생성할 대사" \
  --output-dir exports/ch01_001_best \
  --asr-model small \
  --asr-language ko \
  --asr-device cpu \
  --asr-compute-type int8 \
  --feedback-labels /path/to/voice_gate_feedback.yaml \
  --quality-mode strict
```

## Output contract

`best_selection.json` contains:

```json
{
  "ok": true,
  "quality_mode": "strict",
  "quality_pass": true,
  "best": {
    "path": ".../seed_1000.ogg",
    "score": 100.0,
    "quality_pass": true,
    "flags": ["auto gate ok"]
  }
}
```

Production automation should treat `quality_pass: false` as a hard stop. A strict-fail winner means “best among current candidates”, not “usable”. Generate more candidates, simplify the line, change punctuation, or try a better reference clip.

## Signals used by strict mode

Strict mode combines several cheap local checks:

- volume, peak and clipping
- silence/dropout ratio
- voiced-frame ratio
- low-band mud against a clean anchor
- spectral flatness/noisy texture
- pitch median and low-tail collapse against the anchor
- Praat/Parselmouth HNR, jitter, and shimmer
- optional faster-whisper ASR character error rate
- optional human feedback penalties from YAML labels

These are not a formal MOS model. They are conservative guardrails designed to reject obvious mechanical/muddy/unstable takes before a human listens.

## Human feedback labels

Feedback YAML is project-owned data. Voice Lab only reads it.

```yaml
labels:
  - path: /absolute/or/suffix/path/to/seed_1000.ogg
    verdict: reject
    penalty: 90
    reasons:
      - mechanical_texture
      - muddy_low_pitch
```

Use labels to make future ranking remember subjective failures. Keep generated audio out of git; keep small feedback YAML files in the game/project repo.
