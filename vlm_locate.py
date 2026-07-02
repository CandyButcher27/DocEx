import base64
import json
import os
import re
import time
from io import BytesIO

import requests
from dotenv import load_dotenv

from ocr_engine import render_pages, ocr_image

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _tokens(s):
    return set(t for t in re.sub(r"[^a-z0-9]", " ", str(s).lower()).split() if t)


def _prompt(labels):
    listing = "\n".join(f"- {a}" for a in labels)
    return (
        "You are a layout locator for a scanned form. For each requested field, return the bounding box of the "
        "region where that field's VALUE is written (the area to the right of / below the printed label). "
        "DO NOT read, transcribe, or output the text inside the box — only its location.\n"
        'Return ONLY a JSON array: [{"label": "<field label>", "box_2d": [ymin, xmin, ymax, xmax]}], '
        "coordinates normalized to 0-1000. Omit fields you cannot locate.\n\nFields:\n" + listing
    )


def _locate_page(image, labels):
    buf = BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/png", "data": b64}},
            {"text": _prompt(labels)},
        ]}],
        "generationConfig": {"temperature": 0},
    }
    for attempt in range(3):
        resp = requests.post(GEMINI_URL, params={"key": GEMINI_API_KEY}, json=body, timeout=60)
        if resp.status_code == 429 and attempt < 2:
            time.sleep(float(resp.headers.get("Retry-After", 8)))
            continue
        break
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


def vlm_recover(targets, ocr_entries, pdf_path):
    """targets: [{path, label}] (no_output only). VLM returns boxes; Paddle OCR reads each crop. Returns {path: value}."""
    if not targets or not GEMINI_API_KEY:
        return {}
    labels = [t["label"] for t in targets]
    pages = render_pages(pdf_path)
    recovered = {}
    for image in pages:
        w, h = image.size
        try:
            boxes = _locate_page(image, labels)
        except Exception:
            continue
        for b in boxes:
            label = str(b.get("label", "")).strip()
            box = b.get("box_2d")
            if not label or not isinstance(box, list) or len(box) != 4:
                continue
            lt = _tokens(label)
            cands = [(len(lt & _tokens(t["label"])), t) for t in targets if t["path"] not in recovered]
            cands = [(n, t) for n, t in cands if n > 0]
            if not cands:
                continue
            target = max(cands, key=lambda x: x[0])[1]
            ymin, xmin, ymax, xmax = box
            x0, y0 = int(xmin / 1000 * w), int(ymin / 1000 * h)
            x1, y1 = int(xmax / 1000 * w), int(ymax / 1000 * h)
            if x1 - x0 < 6 or y1 - y0 < 6:
                continue
            toks = ocr_image(image.crop((x0, y0, x1, y1)))
            value = " ".join(t["text"].strip() for t in toks if t["text"].strip()).strip()
            if value and len(value) <= 45 and len(value.split()) <= 7:
                recovered[target["path"]] = value
    return recovered
