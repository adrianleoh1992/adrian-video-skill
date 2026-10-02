# Editorial fit and playback review

Use this guide for a reference-led adaptation, especially when motion graphics explain actions in live or generated footage. Match the visual relationship requested in the brief as well as palette, typography, and transitions. Preserve original narration and licensed/user-owned assets while observing what makes the reference's explanation work.

## Phrase-level timing matrix

Before placing overlays, map every narration phrase that requires a specific visual to an actual shot and source range. Maintain the matrix as timings change. Use phrase IDs or transcript word ranges so wording changes do not leave stale associations.

| Field | Record |
| --- | --- |
| Phrase and purpose | Exact phrase/word range and the action, claim, or change the viewer should understand |
| Output interval | Integer start/end frames, exact output frame rate, corresponding phrase/shot seconds, and the rounding policy |
| Shot/action | Shot ID, visible subject, concrete action, and the point in the action that carries the phrase's meaning |
| Source range | Asset ID/path, source in/out timecodes, playback rate, crop, and any loop or hold |
| Overlay timing | Text/graphic content, entry, readable hold, exit, and the phrase/action it tracks |
| Layer relationship | Placement/anchor, intended action visibility, and possible occlusion by captions or graphics |
| Evidence and state | Observed source/render ranges, review notes, unresolved gaps, and evidence references |

Do not write a source range based only on a prompt, thumbnail, or expected clip duration. Inspect the usable footage. Check that the narrated action actually happens in that range, remains legible after cropping, and is visible when the relevant words and overlay appear. A generic talking face, unrelated gesture, or attractive background is not evidence of the specific action.

When the brief calls for continuous footage beneath graphics, track underlying action separately from overlay animation and camera transforms. A static held frame with animated text still has static underlying footage. Avoid accidental freezes at exhausted source ranges, repeated loops that reset the action, or timing padded with cards merely to reach the narration's duration. Deliberate holds, diagrams, or cutaways are valid when they serve the agreed brief; document that purpose instead of treating constant movement as a universal rule.

For full-frame footage, inspect the crop and layer order throughout the phrase: the relevant action must remain visible as captions and graphics arrive. At every source boundary, record whether action continues, cuts deliberately, overlaps, loops, or holds. Review that behavior in the rendered frames and continuous playback. A file duration, frame-difference score, or motion transform does not establish meaningful action continuity.

If the available footage cannot support a phrase, mark the gap and obtain or edit suitable material within existing authorization. A technical preview can remain useful while that work continues. It must not be described as a faithful finished adaptation while a required visual relationship is missing.

## Four independent review questions

| Review | Evidence and question |
| --- | --- |
| Technical | Does the actual file decode, have the intended streams/dimensions/duration, and pass runtime/layout checks? |
| Semantic | Does each required phrase show the appropriate subject and action at the right moment, and does its overlay clarify that meaning? |
| Readability | At intended viewing size and normal playback speed, can the viewer read the text while following the action? Check dwell time, line breaks, contrast, safe areas, motion blur, and occlusion. |
| Editorial | During uninterrupted playback with sound, do shot changes, action, graphics, captions, voice cadence, pauses, and ending form the requested style and pace? |

Passing one review does not imply passing another. Successful encoding cannot establish semantic fit; a readable still cannot establish readable moving text; a correct storyboard cannot establish what the exported video actually shows.

Inspect source clips to select ranges, preview the assembled timeline, and then review the actual export. Watch continuously at normal speed before using scrubbing, isolated frames, or slowed playback to diagnose problems. Recheck changed intervals and their neighboring transitions after edits. For a substantial pacing/timing revision, replay the assembled result rather than assuming earlier observations still apply.

Audition the actual chosen voice on representative narration before relying on it, where audio playback is available and within the authorized generation plan. Evaluate pronunciation, cadence, emphasis, pauses, and suitability for the language and intended audience. After assembly, listen to the full rendered narration and mix when possible. If only a sample was heard, only synthesized bytes were available, or the environment could not play audio, record that limit explicitly. A model name, transcript, waveform, loudness number, or audio stream is not an audition.

When the soundtrack is a supplied recording, use its actual words and pauses as the timing authority. Preserve the original file and distinguish any local cleanup or edit from it. Update captions or the storyboard when an earlier written script differs from the recording; do not fill missing words with a synthetic imitation. A user-supplied recording can be used locally within the requested edit without a provider or cloning step. A hash proves byte identity, not that its content has been heard or that the final mix sounds right.

## Evidence coverage flags

Keep a private `editorial_review` record alongside the matrix. The existing Python manifest validator does **not** validate these editorial flags; inspect their underlying evidence manually. Suggested flags are:

- `reference_playback`: reference ranges actually watched and any inaccessible intervals.
- `phrase_action_match`: phrase IDs whose source action and rendered synchronization were inspected, plus unresolved IDs.
- `underlying_motion_continuity`: intervals checked for the brief's action/continuity requirement, including intentional holds with reasons.
- `render_continuous_playback`: exact rendered artifact/hash, playback ranges, speed, and whether sound was available.
- `overlay_caption_readability`: rendered ranges, viewing size, and outstanding readability/occlusion findings.
- `voice_audition` and `render_audio_listen`: voice/sample or final artifact reviewed, heard ranges, and playback limits.
- `supplied_recording_use`: original/derivative file hashes and the source ranges actually used when the user supplied the soundtrack; record any substitution or missing phrase explicitly.
- `frame_clock_coverage`: frame-rate representation, authored frame intervals, quantization policy, source-boundary findings, and actual probe/frame evidence. Static arithmetic and rendered inspection have separate scopes.

For each flag use `verified`, `partial`, `unverified`, or `not_applicable`, with `scope`, `evidence_refs`, `observed_ranges` or reviewed phrase IDs, and `limitations`. `verified` applies only to the stated scope. `not_applicable` needs a brief-based reason; it cannot hide a missing requirement. Preserve the distinction between planned shots, inspected source material, and inspected rendered output.

If reporting counts or percentages, state their denominator and unit—for example, required phrase-action matches reviewed out of required phrase-action matches in the brief. Do not equate a count of available clips with visual coverage or a sample of snapshots with full playback. Do not invent a universal “100% motion” or “100% footage” target. Derive acceptance criteria from the actual brief and observed reference, retain evidence for the claim, and report remaining gaps without upgrading a technical preview to editorial completion.
