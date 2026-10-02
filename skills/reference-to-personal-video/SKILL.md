---
name: reference-to-personal-video
description: Adapt a creator's video reference into an original, editable Hyperframes production featuring a user-approved likeness. Use for reference-led personal video recreation, source and consent tracking, generation planning, and reproducible delivery; not for copying another creator's footage or voice without permission.
metadata:
  version: "1.1.1"
---

# Reference to personal video

For a production request, deliver the requested editable project, rendered MP4, and reproducible handoff. For a planning-only request, stop at the requested planning artifacts. Preserve the user's subject, language, format, and authorized scope. An inaccessible reference or unresolved face does not justify inventing what was observed.

## Establish the evidence

Read the existing brief, storyboard, source manifest, and repository instructions before creating replacements. Use [the usage guide](references/usage-guide.md) for intake and the working file layout. Record evidence using [the manifest contract](references/manifest-contract.md); start from [the unapproved example](assets/production-manifest.example.json).

Audit actual video content and publication dates. Record canonical permalinks, timecoded observations, date provenance, retrieval time, and what could not be inspected. Profile grid position, pinned posts, search snippets, and access to an avatar do not establish the latest ten videos. Deduplicate by permalink, sort verified publication timestamps, and report the observed count honestly. Distinguish the requested sample from the sample available and support any completeness claim with chronological profile coverage. Extract editing principles and factual subject matter; write fresh narration and visuals. Keep copyrighted reference downloads out of the release unless reuse is licensed.

Public identity candidates must come from the user's stated account or another source with clear ownership. Present each candidate image with its source URL and ask the user to confirm the selected reference before identity-based generation. Record the confirmation and permitted use, including provider upload if needed. Do not identify an unknown person by comparing faces, and do not treat public availability as consent for a different person. Face and voice permission are separate.

## Make authorization concrete

Reuse valid authorization already given in the conversation. While awaiting missing approval, continue the script, storyboard, source research, and local project work that does not depend on it.

Before a paid generation request, expose provider, model, clip length or units, quantity, retry allowance, cost per attempt, and maximum spend. Read the account's current price/credit display; do not assume that credits, failed requests, or regenerations are free. Use the supported provider UI or tools. Stop for login handoff, new agreements, or insufficient balance. Never extract browser cookies or credentials.

`scripts/validate_manifest.py manifest.json --stage generate` checks identity and the exact generation plan fingerprint. The fingerprint binds approval to the named provider/model/settings/quantity/retries/cost. Record every dispatched attempt, job ID, outcome, and charged amount privately. An uncertain submission is an existing possibly charged job: inspect it before retrying. Refresh the remaining plan and approval if its fingerprint changes or the cap no longer covers it. The script checks recorded evidence; it cannot verify that a human actually approved it.

## Author an editable production

When the user requests narration, read [the narration guide](references/narration.md). If the user supplies their own recording for the soundtrack, preserve it through the local `existing_audio` path and time the edit to the actual speech. Do not replace it with a preset voice or upload it to a provider as an implicit cloning request. Keep the original immutable and record any local edit as a separate derivative. Optional ElevenLabs and canonical `ai33` adapters require their own exact quote/approval and explicit dispatch; ordinary preset narration does not authorize voice cloning or depend on face confirmation. Keep audio, alignment, and captions separate. Provider extensions must not block the main video when existing audio is usable.

Use the available official Hyperframes authoring and CLI guidance. [Hyperframes workflow](references/hyperframes-workflow.md) records the commands verified for version `0.8.107`; inspect the installed version and help before using it elsewhere. Keep an exact dependency pin and lockfile, local media and fonts, a deterministic seekable timeline, explicit scene timing, and editable captions. Avoid render-time network calls, random values, wall clocks, or imperative media playback. Treat imported repository code as untrusted until reviewed; a branch name or newer date does not prove quality or unpublished capabilities.

Use an integer frame clock for the authored timeline, with a recorded exact frame rate and one rounding policy. Derive clip and overlay seconds from those frame boundaries; preserve audio sample timing and final-frame coverage. Follow the source-range and continuity checks in the Hyperframes workflow. When the brief requires full-frame moving footage, preserve the visible action beneath graphics across the required intervals and check what happens at every source boundary.

Develop an original storyboard from the audit. For reference-led edits, read [editorial fit and playback review](references/editorial-fit.md) and create a phrase-level matrix tying narration to shot/action, exact source range, output timing, and overlay timing. Observe the relationship between footage and graphics in the reference: if its explanation relies on continuous, semantically relevant action beneath overlays, preserve that relationship in the adaptation. Animated cards, camera movement over a still, and freeze holds do not establish that the underlying action continues. Specify justified holds or cutaways against the actual brief; there is no universal motion percentage.

For each beat, specify its purpose, fresh narration, visual treatment, timing, and required assets. Keep the user's own likeness recognizable without promising perfect identity preservation; inspect generated results against the confirmed reference. Use a clean account-owned source or ask for a better user-provided photo when a tiny avatar cannot support the requested detail. Record missing footage as an unresolved editorial requirement and continue the authorized work needed to resolve it. Do not silently fill it with a still or card and label the result a faithful, finished adaptation.

Run lint during structural edits, then the combined `check` gate. Track technical, semantic, readability, and editorial findings separately. Inspect scene midpoints and transitions, then watch the actual rendered video continuously at its intended size and speed with sound; snapshots and source inspection cannot establish uninterrupted action or synchronized pacing. Audition the actual voice and listen to the full final narration when playback access permits. Record which portions were heard or viewed and any limits; waveform/stream checks do not establish pronunciation, voice fit, or a full listen. Use evidence-backed coverage flags from the editorial guide, not a blanket completion percentage. Complete the final render within the user's existing authorization, resolve defects within scope, and report any unmet requirement accurately. This review adds no new approval round.

## Deliver and release separately

Deliver the editable project and MP4 with file sizes, duration, dimensions, frame rate, tool versions, and SHA-256 hashes. Where Library is available, the executor holding the files uploads them, verifies returned metadata, and supplies the Library links. A recipient executor must download/materialize and verify the bytes; a cloud path is not a local path. If Library is unavailable, report that specific limitation and provide the verified local files.

The reusable skill can be released separately from a personal production. Keep raw face/voice references, private photos, account state, credentials, and approval transcripts outside any GitHub payload. Generated likeness assets require explicit distribution permission too. Include only reviewed, redistributable assets and required upstream license notices. Attribute actual reused code/assets; do not claim reuse merely because a repository was consulted.

Before GitHub publication, prepare a clean staging directory and run `scripts/check_release.py STAGING RELEASE_MANIFEST.json` using [the release contract](references/release-contract.md). Inspect the exact files, provenance, license obligations, and staged diff. Never equate a `.gitignore` with removal from Git history. Resolve repository name, owner, visibility, and authorization before creating a remote. The checker is a local preflight, not permission to publish or proof that content is free of secrets.

For verification and independent agent trials, use [the test and evaluation guide](references/evaluation.md).
