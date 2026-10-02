# Editable Hyperframes workflow

Verified locally on 2026-10-02 using installed `hyperframes --version` and command help: Hyperframes `0.8.107`, Node `26.8.1`, Python `3.14.6`; FFmpeg and ffprobe available. This is a recorded compatibility baseline, not a claim to the newest release. No dependencies were installed and no production composition was rendered to create this skill. Official upstream: <https://github.com/heygen-com/hyperframes>. Consult the available official Hyperframes core/CLI skills and the installed command help for changes.

## Reproducible project

Use an exact `hyperframes` dependency (`"0.8.107"` for this baseline) and committed lockfile in the deliverable; package scripts resolve the local binary. Do not silently use an unpinned `npx` that downloads a different version. If dependencies are absent, explain and use an authorized installation path; do not pretend the project is reproducible just because a global executable exists. A newer version can be chosen after recording it and revalidating the project.

Suggested scripts, after the matching dependency is installed:

```json
{
  "scripts": {
    "check": "hyperframes check --json",
    "timeline": "hyperframes timeline --json",
    "preview": "hyperframes preview --background --no-open",
    "render": "hyperframes render --quality delivery --output renders/final.mp4"
  },
  "devDependencies": {"hyperframes": "0.8.107"}
}
```

Ship local licensed fonts and media. Record the actual Node, browser, FFmpeg, and package versions, render command, dimensions, frame rate, and asset hashes. Deterministic seeking does not imply byte-identical encodes across different browsers, GPUs, or codecs.

## Composition invariants

- The standalone composition root sits directly in `<body>`, with `data-composition-id`, `data-width`, `data-height`, `data-duration`, and the intended `data-fps`. Its CSS size is `100%`; canvas dimensions come from the data attributes.
- Timed clips have explicit `data-start`, `data-duration`, and useful track indices. Track indices organize Studio; they do not prevent overlapping timing. Keep captions, audio, presenter, and graphics independently editable.
- Register one paused seekable timeline at `window.__timelines[compositionId]`. Animate inner visual elements, while the framework controls timed clip visibility and media seeking.
- Avoid render-time network access, unseeded randomness, wall clocks, infinite repeat, manual `.play()`, and transforms whose CSS initial values conflict with animation properties.
- Audio elements need unique IDs. Do not put `crossorigin` on media. Avoid timing both a video and its plain ancestor. A clip ending after the root duration will be cut off.
- Templated sub-compositions keep their scripts/styles inside the template, and host/root/timeline IDs agree. Inspect at least one visible midpoint of every mounted scene.

These notes summarize observed authoring contracts; they are not a replacement for the complete installed core skill.

## Verification loop

With the exact local project dependency installed, run through its scripts or local binary:

```bash
./node_modules/.bin/hyperframes lint
./node_modules/.bin/hyperframes timeline --json
./node_modules/.bin/hyperframes check --json --snapshots
./node_modules/.bin/hyperframes snapshot --at 1,5,10 --describe false
./node_modules/.bin/hyperframes preview --background --no-open
```

Choose snapshot times from actual scene midpoints and transitions, not the example times above. `snapshot --describe false` disables optional Gemini image analysis, which otherwise may run automatically when a Gemini key exists. This prevents a local inspection command from unexpectedly becoming an external AI request. The combined `check` already runs lint; do not repeat lint immediately before it without intervening edits. Lint errors can suppress later layout/contrast audits, so a report with zero samples is not a successful visual check.

Verify the preview URL responds, inspect the assembled timeline, and preserve any review decisions. Render when authorized by the current task; keep paid cloud rendering separate from local render permission:

```bash
./node_modules/.bin/hyperframes render --quality delivery --output renders/final.mp4
ffprobe -v error -show_format -show_streams -of json renders/final.mp4
```

Confirm nonempty bytes, duration against root duration, expected dimensions/frame rate, an audio stream when required, and an intelligible full listen. Watch first/last frames and transitions for blank flashes or cut-off narration. Record the render's capture/GPU summary and final SHA-256. File existence, a passing lint, or ffprobe alone does not prove a finished video.

## Reference-repository boundary

Audit exact repository URL, commit, branch, license, and relevant files before reuse. Do not run unreviewed install scripts. Compare branch contents rather than interpreting dates as capabilities. Reading a reference repository does not create an obligation to reuse it. If actual code is reused, include its license and notices; if only ideas are consulted, describe inspiration without claiming derived code. This skill contains no code from `buildwithhanif/hyperframe-pro`.
