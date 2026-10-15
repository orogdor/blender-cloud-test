---
name: mudelitehas
description: Build, inspect and collect feedback for Mudelitehas 3D workflows. Version 0.1.2 requires per-point placement checks in at least three views and three independent directions before meshing every new model. Use for Mudelitehas commands, cloud-to-mesh reconstruction, 5000-quad sedan tests, GLB/BLEND exports and neutral-pose rigging. Includes one reviewed car recipe and historical teddy reproduction; not an arbitrary creature generator.
---

# Mudelitehas 0.1.2

## Required method for every new model

Read and apply [three-view-policy.md](references/three-view-policy.md) FIRST. Locate/check EVERY cloud point in at least three views spanning three independent directions (prefer front/side/top). Front plus rear does not provide an extra direction. Save per-point image coordinates, projection errors, attempted/support flags and unresolved depth assumptions BEFORE creating faces. Do not count a silhouette-compatible point as an identified feature match or silently force all points to pass. Report support and conflicts honestly.

Use `scripts/run_car.py --workdir <new-empty-work-directory> --blender <Blender-4.5.3>` for the reviewed 4319.png sedan recipe: 5000 TOTAL quads including wheels/details. It regenerates the saved cloud, runs the three-direction witness gate before meshing, builds the car and validates the actual GLB. It does not accept arbitrary cars or budgets. Read [car-workflow.md](references/car-workflow.md).

For other new objects and living subjects, create and validate a matching recipe under the same three-direction rule. Keep neutral-pose, anatomy, quad-count, deformation and export checks. Missing top/depth evidence must be added or explicitly reported; never pretend a two-direction legacy recipe satisfies 0.1.2.

Preserve the sequence: requested-pose image → same identity in neutral four views → oriented point cloud saved before mesh → neutral mesh → skeleton/skin → animation → validation. Use T-pose for this biped teddy. Never reconstruct a posed/folded character as its rest mesh or sample an existing mesh to fake the point-cloud stage.

## Reproduce the historical teddy example

Use this section only for reproduction/regression of the original teddy. Its original four references span TWO axes and do not meet the new-model 0.1.2 rule. Do not use it as the default for new models or claim old model binaries were improved by this update.

1. Read [workflow.md](references/workflow.md) for the exact supported command and requirements. Keep the 10000-quad budget scoped to the primary body; report separate face and fiber geometry.
2. Run `scripts/run.py --workdir <new-empty-work-directory> --blender <Blender-4.5.3> --preview quick`. Use `--mode resume` for repeats. Set `MUDELITEHAS_PYTHONPATH` to the directory containing Blender-compatible Pillow if it is not installed in Blender's Python.
3. Inspect `output/Control_views.jpg` and the GIF from the actual model. A successful process or a watertight mesh alone does not establish visual quality.
4. Inspect `validation.json`, `pipeline.json`, `run_manifest.json` and `export_reimport_validation.json`. Confirm the actual GLB has skin, animation and synchronized corrective morph targets; do not claim an untested export works.
5. Save user-facing outputs using the available file-saving workflow. Return the animated GLB, editable BLEND, preview and relevant limitations. Keep logs and cached intermediates for repairs; do not deliver runtime binaries.

Use `--preview none` for an inexpensive geometry/animation build. Render previews later with `--preview full`; preserve the mesh and textures. Use `--mode verify` to validate existing outputs without reconstructing them. Never force a rebuild merely because a previous chat ended.

## Handle new requests

Treat `Mudelitehas 10000 3 jalutav mängukaru animatsiooniga` as the reproducible v0.1 example. Do not silently reinterpret a different subject, budget, pose or quality level as this teddy. The runner rejects unsupported command text. For a new character, prepare and visually inspect its requested-pose image and neutral four views, then implement and test a matching reconstruction/anatomy recipe. Do not imply the current teddy recipe supports humans, quadrupeds or arbitrary creatures.

Keep source image generation separate from the Blender runner. This package contains reviewed generated references; GitHub Actions does not call image generation automatically. Hidden depth and joints remain estimates, not measurements. Read [limitations.md](references/limitations.md) before extending the recipe.

## Collect feedback

When asked for feedback reporting, run `scripts/feedback.py --workdir <run> --category <category> --description <text> [--frame N]`. Return the local bundle and generated issue link. Do not open or send an issue automatically. The bundle contains version, run ID, hashes and selected checks; models, screenshots, raw logs and environment variables are not included by default.

When fixing a reported defect, retain the original inputs and version, reproduce it first, change the affected stage, and verify both the failing case and the teddy baseline. Bump the version for distributed changes. Do not rewrite old release results or report that all old assets were repaired by changing instructions.
