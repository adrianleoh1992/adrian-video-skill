"""Transport contracts tested with synthetic responses; never live API calls."""

import base64
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import narration as n
import narration_providers as p
import test_narration as fixtures
from test_narration import request, quote_for, approval_for, wav_bytes

MP3 = b"\xff\xfb\x90\x00" + bytes(413)


class MockClient:
    def __init__(self, responses, downloads=None):
        self.responses = list(responses)
        self.downloads = downloads or {}
        self.calls = 0
        self.seen = []

    def json(self, method, url, credential, **kwargs):
        self.calls += 1
        self.seen.append((method, url, copy.deepcopy(kwargs)))
        if not self.responses:
            raise AssertionError("Unexpected API call")
        return self.responses.pop(0)

    def download(self, url, allowed_hosts):
        if urlsplit(url).hostname not in allowed_hosts:
            raise n.NarrationError("Unreviewed media host")
        self.calls += 1
        self.seen.append(("DOWNLOAD", url, {}))
        return self.downloads[url]


def ai33_request():
    return {"schema_version": 1, "provider": "ai33", "model_id": "provider-default",
            "voice_id": "elevenlabs_preset-a", "voice_mode": "preset", "text": "Halo dunia.",
            "settings": {"speed": 1, "with_transcript": True}, "output_format": "provider-default"}


def profile():
    return {"provider": "ai33", "voice_provider": "elevenlabs",
            "preset_voice_ids": ["elevenlabs_preset-a"], "preset_evidence": "synthetic verified preset record",
            "download_hosts": ["media.example.invalid"]}


class ProviderTests(unittest.TestCase):
    def test_eleven_runtime_catalog_and_timestamp_request(self):
        req = request()
        req.update(provider="elevenlabs", output_format="mp3_44100_128", settings={"voice_settings": {"stability": 0.5}})
        chars = {"characters": list("Hi all"), "character_start_times_seconds": [0, .1, .2, .3, .4, .5],
                 "character_end_times_seconds": [.1, .2, .3, .4, .5, .6]}
        client = MockClient([([{"model_id": "model-a", "can_do_text_to_speech": True, "maximum_text_length_per_request": 100}], {}),
                             ({"voices": [{"voice_id": "preset-a", "category": "premade"}]}, {}),
                             ({"audio_base64": base64.b64encode(MP3).decode(), "alignment": chars}, {"request-id": "job-1"})])
        adapter = p.ElevenLabsAdapter(client)
        adapter.verify_request(req)
        jobs = []
        result = adapter.synthesize(req, "synthetic-key", jobs.append)
        self.assertEqual(jobs, ["job-1"])
        self.assertEqual([segment["text"] for segment in result["alignment"]["segments"]], ["Hi", "all"])
        self.assertEqual(client.seen[-1][0], "POST")
        self.assertIn("/v1/text-to-speech/preset-a/with-timestamps?output_format=mp3_44100_128", client.seen[-1][1])
        self.assertEqual(client.seen[-1][2]["payload"], {"text": req["text"], "model_id": "model-a", "voice_settings": {"stability": .5}})

    def test_eleven_cloned_voice_never_reaches_synthesis(self):
        req = request()
        client = MockClient([([{"model_id": "model-a", "can_do_text_to_speech": True}], {}),
                             ({"voices": [{"voice_id": "preset-a", "category": "cloned"}]}, {})])
        with self.assertRaises(n.NarrationError):
            p.ElevenLabsAdapter(client).synthesize(req, "synthetic", lambda _: None)
        self.assertFalse(any(row[0] == "POST" for row in client.seen))

    def test_ai33_exact_fields_job_cost_and_raw_sidecars(self):
        media = {"audio_url": "https://media.example.invalid/audio.mp3", "srt_url": "https://media.example.invalid/text.srt",
                 "json_url": "https://media.example.invalid/timing.json"}
        client = MockClient([({"success": True, "data": [{"voice_id": "elevenlabs_preset-a"}], "pagination": {"has_more": False}}, {}),
                             ({"success": True, "task_id": "task-1"}, {}),
                             ({"status": "done", "credit_cost": 2, "metadata": media}, {})],
                            {media["audio_url"]: (MP3, {"content-type": "audio/mpeg"}),
                             media["srt_url"]: (b"1\n00:00:00,000 --> 00:00:01,000\nHi\n", {}),
                             media["json_url"]: (b'{"unknown_vendor_schema":true}', {})})
        adapter = p.AI33Adapter(profile(), client, sleep=lambda _: None)
        req = ai33_request()
        adapter.verify_request(req)
        jobs = []
        result = adapter.synthesize(req, "synthetic-key", jobs.append)
        self.assertEqual(jobs, ["task-1"])
        self.assertEqual(result["reported_cost"], 2)
        self.assertIsNone(result["alignment"])
        self.assertIn("provider-alignment.json", result["provider_documents"])
        post = next(row for row in client.seen if row[0] == "POST")
        self.assertEqual(post[2]["multipart"], {"text": req["text"], "voice_id": req["voice_id"], "speed": "1", "with_transcript": "true"})
        self.assertNotIn("model_id", post[2]["multipart"])

    def test_ai33_clone_and_unsupported_model_are_rejected(self):
        adapter = p.AI33Adapter(profile(), MockClient([]))
        for field, value in (("voice_id", "clone_someone"), ("model_id", "eleven_v3"), ("output_format", "mp3_44100_128")):
            req = ai33_request()
            req[field] = value
            with self.assertRaises(n.NarrationError):
                adapter.verify_request(req)

    def test_ai33_pending_task_does_not_repeat_post(self):
        client = MockClient([({"data": [{"voice_id": "elevenlabs_preset-a"}]}, {}),
                             ({"task_id": "task-1"}, {}), ({"status": "doing"}, {}), ({"status": "doing"}, {})])
        jobs = []
        with self.assertRaises(n.NarrationError):
            p.AI33Adapter(profile(), client, sleep=lambda _: None, max_polls=2).synthesize(ai33_request(), "synthetic", jobs.append)
        self.assertEqual(jobs, ["task-1"])
        self.assertEqual(sum(row[0] == "POST" for row in client.seen), 1)

    def test_credentials_never_go_to_download_or_redirect_hosts(self):
        client = p.HttpClient("api.ai33.pro")
        with self.assertRaises(n.NarrationError):
            client.request("GET", "https://media.example.invalid/file", credential="synthetic")
        with self.assertRaises(n.NarrationError):
            client.download("https://unreviewed.example.invalid/file", ["media.example.invalid"])
        self.assertEqual(client.calls, 0)
        self.assertIsNone(p.NoRedirect().redirect_request(None, None, 302, None, None, "https://elsewhere.invalid"))

    def test_registry_does_not_alias_unconfirmed_provider_spelling(self):
        with self.assertRaises(n.NarrationError):
            p.get_adapter("aipro33")
        adapter = p.get_adapter("ai33", profile())
        self.assertEqual(adapter.client.calls, 0)

    def test_error_bodies_cannot_be_cached_as_audio(self):
        for payload, extension in ((b"<html>error</html>", "mp3"), (b'{"error":"quota"}', "wav"), (b"ID3empty", "mp3")):
            with self.assertRaises(n.NarrationError):
                n.validate_audio_bytes(payload, extension)


class FallbackTests(unittest.TestCase):
    setUp = fixtures.NarrationTests.setUp
    run_audio = fixtures.NarrationTests.run_audio
    def test_existing_audio_is_local_immutable_and_cache_verified(self):
        audio = Path(self.temp.name) / "provided.wav"
        audio.write_bytes(wav_bytes())
        result = n.import_existing_audio(audio, "Supplied transcript", self.out)
        self.assertEqual(result["external_calls"], 0)
        self.assertEqual(result["receipt"]["provider"], "existing_audio")
        self.assertTrue(n.import_existing_audio(audio, "Supplied transcript", self.out)["cache_hit"])
        self.assertEqual((Path(result["directory"]) / "audio.wav").read_bytes(), audio.read_bytes())

    def test_supplied_recording_cli_never_loads_provider_and_preserves_bytes(self):
        import builtins
        audio = Path(self.temp.name) / "supplied.wav"
        transcript = Path(self.temp.name) / "spoken.txt"
        original = wav_bytes()
        audio.write_bytes(original)
        transcript.write_text("Words actually supplied in this synthetic recording test.")
        original_import = builtins.__import__
        def local_only(name, *args, **kwargs):
            if name == "narration_providers":
                raise AssertionError("A supplied-recording import must not load a provider adapter")
            return original_import(name, *args, **kwargs)
        stdout = io.StringIO()
        argv = ["narration.py", "import-audio", str(audio), "--text-file", str(transcript), "--output-dir", str(self.out)]
        with patch.object(sys, "argv", argv), patch("builtins.__import__", side_effect=local_only), redirect_stdout(stdout):
            self.assertEqual(n.main(), 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["external_calls"], 0)
        self.assertEqual(result["receipt"]["provider"], "existing_audio")
        self.assertEqual(audio.read_bytes(), original)
        self.assertEqual((Path(result["directory"]) / "audio.wav").read_bytes(), original)
        self.assertFalse((self.out / "attempts").exists())

    def test_ai33_quote_unit_is_checked_before_credential_lookup(self):
        from test_narration import NeverReadCredentials
        req = ai33_request()
        quoted = quote_for(req)
        quoted["unit"] = "USD"
        approval = approval_for(req, quoted)
        with self.assertRaises(n.NarrationError):
            self.run_audio(request=req, quote=quoted, approval=approval,
                           adapter=p.AI33Adapter(profile(), MockClient([])), environ=NeverReadCredentials())


if __name__ == "__main__":
    unittest.main()
