# Release staging contract

Use a newly selected staging directory containing only the intended release. Do not point this checker at a home directory, live credential store, or another user's project. The checker reads every staged file; provide a clean scope. It does not modify files or call GitHub.

Store the release manifest outside staging, so it does not need to hash itself:

```json
{
  "schema_version": 1,
  "visibility": "private",
  "approval_ref": "record naming the approved repository owner/name/visibility",
  "files": [
    {
      "path": "SKILL.md",
      "kind": "documentation",
      "sha256": "actual lowercase SHA-256 of the staged bytes",
      "rights": "Original instructions; release authorized by the author.",
      "redistribution_allowed": true,
      "contains_raw_identity_reference": false,
      "contains_generated_likeness": false
    }
  ]
}
```

Each regular file must appear exactly once, with a slash-separated relative path and its exact hash. Kinds are `source`, `documentation`, `generated_media`, or `licensed_media`. Source and documentation must be UTF-8 text. Media needs explicit classification and rights evidence. Generated media containing the subject's likeness additionally needs `likeness_distribution_approval_ref` covering this repository and visibility. Raw face/voice reference files are excluded from GitHub regardless of public availability. This checker cannot visually recognize them: truthful classification and human review are essential.

```bash
python3 scripts/check_release.py /path/to/staging /path/to/release-manifest.json
```

The checker rejects missing/extra files, changed hashes, unsafe relative paths, symlinks, known private directories and credential filenames, raw-reference declarations, common high-confidence token patterns across file bytes, unclassified media, and archives that hide unreviewed contents. Expand archives into staging first. It withholds detected secret values from output. Encoded or encrypted secrets and compressed metadata can evade this limited pattern scan.

The checker does **not** prove copyright ownership, validate licenses, find every secret, inspect image/video metadata, recognize raw identity photos, inspect Git history, or authorize publication. An allowed media suffix does not prove the bytes are valid media. Manually inspect media and metadata, licensing, and the exact publishing diff; keep private consent records outside the payload. Prefer releasing the generic skill alone. Avoid claiming a new public license until the owner selects one. Preserve any required notices when code or assets are actually reused.

Before an external release, ensure the repository owner/name/visibility match the user's choice, all files are included deliberately, no ignored or deleted secret persists in Git history, and generated likeness distribution is within scope. A private repository is still external distribution.
