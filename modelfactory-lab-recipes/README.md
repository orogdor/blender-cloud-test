# ModelFactory Lab shared recipes

Common catalog for updated Blender-free ModelFactory Lab installations.

- Configuration: `orogdor/blender-cloud-test`, branch `main`, folder `modelfactory-lab-recipes`.
- `catalog.json`: immutable source versions, delivered model fingerprints and explicit shape feedback.
- `bundles/<sha256>.json`: source bytes and per-file hashes. Downloading does not execute source.
- `shared_recipes.py`: standard-library client, pending offline queue, GitHub compare-and-swap writes, pool ranking and weighted random selection.
- All source versions remain archived. An exact family/kind/quad-budget/level pool has at most 10 active versions.
- Only a technically accepted delivered model with an explicit user shape rating 5 qualifies its source version. Failed geometry plus a 5 is not eligible.
- One latest score per delivery; later corrections are not extra votes. Rank by conservative five-star satisfaction, then mean and number of fives. More consistently satisfying new versions displace weaker active versions; archived versions are not deleted.
- Every delivered model needs its own 1–5 shape question. Batch models have separate delivery IDs and ratings. No rating is inferred from praise.
- The imported V4 explorer and V5 spearman are **needs_repair**, unrated source checkpoints, not approved backup recipes. Their archived source declares external inputs and device-path adaptations; they must not be advertised as portable validated recipes.

Read access to this public catalog needs connectivity. Writes require the connected GitHub app or a write-authorized `gh`/`GH_TOKEN`/`GITHUB_TOKEN` on that device. Tokens are never packaged. Offline changes stay device-local until flush succeeds. A local plugin still needs an agent and Python execution. Existing old plugin copies must be updated; merely adding this folder does not alter old installations.

The current ModelFactory Lab skill's `references/shared-recipes.md` defines the full agent workflow. Feedback updates recipe selection; it does not train an AI or automatically fix geometry. GPT authors and tests source improvements.

Tests: `python -m unittest test_shared_recipes.py` with the Lab's `lab_isolation.py` on PYTHONPATH. Test fixtures never write ratings to this production catalog.
