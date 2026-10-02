#!/usr/bin/env python3
"""Provider-neutral narration planning and immutable local delivery.

Planning is offline. Execution requires an explicitly approved request/quote and
a verified preset-voice adapter. This module does not implement voice cloning.
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


class NarrationError(ValueError):
    """A safe, user-readable error without provider credentials or response text."""


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise NarrationError("Use JSON-safe finite request values.") from exc


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def cost(value):
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError()
        parsed = Decimal(str(value))
        if not parsed.is_finite() or parsed < 0:
            raise ValueError()
        return parsed
    except (InvalidOperation, ValueError):
        raise NarrationError("Cost amounts must be finite nonnegative decimals.") from None


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.utcoffset() is None:
            raise ValueError()
        return result
    except (AttributeError, ValueError):
        raise NarrationError("Evidence and expiry timestamps need an explicit timezone.") from None


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise NarrationError(f"{label} must be a nonempty string.")


def reject_secrets(value):
    denied = {"api_key", "apikey", "secret", "password", "token", "authorization", "headers", "cookie"}
    if isinstance(value, dict):
        if any(str(key).lower() in denied for key in value):
            raise NarrationError("Keep credentials in the named environment variable, outside request JSON.")
        for item in value.values():
            reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            reject_secrets(item)


def validate_request(request):
    required = {"schema_version", "provider", "model_id", "voice_id", "voice_mode",
                "text", "settings", "output_format"}
    if not isinstance(request, dict) or set(request) != required:
        raise NarrationError("Request must contain exactly the documented request fields.")
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise NarrationError("Unsupported narration request schema.")
    for key in ("provider", "model_id", "voice_id", "text", "output_format"):
        nonempty(request[key], key)
    if not re.fullmatch(r"[a-z0-9-]+", request["provider"]):
        raise NarrationError("Provider must be a lowercase slug.")
    if request["voice_mode"] != "preset":
        raise NarrationError("Only ordinary provider preset voices are supported; cloning is excluded.")
    if not isinstance(request["settings"], dict):
        raise NarrationError("settings must be an object with explicit generation options.")
    if any(key in request["settings"] for key in ("clone", "voice_clone", "voice_cloning", "reference_audio", "audio_samples")):
        raise NarrationError("Voice cloning and reference-audio inputs are not supported.")
    reject_secrets(request)
    canonical(request)
    return digest(request)


def plan(request, quote, now=None):
    """Validate a supplied, evidenced maximum-cost quote without accessing a provider."""
    now = now or datetime.now(timezone.utc)
    key = validate_request(request)
    if not isinstance(quote, dict):
        raise NarrationError("A verified current quote is required; unknown price is not zero.")
    if quote.get("request_sha256") != key or quote.get("provider") != request["provider"]:
        raise NarrationError("Quote does not describe this exact request/provider.")
    if quote.get("max_attempts") != 1 or type(quote.get("max_attempts")) is not int:
        raise NarrationError("The narration runner permits exactly one attempt; it never retries automatically.")
    for field in ("account_alias", "price_evidence"):
        nonempty(quote.get(field), field)
    unit = quote.get("unit")
    if unit != "credits" and (not isinstance(unit, str) or not re.fullmatch(r"[A-Z]{3}", unit)):
        raise NarrationError("Quote unit must be credits or a three-letter currency.")
    checked, expires = timestamp(quote.get("checked_at")), timestamp(quote.get("expires_at"))
    if checked > now or expires <= now or expires <= checked:
        raise NarrationError("Quote is expired or has invalid evidence timestamps.")
    maximum = cost(quote.get("maximum_cost"))
    return {"schema_version": 1, "request_sha256": key, "quote_sha256": digest(quote),
            "provider": request["provider"], "account_alias": quote["account_alias"],
            "model_id": request["model_id"], "voice_id": request["voice_id"],
            "voice_mode": "preset", "characters": len(request["text"]),
            "output_format": request["output_format"], "maximum_cost": str(maximum),
            "unit": unit, "max_attempts": 1, "external_calls": 0,
            "estimate_source": quote["price_evidence"]}


def approve(request, quote, approval, now=None):
    now = now or datetime.now(timezone.utc)
    prepared = plan(request, quote, now)
    if not isinstance(approval, dict) or approval.get("approved") is not True:
        raise NarrationError("Explicit recorded approval is required, including for a free external request.")
    for field in ("request_sha256", "quote_sha256", "provider", "account_alias", "unit"):
        if approval.get(field) != prepared[field]:
            raise NarrationError(f"Approval {field} does not match the current request and quote.")
    nonempty(approval.get("confirmation_ref"), "confirmation_ref")
    nonempty(approval.get("budget_id"), "budget_id")
    if approval.get("allow_text_upload") is not True:
        raise NarrationError("Approval must cover uploading this narration text to the named provider.")
    if timestamp(approval.get("expires_at")) <= now:
        raise NarrationError("Narration approval has expired.")
    if cost(approval.get("already_spent")) + cost(quote["maximum_cost"]) > cost(approval.get("cap")):
        raise NarrationError("Already spent plus this request's maximum cost exceeds the approved cap.")
    return prepared


def safe_root(value, create=False):
    requested = Path(value).absolute()
    if requested.is_symlink():
        raise NarrationError("Output root must not itself be a symlink.")
    # Canonicalize normal OS aliases such as macOS /var -> /private/var.
    root = requested.resolve()
    for path in (root, *root.parents):
        if (path / ".git").exists():
            raise NarrationError("Keep narration output, approvals, and credentials outside Git working trees.")
    if create:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.exists() and not root.is_dir():
        raise NarrationError("Output root must be a directory.")
    return root


def validate_alignment(alignment):
    if not isinstance(alignment, dict) or alignment.get("schema_version") != 1:
        raise NarrationError("Alignment must use the documented version-1 word segment schema.")
    if alignment.get("unit") != "seconds" or alignment.get("source") not in {"provider", "forced_alignment"}:
        raise NarrationError("Alignment needs a declared source and seconds as its unit.")
    segments = alignment.get("segments")
    if not isinstance(segments, list) or not segments:
        raise NarrationError("Alignment needs actual timed word segments; do not invent timestamps.")
    last = Decimal(0)
    for segment in segments:
        if not isinstance(segment, dict):
            raise NarrationError("Each alignment segment must be an object.")
        nonempty(segment.get("text"), "alignment text")
        start, end = cost(segment.get("start")), cost(segment.get("end"))
        if end <= start or start < last:
            raise NarrationError("Alignment segments need positive duration and non-overlapping order.")
        last = end
    canonical(alignment)


def read_cached(root, key, request):
    if (root / "narration").is_symlink():
        raise NarrationError("Narration cache parent must not be a symlink.")
    target = root / "narration" / key
    if not target.exists():
        return None
    if target.is_symlink() or not target.is_dir():
        raise NarrationError("The immutable cache target is not a regular directory.")
    try:
        receipt_path = target / "receipt.json"
        if receipt_path.is_symlink():
            raise NarrationError("The cache receipt must not be a symlink.")
        receipt = json.loads(receipt_path.read_text())
        if receipt["request_sha256"] != key or receipt["status"] != "complete":
            raise NarrationError("Cache receipt does not match this complete request.")
        if not isinstance(receipt["files"], dict) or not {"request.json", "narration.txt"}.issubset(receipt["files"]):
            raise NarrationError("Cache receipt is incomplete.")
        if receipt["audio_file"] not in receipt["files"]:
            raise NarrationError("Cache receipt does not include its audio artifact.")
        for name, expected in receipt["files"].items():
            path = target / name
            if Path(name).name != name or path.is_symlink() or not path.is_file():
                raise NarrationError("Unsafe or missing file in cache receipt.")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != expected["sha256"] or len(data) != expected["bytes"]:
                raise NarrationError("An immutable cached artifact has changed; refusing silent replacement.")
        if set(p.name for p in target.iterdir()) != set(receipt["files"]) | {"receipt.json"}:
            raise NarrationError("Unexpected files in immutable narration cache.")
        if json.loads((target / "request.json").read_text()) != request:
            raise NarrationError("Cached request content does not match the full request.")
        return {"cache_hit": True, "directory": str(target), "receipt": receipt, "external_calls": 0}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, NarrationError):
            raise
        raise NarrationError("Cannot verify the existing immutable narration cache.") from None


def write_bytes(path, data):
    with path.open("xb") as handle:
        handle.write(data)
    path.chmod(0o400)


def validate_audio_bytes(data, extension):
    """Reject obvious error bodies; full decode/listening remains a delivery check."""
    if not isinstance(data, bytes) or not data:
        raise NarrationError("Audio payload is empty.")
    valid = False
    if extension == "wav":
        valid = len(data) >= 44 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    elif extension == "mp3":
        offset = 0
        if data[:3] == b"ID3" and len(data) >= 10:
            offset = 10 + sum((value & 127) << shift for value, shift in zip(data[6:10], (21, 14, 7, 0)))
            if data[5] & 16:
                offset += 10
        for index in range(offset, min(len(data) - 3, offset + 4096)):
            if (data[index] == 255 and data[index + 1] & 224 == 224 and data[index + 1] & 6
                    and data[index + 2] >> 4 not in {0, 15} and data[index + 2] & 12 != 12):
                valid = True
                break
    elif extension == "ogg":
        valid = len(data) > 27 and data.startswith(b"OggS")
    elif extension == "flac":
        valid = len(data) > 42 and data.startswith(b"fLaC")
    elif extension == "m4a":
        valid = len(data) > 16 and data[4:8] == b"ftyp"
    if not valid:
        raise NarrationError("Returned bytes do not match a supported audio container; refusing to cache an error body.")


def reserve_attempt(attempts, key, prepared, approval):
    """Serialize budget reservations; a stale lock requires manual reconciliation."""
    lock = attempts / ".budget-lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise NarrationError("Another budget reservation is active or unresolved; no request was dispatched.") from None
    os.close(descriptor)
    try:
        reserved = Decimal(0)
        for path in attempts.iterdir():
            if not re.fullmatch(r"[a-f0-9]{64}\.json", path.name):
                continue
            if path.is_symlink():
                raise NarrationError("Budget reservation files must not be symlinks.")
            record = load(path)
            if record.get("budget_id") != approval["budget_id"]:
                continue
            if any(record.get(field) != prepared[field] for field in ("provider", "account_alias", "unit")):
                raise NarrationError("A budget_id cannot be reused across provider accounts or currencies.")
            charge = cost(record.get("maximum_cost"))
            billed = attempts / f"{path.stem}.billing.json"
            if billed.exists():
                if billed.is_symlink():
                    raise NarrationError("Billing evidence must not be a symlink.")
                charge = max(charge, cost(load(billed).get("reported_cost")))
            reserved += charge
        if cost(approval["already_spent"]) + reserved + cost(prepared["maximum_cost"]) > cost(approval["cap"]):
            raise NarrationError("Existing attempt reservations plus this request exceed the approved budget cap.")
        reservation = attempts / f"{key}.json"
        try:
            write_bytes(reservation, canonical({"request_sha256": key, "quote_sha256": prepared["quote_sha256"],
                        "provider": prepared["provider"], "budget_id": approval["budget_id"],
                        "status": "reserved_or_uncertain", "maximum_cost": prepared["maximum_cost"],
                        "unit": prepared["unit"], "account_alias": prepared["account_alias"],
                        "confirmation_ref": approval["confirmation_ref"],
                        "note": "A submission may be charged. Reconcile provider state before any new attempt."}))
        except FileExistsError:
            raise NarrationError("This request already has an attempt reservation. Inspect its provider job/charge; no blind retry.") from None
    finally:
        lock.unlink()


def execute(request, quote, approval, output_dir, adapter, *, execute_external=False, environ=None, now=None):
    """Use an injected verified adapter; transport errors leave an unresolved reservation.

    Adapter contract: provider, credential_env, verify_request(request), and
    synthesize(request, credential, record_job) -> audio/extension/mime_type/request_id/alignment.
    The adapter must check the selected voice is a preset before any synthesis.
    """
    # Copy so an adapter cannot mutate the caller's request or approval after hashing.
    request = json.loads(canonical(request))
    key = validate_request(request)
    root = safe_root(output_dir)
    cached = read_cached(root, key, request) if root.exists() else None
    if cached is not None:
        return cached
    prepared = plan(request, quote, now)
    if not execute_external:
        return {"dry_run": True, "plan": prepared, "external_calls": 0}
    prepared = approve(request, quote, approval, now)
    if adapter is None or adapter.provider != request["provider"]:
        raise NarrationError("A verified adapter for the requested provider is not available.")
    adapter.verify_request(request)
    if getattr(adapter, "cost_unit", prepared["unit"]) != prepared["unit"]:
        raise NarrationError("Quote unit does not match the provider's billing unit.")
    if digest(request) != key:
        raise NarrationError("The adapter changed the full request during validation.")
    env_name = adapter.credential_env
    if not isinstance(env_name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", env_name):
        raise NarrationError("Adapter credential environment variable is invalid.")
    environment = os.environ if environ is None else environ
    credential = environment.get(env_name)
    if not isinstance(credential, str) or not credential:
        raise NarrationError(f"Set {env_name} securely outside the repository before execution.")
    root = safe_root(output_dir, create=True)
    narration_dir, attempts = root / "narration", root / "attempts"
    for directory in (narration_dir, attempts):
        if directory.is_symlink():
            raise NarrationError("Private output subdirectories must not be symlinks.")
        directory.mkdir(exist_ok=True, mode=0o700)
    reserve_attempt(attempts, key, prepared, approval)
    recorded_job = None
    def record_job(job_id):
        nonlocal recorded_job
        if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", job_id) or credential in job_id:
            raise NarrationError("Provider job identifier was not safe to record.")
        write_bytes(attempts / f"{key}.job.json", canonical({"request_sha256": key, "provider_job_id": job_id}))
        recorded_job = job_id
    try:
        result = adapter.synthesize(json.loads(canonical(request)), credential, record_job)
        if not isinstance(result, dict) or not isinstance(result.get("audio"), bytes) or not result["audio"]:
            raise NarrationError("Provider returned no nonempty audio bytes.")
        ext = result.get("extension")
        if ext not in {"mp3", "wav", "ogg", "flac", "m4a"}:
            raise NarrationError("Provider returned an unsupported audio format.")
        validate_audio_bytes(result["audio"], ext)
        alignment = result.get("alignment")
        if alignment is not None:
            validate_alignment(alignment)
        reported_cost = result.get("reported_cost")
        if reported_cost is not None:
            reported_cost = str(cost(reported_cost))
            write_bytes(attempts / f"{key}.billing.json", canonical({"reported_cost": reported_cost, "unit": prepared["unit"]}))
        temp = Path(tempfile.mkdtemp(prefix=f".pending-{key}-", dir=narration_dir))
        audio_name = f"audio.{ext}"
        payload = {audio_name: result["audio"], "request.json": canonical(request),
                   "narration.txt": request["text"].encode("utf-8")}
        if alignment is not None:
            payload["alignment.json"] = canonical(alignment)
        for name, content in result.get("provider_documents", {}).items():
            if name not in {"provider-alignment.json", "provider-captions.srt"} or not isinstance(content, bytes):
                raise NarrationError("Unsupported provider sidecar artifact.")
            if credential.encode() in content:
                raise NarrationError("Provider sidecar unexpectedly contained credential text.")
            payload[name] = content
        mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg", "flac": "audio/flac", "m4a": "audio/mp4", "pcm": "audio/L16"}[ext]
        receipt = {"schema_version": 1, "status": "complete", "request_sha256": key,
                   "quote_sha256": prepared["quote_sha256"], "provider": request["provider"],
                   "audio_file": audio_name, "mime_type": mime,
                   "provider_request_id": recorded_job, "reserved_maximum_cost": prepared["maximum_cost"],
                   "unit": prepared["unit"], "billing_status": "verify actual charge with provider",
                   "reported_cost": reported_cost,
                   "charge_exceeds_reserved_maximum": reported_cost is not None and cost(reported_cost) > cost(prepared["maximum_cost"]),
                   "alignment_available": alignment is not None, "files": {}}
        for name, content in payload.items():
            write_bytes(temp / name, content)
            receipt["files"][name] = {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
        write_bytes(temp / "receipt.json", canonical(receipt))
        target = narration_dir / key
        if target.exists():
            raise NarrationError("Refusing to replace an existing immutable output.")
        temp.rename(target)
        return {"cache_hit": False, "directory": str(target), "receipt": receipt,
                "synthesis_attempts": 1, "external_calls": result.get("external_calls", 1)}
    except Exception:
        # Provider errors can echo credentials or narration; do not expose their text.
        raise NarrationError("Narration attempt did not finish safely. Its reservation remains; inspect provider status and billing before retrying.") from None


def caption_timestamp(seconds, separator):
    millis = int((Decimal(str(seconds)) * 1000).quantize(Decimal("1")))
    hours, remainder = divmod(millis, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    whole, fraction = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d}{separator}{fraction:03d}"


def import_existing_audio(source, text, output_dir):
    """Preserve user-provided/local narrator audio without any provider dependency."""
    source = Path(source)
    ext = source.suffix.lower().lstrip(".")
    if source.is_symlink() or not source.is_file() or ext not in {"mp3", "wav", "ogg", "flac", "m4a"}:
        raise NarrationError("Existing audio must be a regular file in a supported audio format.")
    audio = source.read_bytes()
    if not audio or not isinstance(text, str):
        raise NarrationError("Existing audio must be nonempty, with supplied narration text.")
    validate_audio_bytes(audio, ext)
    request = {"schema_version": 1, "provider": "existing_audio", "audio_sha256": hashlib.sha256(audio).hexdigest(),
               "output_format": ext, "text": text}
    key = digest(request)
    root = safe_root(output_dir, create=True)
    cached = read_cached(root, key, request)
    if cached:
        return cached
    parent = root / "narration"
    parent.mkdir(exist_ok=True, mode=0o700)
    target = parent / key
    # Exclusive creation prevents overwriting even if two local imports race.
    target.mkdir(mode=0o700)
    payload = {f"audio.{ext}": audio, "request.json": canonical(request), "narration.txt": text.encode("utf-8")}
    receipt = {"schema_version": 1, "status": "complete", "request_sha256": key,
               "provider": "existing_audio", "audio_file": f"audio.{ext}", "alignment_available": False,
               "source_audio_sha256": request["audio_sha256"], "files": {}}
    for name, content in payload.items():
        write_bytes(target / name, content)
        receipt["files"][name] = {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    write_bytes(target / "receipt.json", canonical(receipt))
    return {"directory": str(target), "cache_hit": False, "receipt": receipt, "external_calls": 0}


def export_captions(alignment, output_dir, max_chars=42):
    """Create separately keyed SRT/VTT from real word alignment; never touch audio."""
    validate_alignment(alignment)
    if type(max_chars) is not int or not 10 <= max_chars <= 120:
        raise NarrationError("Caption max_chars must be an integer from 10 to 120.")
    root = safe_root(output_dir, create=True)
    key = digest({"schema_version": 1, "alignment": alignment, "max_chars": max_chars})
    parent = root / "captions"
    if parent.is_symlink():
        raise NarrationError("Caption directory must not be a symlink.")
    parent.mkdir(exist_ok=True, mode=0o700)
    target = parent / key
    if target.exists():
        raise NarrationError("These caption outputs already exist; refusing to overwrite them.")
    cues, group = [], []
    for segment in alignment["segments"]:
        text = " ".join(part["text"] for part in group + [segment])
        if group and (len(text) > max_chars or float(segment["end"]) - float(group[0]["start"]) > 4):
            cues.append(group)
            group = []
        group.append(segment)
    if group:
        cues.append(group)
    srt, vtt = [], ["WEBVTT\n"]
    for index, group in enumerate(cues, 1):
        text = " ".join(part["text"] for part in group)
        # Plain text captions: markup-like source is escaped to remain visible text.
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
        start, end = group[0]["start"], group[-1]["end"]
        srt.append(f"{index}\n{caption_timestamp(start, ',')} --> {caption_timestamp(end, ',')}\n{text}\n")
        vtt.append(f"{caption_timestamp(start, '.')} --> {caption_timestamp(end, '.')}\n{text}\n")
    temp = Path(tempfile.mkdtemp(prefix=f".pending-{key}-", dir=parent))
    for name, text in (("captions.srt", "\n".join(srt)), ("captions.vtt", "\n".join(vtt)),
                       ("alignment.json", json.dumps(alignment, ensure_ascii=False, indent=2))):
        write_bytes(temp / name, text.encode("utf-8"))
    temp.rename(target)
    return {"directory": str(target), "caption_sha256": key, "cues": len(cues), "external_calls": 0}


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise NarrationError("Cannot read a valid JSON input file.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fingerprint = commands.add_parser("fingerprint", help="Hash the complete request offline")
    fingerprint.add_argument("request")
    estimate = commands.add_parser("plan", help="Offline dry-run and evidenced cost estimate")
    estimate.add_argument("request")
    estimate.add_argument("quote")
    generate = commands.add_parser("generate", help="Dry-run unless --execute is explicitly set")
    generate.add_argument("request")
    generate.add_argument("quote")
    generate.add_argument("--approval")
    generate.add_argument("--output-dir", required=True)
    generate.add_argument("--execute", action="store_true")
    generate.add_argument("--provider-profile", help="Private AI33 preset/download-host evidence JSON")
    existing = commands.add_parser("import-audio", help="Immutable local existing_audio fallback; no API")
    existing.add_argument("audio")
    existing.add_argument("--text-file", required=True)
    existing.add_argument("--output-dir", required=True)
    captions = commands.add_parser("captions", help="Export captions separately from real alignment")
    captions.add_argument("alignment")
    captions.add_argument("--output-dir", required=True)
    captions.add_argument("--max-chars", type=int, default=42)
    args = parser.parse_args()
    try:
        if args.command == "fingerprint":
            output = {"request_sha256": validate_request(load(args.request)), "external_calls": 0}
        elif args.command == "plan":
            output = plan(load(args.request), load(args.quote))
        elif args.command == "captions":
            output = export_captions(load(args.alignment), args.output_dir, args.max_chars)
        elif args.command == "import-audio":
            output = import_existing_audio(args.audio, Path(args.text_file).read_text(encoding="utf-8"), args.output_dir)
        else:
            request, quote = load(args.request), load(args.quote)
            approval = load(args.approval) if args.approval else None
            adapter = None
            if args.execute:
                from narration_providers import get_adapter
                adapter = get_adapter(request["provider"], load(args.provider_profile) if args.provider_profile else None)
            output = execute(request, quote, approval, args.output_dir, adapter, execute_external=args.execute)
        print(json.dumps({"ok": True, **output}, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        message = str(exc) if isinstance(exc, NarrationError) else "Narration operation could not complete safely."
        print(json.dumps({"ok": False, "error": message}))
        return 1


if __name__ == "__main__":
    # The optional adapters import this module's error type when invoked as a script.
    sys.modules["narration"] = sys.modules[__name__]
    raise SystemExit(main())
