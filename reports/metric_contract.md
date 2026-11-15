# T02 Metric Contract — Raw QC Triage

This records the evaluator contract used for the experiment. Ground-truth labels are not present in the student checkout, so no evaluation metric is reported or used for tuning.

| Item | Frozen protocol |
|---|---|
| Track | T02 · Raw QC Triage |
| Primary metric | Defect Recall@B |
| Direction | Higher is better |
| Unit | Image |
| Formula | TP / (TP + FN); TP = GT defect images in the top B; denominator = all GT defect images in eval |
| Secondary metric | Precision@B = GT defect images in top B / B |
| Prediction-to-GT join | Exact `image_id`; evaluator filters to GT `split=eval` |
| Candidate pool | 40 eval images from the fixed 96-image fixture; scene-group split |
| Review budget | B=20 |
| Seed | 42 |
| PoC score policy | Fixed weighted anomaly score: blur 0.40, dark 0.25, glare 0.20, compression 0.15; robust feature references from dev by camera/light with fallback |
| Baseline policy | One global Laplacian sharpness signal, ranked by inverse variance; no label-based threshold fitting |
| Eval split | `eval`; never used for reference calibration, weights, or policy tuning |
| Error reporting | Recall misses = GT defects outside top 20; false alarms = non-defects inside top 20; both require GT |
| Slices | `light` (day/dusk/night) and `camera_id` (cam_A/cam_B) |
| Uncertainty | Report counts and denominators; if instructor requests intervals, bootstrap over eval images with fixed predictions and disclose small N. Not computable before GT is supplied. |
| Freeze record | 2026-11-15 · Owner/reviewer: Đinh Quốc Tiến; code/config are in the current working tree and not yet committed under the student's Git identity. |

Budget, pool, seed, and score definitions are held fixed for baseline and PoC. Do not change them after inspecting official eval results. If the baseline or PoC produces zero, report zero directly; do not report a percentage gain from a zero denominator.
