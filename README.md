# Reference to Personal Video

An original Codex skill for adapting a creator's video reference into a fresh, editable Hyperframes production with a user-approved likeness.

The workflow covers dated reference evidence, identity confirmation, exact paid-generation plans, deterministic editing, and verified delivery. Its preflight tools check recorded evidence and clean release payloads. Optional narration adapters can submit one approved request to ElevenLabs or AI33; offline planning and existing-audio import make no provider calls. The tools do not authenticate human consent or publish repositories.

## Install and use

Copy `skills/reference-to-personal-video` into your agent's supported skills directory. For Codex, a typical user installation is:

```bash
git clone https://github.com/adrianleoh1992/adrian-video-skill.git
cd adrian-video-skill
mkdir -p ~/.codex/skills
cp -R skills/reference-to-personal-video ~/.codex/skills/
```

Inspect any existing folder with the same name before replacing it. You can also point the agent directly at [SKILL.md](skills/reference-to-personal-video/SKILL.md) without installing it.

Example request:

> Use $reference-to-personal-video to adapt this reference into an original Indonesian video with my approved face reference. Deliver the editable Hyperframes project and MP4. Record the sources and confirm the exact cost plan before paid generation.

Start with the [usage guide](skills/reference-to-personal-video/references/usage-guide.md). The included example manifest intentionally describes an incomplete, unapproved intake; it is not permission to generate.

## Verify

The helpers and tests require Python 3.10+ and use only its standard library:

```bash
cd skills/reference-to-personal-video
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 scripts/validate_manifest.py assets/production-manifest.example.json --stage audit
```

See [manifest validation](skills/reference-to-personal-video/references/manifest-contract.md), [release checks](skills/reference-to-personal-video/references/release-contract.md), and [behavior evaluations](skills/reference-to-personal-video/references/evaluation.md). A passing preflight does not prove accurate evidence, copyright ownership, visual identity quality, or absence of every secret.

## Optional narration

| Capability | Current support |
| --- | --- |
| Local narration/audio already produced | Immutable `import-audio` fallback; no provider, key, or upload |
| ElevenLabs | Runtime model discovery, premade voices only, MP3 plus character/word alignment |
| AI33.pro / OpenSpeaker | Preset allowlist, documented v3 multipart TTS, bounded task polling, provider audio and raw SRT/JSON sidecars |
| Captions | Separate SRT/VTT export from actual normalized word alignment |
| Voice cloning | Excluded |

The adapters were tested with synthetic responses, **not paid live calls**. They require a current evidenced maximum-cost quote, request-bound approval, and an explicit `--execute` flag. Provider prices are not hardcoded. AI33's model/format selection differs from ElevenLabs; undocumented controls are not sent. See the [narration guide](skills/reference-to-personal-video/references/narration.md) for schemas, exact commands, and limitations.

Keep narration requests, approvals, API keys, and outputs in a private production directory outside this Git repository. Example records in the package are synthetic. Quickstart with audio you already own:

```bash
python3 skills/reference-to-personal-video/scripts/narration.py import-audio /absolute/private-production/narration.wav --text-file /absolute/private-production/narration.txt --output-dir /absolute/private-production/voice-artifacts
```

## Worked example: Pegang Kendali

The workflow was used for **Pegang Kendali**, a finished 99-second vertical video at 1080 × 1920 and 30 fps, with nine scenes, 35 caption cues, and four Google Flow shots. The editable source project and MP4 were delivered privately. Personal likeness assets, production files, and delivery identifiers are intentionally omitted from this public repository; the reusable workflow and synthetic tests remain available here.

## Production requirements

The documented compatibility baseline is Hyperframes `0.8.107`; actual video production needs a separately installed, exactly pinned Hyperframes project plus Node, FFmpeg, local assets, and any authorized generation provider. This repository contains no provider login state, personal photos, creator footage, voices, or generated likeness assets. Public availability of a photo does not by itself grant permission to use it.

Version: `1.1.0`. Released under the [MIT License](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for reference context and the boundary between consulted material and reused code.
