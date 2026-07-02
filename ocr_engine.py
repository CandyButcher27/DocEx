import os
import uuid

from pdf2image import convert_from_path
from paddleocr import PaddleOCR

DPI = 150
ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(ROOT, "uploads")
os.makedirs(UPLOADS, exist_ok=True)

_engine = None


def get_ocr():
    global _engine
    if _engine is None:
        _engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            lang="en",
            cpu_threads=8,
        )
    return _engine


def ocr_image(pil_img):
    tmp = os.path.join(UPLOADS, f"_c_{uuid.uuid4().hex}.png")
    pil_img.save(tmp)
    try:
        pred = get_ocr().predict(tmp)[0]
    finally:
        os.remove(tmp)
    out = []
    for text, score, box in zip(pred["rec_texts"], pred["rec_scores"], pred["rec_boxes"]):
        x0, y0, x1, y1 = [int(v) for v in box]
        out.append({"text": text, "confidence": round(float(score), 4), "bbox": [x0, y0, x1, y1]})
    return out


def render_pages(pdf_path):
    return convert_from_path(pdf_path, dpi=DPI)


def run_ocr_on_pdf(pdf_path):
    entries = []
    for page_idx, image in enumerate(render_pages(pdf_path)):
        width, height = image.size
        for e in ocr_image(image):
            entries.append({
                "page": page_idx,
                "text": e["text"],
                "confidence": e["confidence"],
                "bbox": e["bbox"],
                "page_width": width,
                "page_height": height,
            })
    return entries
