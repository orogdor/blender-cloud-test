# Mudelitehas 0.1.2: point placement in three directions

Apply this rule to every NEW model, living or rigid, at all quality levels.

1. Obtain and visually inspect at least three usable views spanning three independent viewing directions, preferably front, side and top. Retain four or more views when supplied. Front and rear are one axis, not two independent directions. Do not count a mirrored copy as another measured view. If evidence is missing, prepare the needed view or disclose the missing direction; do not claim compliance from two directions.
2. Register projection matrices, image coordinates, source hashes, silhouettes, feature traces and scale assumptions. Separate actual observations from synthetic views and shape priors. For living subjects use a neutral rig-friendly pose before point placement; preserve the requested-pose concept separately.
3. Place a genuine dense point cloud BEFORE making faces. For EACH point, attempt its location in at least three views and three directions. Save every tested image coordinate, residual, attempted/support flag, view order and axis assignment. Prefer identifiable surface landmarks where visible. Mark occluded or ambiguous points as inferred, not triangulated.
4. Use bounded, regularised fitting. Retain contradictory constraints and unresolved points in the report. Do not crush a surface into degenerate faces to achieve a 100% support score, remove difficult points without disclosure, or widen tolerances just to pass.
5. Save the cloud and run `scripts/check_multiview.py --cloud <npz> --calibration <json> --output <report.json>` BEFORE mesh creation. Use the documented car witness format: points N×3, reference_pixels N×V×2, signed_silhouette_distance_px N×V, view_support N×V, axis_support N×3; calibration contains view_order, projection_jacobians V×2×3 and projection_offsets V×2. With other camera models, implement an equivalent explicit witness checker and document the model rather than falsifying affine matrices.
6. Reconstruct/retopologise the checked cloud with an object-appropriate recipe. Preserve the requested quad budget and report whether it covers the primary body or the whole object. The car reference uses 5000 total quads; the historical teddy uses 10000 primary-body quads.
7. Reimport GLB, validate geometry and any required skin/animation, and inspect actual front/side/top/oblique renders. Report silhouette IoU and point support separately from visual quality. Silhouette overlap is NOT proof of correct depth or a match of the same feature across three images.
8. Deliver the model, cloud, per-point witnesses, calibration, residual report, previews and limitations. State the observed support percentage and unresolved count. Do not carry the car's 79.22% score to another model.

## Implemented scope

`run_car.py` implements this method for the reviewed 4319.png sedan reference with a structured cloud-to-quad recipe. It is an image-guided approximation with rounded-section and depth priors, not photogrammetry or a general car generator. The rear/top texture seams are known limitations.

`run.py` retains the historical teddy recipe as a regression/reproduction route. Its original front/rear/left/right references span only two independent axes. It is explicitly exempt as historical reproduction, NOT evidence that it meets the new rule. For a NEW teddy or character, add the missing neutral-pose direction and rebuild its recipe under this policy. Never label old binaries as repaired or revalidated merely because these instructions changed.
