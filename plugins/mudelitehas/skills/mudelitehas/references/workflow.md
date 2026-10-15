# Validated workflow

- Version: 0.1.0, test release.
- Command: `Mudelitehas 10000 3 jalutav mängukaru animatsiooniga`.
- Runtime: Blender 4.5.3, Python 3.12 for reconstruction; Blender Python 3.11 with Pillow.
- Reconstruction packages: NumPy, SciPy, Pillow, Open3D 0.19.0.
- Outputs: primary body exactly 10000 quads, 23 bones, eight corrective shape keys, main and LOD GLB, BLEND, actual rendered GIF, reports and intermediate point cloud.

Use an empty work directory or an existing directory marked by `.mudelitehas-run.json`. The installed skill is a source bundle and is not a working directory. The runner copies recipe and references into the run, validates reference hashes, captures stage logs, stops on nonzero Blender exit codes, and records its version and hashes in `output/run_manifest.json`.

Resume invalidates reconstruction, neutral mesh, skin/pose, finish and preview separately using source and reference fingerprints. A pose-only change can reuse the existing material-bearing model. A material-only change reuses the neutral mesh and posed cache. Deleted or incomplete results must be regenerated before a success is reported. Changing the primary budget is not implemented in this test recipe.

Canonical public example and releases: https://github.com/orogdor/blender-cloud-test/tree/main/plugins/mudelitehas

The original user-reviewed walking teddy files are distributed as the v0.1 example. A rebuilt output may differ in bytes across operating systems or dependencies; geometric and animation checks establish compatibility rather than bit-for-bit identity. The canonical example's checksums identify that exact original model.
