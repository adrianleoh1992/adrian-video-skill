"""Offline narration boundary tests; fake adapters only, no credentials or network."""

import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import narration as n

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)


def request():
    return {"schema_version": 1, "provider": "fake-provider", "model_id": "model-a",
            "voice_id": "preset-a", "voice_mode": "preset", "text": "Halo dunia.",
            "settings": {"speed": 1}, "output_format": "wav"}


def quote_for(req):
    return {"request_sha256": n.validate_request(req), "provider": req["provider"],
            "account_alias": "synthetic-account", "unit": "credits", "maximum_cost": "2",
            "price_evidence": "Synthetic quote, not provider pricing", "max_attempts": 1,
            "checked_at": "2026-10-02T11:00:00Z", "expires_at": "2026-10-03T11:00:00Z"}


def approval_for(req, quote):
    return {"approved": True, "request_sha256": n.validate_request(req), "quote_sha256": n.digest(quote),
            "provider": req["provider"], "account_alias": quote["account_alias"], "unit": quote["unit"],
            "cap": "4", "already_spent": "0", "budget_id": "synthetic-budget",
            "confirmation_ref": "synthetic-approval", "allow_text_upload": True,
            "expires_at": "2026-10-03T11:00:00Z"}


def alignment():
    return {"schema_version": 1, "source": "provider", "unit": "seconds",
            "segments": [{"text": "Halo", "start": 0, "end": 0.4},
                         {"text": "dunia.", "start": 0.4, "end": 0.8}]}


def wav_bytes():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x00" * 80)
    return stream.getvalue()


class FakeAdapter:
    provider = "fake-provider"
    credential_env = "FAKE_NARRATION_KEY"

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail
        self.verified = 0

    def verify_request(self, req):
        self.verified += 1
        if req["voice_id"] != "preset-a":
            raise n.NarrationError("Unknown preset")

    def synthesize(self, req, credential, record_job):
        self.calls += 1
        record_job(f"synthetic-job-{n.digest(req)[:8]}")
        if self.fail:
            raise TimeoutError("Potentially sensitive provider error: " + credential)
        return {"audio": wav_bytes(), "extension": "wav", "mime_type": "audio/wav",
                "request_id": "synthetic-job", "alignment": alignment(), "reported_cost": "2"}


class NeverReadCredentials(dict):
    def get(self, key, default=None):
        raise AssertionError("Credential lookup was not allowed")


class NarrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "private-output"
        self.req = request()
        self.quote = quote_for(self.req)
        self.approval = approval_for(self.req, self.quote)
        self.adapter = FakeAdapter()
        self.env = {"FAKE_NARRATION_KEY": "synthetic-secret-do-not-record"}

    def run_audio(self, **changes):
        args = dict(request=self.req, quote=self.quote, approval=self.approval,
                    output_dir=self.out, adapter=self.adapter, execute_external=True,
                    environ=self.env, now=NOW)
        args.update(changes)
        return n.execute(**args)

    def test_full_request_cache_identity_preserves_text_and_settings(self):
        baseline = n.validate_request(self.req)
        for key, value in (("provider", "another"), ("model_id", "model-b"), ("voice_id", "preset-b"),
                           ("text", "Halo\ndunia."), ("settings", {"speed": 1.1}), ("output_format", "mp3")):
            changed = copy.deepcopy(self.req)
            changed[key] = value
            self.assertNotEqual(n.validate_request(changed), baseline)
        self.assertEqual(n.validate_request(dict(reversed(list(self.req.items())))), baseline)
        one, two = copy.deepcopy(self.req), copy.deepcopy(self.req)
        one["text"], two["text"] = "café", "cafe\u0301"
        self.assertNotEqual(n.validate_request(one), n.validate_request(two))

    def test_dry_run_never_reads_key_or_writes_or_invokes_adapter(self):
        result = self.run_audio(execute_external=False, environ=NeverReadCredentials())
        self.assertTrue(result["dry_run"])
        self.assertEqual(self.adapter.calls, 0)
        self.assertEqual(self.adapter.verified, 0)
        self.assertFalse(self.out.exists())

    def test_stale_or_missing_approval_rejects_before_key_lookup(self):
        for field, value in (("approved", False), ("request_sha256", "wrong"),
                             ("quote_sha256", "wrong"), ("unit", "USD"),
                             ("allow_text_upload", False), ("expires_at", "2026-10-01T12:00:00Z")):
            changed = copy.deepcopy(self.approval)
            changed[field] = value
            with self.assertRaises(n.NarrationError):
                self.run_audio(approval=changed, environ=NeverReadCredentials())
        self.assertEqual(self.adapter.calls, 0)

    def test_changed_quote_and_expiry_are_rejected(self):
        for field, value in (("maximum_cost", "1"), ("price_evidence", "changed"),
                             ("expires_at", "2026-10-01T12:00:00Z"), ("max_attempts", 2)):
            changed = copy.deepcopy(self.quote)
            changed[field] = value
            with self.assertRaises(n.NarrationError):
                self.run_audio(quote=changed, environ=NeverReadCredentials())

    def test_invalid_costs_and_over_cap_fail(self):
        for value in ("NaN", "Infinity", -1, True, None):
            changed = copy.deepcopy(self.quote)
            changed["maximum_cost"] = value
            with self.assertRaises(n.NarrationError):
                n.plan(self.req, changed, NOW)
        self.approval.update(cap="2", already_spent="0.0001")
        with self.assertRaises(n.NarrationError):
            self.run_audio(environ=NeverReadCredentials())
        self.approval["already_spent"] = "0"
        self.assertFalse(self.run_audio()["cache_hit"])

    def test_free_external_calls_still_need_approval(self):
        self.quote["maximum_cost"] = "0"
        with self.assertRaises(n.NarrationError):
            self.run_audio(approval=None, environ=NeverReadCredentials())

    def test_success_is_immutable_and_reuse_needs_no_credentials(self):
        result = self.run_audio()
        cache = Path(result["directory"])
        self.assertTrue((cache / "audio.wav").is_file())
        self.assertTrue((cache / "alignment.json").is_file())
        self.assertTrue((cache / "narration.txt").is_file())
        again = self.run_audio(approval=None, environ=NeverReadCredentials())
        self.assertTrue(again["cache_hit"])
        self.assertEqual(self.adapter.calls, 1)
        all_text = "".join(path.read_text() for path in self.out.rglob("*.json"))
        self.assertNotIn(self.env["FAKE_NARRATION_KEY"], all_text)

    def test_corrupt_cache_is_not_replaced_or_resynthesized(self):
        result = self.run_audio()
        audio = Path(result["directory"]) / "audio.wav"
        audio.chmod(0o600)
        audio.write_bytes(b"changed")
        with self.assertRaises(n.NarrationError):
            self.run_audio()
        self.assertEqual(self.adapter.calls, 1)
        self.assertEqual(audio.read_bytes(), b"changed")

    def test_uncertain_attempt_keeps_job_id_and_blocks_retry(self):
        self.adapter.fail = True
        with self.assertRaises(n.NarrationError) as error:
            self.run_audio()
        self.assertNotIn(self.env["FAKE_NARRATION_KEY"], str(error.exception))
        jobs = list((self.out / "attempts").glob("*.job.json"))
        self.assertEqual(len(jobs), 1)
        with self.assertRaises(n.NarrationError):
            self.run_audio()
        self.assertEqual(self.adapter.calls, 1)

    def test_distinct_requests_share_budget_reservations(self):
        self.approval["cap"] = "3"
        self.run_audio()
        other = request()
        other["text"] = "Kalimat kedua."
        quote = quote_for(other)
        approval = approval_for(other, quote)
        approval["cap"] = "3"
        with self.assertRaises(n.NarrationError):
            self.run_audio(request=other, quote=quote, approval=approval)
        self.assertEqual(self.adapter.calls, 1)

    def test_concurrent_identical_request_dispatches_once(self):
        barrier = threading.Barrier(2)
        results = []
        def run():
            barrier.wait()
            try:
                results.append(self.run_audio())
            except n.NarrationError as exc:
                results.append(str(exc))
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(self.adapter.calls, 1)
        self.assertEqual(len(results), 2)

    def test_presets_only_and_credentials_not_in_request(self):
        for field, value in (("voice_mode", "cloned"), ("settings", {"reference_audio": "private.wav"}),
                             ("settings", {"api_key": "synthetic"})):
            changed = copy.deepcopy(self.req)
            changed[field] = value
            with self.assertRaises(n.NarrationError):
                n.validate_request(changed)
        self.req["voice_id"] = "not-a-preset"
        self.quote = quote_for(self.req)
        self.approval = approval_for(self.req, self.quote)
        with self.assertRaises(n.NarrationError):
            self.run_audio(environ=NeverReadCredentials())

    def test_git_output_and_symlink_cache_are_rejected(self):
        repo = Path(self.temp.name) / "repo"
        (repo / ".git").mkdir(parents=True)
        with self.assertRaises(n.NarrationError):
            self.run_audio(output_dir=repo / "private")
        self.out.mkdir()
        other = Path(self.temp.name) / "outside"
        other.mkdir()
        (self.out / "narration").symlink_to(other, target_is_directory=True)
        with self.assertRaises(n.NarrationError):
            self.run_audio()

    def test_captions_are_separate_and_do_not_resynthesize_audio(self):
        audio = self.run_audio()
        audio_hash = (Path(audio["directory"]) / "audio.wav").read_bytes()
        one = n.export_captions(alignment(), self.out, max_chars=10)
        two = n.export_captions(alignment(), self.out, max_chars=42)
        self.assertNotEqual(one["directory"], two["directory"])
        self.assertEqual((Path(audio["directory"]) / "audio.wav").read_bytes(), audio_hash)
        self.assertEqual(self.adapter.calls, 1)
        self.assertTrue((Path(one["directory"]) / "captions.srt").read_text().startswith("1\n00:00:00,000"))
        with self.assertRaises(n.NarrationError):
            n.export_captions(alignment(), self.out, max_chars=42)
        with self.assertRaises(n.NarrationError):
            n.export_captions({"schema_version": 1, "segments": []}, self.out)


if __name__ == "__main__":
    unittest.main()
