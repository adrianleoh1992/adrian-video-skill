#!/usr/bin/env python3
"""Validate recorded production evidence; never submit generation or grant consent."""

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def plan_hash(plan):
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def is_timestamp(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(
            value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def https_url(value):
    try:
        parts = urlsplit(value)
        return (isinstance(value, str) and parts.scheme == "https" and bool(parts.hostname)
                and not parts.username and not parts.password)
    except (TypeError, ValueError, AttributeError):
        return False


def instagram_permalink(value):
    if not https_url(value):
        return False
    parts = urlsplit(value)
    return (parts.netloc in {"instagram.com", "www.instagram.com"}
            and not parts.query and not parts.fragment
            and re.fullmatch(r"/(?:p|reel)/[A-Za-z0-9_-]+/", parts.path) is not None)


def amount(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("cost must be a finite nonnegative number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("cost must be a finite nonnegative number") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("cost must be a finite nonnegative number")
    return result


def positive_int(value):
    return type(value) is int and value > 0


def validate(data, stage="audit"):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)

    if not isinstance(data, dict):
        return ["manifest must be an object"]
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1,
            "schema_version must be 1")
    require(isinstance(data.get("project_id"), str) and bool(data["project_id"].strip()),
            "project_id is required")
    toolchain = data.get("toolchain", {})
    if not isinstance(toolchain, dict):
        toolchain = {}
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?",
                         str(toolchain.get("hyperframes_version", ""))) is not None,
            "toolchain.hyperframes_version must be an exact version")

    refs = data.get("references")
    if not isinstance(refs, list):
        errors.append("references must be an array")
        refs = []
    sample = data.get("sample", {})
    if not isinstance(sample, dict):
        sample = {}
    target_creator = sample.get("creator")
    seen_urls, seen_ids, observed_dated = set(), set(), 0
    for index, ref in enumerate(refs):
        prefix = f"references[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rid, url = ref.get("id"), ref.get("url")
        require(isinstance(rid, str) and bool(rid) and rid not in seen_ids,
                f"{prefix}.id must be a unique nonempty string")
        if isinstance(rid, str):
            seen_ids.add(rid)
        valid_url = instagram_permalink(url)
        require(valid_url, f"{prefix}.url must be a canonical Instagram video permalink")
        canonical = url.replace("https://www.", "https://") if valid_url else None
        require(not valid_url or canonical not in seen_urls, f"{prefix} duplicates a permalink")
        unique_url = valid_url and canonical not in seen_urls
        if valid_url:
            seen_urls.add(canonical)
        require(ref.get("status") in {"observed", "partial", "unavailable"},
                f"{prefix}.status is invalid")
        require(is_timestamp(ref.get("retrieved_at")), f"{prefix}.retrieved_at needs a timezone")
        require(isinstance(ref.get("creator"), str) and bool(ref.get("creator")),
                f"{prefix}.creator is required")
        require(isinstance(ref.get("evidence"), str) and bool(ref.get("evidence")),
                f"{prefix}.evidence is required")
        published = ref.get("published_at")
        require(published is None or is_timestamp(published),
                f"{prefix}.published_at must have a timezone or be null")
        if published is not None:
            require(isinstance(ref.get("date_evidence"), str) and bool(ref.get("date_evidence")),
                    f"{prefix}.date_evidence is required for a publication timestamp")
        if (ref.get("status") == "observed" and is_timestamp(published) and unique_url
                and ref.get("creator") == target_creator):
            observed_dated += 1
    require(positive_int(sample.get("requested_count")), "sample.requested_count must be positive")
    require(type(sample.get("claimed_complete")) is bool, "sample.claimed_complete must be boolean")
    if sample.get("claimed_complete") is True:
        require(isinstance(target_creator, str) and bool(target_creator.strip()),
                "complete sample requires sample.creator")
        require(positive_int(sample.get("requested_count")) and
                observed_dated >= sample["requested_count"],
                "complete sample requires enough unique observed videos from sample.creator with verified timestamps")
        require(isinstance(sample.get("coverage_evidence"), str) and bool(sample["coverage_evidence"].strip()),
                "complete sample requires chronological coverage evidence, not grid position")
    else:
        require(isinstance(sample.get("limitation"), str) and bool(sample["limitation"].strip()),
                "incomplete sample requires a limitation")

    assets = data.get("assets")
    if not isinstance(assets, list):
        errors.append("assets must be an array")
        assets = []
    assets_by_id = {}
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be an object")
            continue
        aid = asset.get("id")
        require(isinstance(aid, str) and bool(aid) and aid not in assets_by_id,
                f"{prefix}.id must be unique")
        if isinstance(aid, str):
            assets_by_id[aid] = asset
        require(asset.get("role") in {"face_reference", "voice_reference", "media"}, f"{prefix}.role is invalid")
        require(asset.get("privacy") in {"public", "private"}, f"{prefix}.privacy is invalid")
        require(asset.get("rights_basis") in {"user_owned", "licensed", "generated", "unknown"},
                f"{prefix}.rights_basis is invalid")
        require(https_url(asset.get("source_url")) or asset.get("source_type") == "user_upload",
                f"{prefix} needs a source URL or a user_upload source")
        require(isinstance(asset.get("owner"), str) and bool(asset.get("owner")), f"{prefix}.owner is required")
        require(type(asset.get("github_allowed")) is bool, f"{prefix}.github_allowed must be boolean")
        if asset.get("role") in {"face_reference", "voice_reference"} or asset.get("privacy") == "private":
            require(asset.get("github_allowed") is False, f"{prefix} raw/private references cannot be in GitHub")

    if stage == "audit":
        return errors
    identity = data.get("identity", {})
    if not isinstance(identity, dict):
        identity = {}
    require(identity.get("status") == "confirmed", "identity must be confirmed by the user")
    require(isinstance(identity.get("confirmation_ref"), str) and bool(identity["confirmation_ref"].strip()),
            "identity.confirmation_ref is required")
    subject = identity.get("subject_handle")
    require(isinstance(subject, str) and bool(subject.strip()), "identity.subject_handle is required")
    selected = identity.get("selected_asset_ids")
    require(isinstance(selected, list) and bool(selected), "select at least one confirmed face asset")
    if isinstance(selected, list):
        for aid in selected:
            asset = assets_by_id.get(aid) if isinstance(aid, str) else None
            require(asset is not None and asset.get("role") == "face_reference",
                    "every selected asset must identify a face_reference in assets")
            if asset:
                require(asset.get("owner") == subject, "selected face asset owner must match the declared subject")
                require(asset.get("rights_basis") == "user_owned", "selected face needs user-owned source evidence")
    require(identity.get("provider_upload_allowed") is True,
            "identity.provider_upload_allowed must be true before provider upload")

    generation = data.get("generation", {})
    if not isinstance(generation, dict):
        generation = {}
    unit = generation.get("unit")
    require(unit == "credits" or (isinstance(unit, str) and re.fullmatch(r"[A-Z]{3}", unit)),
            "generation.unit must be credits or a three-letter currency")
    plan = generation.get("plan")
    if not isinstance(plan, list) or not plan:
        errors.append("generation.plan must contain the exact planned requests")
        plan = []
    total, jobs, providers = Decimal(0), set(), set()
    for index, job in enumerate(plan):
        prefix = f"generation.plan[{index}]"
        if not isinstance(job, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for key in ("id", "provider", "model", "price_evidence"):
            require(isinstance(job.get(key), str) and bool(job[key].strip()), f"{prefix}.{key} is required")
        jid = job.get("id")
        require(not isinstance(jid, str) or jid not in jobs, f"{prefix}.id must be unique")
        if isinstance(jid, str):
            jobs.add(jid)
        if isinstance(job.get("provider"), str):
            providers.add(job["provider"])
        require(isinstance(job.get("settings"), dict) and bool(job["settings"]),
                f"{prefix}.settings must record duration/resolution and other priced settings")
        for key in ("quantity", "max_attempts"):
            require(positive_int(job.get(key)), f"{prefix}.{key} must be a positive integer")
        require(is_timestamp(job.get("price_checked_at")), f"{prefix}.price_checked_at needs a timezone")
        try:
            cost = amount(job.get("unit_cost"))
            if positive_int(job.get("quantity")) and positive_int(job.get("max_attempts")):
                total += cost * job["quantity"] * job["max_attempts"]
        except ValueError as exc:
            errors.append(f"{prefix}.unit_cost: {exc}")
    # Credits are not portable across provider accounts. Split plans by provider/account.
    require(unit != "credits" or len(providers) <= 1, "credit plans must use one provider/account")
    try:
        spent = amount(generation.get("spent"))
    except ValueError as exc:
        errors.append(f"generation.spent: {exc}")
        spent = Decimal(0)
    approval = generation.get("approval")
    if total > 0 or approval is not None:
        if not isinstance(approval, dict):
            errors.append("paid generation requires a valid recorded budget approval")
        else:
            require(approval.get("unit") == unit, "budget approval unit must match generation unit")
            require(isinstance(approval.get("confirmation_ref"), str) and bool(approval["confirmation_ref"].strip()),
                    "budget approval confirmation_ref is required")
            try:
                require(approval.get("plan_sha256") == plan_hash(plan), "budget approval plan fingerprint is stale")
            except (ValueError, TypeError):
                errors.append("generation.plan must contain JSON-safe finite values")
            try:
                require(spent + total <= amount(approval.get("cap")),
                        "spent plus planned maximum attempts exceeds approved cap")
            except ValueError as exc:
                errors.append(f"budget approval cap: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--stage", choices=("audit", "generate"), default="audit")
    parser.add_argument("--plan-hash", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.plan_hash:
            print(plan_hash(data["generation"]["plan"]))
            return 0
        errors = validate(data, args.stage)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}))
        return 1
    print(json.dumps({"ok": not errors, "stage": args.stage, "errors": errors}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
