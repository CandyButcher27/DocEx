import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
XLSX = ROOT / "GSS-SchemaSummary-V3(Mar-30) 2.xlsx"
CODE_MAPPER = ROOT / "code_mapper.json"
OUT = ROOT / "field_spec.json"

SYSTEM_PATHS = {
    "quoteId",
    "documents[0].documentId",
    "documents[0].base64",
    "otp_details.otp_timestamp",
    "otp_details[0].otp_timestamp",
}

OPTION_RULES = [
    (r"mobile_country_code$|country_code$", "countryCodeOptions"),
    (r"appointee_relationship", "relationshipOptions"),
    (r"relationship_with|declarant_relation", "relationshipOptions"),
    (r"appointee_gender$|(^|\.)gender$", "genderOptions"),
    (r"nationality$", "nationalityOptions"),
    (r"occupation$", "occupationOptions"),
    (r"education$", "educationOptions"),
    (r"share_in_loan$", "shareInLoanOptions"),
    (r"language$", "languageOptions"),
    (r"(^|\.)state$", "stateOptions"),
    (r"address_details\[\d+\]\.type$", "addressTypeOptions"),
    (r"applicant", "applicantDetailsOptions"),
    (r"medical_lifestyle_questions\[\d+\]\.code$", "medicalQuestionOptions"),
]


def resolve_options_key(path):
    for pat, key in OPTION_RULES:
        if re.search(pat, path):
            return key
    return None


def group_of(path):
    m = re.match(r"^([a-zA-Z_]+)\[\d+\]", path)
    return m.group(1) if m else None


def main():
    mapper = json.loads(CODE_MAPPER.read_text(encoding="utf-8"))
    schema = pd.read_excel(XLSX, "Proposal Schema")
    mapping = pd.read_excel(XLSX, "Proposal Mapping")

    type_by_path = {
        str(r["Field ID"]).strip(): str(r["Field Data Type"]).strip()
        for _, r in mapping.iterrows()
        if pd.notna(r.get("Field ID")) and pd.notna(r.get("Field Data Type"))
    }

    fields = []
    unresolved_coded = []
    for _, r in schema.iterrows():
        path = r.get("Field ID")
        if pd.isna(path):
            continue
        path = str(path).strip()
        if path in SYSTEM_PATHS:
            continue
        coded = str(r.get("Master")).strip().lower() == "yes"
        options_key = resolve_options_key(path) if coded else None
        options = None
        if options_key:
            opts = mapper[options_key]
            if options_key == "medicalQuestionOptions":
                options = [{"text": o["text"], "value": o["id"]} for o in opts]
            else:
                options = [{"text": o["text"], "value": o["value"]} for o in opts]
        if coded and options is None:
            unresolved_coded.append(path)

        field = {
            "path": path,
            "label": str(r.get("Field Name")).strip(),
            "section": str(r.get("Category")).strip() if pd.notna(r.get("Category")) else None,
            "type": type_by_path.get(path),
            "coded": coded,
            "repeat_group": group_of(path),
        }
        if options is not None:
            field["allowed_values"] = [o["text"] for o in options]
            field["options"] = options
        fields.append(field)

    spec = {
        "source": XLSX.name,
        "template_shape": "template.json",
        "not_found_token": "NOT_FOUND",
        "fields": fields,
    }
    OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    total = len(fields)
    coded = sum(1 for f in fields if f["coded"])
    with_opts = sum(1 for f in fields if "options" in f)
    groups = sorted({f["repeat_group"] for f in fields if f["repeat_group"]})
    out = sys.stdout
    print(f"wrote {OUT.name}: {total} fields", file=out)
    print(f"  coded: {coded}  (decodable: {with_opts})", file=out)
    print(f"  repeat groups: {groups}", file=out)
    print(f"  coded WITHOUT options (leave as human text): {unresolved_coded}", file=out)


if __name__ == "__main__":
    main()
