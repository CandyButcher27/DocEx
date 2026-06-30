from __future__ import annotations

import base64
import json
import re
import time
import urllib.request
from abc import ABC, abstractmethod

import cv2
import numpy as np

from .config import vlm_settings
from .models import FieldSpec, Template
from .phash import dhash
from .textutil import normalize_tokens


def _encode(image: np.ndarray, max_side: int = 1600) -> str:
    h, w = image.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode()


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    starts = [i for i in (text.find("["), text.find("{")) if i >= 0]
    if not starts:
        raise ValueError("no JSON found")
    i = min(starts)
    close = "]" if text[i] == "[" else "}"
    j = text.rfind(close)
    return json.loads(text[i:j + 1])


class VLMClient(ABC):
    name = "vlm"

    @abstractmethod
    def extract_fields(self, image: np.ndarray, fields: list[FieldSpec]) -> dict:
        ...

    @abstractmethod
    def detect_format(self, image: np.ndarray, page_text: str) -> Template:
        ...


class FakeVLM(VLMClient):
    name = "fake"

    def extract_fields(self, image, fields):
        return {}

    def detect_format(self, image, page_text):
        sig = list(dict.fromkeys(normalize_tokens(page_text)))[:8]
        return Template("vlm_generated", "VLM-generated (fake)", sig, [],
                        phash=dhash(image), source="vlm_fake")


class GeminiVLM(VLMClient):
    name = "gemini"

    def __init__(self, key: str, model: str):
        self.key = key
        self.model = model

    def _call(self, prompt: str, image: np.ndarray, retries: int = 4) -> str:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.key}")
        body = json.dumps({
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": _encode(image)}},
            ]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 8192,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }).encode()
        last = ""
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
                r = json.load(urllib.request.urlopen(req, timeout=90))
                return r["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}"
                if e.code in (429, 503, 500) and attempt < retries - 1:
                    time.sleep(8 * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last = str(e)
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                raise
        raise RuntimeError(f"gemini call failed: {last}")

    def extract_fields(self, image, fields):
        spec_lines = "\n".join(
            f"- {f.name} (type={f.datatype}): printed label is '{f.anchors[0]}'"
            for f in fields)
        prompt = (
            "You are reading a filled insurance enrolment form (handwriting + print). "
            "Extract the value the applicant wrote for each field below. "
            "Read handwriting carefully. If a field is blank or unreadable, use an empty "
            "string. For PAN use format AAAAA9999A. For dates use DD-MM-YYYY. For numbers "
            "return digits only.\n\nFields:\n" + spec_lines +
            '\n\nReturn ONLY a JSON object mapping each field name to '
            '{"value": "<string>", "confidence": <0..1>}. No commentary.')
        try:
            data = _extract_json(self._call(prompt, image))
        except Exception:
            return {}
        out = {}
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    out[k] = {"value": str(v.get("value", "")).strip(),
                              "confidence": float(v.get("confidence", 0.7) or 0.0)}
                else:
                    out[k] = {"value": str(v).strip(), "confidence": 0.7}
        return out

    def detect_format(self, image, page_text):
        prompt = (
            "Analyze this form image. Identify every data field a user fills in. "
            "For each field return: name (snake_case), label (exact printed label text), "
            "value_region (one of: right, below), datatype (one of: text, number, date, "
            "pan, choice). Ignore section headers and instructions. "
            "Return ONLY a JSON array of objects with keys name,label,value_region,datatype.")
        try:
            data = _extract_json(self._call(prompt, image))
        except Exception:
            data = []
        fields: list[FieldSpec] = []
        for d in data if isinstance(data, list) else []:
            name = normalize_tokens(str(d.get("name", "")))
            name = "_".join(name) if name else None
            label = str(d.get("label", "")).strip()
            if not name or not label:
                continue
            dt = str(d.get("datatype", "text")).lower()
            if dt not in ("text", "number", "date", "pan"):
                continue  # skip checkbox/option fields: anchor extraction needs a written value
            vr = str(d.get("value_region", "right")).lower()
            if vr not in ("right", "below", "right_then_below"):
                vr = "right"
            fields.append(FieldSpec(name=name, anchors=[label], value_region=vr, datatype=dt))
        seen, uniq = set(), []
        for f in fields:
            if f.name in seen:
                continue
            seen.add(f.name)
            uniq.append(f)
        fields = uniq[:40]
        sig = [f.anchors[0] for f in fields[:8]] or \
            list(dict.fromkeys(normalize_tokens(page_text)))[:8]
        return Template("vlm_generated", "VLM-generated", sig, fields,
                        phash=dhash(image), source="vlm_gemini")


class OllamaVLM(VLMClient):
    name = "ollama"

    def __init__(self, key: str, base: str, model: str):
        self.key, self.base, self.model = key, base, model

    def _call(self, prompt: str, image: np.ndarray) -> str:
        url = f"{self.base.rstrip('/')}/chat/completions"
        data_uri = "data:image/png;base64," + _encode(image)
        body = json.dumps({
            "model": self.model,
            "temperature": 0,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]}],
        }).encode()
        req = urllib.request.Request(url, body, {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}"})
        r = json.load(urllib.request.urlopen(req, timeout=120))
        return r["choices"][0]["message"]["content"]

    extract_fields = GeminiVLM.extract_fields
    detect_format = GeminiVLM.detect_format


def get_vlm() -> VLMClient:
    s = vlm_settings()
    if s["provider"] == "gemini" and s["gemini_key"]:
        return GeminiVLM(s["gemini_key"], s["gemini_model"])
    if s["provider"] == "ollama" and s["ollama_key"]:
        return OllamaVLM(s["ollama_key"], s["ollama_base"], s["ollama_model"])
    return FakeVLM()


# Backwards-compatible alias used by the decision engine / tests.
StubVLM = FakeVLM
