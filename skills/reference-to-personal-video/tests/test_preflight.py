"""Observable authorization and release-boundary tests; standard library only."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


production = load("validate_manifest")
release = load("check_release")


def approved_manifest():
    data = json.loads((ROOT / "assets" / "production-manifest.example.json").read_text())
    data["assets"] = [{"id": "face-01", "role": "face_reference", "source_type": "user_upload",
                       "owner": "@example_subject", "privacy": "private", "rights_basis": "user_owned",
                       "github_allowed": False}]
    data["identity"] = {"subject_handle": "@example_subject", "status": "confirmed",
                        "selected_asset_ids": ["face-01"], "confirmation_ref": "test-record-01",
                        "provider_upload_allowed": True, "voice_clone_allowed": False}
    data["generation"] = {"unit": "credits", "spent": "0", "plan": [
        {"id": "intro", "provider": "Provider / account-alias", "model": "Model A",
         "settings": {"duration_seconds": 8, "aspect_ratio": "9:16"}, "quantity": 2,
         "max_attempts": 1, "unit_cost": "20", "price_evidence": "test-price-record",
         "price_checked_at": "2026-10-02T10:00:00Z"}],
        "approval": {"unit": "credits", "cap": "40", "confirmation_ref": "test-record-02"}}
    data["generation"]["approval"]["plan_sha256"] = production.plan_hash(data["generation"]["plan"])
    return data


def video(shortcode="Example01", status="observed"):
    return {"id": shortcode, "url": f"https://www.instagram.com/reel/{shortcode}/",
            "creator": "@example_creator", "published_at": "2026-10-01T10:00:00Z",
            "date_evidence": "test post timestamp", "retrieved_at": "2026-10-02T10:00:00Z",
            "status": status, "evidence": "test audit record"}


class ManifestTests(unittest.TestCase):
    def test_example_is_honest_incomplete_audit_but_not_generation_ready(self):
        data = json.loads((ROOT / "assets" / "production-manifest.example.json").read_text())
        self.assertEqual(production.validate(data, "audit"), [])
        self.assertTrue(production.validate(data, "generate"))

    def test_approved_exact_plan_passes(self):
        self.assertEqual(production.validate(approved_manifest(), "generate"), [])

    def test_model_and_settings_changes_invalidate_approval(self):
        for field, value in [("model", "Model B"), ("settings", {"duration_seconds": 16})]:
            data = approved_manifest()
            data["generation"]["plan"][0][field] = value
            self.assertIn("budget approval plan fingerprint is stale", production.validate(data, "generate"))

    def test_retry_cost_and_already_spent_are_counted(self):
        data = approved_manifest()
        data["generation"]["plan"][0]["max_attempts"] = 2
        data["generation"]["approval"]["plan_sha256"] = production.plan_hash(data["generation"]["plan"])
        self.assertTrue(any("exceeds" in error for error in production.validate(data, "generate")))
        data = approved_manifest()
        data["generation"]["spent"] = "0.01"
        self.assertTrue(any("exceeds" in error for error in production.validate(data, "generate")))

    def test_zero_cost_does_not_skip_existing_approval_validation(self):
        data = approved_manifest()
        data["generation"]["plan"][0]["unit_cost"] = 0
        data["generation"]["spent"] = 100
        errors = production.validate(data, "generate")
        self.assertTrue(any("fingerprint" in error for error in errors))
        self.assertTrue(any("exceeds" in error for error in errors))

    def test_evidenced_free_plan_needs_identity_but_no_paid_approval(self):
        data = approved_manifest()
        data["generation"]["plan"][0]["unit_cost"] = 0
        data["generation"]["approval"] = None
        self.assertEqual(production.validate(data, "generate"), [])
        data["identity"]["status"] = "pending"
        self.assertTrue(production.validate(data, "generate"))

    def test_nonfinite_negative_boolean_or_missing_costs_fail(self):
        for cost in ("NaN", "Infinity", -1, True, None):
            data = approved_manifest()
            data["generation"]["plan"][0]["unit_cost"] = cost
            self.assertTrue(production.validate(data, "generate"), str(cost))

    def test_wrong_owner_and_missing_upload_permission_fail(self):
        data = approved_manifest()
        data["assets"][0]["owner"] = "@someone_else"
        data["identity"]["provider_upload_allowed"] = False
        errors = production.validate(data, "generate")
        self.assertTrue(any("owner" in error for error in errors))
        self.assertTrue(any("upload" in error for error in errors))

    def test_public_raw_face_is_still_not_github_safe(self):
        data = approved_manifest()
        data["assets"][0].update(privacy="public", github_allowed=True)
        self.assertTrue(any("GitHub" in error for error in production.validate(data)))

    def test_latest_sample_rejects_duplicates_partial_and_unknown_dates(self):
        data = approved_manifest()
        data["sample"] = {"creator": "@example_creator", "requested_count": 2, "claimed_complete": True,
                          "coverage_evidence": "test chronological observation"}
        data["references"] = [video(), video("Example02", "partial")]
        self.assertTrue(any("enough" in error for error in production.validate(data)))
        data["references"][1] = video("Example02")
        data["references"][1]["published_at"] = None
        self.assertTrue(any("enough" in error for error in production.validate(data)))
        data["references"][1] = copy.deepcopy(data["references"][0])
        data["references"][1]["id"] = "different-id"
        data["references"][1]["url"] = data["references"][1]["url"].replace("www.", "")
        self.assertTrue(any("duplicates" in error for error in production.validate(data)))

    def test_complete_sample_requires_coverage_beyond_count(self):
        data = approved_manifest()
        data["references"] = [video()]
        data["sample"] = {"creator": "@example_creator", "requested_count": 1, "claimed_complete": True, "coverage_evidence": ""}
        self.assertTrue(any("coverage" in error for error in production.validate(data)))

    def test_other_creators_cannot_fill_the_requested_sample(self):
        data = approved_manifest()
        data["references"] = [video()]
        data["sample"] = {"creator": "@another_creator", "requested_count": 1,
                          "claimed_complete": True, "coverage_evidence": "test observation"}
        self.assertTrue(any("enough" in error for error in production.validate(data)))

    def test_spoofed_instagram_domains_do_not_count(self):
        self.assertFalse(production.instagram_permalink("https://instagram.com.attacker.test/reel/Example01/"))
        self.assertFalse(production.instagram_permalink("https://instagram.com@attacker.test/reel/Example01/"))
        self.assertFalse(production.instagram_permalink("https://www.instagram.com/reel/Example01/?tracker=1"))

    def test_cli_fails_closed_on_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text('{"schema_version": 1, "references": "invalid"}')
            result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_manifest.py"), str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["ok"])


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "staging"
        self.root.mkdir()
        (self.root / "SKILL.md").write_text("Original safe instructions.\n", encoding="utf-8")
        self.manifest = {"schema_version": 1, "visibility": "private", "approval_ref": "test-release-record",
                         "files": [self.entry("SKILL.md")]}

    def entry(self, relative, kind="documentation"):
        return {"path": relative, "sha256": release.sha256(self.root / relative), "kind": kind,
                "rights": "Original test data", "redistribution_allowed": True,
                "contains_raw_identity_reference": False, "contains_generated_likeness": False}

    def test_exact_clean_staging_passes(self):
        self.assertEqual(release.scan(self.root, self.manifest), [])

    def test_changed_or_undeclared_file_fails(self):
        (self.root / "SKILL.md").write_text("Changed after approval")
        (self.root / "extra.txt").write_text("Unexpected")
        errors = release.scan(self.root, self.manifest)
        self.assertTrue(any("hash mismatch" in error for error in errors))
        self.assertTrue(any("undeclared" in error for error in errors))

    def test_raw_reference_or_unapproved_likeness_fails(self):
        self.manifest["files"][0]["contains_raw_identity_reference"] = True
        self.assertTrue(release.scan(self.root, self.manifest))
        self.manifest["files"][0]["contains_raw_identity_reference"] = False
        self.manifest["files"][0]["contains_generated_likeness"] = True
        self.assertTrue(release.scan(self.root, self.manifest))

    def test_credentials_in_text_and_media_are_withheld(self):
        token = "gh" + "p_" + "A" * 36
        for filename, kind in (("notes.txt", "documentation"), ("poster.png", "licensed_media")):
            path = self.root / filename
            path.write_bytes(token.encode())
            self.manifest["files"].append(self.entry(filename, kind))
        errors = release.scan(self.root, self.manifest)
        self.assertEqual(sum("credential detected" in error for error in errors), 2)
        self.assertNotIn(token, "\n".join(errors))

    def test_symlink_escape_fails_without_reading_target(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("Private external text")
        (self.root / "linked.txt").symlink_to(outside)
        self.assertTrue(any("symlink" in error for error in release.scan(self.root, self.manifest)))

    def test_private_directories_and_env_files_fail_even_if_allowlisted(self):
        (self.root / "private").mkdir()
        (self.root / "private" / "photo.txt").write_text("Do not publish")
        (self.root / ".env").write_text("CONFIG=not-secret")
        self.manifest["files"] += [self.entry("private/photo.txt"), self.entry(".env")]
        errors = release.scan(self.root, self.manifest)
        self.assertTrue(any("private/cache" in error for error in errors))
        self.assertTrue(any("file name" in error for error in errors))

    def test_path_traversal_and_archives_fail(self):
        for relative in ("../outside", "/absolute", "folder\\file", "./file"):
            self.assertFalse(release.safe_relative(relative))
        (self.root / "hidden.zip").write_bytes(b"PK\x03\x04")
        self.manifest["files"].append(self.entry("hidden.zip", "licensed_media"))
        self.assertTrue(any("archive" in error for error in release.scan(self.root, self.manifest)))

    def test_visibility_must_be_resolved(self):
        self.manifest["visibility"] = "undecided"
        self.assertTrue(any("visibility" in error for error in release.scan(self.root, self.manifest)))


if __name__ == "__main__":
    unittest.main()
