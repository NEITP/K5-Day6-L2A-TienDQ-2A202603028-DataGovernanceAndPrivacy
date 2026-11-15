"""T02 baseline: rank by one global Laplacian-variance threshold/proxy.

The same monotonic inverse-Laplacian score gives the threshold baseline's
ranking at a fixed review budget without using labels or split-specific tuning.
"""
from __future__ import annotations

import pandas as pd

from ..common.context import RunContext
from ..common.decision import Decision, write_decision
from ..common.image_ops import laplacian_variance, load_rgb
from ..common.review import make_review_queue, write_review_queue
from ..metrics.tracks import get_track


def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)
    if ctx.track != "t02":
        raise ValueError("T02 Laplacian baseline only supports track t02")

    images = pd.read_csv(ctx.input_dir / "images.csv", dtype={"image_id": str})
    required = {"image_id", "path", "split"}
    missing = required - set(images.columns)
    if missing:
        raise ValueError(f"images.csv missing columns: {sorted(missing)}")

    images["laplacian_variance"] = [
        laplacian_variance(load_rgb(ctx.input_dir / p)) for p in images["path"]
    ]
    # Lower sharpness is more suspicious. This is one global score across all
    # cameras and lighting conditions, matching the assignment baseline.
    images["score"] = -images["laplacian_variance"]
    images["reason"] = "global_laplacian"
    pool = images[images["split"] == "eval"]
    if pool.empty:
        pool = images

    budget = int(ctx.param("budget", 20))
    queue = make_review_queue(
        pool, id_col="image_id", score_col="score", budget=budget,
        reason_col="reason", evidence_col="path",
    )
    write_review_queue(queue, ctx.out("review_queue.csv"))
    images[["image_id", "score"]].to_csv(ctx.out(spec.pred_file), index=False)
    ctx.stats["n_items"] = len(images)
    ctx.stats["review_budget"] = min(budget, len(pool))
    write_decision(
        Decision(
            status="HOLD", reason_code="BASELINE_ONLY",
            reason="Laplacian baseline is for ranking comparison; human release decision required.",
            owner=ctx.config.get("owner", "T02 baseline"), scope=ctx.track,
            evidence=[str(ctx.out(spec.pred_file))],
        ),
        ctx.out("decision.json"), ctx.out("decision_log.csv"),
    )
