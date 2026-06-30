import json

from .schema import DerivedDocument, DerivedField, DerivedPage, DerivedSection

INSTRUCTION = """You are a document-structure analyzer. You are given the page images of a scanned form.
Identify every fillable field and return ONLY a JSON object (no prose, no markdown fences) with this exact shape:

{
  "family": "short_snake_case_family_name",
  "issuer": "organization that issued the form",
  "document_type": "human readable document type",
  "pages": [
    {
      "number": 1,
      "sections": [
        {
          "id": "snake_case_section_id",
          "fields": [
            {
              "id": "snake_case_field_id",
              "label": "Human Readable Label",
              "datatype": "one of: text|number|date|pan|email|phone|address|checkbox|radio|signature|image",
              "widget": "one of: textbox|checkbox|radio|dropdown|signature|image|table",
              "validator": "one of: text|number|date|pan|email|phone|amount|pincode|ifsc|account_number|none",
              "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0
            }
          ]
        }
      ]
    }
  ]
}

Bounding boxes (x, y, width, height) are normalized to [0,1] with the top-left origin and describe the region
where the field's VALUE is written (not the printed label). Do not transcribe any handwriting or values."""


def parse_derived_document(data: dict) -> DerivedDocument:
    pages = []
    for page in data.get("pages", []):
        sections = []
        for section in page.get("sections", []):
            fields = [
                DerivedField(
                    id=f["id"],
                    label=f["label"],
                    datatype=f.get("datatype", "text"),
                    widget=f.get("widget", "textbox"),
                    validator=f.get("validator", "text"),
                    x=float(f["x"]),
                    y=float(f["y"]),
                    width=float(f["width"]),
                    height=float(f["height"]),
                )
                for f in section.get("fields", [])
            ]
            sections.append(DerivedSection(id=section["id"], fields=fields))
        pages.append(DerivedPage(number=int(page["number"]), sections=sections))

    return DerivedDocument(
        family=data.get("family", "auto_generated"),
        issuer=data.get("issuer", "Unknown"),
        document_type=data.get("document_type", "Auto-derived document"),
        pages=pages,
    )


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in VLM response.")
    return json.loads(text[start : end + 1])
