"""Original optional ElevenLabs and AI33 adapters; no automatic HTTP retries."""

import base64
import json
from pathlib import PurePosixPath
import time
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid

from narration import NarrationError, canonical, cost, nonempty, reject_secrets, validate_alignment, validate_audio_bytes


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HttpClient:
    """Bounded HTTPS transport; API credentials never follow redirects."""
    def __init__(self, api_host, timeout=30, maximum_bytes=64 * 1024 * 1024):
        self.api_host, self.timeout, self.maximum_bytes = api_host, timeout, maximum_bytes
        self.calls = 0
        self.opener = build_opener(NoRedirect())

    def request(self, method, url, credential=None, body=None, content_type=None):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port not in {None, 443}:
            raise NarrationError("Provider URLs require HTTPS without embedded credentials.")
        if credential is not None and parts.hostname != self.api_host:
            raise NarrationError("Refusing to send credentials to a non-provider host.")
        headers = {"Accept": "application/json" if credential is not None else "*/*"}
        if credential is not None:
            headers["xi-api-key"] = credential
        if content_type:
            headers["Content-Type"] = content_type
        self.calls += 1
        try:
            with self.opener.open(Request(url, data=body, headers=headers, method=method), timeout=self.timeout) as response:
                data = response.read(self.maximum_bytes + 1)
                if len(data) > self.maximum_bytes:
                    raise NarrationError("Provider response exceeds the byte limit.")
                return data, {key.lower(): value for key, value in response.headers.items()}
        except Exception:
            raise NarrationError("Provider HTTP request failed; response and credential details are withheld.") from None

    def json(self, method, url, credential, payload=None, multipart=None):
        body, content_type = None, None
        if payload is not None:
            body, content_type = canonical(payload), "application/json"
        if multipart is not None:
            boundary = "narration-" + uuid.uuid4().hex
            parts = []
            for key, value in multipart.items():
                if not key.isidentifier():
                    raise NarrationError("Invalid multipart field name.")
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n')
            parts.append(f"--{boundary}--\r\n")
            body, content_type = "".join(parts).encode(), f"multipart/form-data; boundary={boundary}"
        data, headers = self.request(method, url, credential, body, content_type)
        try:
            return json.loads(data), headers
        except (ValueError, UnicodeError):
            raise NarrationError("Provider response was not valid JSON.") from None

    def download(self, url, allowed_hosts):
        if urlsplit(url).hostname not in allowed_hosts:
            raise NarrationError("Returned media host is outside the reviewed download-host allowlist.")
        return self.request("GET", url)


def character_alignment(value):
    """Convert real provider character timing into separate word alignment."""
    if not isinstance(value, dict):
        return None
    chars = value.get("characters")
    starts, ends = value.get("character_start_times_seconds"), value.get("character_end_times_seconds")
    if not isinstance(chars, list) or not isinstance(starts, list) or not isinstance(ends, list) or not (len(chars) == len(starts) == len(ends)):
        raise NarrationError("Provider character alignment arrays do not match.")
    segments, word = [], []
    def finish():
        if word:
            if cost(word[-1][2]) > cost(word[0][1]):
                segments.append({"text": "".join(item[0] for item in word), "start": word[0][1], "end": word[-1][2]})
            word.clear()
    for char, start, end in zip(chars, starts, ends):
        if not isinstance(char, str) or cost(end) < cost(start):
            raise NarrationError("Provider character timing was invalid.")
        if char.isspace():
            finish()
        else:
            word.append((char, start, end))
    finish()
    result = {"schema_version": 1, "source": "provider", "unit": "seconds", "segments": segments}
    validate_alignment(result)
    return result


class ElevenLabsAdapter:
    provider, credential_env = "elevenlabs", "ELEVENLABS_API_KEY"

    def __init__(self, client=None):
        self.client = client or HttpClient("api.elevenlabs.io")

    def verify_request(self, request):
        if set(request["settings"]) - {"voice_settings"} or not isinstance(request["settings"].get("voice_settings", {}), dict):
            raise NarrationError("ElevenLabs settings support only an explicit voice_settings object.")
        if not request["output_format"].startswith("mp3_"):
            raise NarrationError("This adapter currently delivers MP3 output formats only.")

    def synthesize(self, request, credential, record_job):
        base = "https://api.elevenlabs.io"
        models, _ = self.client.json("GET", base + "/v1/models", credential)
        model = next((item for item in models if isinstance(item, dict) and item.get("model_id") == request["model_id"]), None) if isinstance(models, list) else None
        if not model or model.get("can_do_text_to_speech") is not True:
            raise NarrationError("Requested model is not in the current TTS model catalog.")
        maximum = model.get("maximum_text_length_per_request")
        if isinstance(maximum, int) and len(request["text"]) > maximum:
            raise NarrationError("Narration exceeds the selected model's request limit.")
        voices, _ = self.client.json("GET", base + "/v2/voices?" + urlencode({"category": "premade", "page_size": 100}), credential)
        items = voices.get("voices", []) if isinstance(voices, dict) else []
        if not any(isinstance(item, dict) and item.get("voice_id") == request["voice_id"] and item.get("category") == "premade" for item in items):
            raise NarrationError("Voice was not verified as premade in the returned runtime catalog.")
        url = base + "/v1/text-to-speech/" + quote(request["voice_id"], safe="") + "/with-timestamps?" + urlencode({"output_format": request["output_format"]})
        response, headers = self.client.json("POST", url, credential, payload={"text": request["text"], "model_id": request["model_id"], **request["settings"]})
        request_id = headers.get("request-id") or headers.get("x-request-id")
        if request_id:
            record_job(request_id)
        try:
            audio = base64.b64decode(response["audio_base64"], validate=True)
        except (ValueError, KeyError, TypeError):
            raise NarrationError("Provider returned invalid encoded audio.") from None
        validate_audio_bytes(audio, "mp3")
        timing = response.get("normalized_alignment") or response.get("alignment")
        return {"audio": audio, "extension": "mp3", "mime_type": "audio/mpeg", "request_id": request_id,
                "alignment": character_alignment(timing) if timing else None,
                "provider_documents": {"provider-alignment.json": canonical({"alignment": response.get("alignment"), "normalized_alignment": response.get("normalized_alignment")})},
                "external_calls": self.client.calls}


class AI33Adapter:
    provider, credential_env, cost_unit = "ai33", "AI33_API_KEY", "credits"

    def __init__(self, profile, client=None, sleep=time.sleep, max_polls=30):
        self.profile = profile
        self.client = client or HttpClient("api.ai33.pro")
        self.sleep, self.max_polls = sleep, max_polls

    def verify_request(self, request):
        if not isinstance(self.profile, dict) or self.profile.get("provider") != "ai33":
            raise NarrationError("AI33 needs an explicitly selected canonical provider profile.")
        reject_secrets(self.profile)
        for field in ("voice_provider", "preset_evidence"):
            nonempty(self.profile.get(field), field)
        presets = self.profile.get("preset_voice_ids")
        if request["voice_id"].startswith("clone_"):
            raise NarrationError("AI33 clone_ voices are excluded from this preset-only adapter.")
        if not isinstance(presets, list) or request["voice_id"] not in presets:
            raise NarrationError("AI33 voice must be in the verified ordinary-preset allowlist.")
        hosts = self.profile.get("download_hosts")
        if not isinstance(hosts, list) or not hosts or any(not isinstance(host, str) or not host or "/" in host or ":" in host for host in hosts):
            raise NarrationError("AI33 requires an explicit reviewed media-host allowlist.")
        if request["model_id"] != "provider-default" or request["output_format"] != "provider-default":
            raise NarrationError("AI33 v3 chooses its underlying model/format; select provider-default explicitly.")
        if set(request["settings"]) != {"speed", "with_transcript"}:
            raise NarrationError("AI33 settings must explicitly contain speed and with_transcript.")
        if not cost("0.5") <= cost(request["settings"]["speed"]) <= cost("1.5") or type(request["settings"]["with_transcript"]) is not bool:
            raise NarrationError("AI33 speed must be 0.5–1.5 and with_transcript must be boolean.")

    @staticmethod
    def unwrap(value):
        return value["data"] if isinstance(value, dict) and isinstance(value.get("data"), dict) else value

    def synthesize(self, request, credential, record_job):
        base = "https://api.ai33.pro"
        found = False
        for page in range(1, 11):
            voices, _ = self.client.json("GET", base + "/v3/voices?" + urlencode({"provider": self.profile["voice_provider"], "page": page, "page_size": 100}), credential)
            items = voices.get("data", []) if isinstance(voices, dict) else []
            found = isinstance(items, list) and any(isinstance(item, dict) and item.get("voice_id") == request["voice_id"] for item in items)
            if found or not isinstance(voices, dict) or not voices.get("pagination", {}).get("has_more"):
                break
        if not found:
            raise NarrationError("Selected AI33 voice was not returned by the runtime catalog.")
        response, _ = self.client.json("POST", base + "/v3/text-to-speech", credential, multipart={
            "text": request["text"], "voice_id": request["voice_id"], "speed": str(request["settings"]["speed"]),
            "with_transcript": str(request["settings"]["with_transcript"]).lower()})
        response = self.unwrap(response)
        task_id = response.get("task_id") if isinstance(response, dict) else None
        nonempty(task_id, "provider task_id")
        record_job(task_id)
        for index in range(self.max_polls):
            task, _ = self.client.json("GET", base + "/v1/task/" + quote(task_id, safe=""), credential)
            task = self.unwrap(task)
            status = task.get("status") if isinstance(task, dict) else None
            if status == "done":
                break
            if status == "error":
                raise NarrationError("AI33 reported an error; inspect billing before any new attempt.")
            if index + 1 < self.max_polls:
                self.sleep(2)
        else:
            raise NarrationError("AI33 task is pending; reconcile the saved task ID before retrying.")
        media = task.get("metadata", task)
        if not isinstance(media, dict):
            raise NarrationError("AI33 task did not provide media metadata.")
        audio_url = media.get("audio_url")
        nonempty(audio_url, "audio_url")
        audio, headers = self.client.download(audio_url, self.profile["download_hosts"])
        mime = headers.get("content-type", "").split(";")[0].lower()
        if mime and not mime.startswith("audio/") and mime != "application/octet-stream":
            raise NarrationError("AI33 media response is explicitly not audio.")
        ext = {"audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/wav": "wav", "audio/x-wav": "wav", "audio/ogg": "ogg", "audio/flac": "flac", "audio/mp4": "m4a"}.get(mime)
        if not ext:
            ext = PurePosixPath(urlsplit(audio_url).path).suffix.lstrip(".").lower()
        validate_audio_bytes(audio, ext)
        documents = {}
        if request["settings"]["with_transcript"]:
            for field, name in (("srt_url", "provider-captions.srt"), ("json_url", "provider-alignment.json")):
                if media.get(field):
                    data, _ = self.client.download(media[field], self.profile["download_hosts"])
                    if name.endswith(".json"):
                        canonical(json.loads(data))
                    else:
                        data.decode("utf-8")
                    documents[name] = data
        return {"audio": audio, "extension": ext, "mime_type": mime, "request_id": task_id,
                "alignment": None, "provider_documents": documents, "reported_cost": task.get("credit_cost"),
                "external_calls": self.client.calls}


def get_adapter(provider, profile=None):
    if provider == "elevenlabs":
        return ElevenLabsAdapter()
    if provider == "ai33":
        return AI33Adapter(profile)
    if provider == "aipro33":
        raise NarrationError("Select canonical ai33 explicitly after confirming AI33.pro/OpenSpeaker; aliases are not silently routed.")
    raise NarrationError("No verified narration adapter is registered for this provider.")
