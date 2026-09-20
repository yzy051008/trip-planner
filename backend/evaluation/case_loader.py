"""Load and validate JSONL evaluation cases."""

import json
from dataclasses import dataclass
from pathlib import Path

try:
    from app.models.schemas import TripRequest
except ModuleNotFoundError:
    from backend.app.models.schemas import TripRequest


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    category: str
    description: str
    request: TripRequest
    expected: dict


def load_cases(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {line_number}: {exc.msg}") from exc
        case_id = raw.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"missing case_id at line {line_number}")
        if case_id in seen:
            raise ValueError(f"duplicate case_id at line {line_number}: {case_id}")
        try:
            request = TripRequest.model_validate(raw["request"])
        except Exception as exc:
            raise ValueError(f"invalid request at line {line_number}: {exc}") from exc
        seen.add(case_id)
        cases.append(EvaluationCase(
            case_id=case_id,
            category=str(raw.get("category", "")),
            description=str(raw.get("description", "")),
            request=request,
            expected=dict(raw.get("expected", {})),
        ))
    return cases
