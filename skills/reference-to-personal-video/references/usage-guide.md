# Usage guide

This package is an original workflow, two Python standard-library preflight tools, and behavior evaluations. It includes no personal photos, provider login state, paid generator, or copied creator assets. Its helpers do not install dependencies, publish files, or spend credits.

## Invoke

Place this folder in a skill directory supported by the agent, or explicitly point the agent at `SKILL.md`. A typical request is:

> Use $reference-to-personal-video. Adapt this Instagram reel's pacing and explanatory format into a fresh Indonesian video for my account. Use only a face reference I confirm. Deliver the Hyperframes project, MP4, and source manifest. Ask before paid generation and before creating a GitHub repository.

Preserve the actual user's approval choices. The example is not a requirement to ask again when the current conversation already grants the relevant action.

## Working layout

Keep a private production directory separate from the reusable skill:

```text
production/
  BRIEF.md
  STORYBOARD.md
  private/
    production-manifest.json
    generation-ledger.json
    face-references/
  project/
    package.json
    package-lock.json
    hyperframes.json
    index.html
    compositions/
    assets/
  evidence/
    reference-audit.md
    checks.json
    media-probe.json
    delivery-sha256.txt
  deliverables/
    final.mp4
    editable-project.zip
```

This layout is a suggestion, not a script-created scaffold. `.gitignore` does not protect files already tracked. Raw face references stay private even when their origin was a public profile. Include a generated likeness in a project delivered to the user only within their authorized distribution scope; GitHub distribution needs its own recorded scope.

## Intake and audit

Capture reference URL, account, intended lesson, language, duration/aspect ratio, audience, face/voice preference, requested deliverables, and spending/release constraints. Reuse details already supplied. Do not force ten samples when the user requested a different count.

For each video actually inspected, record timestamped observations: hook, shot duration, text placement, graphic transitions, voice cadence, sound accents, and ending. Separate observation from inference. Record publication date provenance, including timezone or date-only uncertainty. A date-only source cannot support strict order for multiple same-day uploads. Describe licensed reusable material separately from stylistic inspiration. If a source cannot be played, mark it unavailable or partial and continue with supported observations.

Write fresh narration and an adaptation rationale. Reference-inspired timing is not permission to copy a complete script, watermark, face, voice, music, or third-party footage. Verify factual claims independently when they materially affect the viewer's actions.

## Run local preflight

Python 3.10+ is sufficient for the package's scripts and tests:

```bash
python3 scripts/validate_manifest.py /path/to/production-manifest.json --stage audit
python3 scripts/validate_manifest.py /path/to/production-manifest.json --plan-hash
python3 scripts/validate_manifest.py /path/to/production-manifest.json --stage generate
python3 -m unittest discover -s tests -v
```

Run commands from this skill folder or use absolute script paths. The example manifest intentionally passes audit as an incomplete intake and fails generation until real evidence and authorization are recorded. `--plan-hash` only computes a fingerprint; it grants no approval.

Before packaging, create a separate, explicitly selected staging directory with only the intended files. Record every staged file in a release manifest outside that directory, then run the release checker described in `release-contract.md`. Review the scan limitations and human checklist before publishing.

## Resume and handoff

On resume, read the latest brief, approvals, generation ledger, exact toolchain pin, and local file hashes. Do not regenerate an already delivered job merely because a prior tool call timed out. Record what finished, what was blocked, and where the bytes are located. The handoff must identify the final MP4 and editable project, how to preview/render, what assets may be redistributed, and any inaccessible evidence. Do not call a placeholder or silent draft a finished narrated video.
