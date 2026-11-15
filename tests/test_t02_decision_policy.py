"""Focused tests for the T02 reviewer-gated batch decision policy."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common.context import RunContext
from src.common.review import AuditLog, REVIEW_COLUMNS
from src.pipeline import decide, review


def _context(tmp_path, item_ids: list[str]) -> RunContext:
    tmp_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"item_id": item_ids}).to_csv(
        tmp_path / "review_queue.csv", index=False
    )
    return RunContext(
        track="t02",
        input_dir=tmp_path,
        output_dir=tmp_path,
        config={"owner": "T02 reviewer"},
        seed=42,
        rng=np.random.default_rng(42),
        stats={"n_items": 96, "review_budget": len(item_ids)},
    )


def test_t02_decision_holds_for_skip_or_escalation(tmp_path):
    ctx = _context(tmp_path, ["a", "b", "c"])
    final = pd.DataFrame({
        "image_id": ["a", "b", "c", "outside_queue"],
        "review_action": ["KEEP", "SKIP", "HOLD", ""],
    })

    result = decide(ctx, final)

    assert result.status == "HOLD"
    assert result.reason_code == "REVIEW_INCOMPLETE"
    assert result.metrics["unresolved_review_items"] == 2
    assert result.metrics["unreviewed_queue_items"] == 0


def test_t02_decision_requires_all_queue_items_reviewed(tmp_path):
    ctx = _context(tmp_path, ["a", "b"])
    final = pd.DataFrame({"image_id": ["a", "b"], "review_action": ["KEEP", ""]})

    result = decide(ctx, final)

    assert result.status == "HOLD"
    assert result.metrics["unreviewed_queue_items"] == 1


def test_t02_decision_requests_recapture_after_complete_review(tmp_path):
    ctx = _context(tmp_path, ["a", "b"])
    final = pd.DataFrame({
        "image_id": ["a", "b"],
        "review_action": ["KEEP", "RECAPTURE"],
    })

    result = decide(ctx, final)

    assert result.status == "RECAPTURE"
    assert result.canonical == "REWORK"
    assert result.reason_code == "REVIEW_FOUND_RECAPTURE_ITEMS"


def test_t02_decision_keeps_batch_when_all_items_approved(tmp_path):
    ctx = _context(tmp_path, ["a", "b"])
    final = pd.DataFrame({"image_id": ["a", "b"], "review_action": ["KEEP", "KEEP"]})

    result = decide(ctx, final)

    assert result.status == "KEEP"
    assert result.canonical == "GO"
    assert result.reason_code == "REVIEW_APPROVED_ALL_ITEMS"


def test_t02_review_maps_decisions_and_writes_audit(tmp_path):
    ctx = _context(tmp_path, ["a", "b", "c", "d", "e"])
    ctx.audit = AuditLog(tmp_path / "audit_log.jsonl")
    rows = []
    for item_id, action, override in [
        ("a", "approve", ""),
        ("b", "reject", ""),
        ("c", "edit", "RECAPTURE"),
        ("d", "escalate", ""),
        ("e", "skip", ""),
    ]:
        rows.append({
            "rank": len(rows) + 1,
            "item_id": item_id,
            "score": 0.5,
            "reason": "blur",
            "suggested_action": "",
            "slice": "",
            "evidence_path": "",
            "reviewer": "T02 reviewer",
            "reviewer_decision": action,
            "override_value": override,
            "review_note": "unit test",
            "reviewed_at": "",
        })
    pd.DataFrame(rows, columns=REVIEW_COLUMNS).to_csv(
        tmp_path / "review_queue_reviewed.csv", index=False
    )
    scored = pd.DataFrame({"image_id": list("abcde"), "score": [0.5] * 5})
    queue = pd.DataFrame({"item_id": list("abcde")})

    result = review(ctx, scored, queue)

    assert result["review_action"].tolist() == [
        "KEEP", "RECAPTURE", "RECAPTURE", "HOLD", "SKIP"
    ]
    assert len(ctx.audit.read()) == 5
