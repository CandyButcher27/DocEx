import argparse
import json
from pathlib import Path

from PIL import Image
from paddleocr import PaddleOCR, __version__ as paddleocr_version

ROOT = Path(__file__).resolve().parent


def get_ocr():
    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
        lang="en",
    )


def run_page_ocr(ocr, image_path):
    with Image.open(image_path) as im:
        width, height = im.size

    pred = ocr.predict(str(image_path))[0]

    texts = pred["rec_texts"]
    scores = pred["rec_scores"]
    boxes = pred["rec_boxes"]
    polys = pred["rec_polys"]

    entries = []
    for i, (text, score, box, poly) in enumerate(zip(texts, scores, boxes, polys)):
        x0, y0, x1, y1 = [int(v) for v in box]
        entries.append({
            "id": i,
            "text": text,
            "confidence": round(float(score), 4),
            "bbox": [x0, y0, x1, y1],
            "bbox_norm": [
                round(x0 / width, 6),
                round(y0 / height, 6),
                round(x1 / width, 6),
                round(y1 / height, 6),
            ],
            "poly": [[int(px), int(py)] for px, py in poly],
        })

    return {
        "page_width": width,
        "page_height": height,
        "paddleocr_version": paddleocr_version,
        "source": Path(image_path).name,
        "ocr": entries,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="path to page image (png/jpg)")
    ap.add_argument("-o", "--output", default=None, help="output json path")
    args = ap.parse_args()

    ocr = get_ocr()
    result = run_page_ocr(ocr, args.image)

    out_path = Path(args.output) if args.output else Path(args.image).with_suffix(".ocr.json")
    out_path.write_text(json.dumps(result, indent=2))
    print(f"wrote {out_path} ({len(result['ocr'])} lines)")
