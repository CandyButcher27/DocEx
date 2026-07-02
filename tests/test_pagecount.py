import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest_gate import MATCH_THRESH, check_pagecount

STORE = {"docs": [{"name": "DOGH", "n_pages": 2}, {"name": "LFQ", "n_pages": 2}]}

HI = MATCH_THRESH + 0.5
LO = MATCH_THRESH - 0.1


def page(kind, score):
    return {"kind": kind, "score": score}


def test_legit_multikind_packet_accepts():
    match = {"pages": [page("DOGH", HI), page("DOGH", HI), page("LFQ", HI), page("LFQ", HI), page("DOGH", LO)]}
    ok, _ = check_pagecount(match, STORE)
    assert ok


def test_duplicate_form_rejects():
    match = {"pages": [page("DOGH", HI)] * 4}
    ok, detail = check_pagecount(match, STORE)
    assert not ok
    assert detail["per_kind"]["DOGH"] == 4


def test_too_many_foreign_pages_rejects():
    match = {"pages": [page("DOGH", HI), page("LFQ", LO), page("LFQ", LO), page("DOGH", LO)]}
    ok, detail = check_pagecount(match, STORE)
    assert not ok
    assert detail["unmatched"] == 3


def test_exactly_at_budget_accepts():
    match = {"pages": [page("DOGH", HI), page("DOGH", HI), page("LFQ", HI), page("LFQ", HI)]}
    ok, _ = check_pagecount(match, STORE)
    assert ok
