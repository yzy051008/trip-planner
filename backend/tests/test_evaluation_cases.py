import json

import pytest

from evaluation.case_loader import load_cases


VALID_REQUEST = {
    "city": "上海", "start_date": "2026-10-01", "end_date": "2026-10-01",
    "travel_days": 1, "transportation": "步行", "accommodation": "经济型酒店",
}


def test_loader_rejects_duplicate_case_ids(tmp_path):
    path = tmp_path / "cases.jsonl"
    item = {"case_id": "same", "category": "normal", "description": "x", "request": VALID_REQUEST, "expected": {}}
    path.write_text(json.dumps(item) + "\n" + json.dumps(item), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate case_id"):
        load_cases(path)


def test_loader_rejects_invalid_json_with_line_number(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps({"case_id": "ok", "request": VALID_REQUEST}) + "\nnot-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        load_cases(path)


def test_loader_converts_valid_request_to_trip_request(tmp_path):
    path = tmp_path / "cases.jsonl"
    item = {
        "case_id": "normal_001", "category": "normal", "description": "test",
        "request": {
            "city": "上海", "start_date": "2026-10-01", "end_date": "2026-10-01",
            "travel_days": 1, "transportation": "步行", "accommodation": "经济型酒店",
        }, "expected": {"days": 1},
    }
    path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")

    cases = load_cases(path)

    assert len(cases) == 1
    assert cases[0].request.city == "上海"
    assert cases[0].expected["days"] == 1
