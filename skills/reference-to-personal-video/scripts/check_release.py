#!/usr/bin/env python3
"""Read-only allowlist/hash/secret preflight of a separate release staging tree."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    re.compile(rb"(?im)^\s*(?:authorization\s*[:=]\s*bearer|cookie\s*:)\s+\S{12,}"),
)
DENIED_PARTS = {".git", ".aws", ".ssh", ".codex", ".agents", "node_modules",
                "__pycache__", "private", "face-references", "voice-references", "account-state"}
DENIED_NAMES = {"cookies.txt", "cookies.json", "storage-state.json", "credentials", "credentials.json",
                "id_rsa", "id_ed25519", ".ds_store"}
MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".mp4", ".mov", ".webm",
                  ".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".woff", ".woff2", ".ttf", ".otf"}
KINDS = {"source", "documentation", "generated_media", "licensed_media"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def has_secret(path):
    tail = b""
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            window = tail + block
            if any(pattern.search(window) for pattern in SECRET_PATTERNS):
                return True
            tail = window[-4096:]
    return False


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(p not in {".", "..", ""} for p in value.split("/"))


def scan(root, manifest):
    errors = []
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return ["staging root must be an existing real directory"]
    if not isinstance(manifest, dict):
        return ["release manifest must be an object"]
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if manifest.get("visibility") not in {"public", "private"}:
        errors.append("repository visibility must be resolved")
    if not isinstance(manifest.get("approval_ref"), str) or not manifest["approval_ref"].strip():
        errors.append("repository scope approval_ref is required")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        return errors + ["files must be a nonempty explicit allowlist"]
    declared = {}
    for entry in entries:
        if not isinstance(entry, dict) or not safe_relative(entry.get("path")):
            errors.append("each file requires a safe relative path")
            continue
        relative = entry["path"]
        if relative in declared:
            errors.append(f"duplicate declaration: {relative}")
        declared[relative] = entry
        if entry.get("kind") not in KINDS:
            errors.append(f"unsupported or private asset kind: {relative}")
        if entry.get("redistribution_allowed") is not True:
            errors.append(f"redistribution permission missing: {relative}")
        if not isinstance(entry.get("rights"), str) or not entry["rights"].strip():
            errors.append(f"rights/license evidence missing: {relative}")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]):
            errors.append(f"valid SHA-256 required: {relative}")
        if entry.get("contains_raw_identity_reference") is not False:
            errors.append(f"raw identity reference exclusion must be confirmed: {relative}")
        if type(entry.get("contains_generated_likeness")) is not bool:
            errors.append(f"generated likeness classification required: {relative}")
        if entry.get("contains_generated_likeness") is True and not entry.get("likeness_distribution_approval_ref"):
            errors.append(f"generated likeness distribution approval missing: {relative}")
    actual = set()
    # Path.rglob does not recurse into symlink directories; symlinks themselves fail.
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        parts = [part.lower() for part in path.relative_to(root).parts]
        if path.is_symlink():
            errors.append(f"symlinks are not accepted: {relative}")
            continue
        if set(parts) & DENIED_PARTS:
            errors.append(f"private/cache/repository path present: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            errors.append(f"unsupported filesystem entry: {relative}")
            continue
        actual.add(relative)
        name = path.name.lower()
        if name in DENIED_NAMES or name == ".env" or name.startswith(".env.") or path.suffix.lower() in {".key", ".pem", ".p12", ".pfx"}:
            errors.append(f"credential or private file name present: {relative}")
        entry = declared.get(relative)
        if entry is None:
            errors.append(f"undeclared file: {relative}")
            continue
        if sha256(path) != entry.get("sha256"):
            errors.append(f"hash mismatch: {relative}")
        if has_secret(path):
            errors.append(f"possible credential detected (value withheld): {relative}")
        kind = entry.get("kind")
        if path.suffix.lower() in MEDIA_SUFFIXES and kind not in {"generated_media", "licensed_media"}:
            errors.append(f"media needs explicit asset classification: {relative}")
        if kind in {"source", "documentation"}:
            try:
                content = path.read_bytes()
                content.decode("utf-8")
            except UnicodeError:
                errors.append(f"source/documentation must be UTF-8 text: {relative}")
                continue
        elif path.suffix.lower() not in MEDIA_SUFFIXES:
            errors.append(f"unsupported binary/archive type; inspect and stage expanded files: {relative}")
    for missing in sorted(set(declared) - actual):
        errors.append(f"declared file missing: {missing}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        if args.manifest.resolve().is_relative_to(args.staging.resolve()):
            raise ValueError("keep the release manifest outside staging to avoid a self-hash cycle")
        errors = scan(args.staging, json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"ok": not errors, "errors": errors,
                      "limits": "Recorded rights/consent are not independently verified. Manually inspect media, metadata, licenses, and the exact publishing diff."}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
