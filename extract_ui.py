import json
import os
import re
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from urllib.parse import urlparse

from PIL import Image

from ocr_engine import UPLOADS, run_ocr_on_pdf
from llm_client import run_extraction
from field_extractor import extract as extract_template

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(ROOT, "extract_ui.html")

DOCS = {}  # doc_id -> {"pdf_path": str, "filename": str, "ocr": list | None}


def parse_multipart(body, boundary):
    parts = body.split(b"--" + boundary)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        headers = part[:header_end].decode("utf-8", errors="replace")
        content = part[header_end + 4:]
        if content.endswith(b"\r\n"):
            content = content[:-2]
        m = re.search(r'filename="([^"]*)"', headers)
        if m:
            return m.group(1), content
    return None, None


def image_bytes_to_pdf_bytes(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    out = BytesIO()
    img.save(out, format="PDF")
    return out.getvalue()


EXTRACTION_PROMPT = """You are a document field extractor. You are given OCR output from a scanned form as JSON \
(a list of text lines with page, bbox and confidence) and a list of requested field names. \
Find the value for each requested field using the OCR text. \
Respond ONLY with a JSON object mapping each requested field name to its extracted value as a string. \
If a field cannot be found in the document, use "NOT_FOUND" as its value. Do not include any other text."""


def run_llm_extraction(ocr_entries, fields):
    payload = {
        "fields": fields,
        "ocr": ocr_entries,
    }
    raw = run_extraction(payload, EXTRACTION_PROMPT)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {f: "NOT_FOUND" for f in fields}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {f: "NOT_FOUND" for f in fields}
    return {f: str(parsed.get(f, "NOT_FOUND")) for f in fields}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            with open(HTML_FILE, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/upload":
            content_type = self.headers["Content-Type"]
            boundary_match = re.search(r"boundary=(.+)", content_type)
            boundary = boundary_match.group(1).encode()
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)
            filename, content = parse_multipart(body, boundary)
            if not filename:
                self._send_json({"error": "no file found"}, 400)
                return

            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                content = image_bytes_to_pdf_bytes(content)

            doc_id = uuid.uuid4().hex
            pdf_path = os.path.join(UPLOADS, f"{doc_id}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(content)

            DOCS[doc_id] = {"pdf_path": pdf_path, "filename": filename, "ocr": None}
            self._send_json({"doc_id": doc_id, "filename": filename})
            return

        if parsed.path == "/run_ocr":
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))
            doc_id = data["doc_id"]
            doc = DOCS.get(doc_id)
            if not doc:
                self._send_json({"error": "unknown doc_id"}, 404)
                return
            entries = run_ocr_on_pdf(doc["pdf_path"])
            doc["ocr"] = entries
            self._send_json({"lines": len(entries)})
            return

        if parsed.path == "/run_llm":
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))
            doc_id = data["doc_id"]
            fields = data["fields"]
            doc = DOCS.get(doc_id)
            if not doc or doc["ocr"] is None:
                self._send_json({"error": "run /run_ocr first"}, 400)
                return
            results = run_llm_extraction(doc["ocr"], fields)
            self._send_json({"results": results})
            return

        if parsed.path == "/run_template":
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))
            doc_id = data["doc_id"]
            doc = DOCS.get(doc_id)
            if not doc or doc["ocr"] is None:
                self._send_json({"error": "run /run_ocr first"}, 400)
                return
            result = extract_template(doc["ocr"], pdf_path=doc["pdf_path"])
            self._send_json(result)
            return

        self.send_error(404)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = 8002
    print(f"Serving on http://localhost:{port}")
    HTTPServer(("localhost", port), Handler).serve_forever()
