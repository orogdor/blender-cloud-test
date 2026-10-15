# Mudelitehas 0.1.2 — new-model default

For EVERY new model, place/check every pre-mesh point in at least three views and three independent viewing directions (prefer front/side/top). Front plus rear is one axis. Save point witnesses and residuals; report unresolved and inferred points instead of fabricating feature matches. Apply the same rule to neutral-pose living subjects. Use the packaged `plugins/mudelitehas/skills/mudelitehas/references/three-view-policy.md` and `scripts/check_multiview.py`.

The reviewed 5000-total-quad sedan implements the policy. Legacy two-axis reconstruction recipes are historical reproduction only and must not silently create new 0.1.2 models. Updating instructions does not repair old assets.

# Mudelitehas instructions

For every new Mudelitehas model request, read `mudelitehas/README.md`,
`mudelitehas/POSE_WORKFLOW.md`, and the chosen profile before preparing images or
creating a Blender job. Preserve the command form and exact primary quad budget.

For living subjects, separate the requested pose from the reconstruction pose:
requested-pose 2D concept -> same character in neutral four-view references ->
point cloud -> mesh in neutral pose -> skeleton/skin -> requested pose via
animation -> final validation. Humans use a T pose; ordinary quadrupeds stand
on four legs. Review custom creatures' anatomy before selecting a skeleton.

Do not reconstruct a seated/folded/crossed character directly as its rest mesh.
Do not replace the genuine point-cloud-before-mesh stage by sampling an existing
model. Preserve reference identity, document inferred depths and joints, check
limb separation, rounded organic cross sections, deformations, self-intersections
and stance contacts. Smooth shading alone does not correct blocky geometry.

The existing teddy and sitting-dog scripts are legacy posed-reference examples,
not compliant templates for the new neutral-pose character workflow. A living
subject requires its own skeleton/pose recipe; do not deliver the static level 1
base output as if it were a rigged posed character. Never mark a visual-review
manifest approved without inspecting the actual reference images.

Do not claim the old model files are repaired by changing instructions or
configuration. Report actual generated assets and tests separately from plans.
