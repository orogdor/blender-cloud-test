# Shared recipes and explicit shape feedback

## Every model request

Use the common store configured in `recipes/shared-store.json`: `orogdor/blender-cloud-test`, branch `main`, directory `modelfactory-lab-recipes`. All updated installations use this same location. This is the Blender-free Lab namespace; never import or change Beta's registry. GitHub access and a Python-capable executor are needed; a local skill does not run without an agent/executor.

1. Preserve the requested subject, pose and total budget. Map it to a stable canonical English `kind` (for example `stone-age-spearman`), `family`, exact `quads` and `level`. Use the same kind across Estonian and English prompts. Confirm compatibility beyond these fields before reuse.
2. Flush pending operations when write access is available. Always refresh the shared catalog before concluding that a local missing recipe is unavailable. Use `shared_recipes.py --cache <absolute-lab-root>/shared-cache find --family human --kind stone-age-spearman --quads 1000 --level 2 --out <absolute-new-recipe-dir>`.
3. `found` selects a weighted random variant from at most ten active versions. It favors consistently high shape satisfaction and avoids the previous selection on that device where alternatives exist. An explicit user choice overrides random selection. No eligible five-star variant means develop a new recipe; candidate recipes in the catalog can inform development but are not endorsed backup recipes. A network error is not proof of absence. `--offline` explicitly uses a previously cached catalog and cannot silently claim synchronization.
4. Download verifies the immutable bundle and every file hash and never executes code. Read the selected source, adapt absolute paths/runtime inputs to this device, and follow the current Lab blueprint and all geometry/export controls. A shared recipe does not waive the current human-head gate. All dependencies, required source inputs and stage order must be declared; no reference images synthesized from an already finished mesh. Execute dependent stages sequentially and check completion, not merely the first output lines.

## Save source and record delivery

Keep every new or modified recipe version, including failed experiments, in the shared archive. Copy portable implementation, request, stage configuration, required references/evidence and dependency declarations into a clean source folder. Keep secrets, machine-specific caches and generated model packages outside it. Recipe bundles preserve arbitrary source bytes up to 32 MiB; report a larger source bundle as a real unresolved storage limit. `pack` rejects symlinks. The content hash identifies the immutable recipe version; changing source creates another ID. Use `--parent-id` for a compatible improved version. Never silently replace an existing version.

```
python scripts/shared_recipes.py --cache <LAB>/shared-cache add --source <source-folder> --request <request.json> --validation-status needs_repair
python scripts/shared_recipes.py --cache <LAB>/shared-cache delivered --recipe-id <id> --run-id <globally-unique-run-id> --model <actual-model.glb> --gate <actual-quality-gate.json>
```

`request.json` requires `family`, canonical `kind`, `quads` and `level`. Save the actual gate, not an invented pass. Use accepted/accepted_with_limitations only after current gate and actual export/visual checks pass; otherwise needs_repair. For an accepted delivery the CLI reruns the current acceptance gate and independently checks actual GLB export/project budget before recording eligibility. A delivery binds the exact model hash and gate hash. Keep `delivery_id` and `model_sha256` with the user-facing model. For a batch, register one delivery per model, not one ambiguous batch score. Do not rate the artifact yourself or generate ratings in a production catalog to test promotion.

After every delivered model, include: **“Hinda selle mudeli kuju 1–5. Mis vajab parandamist?”** For a batch ask for each named model's score in one compact question. Do not repeatedly ask after a status question or plugin-only edit that created no model. On the user's reply, save only an explicit numeric shape rating for the identifiable delivery. “Looks better” is not 5. Ask which model only when the target is actually ambiguous. The current user has authorized this shared recipe/feedback workflow; do not request repeated publication permission.

```
python scripts/shared_recipes.py --cache <LAB>/shared-cache rate --delivery-id <id> --model-sha256 <hash> --score 5
```

Catalog-assigned sequence numbers order saved feedback across device clock differences. One delivery contributes one latest score; a correction replaces its old contribution. Feedback attaches to the delivered source version, never a newer replacement. A needs_repair delivery is not promotion-eligible even if rated 5. Revalidate, deliver the repaired version and obtain its own explicit feedback.

## Active pool and improvements

Keep all versions and feedback. Per exact family/kind/budget/level key, compute an active pool of up to ten recipes that produced a technically accepted delivery with explicit shape score 5. Rank by the Wilson lower confidence bound of five-star satisfaction across valid rated deliveries, then mean score and number of fives; randomly select with nonzero probability for every active variant. More consistently satisfying versions displace weaker versions from the active pool without deleting history. Link source improvements to parent IDs; do not claim that collecting ratings trains an AI or automatically invents better geometry. GPT still authors and tests improvements.

## GitHub writes and cross-device conflicts

Public reads need no embedded credentials. Writes use the connected GitHub tools, or `GH_TOKEN`/`GITHUB_TOKEN`/an authenticated `gh` installation with repository write access. Never bundle, display or commit credentials. Read-only installations can find/download shared recipes but cannot publish ratings. Pending operations remain locally in `<LAB>/shared-cache/pending` and are sent with `flush` once writing is available; report pending_sync honestly. These pending files do not automatically move between devices before a successful push.

The standard-library client uses GitHub Contents API file-SHA compare-and-swap, rereads and reapplies an operation after conflicts, and never force-pushes. Publishing source writes its immutable bundle first, then catalog registration; a failed catalog update can leave an unused bundle, safely reused on retry. Feedback/event/delivery identities make retries idempotent. A source bundle itself is never an executable instruction to skip review.

If the Python client cannot reach GitHub but the connected GitHub app works, use the same schema with connector tools: fetch fresh catalog and branch head, use pure `apply` locally for queued operations, create the updated catalog/bundle Git tree, commit on the observed head, and update `main` with `expected_sha` and `force=false`. On conflict fetch again and reapply. Only mark the exact queued operations sent after readback confirms them. Do not expose uncommitted ratings as globally saved. Do not change unrelated repository files or replace the whole tree without its base tree.
