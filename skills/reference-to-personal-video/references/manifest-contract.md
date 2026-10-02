# Production manifest contract, version 1

The manifest is private production evidence. It can contain source URLs, account handles, and short references to approvals, but never authentication values. Keep full private approval transcripts elsewhere. `confirmation_ref` is an opaque local record reference, not a claim that the validator witnessed consent. JSON amounts may be numbers or decimal strings; strings avoid floating-point ambiguity. Unknown prices must not be entered as zero.

## Top-level fields

- `schema_version`: integer `1`.
- `project_id`: nonempty local project identifier.
- `toolchain.hyperframes_version`: exact semantic version; no `latest`, ranges, or caret.
- `references`: observed, partial, and inaccessible video evidence.
- `sample`: requested count, honest completeness claim, coverage evidence or limitation.
- `assets`: face/voice candidates and other media provenance.
- `identity`: selected face and recorded user confirmation.
- `generation`: the remaining exact request plan, budget unit, cumulative spend, and approval.

## Video reference

```json
{
  "id": "reference-01",
  "url": "https://www.instagram.com/reel/ExampleVideo01/",
  "creator": "@example_creator",
  "published_at": "2026-09-30T08:00:00+07:00",
  "date_evidence": "The post detail view exposed this timestamp; privately saved observation 01.",
  "retrieved_at": "2026-10-02T10:00:00Z",
  "status": "observed",
  "evidence": "Audit record 01 contains observed frames and timecoded pacing notes."
}
```

The example URL and timestamp are synthetic, not an assertion about a real post. Use canonical `https://www.instagram.com/p/SHORTCODE/` or `/reel/SHORTCODE/` links with no tracking parameters. `published_at` is null if unverified; retain a date-only observation in `date_evidence` rather than inventing a time. `retrieved_at` always includes a timezone. `observed` means the video was actually inspected, not that a grid thumbnail loaded.

`sample.creator` identifies the requested account and must match the relevant `references[].creator` labels. `sample.requested_count` is a positive integer. `claimed_complete: true` needs at least that many unique fully observed and dated videos from `sample.creator`, plus `coverage_evidence` explaining how the creator's chronological history was covered. Ten dated videos alone do not establish they are the latest ten. Audit the requested creator, exclude unrelated accounts, and resolve same-day ambiguities. A false claim is still possible in an inaccurate manifest; inspect the underlying evidence. An incomplete sample needs a nonempty `limitation`.

## Identity source and confirmation

An asset has `id`, `role` (`face_reference`, `voice_reference`, `media`), `source_url` (HTTPS) or `source_type: user_upload`, `owner`, `privacy` (`public`/`private`), `rights_basis` (`user_owned`/`licensed`/`generated`/`unknown`), and boolean `github_allowed`. Private assets and raw face/voice references require `github_allowed: false`.

The generation gate requires `identity.status: confirmed`, an exact `subject_handle`, nonempty `selected_asset_ids`, a `confirmation_ref`, and `provider_upload_allowed: true`. Each selected asset must be a user-owned face reference whose `owner` matches the subject handle. Owner labels are declarations and need source evidence and the user's confirmation. The confirmation should identify the selected image, use, and provider; changing that scope needs a fresh confirmation. `voice_clone_allowed` is independently recorded and must be checked before voice cloning; face approval never grants it. The current script validates face-based generation only and does not authorize voice cloning.

## Exact generation plan

```json
{
  "unit": "credits",
  "spent": "0",
  "plan": [
    {
      "id": "intro-clip",
      "provider": "Google Flow / account-alias",
      "model": "the exact model label displayed in the UI",
      "settings": {"duration_seconds": 8, "aspect_ratio": "9:16", "resolution": "as displayed"},
      "quantity": 1,
      "max_attempts": 1,
      "unit_cost": "20",
      "price_evidence": "Private capture of the current price display before submission.",
      "price_checked_at": "2026-10-02T10:00:00Z"
    }
  ],
  "approval": null
}
```

All price/model values above are examples, **not current provider pricing**. `unit_cost` is the cost of one attempt for the recorded settings, including any batch output charged by the provider. `quantity × max_attempts × unit_cost` is the maximum planned spend per job. `max_attempts: 1` allows no automatic retry. Retry allowance and quantity must be positive integers. Use one provider/account per credit plan because balances are not interchangeable. Currency units are three-letter codes such as `USD`; do not mix units in a plan.

After exposing the complete plan to the user and receiving valid authorization, record:

```json
{
  "unit": "credits",
  "cap": "20",
  "confirmation_ref": "private-approval-record-04",
  "plan_sha256": "the actual 64-character result from --plan-hash"
}
```

The validator requires `spent + maximum remaining plan cost <= cap` and an exact plan hash. It includes all job fields in that hash, including model settings and price evidence. It does not refresh account prices or balances, submit jobs, authenticate the approval, or track spend automatically. Update the ledger first, then the remaining plan; a changed plan requires approval of its new fingerprint. Zero-cost plans still require identity confirmation and evidence for the zero price, but no paid budget approval. Unknown-status jobs consume their maximum possible charge until the account confirms otherwise.

`audit` permits incomplete identity/generation fields while enforcing honest reference/asset structure. `generate` adds identity and budget checks. A failed gate exits 1 and reports field-level errors; it never prints credential values.
