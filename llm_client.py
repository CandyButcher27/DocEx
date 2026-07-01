import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"].rstrip("/")
OLLAMA_API_KEY = os.environ["OLLAMA_API_KEY"]
OLLAMA_MODEL = os.environ["OLLAMA_MODEL"]


def run_extraction(ocr_json: dict, prompt: str, model: str = OLLAMA_MODEL) -> str:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(ocr_json)},
    ]
    resp = requests.post(
        f"{OLLAMA_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("ocr_json", help="path to OCR bbox json (from paddle_page_ocr.py)")
    ap.add_argument("--prompt", default="You are given OCR output from a scanned form as JSON. Summarize what fields you see.")
    args = ap.parse_args()

    ocr_data = json.loads(Path(args.ocr_json).read_text())
    output = run_extraction(ocr_data, args.prompt)
    print(output)
