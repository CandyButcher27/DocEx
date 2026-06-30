from __future__ import annotations

from .models import FieldDecision


def build_review_queue(decisions: list[FieldDecision]) -> list[dict]:
    queue = []
    for d in decisions:
        if d.status == "review":
            queue.append({
                "field": d.name,
                "prediction": d.value,
                "confidence": round(d.confidence, 3),
                "crop": d.crop_path,
                "reason": d.note or "uncertain",
            })
    return queue


def apply_human_answers(decisions: list[FieldDecision], answers: dict[str, str]) -> None:
    for d in decisions:
        if d.name in answers:
            d.value = answers[d.name]
            d.confidence = 1.0
            d.source = "human"
            d.validated = True
            d.status = "accepted"
            d.note = "human verified"
