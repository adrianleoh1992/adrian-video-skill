---
name: reference-to-personal-video
description: Adapt a creator's video reference into an original, editable Hyperframes production featuring a user-approved likeness. Use for reference-led personal video recreation, source and consent tracking, generation planning, and reproducible delivery; not for copying another creator's footage or voice without permission.
metadata:
  version: "1.0.0"
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

Use the available official Hyperframes authoring and CLI guidance. [Hyperframes workflow](references/hyperframes-workflow.md) records the commands verified for version `0.8.107`; inspect the installed version and help before using it elsewhere. Keep an exact dependency pin and lockfile, local media and fonts, a deterministic seekable timeline, explicit scene timing, and editable captions. Avoid render-time network calls, random values, wall clocks, or imperative media playback. Treat imported repository code as untrusted until reviewed; a branch name or newer date does not prove quality or unpublished capabilities.

Develop an original storyboard from the audit. For each beat, specify its purpose, fresh narration, visual treatment, timing, and required assets. Keep the user's own likeness recognizable without promising perfect identity preservation; inspect generated results against the confirmed reference. Use a clean account-owned source or ask for a better user-provided photo when a tiny avatar cannot support the requested detail.

Run lint during structural edits, then the combined `check` gate. Inspect scene midpoints and transitions visually; scrub forward and backward. Listen to the full output, inspect face continuity, captions, safety margins, and the ending. Passing static checks is not a visual or audio review. Complete the final render within the user's existing authorization; if a genuinely missing approval blocks an external action, finish the concrete reviewable artifact first.

## Deliver and release separately

Deliver the editable project and MP4 with file sizes, duration, dimensions, frame rate, tool versions, and SHA-256 hashes. Where Library is available, the executor holding the files uploads them, verifies returned metadata, and supplies the Library links. A recipient executor must download/materialize and verify the bytes; a cloud path is not a local path. If Library is unavailable, report that specific limitation and provide the verified local files.

The reusable skill can be released separately from a personal production. Keep raw face/voice references, private photos, account state, credentials, and approval transcripts outside any GitHub payload. Generated likeness assets require explicit distribution permission too. Include only reviewed, redistributable assets and required upstream license notices. Attribute actual reused code/assets; do not claim reuse merely because a repository was consulted.

Before GitHub publication, prepare a clean staging directory and run `scripts/check_release.py STAGING RELEASE_MANIFEST.json` using [the release contract](references/release-contract.md). Inspect the exact files, provenance, license obligations, and staged diff. Never equate a `.gitignore` with removal from Git history. Resolve repository name, owner, visibility, and authorization before creating a remote. The checker is a local preflight, not permission to publish or proof that content is free of secrets.

For verification and independent agent trials, use [the test and evaluation guide](references/evaluation.md).
