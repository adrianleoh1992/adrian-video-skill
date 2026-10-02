# Reference to Personal Video

An original Codex skill for adapting a creator's video reference into a fresh, editable Hyperframes production with a user-approved likeness.

The workflow covers dated reference evidence, identity confirmation, exact paid-generation plans, deterministic editing, and verified delivery. Its Python preflight tools check recorded consent/budget fields and a clean release payload. They do not generate media, spend credits, authenticate consent, or publish repositories.

## Install and use

Copy `skills/reference-to-personal-video` into your agent's supported skills directory. For Codex, a typical user installation is:

```bash
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

## Production requirements

The documented compatibility baseline is Hyperframes `0.8.107`; actual video production needs a separately installed, exactly pinned Hyperframes project plus Node, FFmpeg, local assets, and any authorized generation provider. This repository contains no provider login state, personal photos, creator footage, voices, or generated likeness assets. Public availability of a photo does not by itself grant permission to use it.

Version: `1.0.0`. Released under the [MIT License](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for reference context and the boundary between consulted material and reused code.
