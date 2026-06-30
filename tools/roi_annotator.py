import argparse
import copy
import sys
import tkinter as tk
from pathlib import Path

import yaml
from PIL import Image, ImageTk
from docx2pdf import convert as docx2pdf_convert
from pdf2image import convert_from_path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.template.loader import _resolve_variant
from src.template.parser import parse_template

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
MAX_CANVAS_SIZE = (1200, 900)


def render_reference(docx_path: Path, out_dir: Path) -> dict[int, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("page_*.png"), key=lambda p: int(p.stem.split("_")[1]))

    if existing:
        return {int(p.stem.split("_")[1]): p for p in existing}

    pdf_path = out_dir / (docx_path.stem + ".pdf")
    docx2pdf_convert(str(docx_path), str(pdf_path))
    images = convert_from_path(str(pdf_path))

    pages = {}
    for i, image in enumerate(images, start=1):
        page_path = out_dir / f"page_{i}.png"
        image.save(page_path)
        pages[i] = page_path

    return pages


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def find_field_source(base_data: dict, variant_data: dict, field_id: str) -> tuple[dict, str]:
    for page in base_data["pages"]:
        for section in page["sections"]:
            for field in section["fields"]:
                if field["id"] == field_id:
                    return field, "base"

    for section_override in variant_data.get("overrides", {}).get("sections", []):
        for field in section_override.get("add_fields", []):
            if field["id"] == field_id:
                return field, "variant"

    raise KeyError(f"Field '{field_id}' not found in base or variant overrides.")


class AnnotatorApp:

    def __init__(self, family_dir: Path, variant_filename: str):
        family_dir = family_dir.resolve()
        self.family_dir = family_dir
        self.base_path = family_dir / "base.yaml"
        self.variant_path = family_dir / "variants" / variant_filename

        self.base_data = load_yaml(self.base_path)
        self.variant_data = load_yaml(self.variant_path)

        merged = _resolve_variant(copy.deepcopy(self.base_data), copy.deepcopy(self.variant_data))
        self.template = parse_template(merged, family_dir.name)

        reference_docx = self.variant_data.get("metadata", {}).get("reference_docx")
        if not reference_docx:
            raise ValueError(f"{self.variant_path} has no metadata.reference_docx set.")

        docx_path = family_dir / reference_docx
        rendered_dir = family_dir / "reference" / "rendered" / self.template.metadata.template_id
        self.page_images = render_reference(docx_path, rendered_dir)
        self.registration_reference_images = {n: str(p.relative_to(REPO_ROOT)) for n, p in self.page_images.items()}

        self.queue = self._build_queue()
        self.queue_index = 0

        self.root = tk.Tk()
        self.root.title(f"ROI Annotator — {self.template.metadata.template_id}")

        self.status_label = tk.Label(self.root, anchor="w", font=("Segoe UI", 11))
        self.status_label.pack(fill="x", padx=8, pady=4)

        self.canvas = tk.Canvas(self.root, bg="gray20", cursor="cross")
        self.canvas.pack(fill="both", expand=True)

        help_text = "Drag a box around the field. 's' skip field. 'q' save & quit."
        tk.Label(self.root, text=help_text, anchor="w", fg="gray50").pack(fill="x", padx=8, pady=4)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("s", lambda e: self._skip_field())
        self.root.bind("q", lambda e: self._save_and_quit())

        self.rect_id = None
        self.start_xy = None
        self.tk_image = None
        self.current_page = None
        self.image_size = (0, 0)

        self._show_current_field()

    def _build_queue(self) -> list[tuple[int, str, str]]:
        queue = []
        for page in self.template.pages:
            for section in page.sections:
                for field in section.fields:
                    if field.roi.x is None:
                        queue.append((page.number, field.id, field.label))
        return queue

    def _show_current_field(self) -> None:
        if self.queue_index >= len(self.queue):
            self._save_and_quit()
            return

        page_number, field_id, label = self.queue[self.queue_index]
        self.status_label.config(
            text=f"[{self.queue_index + 1}/{len(self.queue)}] page {page_number} — {label} ({field_id})"
        )

        if self.current_page != page_number:
            self._load_page_image(page_number)

    def _load_page_image(self, page_number: int) -> None:
        image_path = self.page_images.get(page_number)
        if image_path is None:
            raise ValueError(f"No rendered reference image for page {page_number}.")

        image = Image.open(image_path)
        w, h = image.size
        scale = min(MAX_CANVAS_SIZE[0] / w, MAX_CANVAS_SIZE[1] / h, 1.0)
        resized = image.resize((int(w * scale), int(h * scale)))

        self.tk_image = ImageTk.PhotoImage(resized)
        self.image_size = resized.size
        self.current_page = page_number

        self.canvas.config(width=resized.size[0], height=resized.size[1])
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

    def _on_press(self, event) -> None:
        self.start_xy = (event.x, event.y)
        self.rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=2
        )

    def _on_drag(self, event) -> None:
        if self.rect_id is None or self.start_xy is None:
            return
        x0, y0 = self.start_xy
        self.canvas.coords(self.rect_id, x0, y0, event.x, event.y)

    def _on_release(self, event) -> None:
        if self.rect_id is None or self.start_xy is None:
            return

        x0, y0 = self.start_xy
        x1, y1 = event.x, event.y
        self.canvas.delete(self.rect_id)
        self.rect_id = None
        self.start_xy = None

        w, h = self.image_size
        nx = max(0.0, min(x0, x1) / w)
        ny = max(0.0, min(y0, y1) / h)
        nw = min(1.0 - nx, abs(x1 - x0) / w)
        nh = min(1.0 - ny, abs(y1 - y0) / h)

        if nw <= 0 or nh <= 0:
            return

        self._save_roi(nx, ny, nw, nh)
        self.queue_index += 1
        self._show_current_field()

    def _save_roi(self, x: float, y: float, width: float, height: float) -> None:
        _, field_id, _ = self.queue[self.queue_index]
        field_dict, source = find_field_source(self.base_data, self.variant_data, field_id)
        field_dict["roi"] = {"x": round(x, 4), "y": round(y, 4), "width": round(width, 4), "height": round(height, 4)}

    def _skip_field(self) -> None:
        self.queue_index += 1
        self._show_current_field()

    def _save_and_quit(self) -> None:
        self.variant_data.setdefault("registration", {})
        self.variant_data["registration"]["method"] = self.variant_data["registration"].get("method", "orb")
        self.variant_data["registration"]["reference_images"] = self.registration_reference_images

        save_yaml(self.base_path, self.base_data)
        save_yaml(self.variant_path, self.variant_data)

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Click-to-annotate ROI coordinates onto a template YAML.")
    parser.add_argument("family", help="Template family directory name, e.g. axis_max")
    parser.add_argument("variant_filename", help="Variant YAML filename under variants/, e.g. premier_lfq.yaml")
    args = parser.parse_args()

    family_dir = TEMPLATES_DIR / args.family
    app = AnnotatorApp(family_dir, args.variant_filename)
    app.run()


if __name__ == "__main__":
    main()
