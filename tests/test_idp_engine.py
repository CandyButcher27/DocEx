from __future__ import annotations

import numpy as np
import pytest

from idp.classify import classify
from idp.decision import DecisionEngine
from idp.models import BBox, FieldSpec, OCRCandidate, OCRWord, Template
from idp.phash import dhash, hamming
from idp.roi import _is_marker, find_anchor, value_region
from idp.store import load_templates, save_template
from idp.textutil import contains_ratio, normalize, similarity
from idp.validate import validate_field


# ---------- textutil ----------

def test_contains_ratio_windowed():
    assert contains_ratio("Insured Member", "blah InsureuMember blah") > 0.83
    assert contains_ratio("PAN Number", "PAN Numbey nearby") > 0.85
    assert contains_ratio("Nonexistent Phrase", "totally different text here") < 0.5


def test_similarity_and_normalize():
    assert normalize("PAN A/c No.!") == "panacno"
    assert similarity("Group Policy", "GroupPoliy") > 0.8


# ---------- validate ----------

@pytest.mark.parametrize("dt,val,ok,clean", [
    ("pan", "anspk 6125 e", True, "ANSPK6125E"),
    ("pan", "garbage", False, None),
    ("number", "1,00,000", True, "100000"),
    ("number", "Reference Cheque No 14 month", False, None),
    ("date", "29 06 1978", True, "29-06-1978"),
    ("date", "99 99 99", False, None),
])
def test_validate(dt, val, ok, clean):
    spec = FieldSpec("f", ["f"], datatype=dt)
    got_ok, got_clean, _ = validate_field(spec, val)
    assert got_ok == ok
    if clean is not None:
        assert got_clean == clean


def test_validate_choice():
    spec = FieldSpec("gender", ["Gender"], datatype="choice", choices=["Male", "Female"])
    assert validate_field(spec, "male")[0]
    assert not validate_field(spec, "robot")[0]


# ---------- roi ----------

def test_is_marker():
    assert _is_marker("14)")
    assert _is_marker("(3.")
    assert not _is_marker("100000")
    assert not _is_marker("AB12")


def _w(text, x1, y1, x2, y2, conf=0.9):
    return OCRWord(text, BBox(x1, y1, x2, y2), conf)


def test_find_anchor_and_value_region():
    words = [
        _w("Policy", 10, 10, 80, 30),
        _w("Number", 85, 10, 160, 30),
        _w("AB123456", 200, 10, 320, 30),
        _w("Amount", 10, 60, 90, 80),
        _w("50000", 200, 60, 280, 80),
    ]
    spec = FieldSpec("policy", ["Policy Number"], "right", "text")
    hit = find_anchor(words, spec.anchors)
    assert hit is not None and hit.score > 0.8
    region, found = value_region(hit, words, spec, 800, 200, {normalize("Amount")})
    assert [f.text for f in found] == ["AB123456"]


def test_value_region_stops_at_other_anchor():
    words = [
        _w("Name", 10, 10, 60, 30),
        _w("JOHN", 120, 10, 180, 30),
        _w("Gender", 400, 10, 470, 30),
        _w("Male", 520, 10, 570, 30),
    ]
    spec = FieldSpec("name", ["Name"], "right", "text")
    hit = find_anchor(words, spec.anchors)
    region, found = value_region(hit, words, spec, 800, 200, {normalize("Gender")})
    assert "JOHN" in [f.text for f in found]
    assert "Male" not in [f.text for f in found]


# ---------- phash ----------

def test_phash():
    a = np.zeros((100, 100, 3), np.uint8)
    b = a.copy()
    b[:, 50:] = 255
    assert hamming(dhash(a), dhash(a)) == 0
    assert hamming(dhash(a), dhash(b)) > 0


# ---------- decision ----------

def test_decision_consensus_accept():
    spec = FieldSpec("pan", ["PAN"], datatype="pan")
    cands = [OCRCandidate("ANSPK6125E", 0.95, "rapidocr"),
             OCRCandidate("ANSPK6125E", 0.93, "rapidocr+bin")]
    dec = DecisionEngine().decide(spec, cands, None, np.zeros((10, 10, 3), np.uint8), None)
    assert dec.status == "accepted" and dec.value == "ANSPK6125E" and dec.source == "ocr"


def test_decision_validation_fail_review():
    spec = FieldSpec("pan", ["PAN"], datatype="pan")
    cands = [OCRCandidate("NOTAPAN", 0.95, "rapidocr"),
             OCRCandidate("NOTAPAN", 0.9, "rapidocr+bin")]
    dec = DecisionEngine().decide(spec, cands, None, np.zeros((10, 10, 3), np.uint8), None)
    assert dec.status == "review"


def test_decision_no_candidates_review():
    spec = FieldSpec("x", ["x"])
    dec = DecisionEngine().decide(spec, [], None, np.zeros((10, 10, 3), np.uint8), None)
    assert dec.status == "review" and dec.source == "pending_human"


def test_decision_vlm_authoritative():
    spec = FieldSpec("pan", ["PAN"], datatype="pan")
    ocr = [OCRCandidate("PKANT", 0.7, "rapidocr")]
    vlm = OCRCandidate("ANSPK6125E", 0.9, "vlm")
    dec = DecisionEngine().decide(spec, ocr, vlm, np.zeros((10, 10, 3), np.uint8), None)
    assert dec.status == "accepted" and dec.value == "ANSPK6125E" and dec.source == "vlm"


# ---------- classify ----------

def test_classify_picks_template():
    t = Template("t1", "T1", ["Policy Number", "Sum Assured", "Nominee"], [], phash="00")
    img = np.zeros((50, 50, 3), np.uint8)
    res = classify(img, "Policy Number Sum Assured Nominee Member", [t])
    assert res.template is t and res.method == "text"


def test_classify_unknown():
    t = Template("t1", "T1", ["Policy Number", "Sum Assured", "Nominee"], [], phash="00")
    res = classify(np.zeros((50, 50, 3), np.uint8), "completely unrelated invoice text", [t])
    assert res.template is None


# ---------- store ----------

def test_vlm_extract_json():
    from idp.vlm import _extract_json
    assert _extract_json('```json\n[{"a":1}]\n```') == [{"a": 1}]
    assert _extract_json('here it is: {"x": "y"} done')["x"] == "y"
    assert _extract_json('[{"name":"f","label":"L"}]')[0]["name"] == "f"


def test_fake_vlm():
    from idp.vlm import FakeVLM
    v = FakeVLM()
    img = np.zeros((40, 40, 3), np.uint8)
    assert v.extract_fields(img, []) == {}
    t = v.detect_format(img, "policy number nominee member")
    assert t.source == "vlm_fake" and t.phash


def test_store_roundtrip(tmp_path):
    t = Template("rt", "RT", ["a", "b"],
                 [FieldSpec("f1", ["A"], datatype="pan")], phash="ab")
    save_template(t, tmp_path)
    loaded = load_templates(tmp_path)
    assert loaded[0].template_id == "rt"
    assert loaded[0].fields[0].datatype == "pan"
