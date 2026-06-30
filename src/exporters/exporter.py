from pathlib import Path

from src.models.document import Document
from src.template.enums import ExportFormat

from .serializer import document_to_records
from .writers import write_csv, write_excel, write_json

_EXTENSIONS = {ExportFormat.JSON: ".json", ExportFormat.CSV: ".csv", ExportFormat.EXCEL: ".xlsx"}
_WRITERS = {ExportFormat.JSON: write_json, ExportFormat.CSV: write_csv, ExportFormat.EXCEL: write_excel}


def export_document(document: Document, fmt: ExportFormat, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    if out_path.suffix == "":
        out_path = out_path.with_suffix(_EXTENSIONS[fmt])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    records = document_to_records(document)
    _WRITERS[fmt](records, out_path)
    return out_path
