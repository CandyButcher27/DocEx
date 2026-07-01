import argparse
import os

import yaml
from pdf2image import convert_from_path
from PIL import ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(ROOT, "templates")
SCANNED_DOCS = os.path.join(ROOT, "scanned_docs")
OUT_DIR = os.path.join(ROOT, "overlay_out")
DPI = 150


def load_template(name):
    path = os.path.join(TEMPLATES, name if name.endswith(".yaml") else name + ".yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def draw_overlay(pdf_path, template, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pages = convert_from_path(pdf_path, dpi=DPI)
    by_page = {}
    for field in template["fields"]:
        by_page.setdefault(field["page"], []).append(field)

    saved = []
    for page_idx, fields in by_page.items():
        if page_idx >= len(pages):
            continue
        img = pages[page_idx].copy()
        draw = ImageDraw.Draw(img)
        iw, ih = img.size
        for f in fields:
            b = f["box"]
            x0 = b["x"] * iw
            y0 = b["y"] * ih
            x1 = x0 + b["w"] * iw
            y1 = y0 + b["h"] * ih
            color = "red" if f.get("required") else "blue"
            draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
            draw.text((x0, max(0, y0 - 12)), f["name"], fill=color)
        out_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_p{page_idx + 1}_overlay.png"
        out_path = os.path.join(out_dir, out_name)
        img.save(out_path)
        saved.append(out_path)
    return saved


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("template", help="template yaml name in templates/ (with or without .yaml)")
    ap.add_argument("scanned_pdf", help="pdf filename in scanned_docs/")
    args = ap.parse_args()

    template = load_template(args.template)
    pdf_path = os.path.join(SCANNED_DOCS, args.scanned_pdf)
    saved = draw_overlay(pdf_path, template, OUT_DIR)
    for p in saved:
        print(p)
