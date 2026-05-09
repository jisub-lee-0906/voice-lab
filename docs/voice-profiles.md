# Voice profiles

Voice Lab stores reference clips by voice profile and emotion.

```text
refs/<voice_profile>/<emotion>/audio_ref.wav
```

The built-in local reference used during the VN prototype is not a generic default voice. It should be treated as a tsundere-style character reference:

```text
refs/tsundere/tsun/audio_ref.wav
voice_name: tsundere
emotion: 츤츤 / tsun
```

Avoid keeping production references under vague paths such as `refs/default/neutral/audio_ref.wav`. That makes later multi-voice projects ambiguous.

When adding more voices:

```text
refs/calm_heroine/soft/audio_ref.wav
refs/cool_senior/serious/audio_ref.wav
refs/comic_friend/happy/audio_ref.wav
```

Rules:

- Reference clips must be 3-10 seconds.
- Keep raw uploaded audio and generated references out of git.
- Use Korean profile names only if they are stable and filesystem-safe; otherwise prefer lowercase ASCII IDs.
- `voice_name` should match the profile directory.
- `emotion` should describe the reference clip's actual tone, not the desired output fantasy.
- `prompt_text` is only the actual transcript of the reference clip. Leave it blank when unknown.
