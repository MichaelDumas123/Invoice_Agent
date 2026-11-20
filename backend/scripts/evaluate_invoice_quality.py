"""Evaluate deterministic invoice checks on a labeled JSON fixture.

This runner supports synthetic-only checks. It does not run OCR or call an LLM.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from invoice_assistant.domain.policy import WorkspacePolicy
from invoice_assistant.domain.validation import validate_invoice


def evaluate(path: Path) -> dict[str, Any]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Evaluation file must contain a JSON array")
    cases = []
    totals = {"pass": 0, "warning": 0, "inconclusive": 0, "hard_stop": 0}
    for record in records:
        results = validate_invoice(record["fields"], WorkspacePolicy(), record.get("existing_records", []))
        observed = {result.check: result.status.value for result in results}
        expected = record.get("expected", {})
        correct = all(observed.get(check) == status for check, status in expected.items())
        for result in results:
            totals[result.status.value] = totals.get(result.status.value, 0) + 1
        cases.append({"case_id": record.get("case_id", "anonymous"), "correct": correct, "observed": observed, "expected": expected})
    return {"cases": len(cases), "passed": sum(case["correct"] for case in cases), "checks_by_status": totals, "results": cases}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.fixture), indent=2))


if __name__ == "__main__":
    main()
