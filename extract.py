import argparse
from pathlib import Path

from src.pipeline.orchestrator import extract_document
from src.template.enums import ExportFormat

_FORMATS = {"json": ExportFormat.JSON, "csv": ExportFormat.CSV, "excel": ExportFormat.EXCEL}


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract fields from a scanned document.")
    parser.add_argument("pdf_path", help="Path to the scanned PDF.")
    parser.add_argument("--format", choices=list(_FORMATS), default="json")
    parser.add_argument("--out", default=None, help="Output file path (extension added if omitted).")
    args = parser.parse_args()

    out = args.out or str(Path("output") / Path(args.pdf_path).stem)
    result = extract_document(args.pdf_path, export_format=_FORMATS[args.format], output_path=out)

    print(f"route       : {result.route.value}")
    print(f"template    : {result.template_id}")
    print(f"match score : {result.match_score:.3f}")
    print(f"fields      : {len(result.document.all_fields())}")
    print(f"exported    : {result.export_path}")


if __name__ == "__main__":
    main()
