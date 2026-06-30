from src.confidence.scorer import compute_confidence
from src.models.document import Document


def document_to_records(document: Document) -> list[dict]:
    records = []

    for page in document.pages:
        for field in page.fields:
            ocr = field.ocr_result
            validation = field.validation_result

            if validation is not None:
                value = validation.normalized_text
            elif ocr is not None:
                value = ocr.raw_text
            else:
                value = ""

            if ocr is not None and validation is not None:
                confidence = compute_confidence(ocr, validation)
            elif ocr is not None:
                confidence = ocr.confidence
            else:
                confidence = 0.0

            records.append(
                {
                    "key": field.config.export.key,
                    "field_id": field.config.id,
                    "label": field.config.label,
                    "page": page.number,
                    "value": value,
                    "confidence": round(confidence, 4),
                    "valid": validation.is_valid if validation is not None else None,
                }
            )

    return records
