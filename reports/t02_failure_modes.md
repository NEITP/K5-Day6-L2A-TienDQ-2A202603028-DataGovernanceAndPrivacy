# T02 failure mode review (input-only)

This inspection uses `images.csv`, the generated `ranked_review.csv`, and the
synthetic images only. It does not read `gt/`; therefore these are visual and
algorithmic failure-mode candidates, not confirmed false positives/negatives.

![Input-only examples: low-scoring night scenes, local glare, a cam_B dev sample, and a visibly blurred cam_B eval image](t02_failure_examples.png)

## Night scenes that may be useful but rank low

The night eval slice contains 16 images. Several night images with moderate
visual detail have low scores and fall outside the review budget of 20 across
the whole eval pool:

| Image | Score | Reason | Mean brightness | Dark-pixel fraction | Laplacian variance |
|---|---:|---|---:|---:|---:|
| `img_03_0` | 0.000037 | compression | 33.60 | 0.537 | 353.53 |
| `img_03_1` | 0.033676 | glare | 33.50 | 0.534 | 1859.77 |
| `img_13_1` | 0.039097 | glare | 34.79 | 0.546 | 2263.33 |
| `img_13_0` | 0.054297 | glare | 34.86 | 0.542 | 2231.74 |
| `img_01_1` | 0.059989 | glare | 31.61 | 0.633 | 1949.61 |

These are plausible hard negatives: low brightness and many dark pixels are
normal for night scenes, while the strong Laplacian values suggest visible
edges remain. Root cause: brightness signals can still increase suspicion
even when normalized within a lighting slice; the model has no semantic
measure of whether road users or plates remain usable. `img_03_0` also shows
how the blockiness proxy can label a night image for compression. Inspect at
full size and use instructor labels before calling these errors.

## Local glare can dominate an otherwise sharp image

`img_17_2` is a daytime eval image with score 0.345697 and reason `glare`.
Its global saturated fraction is 0.241, while the most saturated 20-pixel
tile is 1.0. This is consistent with a localized bright region, and the
contact sheet shows a large washed-out area. `img_05_3` is another candidate:
global saturated fraction 0.011, but the brightest tile fraction is 0.695.
The local-tile feature helps surface concentrated glare, but it cannot tell
whether the affected region covers a critical plate or harmless sky. Reviewer
escalation is reasonable until ROI relevance is checked.

## Camera-dependent sharpness / cam_B

On the dev set, median Laplacian variance is 955.0 for cam_A day (n=24) and
235.8 for cam_B day (n=12); cam_B dusk is 174.5 (n=4). This supports the
concern that a global sharpness threshold would treat camera characteristics
as defects. The PoC calibrates sharpness by camera and lighting when there are
at least four dev examples, but the small cam_B dusk group is fragile and can
include corrupted examples that shift its reference. For instance,
`img_15_2` (cam_B, dusk) has Laplacian variance 1.91 and score 0.222108; the
image is visibly blurred and was marked SKIP in the current review, so it
needs a human KEEP/RECAPTURE decision rather than automatic attribution to
camera optics. The median comparison alone cannot distinguish softer optics
from actual blur; inspect matched clean images and obtain GT labels.

## Current reviewer disposition

The current CSV has 2 RECAPTURE, 6 KEEP, 8 SKIP, and 4 HOLD among the 20
queued images. In particular, dark-scene candidates should not all be treated
as unusable solely because of brightness. Keep the batch decision at HOLD
until SKIP/HOLD rows are resolved. After the instructor GT is available,
report Recall@20 and Precision@20 for both the global Laplacian baseline and
the PoC without retuning on eval.
