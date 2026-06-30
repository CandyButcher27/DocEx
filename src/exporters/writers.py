import csv
import json
from pathlib import Path

_COLUMNS = ["key", "field_id", "label", "page", "value", "confidence", "valid"]


def write_json(records: list[dict], out_path: Path) -> None:
    payload = {"fields": records}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_csv(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({col: record.get(col, "") for col in _COLUMNS})


def write_excel(records: list[dict], out_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "extraction"
    ws.append(_COLUMNS)
    for record in records:
        ws.append([record.get(col, "") for col in _COLUMNS])
    wb.save(out_path)
