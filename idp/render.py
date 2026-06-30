from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .config import GHOSTSCRIPT_BIN, RENDER_DPI, WORK_DIR


def pdf_to_images(pdf_path: str | Path, dpi: int = RENDER_DPI) -> list[np.ndarray]:
    pdf_path = Path(pdf_path)
    out_dir = Path(tempfile.mkdtemp(prefix="idp_render_", dir=WORK_DIR))
    pattern = str(out_dir / "page_%d.png")
    cmd = [
        GHOSTSCRIPT_BIN, "-dNOPAUSE", "-dBATCH", "-dSAFER",
        "-sDEVICE=png16m", f"-r{dpi}",
        f"-sOutputFile={pattern}", str(pdf_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ghostscript failed: {proc.stderr[-500:]}")
    pages = sorted(out_dir.glob("page_*.png"), key=lambda p: int(p.stem.split("_")[1]))
    if not pages:
        raise RuntimeError("ghostscript produced no pages")
    return [cv2.imread(str(p)) for p in pages]


def docx_to_images(docx_path: str | Path, dpi: int = RENDER_DPI) -> list[np.ndarray]:
    from docx2pdf import convert

    docx_path = Path(docx_path)
    tmp_pdf = Path(tempfile.mktemp(suffix=".pdf", dir=WORK_DIR))
    convert(str(docx_path), str(tmp_pdf))
    return pdf_to_images(tmp_pdf, dpi=dpi)


def load_first_page(path: str | Path, dpi: int = RENDER_DPI) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return pdf_to_images(path, dpi=dpi)[0]
    if path.suffix.lower() in (".docx", ".doc"):
        return docx_to_images(path, dpi=dpi)[0]
    img = cv2.imread(str(path))
    if img is None:
        raise RuntimeError(f"could not read image: {path}")
    return img
