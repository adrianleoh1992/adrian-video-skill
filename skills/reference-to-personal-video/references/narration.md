# Narration and supplied recordings

`scripts/narration.py` separates offline planning, optional paid narration, existing local audio, and caption export. Python 3.10+ and its standard library are sufficient. Neither importing the module nor constructing a provider adapter reads credentials or calls a provider. Development verification used synthetic responses only; authenticated paid behavior has not been tested.

## Use the supplied recording when requested

If a user provides a recording to use as their actual voice, use `import-audio` as the local `existing_audio` route. This copies and hashes the recording without synthesis, external upload, or cloning. Keep its original bytes immutable. Local extraction, trimming, cleanup, or normalization belongs in a separately recorded derivative with source ranges and edit settings; the import command itself does not perform those edits.

Time shots and captions to the supplied speech, including its real pauses. If a written script and the recording differ, record the mismatch and align captions to the actual words. Do not substitute a preset voice or synthesize missing phrases merely because a provider adapter is available. A complete soundtrack request with only a partial recording has an unresolved content gap; continue independent authorized editing and report the specific missing part without inventing consent or speech.

Record actual listening coverage separately from file integrity or decode checks. A successful local import establishes preserved bytes, not an audition or a verified final mix. The existing tests use synthetic temporary audio and do not establish the quality of any private recording or new rendered video.

## Provider capabilities and verified sources

Official contracts inspected on 2026-10-02:

- ElevenLabs [timestamp synthesis](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps): `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps`, `xi-api-key`, JSON `text`, `model_id`, optional `voice_settings`, and `output_format` query. Returns base64 audio plus character timing. This adapter supports MP3 formats.
- ElevenLabs [models](https://elevenlabs.io/docs/api-reference/models/list) and [voices](https://elevenlabs.io/docs/api-reference/voices/search): runtime `GET /v1/models` checks TTS support and request length; `GET /v2/voices?category=premade&page_size=100` verifies the selected voice's actual category. A voice absent from that returned catalog fails before synthesis. No cloned, generated, or professional voice is selected automatically. Inspect runtime model languages when choosing Indonesian narration; no model or current price is guessed.
- [AI33.pro / OpenSpeaker API](https://ai33.pro/app/api-document): canonical provider name `ai33`; `POST https://api.ai33.pro/v3/text-to-speech`, multipart `text`, exact provider-prefixed `voice_id`, `speed` 0.5–1.5, and boolean `with_transcript`. Auth is `xi-api-key`. `GET /v3/voices` requires provider and returns `data[]` with pagination; this implementation searches at most ten pages of 100. `GET /v1/task/{task_id}` polls `doing`/`done`/`error` and captures `credit_cost` plus metadata URLs. `GET /v1/credits` is a balance, **not a price quote**, and is not used to invent one.

AI33's documented route has no model ID, output format, seed, or ElevenLabs voice-settings selector. Its request record therefore explicitly uses `model_id: "provider-default"` and `output_format: "provider-default"`; these bookkeeping values are never sent to the API. A `clone_` voice is always rejected. Other prefixed voices still need independently verified ordinary-preset evidence; catalog availability alone does not establish this.

AI33 media downloads carry no API key and require reviewed exact hostnames in a private provider profile. Redirects are not followed. A new/unexpected media host fails safely with the task ID retained. Raw provider JSON and SRT stay separate; no undocumented word-timing schema is inferred. `aipro33` is not silently treated as an alias for `ai33`.

## Full request and offline estimate

Keep real input JSON outside Git. A request has **exactly** these fields:

```json
{
  "schema_version": 1,
  "provider": "elevenlabs",
  "model_id": "selected-from-current-model-catalog",
  "voice_id": "selected-from-current-premade-voice-catalog",
  "voice_mode": "preset",
  "text": "Narasi asli yang akan dibacakan.",
  "settings": {"voice_settings": {"stability": 0.5}},
  "output_format": "mp3_44100_128"
}
```

Those selection labels are illustrative, not usable IDs. AI33 settings instead contain exactly `speed` and `with_transcript`. Use the actual ID returned by its catalog. Text is hashed exactly, including whitespace and Unicode representation. Provider, model, voice, settings, text, output format, and schema all contribute to the immutable cache key.

```bash
python3 scripts/narration.py fingerprint /private-production/request.json
python3 scripts/narration.py plan /private-production/request.json /private-production/quote.json
```

The quote contains `request_sha256`, `provider`, `account_alias`, `unit` (`credits` or a currency code), `maximum_cost`, `price_evidence`, timezone-aware `checked_at` and `expires_at`, and `max_attempts: 1`. Obtain a defensible upper bound from current account/provider pricing for this exact text and request. Unknown cost is not zero. `plan` reports the supplied estimate and its source; it is not an automatic billing estimator and makes no network calls. Expired quotes fail.

## Approval, credentials, and dispatch

An approval contains `approved: true`, the exact `request_sha256` and `quote_sha256` from `plan`, matching `provider`, `account_alias`, `unit`, a shared `budget_id`, `cap`, `already_spent`, `confirmation_ref`, `allow_text_upload: true`, and timezone-aware `expires_at`. Zero-price external requests still require approval of the text upload. AI33 quotes must use credits.

`already_spent` is known spending **outside the local attempt ledger**; the runner adds that ledger's reservations itself. Use one stable output directory and budget ID for a budget across requests. An exclusive local lock prevents concurrent reservations from exceeding the recorded cap. This is a local guard, not a provider-side hard cap or cross-machine/account billing system. Unknown charges remain reserved at the maximum; a reported AI33 charge above the estimate is recorded and flags the receipt. Do not reduce reservations or change budget IDs to bypass unresolved spending.

Credentials are read only after approval validation: `ELEVENLABS_API_KEY` or `AI33_API_KEY`. Supply them through a secure local environment outside the repository; no `.env` file or secret value is included here. Do not paste keys into chat, command history, request JSON, or provider profiles.

Without `--execute`, `generate` is an offline dry-run and does not read a key or write a reservation:

```bash
python3 scripts/narration.py generate /private-production/request.json /private-production/quote.json --output-dir /private-production/voice-artifacts
```

After the exact request and cost are approved, add `--approval /private-production/approval.json --execute`. AI33 also needs `--provider-profile /private-production/ai33-profile.json`. That profile contains `provider: "ai33"`, `voice_provider`, `preset_voice_ids`, `preset_evidence`, and `download_hosts` (exact reviewed hostnames); it contains no key. Neither default provider construction nor local cache reuse makes a live call.

One synthesis attempt is permitted. The runner records an immutable reservation before dispatch and saves a returned task/request ID as soon as available. AI33 polls at most 30 times with two-second gaps; individual HTTP calls have a 30-second timeout. A timeout, process crash, provider error, or incomplete download leaves the reservation in place. Inspect the recorded job and actual billing before any new attempt; this version intentionally has no automatic retry, reservation-delete, or refund command. Provider state reconciliation is manual.

## Output, captions, and existing audio

Completed narration lives under `OUTPUT/narration/REQUEST_SHA256/` with audio, `request.json`, exact `narration.txt`, receipt hashes, and available alignment/sidecars. Files are created without overwriting and made read-only. Reuse verifies hashes and exact request association; corruption raises an error instead of silently generating again. The files are locally immutable by convention and mode bits, not cryptographically protected against their owner editing both files and receipts.

ElevenLabs character timing is retained and converted to separate word alignment when valid. AI33's `provider-alignment.json` and `provider-captions.srt` preserve the original schema. Missing timing remains missing. Normalized alignment uses `schema_version: 1`, `source: "provider"` or `"forced_alignment"`, `unit: "seconds"`, and non-overlapping `segments` with `text`, `start`, and `end`.

```bash
python3 scripts/narration.py captions /private-production/word-alignment.json --output-dir /private-production/voice-artifacts --max-chars 42
python3 scripts/narration.py import-audio /private-production/narration.wav --text-file /private-production/narration.txt --output-dir /private-production/voice-artifacts
```

Caption outputs have their own key and do not alter audio or trigger synthesis. `import-audio` is the `existing_audio` fallback for a user's recording or a local narrator such as Piper; it requires no provider, key, quote, or upload. It copies verified nonempty container bytes and supplied text into immutable output. It does not invent transcription or alignment.

Supported audio containers are MP3, WAV, Ogg, FLAC, and M4A; raw PCM is excluded without a sample-format contract. Basic MIME/signature checks reject common HTML/JSON error bodies. They do not replace `ffprobe`, full playback, pronunciation review, or caption timing inspection before final video delivery.
