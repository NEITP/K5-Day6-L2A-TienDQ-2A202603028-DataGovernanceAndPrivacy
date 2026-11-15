"""YOUR PoC PIPELINE — this is the file your group owns.

Lab contract = 5 automated steps, run by `python -m src.main ...`:
    01 load      input + provenance check (manifest.csv)
    02 process   your algorithm / model (the research part)
    03 rank      prioritise for a fixed review budget B
    04 review    human-in-the-loop: queue -> reviewer decisions -> overrides + audit log
    05 decide    GO / HOLD / REWORK (or track equivalent) with reason_code + owner, write outputs

Required output: out/<pred_file> with the columns listed for your track in
docs/tracks/TXX.md (also in src/metrics/tracks.py::TRACKS). Then evaluate with
    python -m src.evaluate --track tXX --pred out/<pred_file>

Rules: never read fixtures/*/gt/ here (the GT guard will stop you); seed everything via ctx.rng;
no network calls; fail loudly on missing models instead of downloading.
See src/examples/random_baseline.py for a minimal end-to-end wiring example.
"""
from __future__ import annotations

import pandas as pd

from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.manifest import verify_manifest
from .common.review import load_review_decisions, make_review_queue, write_review_queue
from .metrics.tracks import get_track

import numpy as np

from .common.image_ops import brightness_stats, laplacian_variance, load_rgb
from .common.contact_sheet import render_contact_sheet


def _jpeg_blockiness(img: np.ndarray) -> float:
    """Estimate JPEG blocking from 8-pixel boundary differences."""
    gray = (0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]).astype(float)
    dx = np.abs(np.diff(gray, axis=1))
    dy = np.abs(np.diff(gray, axis=0))
    x_boundary = np.arange(1, gray.shape[1]) % 8 == 0
    y_boundary = np.arange(1, gray.shape[0]) % 8 == 0
    boundary = np.concatenate([dx[:, x_boundary].ravel(), dy[y_boundary, :].ravel()])
    interior = np.concatenate([dx[:, ~x_boundary].ravel(), dy[~y_boundary, :].ravel()])
    if not len(boundary) or not len(interior):
        return 0.0
    return float(boundary.mean() - interior.mean())


def _local_saturation(img: np.ndarray, tile_size: int = 20) -> float:
    """Largest share of very bright pixels in a small tile; a glare cue, not a detector."""
    gray = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    tile_rates = []
    for y in range(0, gray.shape[0], tile_size):
        for x in range(0, gray.shape[1], tile_size):
            tile = gray[y:y + tile_size, x:x + tile_size]
            tile_rates.append(float((tile > 245).mean()))
    return max(tile_rates, default=0.0)



# ---------------------------------------------------------------- 01 load
def load(ctx: RunContext) -> dict:
    manifest = ctx.input_dir / "manifest.csv"
    problems = (
        verify_manifest(manifest)
        if manifest.exists()
        else [{"problem": "no_manifest"}]
    )

    if problems:
        if ctx.audit:
            ctx.audit.log(
                actor="pipeline",
                action="provenance_problems",
                item_id=str(manifest),
                after=problems[:20],
            )
        if ctx.config.get("strict_provenance", True):
            raise ValueError(
                f"provenance check failed ({len(problems)} problems), "
                f"first: {problems[:3]}"
            )

    images = pd.read_csv(ctx.input_dir / "images.csv", dtype={"image_id": str})
    required = {"image_id", "path", "camera_id", "light", "split"}
    missing = required - set(images.columns)
    if missing:
        raise ValueError(f"images.csv missing columns: {sorted(missing)}")
    if images["image_id"].duplicated().any():
        raise ValueError("images.csv has duplicate image_id values")

    missing_files = [
        path for path in images["path"]
        if not (ctx.input_dir / path).is_file()
    ]
    if missing_files:
        raise ValueError(
            f"images.csv references missing images: {missing_files[:5]}"
        )

    return {
        "manifest": pd.read_csv(manifest) if manifest.exists() else None,
        "images": images,
    }



# ---------------------------------------------------------------- 02 process
def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    images = data["images"].copy()
    rows = []

    for row in images.itertuples(index=False):
        img = load_rgb(ctx.input_dir / row.path)
        rows.append({
            "image_id": str(row.image_id),
            "path": row.path,
            "camera_id": row.camera_id,
            "light": row.light,
            "split": row.split,
            "lap": laplacian_variance(img),
            "blockiness": _jpeg_blockiness(img),
            "local_saturated": _local_saturation(img),
            **brightness_stats(img),
        })

    scored = pd.DataFrame(rows)
    dev = scored[scored["split"] == "dev"]
    if dev.empty:
        raise ValueError("No dev images available for feature calibration")

    def outlier_score(value, reference, direction):
        reference = np.asarray(reference, dtype=float)
        median = float(np.median(reference))
        mad = float(np.median(np.abs(reference - median)))
        scale = max(1.4826 * mad, abs(median) * 0.05, 1e-3)

        delta = median - value if direction == "low" else value - median
        return float(np.clip(delta / (3 * scale), 0, 1))

    scores = []
    reasons = []

    for row in scored.itertuples(index=False):
        same_camera_light = dev[
            (dev["camera_id"] == row.camera_id) &
            (dev["light"] == row.light)
        ]
        same_camera = dev[dev["camera_id"] == row.camera_id]
        same_light = dev[dev["light"] == row.light]

        # Sharpness depends on camera; fall back to camera-level reference
        # if this camera/light combination is missing from dev.
        sharp_ref = same_camera_light["lap"]
        if len(sharp_ref) < 4:
            sharp_ref = same_camera["lap"]
        if len(sharp_ref) < 4:
            sharp_ref = dev["lap"]

        # Brightness and saturation are compared within the same lighting
        # condition so normal night images are not judged against daylight.
        light_ref = same_light if len(same_light) >= 4 else dev

        blur_score = outlier_score(row.lap, sharp_ref, "low")
        dark_score = 0.5 * (
            outlier_score(row.mean, light_ref["mean"], "low") +
            outlier_score(row.frac_dark, light_ref["frac_dark"], "high")
        )
        glare_score = outlier_score(
            row.frac_saturated, light_ref["frac_saturated"], "high"
        )
        local_glare_score = outlier_score(
            row.local_saturated, light_ref["local_saturated"], "high"
        )
        compression_ref = same_camera_light["blockiness"]
        if len(compression_ref) < 4:
            compression_ref = same_camera["blockiness"]
        if len(compression_ref) < 4:
            compression_ref = dev["blockiness"]
        compression_score = outlier_score(
            row.blockiness, compression_ref, "high"
        )
        glare_score = 0.5 * glare_score + 0.5 * local_glare_score

        component_scores = {
            "blur": blur_score,
            "dark": dark_score,
            "glare": glare_score,
            "compression": compression_score,
        }
        scores.append(
            0.40 * blur_score + 0.25 * dark_score +
            0.20 * glare_score + 0.15 * compression_score
        )
        reasons.append(max(component_scores, key=component_scores.get))

    scored["score"] = scores
    scored["reason"] = reasons
    return scored


# ---------------------------------------------------------------- 03 rank
def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    """Build a review queue from the held-out evaluation pool."""
    budget = int(ctx.param("budget", 20))
    if "score" not in scored.columns:
        raise ValueError("rank(): process() output needs a numeric `score` column (higher = review first), "
                         "or adapt rank() to your track")

    review_pool = scored
    if "split" in scored.columns:
        eval_pool = scored[scored["split"] == "eval"]
        if not eval_pool.empty:
            review_pool = eval_pool

    q = make_review_queue(
        review_pool,
        id_col="image_id" if "image_id" in review_pool.columns else review_pool.columns[0],
        score_col="score",
        budget=budget,
        reason_col="reason" if "reason" in review_pool.columns else None,
        evidence_col="path" if "path" in review_pool.columns else None,
    )
    write_review_queue(q, ctx.out("review_queue.csv"))
    if "evidence_path" in q.columns:
        render_contact_sheet(
            q,
            ctx.out("contact_sheet.html"),
            image_root=ctx.input_dir,
            title=f"{ctx.track.upper()} review queue",
        )
    return q


# ---------------------------------------------------------------- 04 review
def review(ctx: RunContext, scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    reviewed_path = ctx.output_dir / "review_queue_reviewed.csv"
    if not reviewed_path.exists():
        return scored

    reviewed = load_review_decisions(reviewed_path)

    if reviewed["item_id"].duplicated().any():
        raise ValueError("review file has duplicate item_id values")

    queue_ids = set(queue["item_id"].astype(str))
    unknown = set(reviewed["item_id"].astype(str)) - queue_ids
    if unknown:
        raise ValueError(f"review contains items outside the queue: {sorted(unknown)[:5]}")

    out = scored.copy()
    out["review_action"] = ""

    for row in reviewed.itertuples(index=False):
        decision = row.reviewer_decision

        if decision == "approve":
            action = "KEEP"
        elif decision == "reject":
            action = "RECAPTURE"
        elif decision == "edit":
            action = str(row.override_value).strip().upper()
            if action not in {"KEEP", "RECAPTURE"}:
                raise ValueError(
                    "edit requires override_value KEEP or RECAPTURE "
                    f"(item_id={row.item_id})"
                )
        elif decision == "escalate":
            action = "HOLD"
        else:  # skip
            action = "SKIP"

        mask = out["image_id"].astype(str) == str(row.item_id)
        if not mask.any():
            raise ValueError(f"review item not found in predictions: {row.item_id}")

        ctx.audit.log(
            actor=row.reviewer,
            action=f"review:{decision}",
            item_id=row.item_id,
            after=action,
            reason=row.review_note,
        )
        out.loc[mask, "review_action"] = action

    ctx.stats["n_reviewed"] = len(reviewed)
    return out



# ---------------------------------------------------------------- 05 decide
def decide(ctx: RunContext, final: pd.DataFrame) -> Decision:
    """Reviewer-gated batch decision for T02.

    SKIP/HOLD or an incomplete review leaves the batch on HOLD. Once every
    queued item has a KEEP/RECAPTURE action, any RECAPTURE makes the batch
    RECAPTURE; otherwise it is KEEP. This is an operational policy, not a
    quality claim based on hidden evaluation labels.
    """
    owner = str(ctx.config.get("owner", "")).strip()
    if not owner or owner.upper().startswith("TODO"):
        owner = "T02 reviewer / data owner"

    if "review_action" in final.columns:
        actions = final["review_action"].fillna("").astype(str).str.upper()
    else:
        actions = pd.Series("", index=final.index, dtype=str)
    counts = actions[actions != ""].value_counts().to_dict()
    n_items = int(ctx.stats.get("n_items", len(final)))
    unresolved = int(counts.get("HOLD", 0) + counts.get("SKIP", 0))
    queue_path = ctx.output_dir / "review_queue.csv"
    if queue_path.exists():
        queue_ids = set(pd.read_csv(queue_path, dtype={"item_id": str})["item_id"].astype(str))
        reviewed_ids = set(final.loc[actions.ne(""), "image_id"].astype(str))
        unreviewed = len(queue_ids - reviewed_ids)
    else:
        unreviewed = int(ctx.stats.get("review_budget", 20))
    metrics = {
        "reviewed_actions": {k: int(v) for k, v in counts.items()},
        "n_items": n_items,
        "review_budget": int(ctx.stats.get("review_budget", 20)),
        "unresolved_review_items": unresolved,
        "unreviewed_queue_items": unreviewed,
    }
    evidence = [str(ctx.output_dir / "ranked_review.csv"), str(ctx.output_dir / "review_queue.csv")]
    reviewed_path = ctx.output_dir / "review_queue_reviewed.csv"
    if reviewed_path.exists():
        evidence.append(str(reviewed_path))

    if unresolved or unreviewed:
        return Decision(
            status="HOLD",
            reason_code="REVIEW_INCOMPLETE",
            reason=f"Human review is incomplete: {unresolved} unresolved and {unreviewed} unreviewed queue items.",
            owner=owner,
            scope=ctx.track,
            evidence=evidence,
            metrics=metrics,
        )
    if counts.get("RECAPTURE", 0):
        return Decision(
            status="RECAPTURE",
            reason_code="REVIEW_FOUND_RECAPTURE_ITEMS",
            reason=f"Reviewer marked {counts['RECAPTURE']} item(s) for recapture; recapture before release.",
            owner=owner,
            scope=ctx.track,
            evidence=evidence,
            metrics=metrics,
        )
    return Decision(
        status="KEEP",
        reason_code="REVIEW_APPROVED_ALL_ITEMS",
        reason="All queued items were reviewed and marked KEEP.",
        owner=owner,
        scope=ctx.track,
        evidence=evidence,
        metrics=metrics,
    )


def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)
    data = load(ctx)
    scored = process(ctx, data)
    ctx.stats["n_items"] = len(scored)
    queue = rank(ctx, scored)
    ctx.stats["review_budget"] = len(queue)
    final = review(ctx, scored, queue)
    final[spec.pred_columns + [c for c in final.columns if c not in spec.pred_columns]].to_csv(ctx.out(spec.pred_file), index=False)
    write_decision(decide(ctx, final), ctx.out("decision.json"), ctx.out("decision_log.csv"))
