import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from io import BytesIO

import yaml
from pdf2image import convert_from_path, pdfinfo_from_path

ROOT = os.path.dirname(os.path.abspath(__file__))
PROPER_DOCS = os.path.join(ROOT, "proper_docs")
PDF_CACHE = os.path.join(ROOT, "proper_docs_pdf")
TEMPLATES = os.path.join(ROOT, "templates")
HTML_FILE = os.path.join(ROOT, "template_tool.html")
DPI = 150

os.makedirs(PDF_CACHE, exist_ok=True)
os.makedirs(TEMPLATES, exist_ok=True)


def docx_to_pdf(docx_name):
    base = os.path.splitext(docx_name)[0]
    pdf_path = os.path.join(PDF_CACHE, base + ".pdf")
    docx_path = os.path.join(PROPER_DOCS, docx_name)
    if os.path.exists(pdf_path) and os.path.getmtime(pdf_path) >= os.path.getmtime(docx_path):
        return pdf_path
    from docx2pdf import convert
    convert(docx_path, pdf_path)
    return pdf_path


def resolve_pdf(name):
    if name.lower().endswith(".pdf"):
        return os.path.join(PROPER_DOCS, name)
    if name.lower().endswith(".docx"):
        return docx_to_pdf(name)
    raise ValueError("unsupported file type")


def render_page(name, page):
    path = resolve_pdf(name)
    pages = convert_from_path(path, dpi=DPI, first_page=page + 1, last_page=page + 1)
    return pages[0]


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

        if parsed.path == "/docs":
            files = sorted(
                f for f in os.listdir(PROPER_DOCS)
                if f.lower().endswith((".pdf", ".docx"))
            )
            self._send_json(files)
            return

        if parsed.path == "/pages":
            qs = parse_qs(parsed.query)
            filename = qs["file"][0]
            path = resolve_pdf(filename)
            info = pdfinfo_from_path(path)
            self._send_json({"pages": info["Pages"]})
            return

        if parsed.path == "/render":
            qs = parse_qs(parsed.query)
            filename = qs["file"][0]
            page = int(qs.get("page", [0])[0])
            image = render_page(filename, page)
            buf = BytesIO()
            image.save(buf, format="PNG")
            body = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/template":
            qs = parse_qs(parsed.query)
            filename = qs["file"][0]
            base = os.path.splitext(filename)[0]
            yaml_path = os.path.join(TEMPLATES, base + ".yaml")
            if os.path.exists(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {"template": base, "fields": []}
            else:
                data = {"template": base, "fields": []}
            self._send_json(data)
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/save_field":
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))
            filename = data["file"]
            base = os.path.splitext(filename)[0]
            yaml_path = os.path.join(TEMPLATES, base + ".yaml")

            if os.path.exists(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    template = yaml.safe_load(f) or {"template": base, "fields": []}
            else:
                template = {"template": base, "fields": []}

            field = {
                "name": data["name"],
                "type": data["type"],
                "required": bool(data["required"]),
                "page": int(data["page"]),
                "box": {
                    "x": data["x"],
                    "y": data["y"],
                    "w": data["w"],
                    "h": data["h"],
                },
            }

            template["fields"] = [f for f in template["fields"] if f["name"] != field["name"]]
            template["fields"].append(field)

            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(template, f, sort_keys=False, allow_unicode=True)

            self._send_json({"saved": os.path.basename(yaml_path), "fields": len(template["fields"])})
            return

        if parsed.path == "/delete_field":
            length = int(self.headers["Content-Length"])
            data = json.loads(self.rfile.read(length))
            filename = data["file"]
            base = os.path.splitext(filename)[0]
            yaml_path = os.path.join(TEMPLATES, base + ".yaml")
            if os.path.exists(yaml_path):
                with open(yaml_path, "r", encoding="utf-8") as f:
                    template = yaml.safe_load(f) or {"template": base, "fields": []}
                template["fields"] = [f for f in template["fields"] if f["name"] != data["name"]]
                with open(yaml_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(template, f, sort_keys=False, allow_unicode=True)
            self._send_json({"ok": True})
            return

        self.send_error(404)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = 8001
    print(f"Serving on http://localhost:{port}")
    HTTPServer(("localhost", port), Handler).serve_forever()
