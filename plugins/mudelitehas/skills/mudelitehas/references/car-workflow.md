# Reviewed sedan recipe

Use the bundled 4319.png four-view image only. No image generation or external model service is called. Exact budget: 5000 total quads / 10000 exported triangles; body 3400, wheels 1440 and other details 160. Original reviewed model: 83,747 cloud points, 79.22% three-axis silhouette support at 3 px. These are baseline measurements, not guarantees for other inputs.

Run `python scripts/run_car.py --workdir <empty-directory> --blender <Blender-4.5.3>`. Repeats require `--rebuild` and a marked car run. Use an execution-capable environment with NumPy, SciPy, Pillow and Blender 4.5.3. `scripts/install_runtime.py` can prepare the pinned Linux x64 Blender. The car recipe uses only Blender's bundled Python modules; it does not need Pillow inside Blender.

The runner copies reviewed inputs and recipe into the work directory, checks source integrity, reconstructs the independent cloud, executes the witness gate before forming faces, builds and exports the mesh, reimports GLB, then generates diagnostic renders, CSV and a model ZIP. On failure inspect logs; do not overwrite an unrelated directory. Feedback uses the shared local `feedback.py` helper and run_manifest.json.

Expected outputs: Auto_5000_3vaate_test.glb/.blend, three_direction_gate.json, three_view_test.json, validation.json, export_reimport_validation.json, the pre-mesh cloud NPZ/PLY, point witness CSV, reprojection image and actual control renders.

The cross-sections, symmetry, wheel/mirror depths and scale are priors. All points are attempted in all four registered views, but not all points pass. Hidden points are not independently identified in three images. Texture projection seams remain at some transitions, especially rear/top. It is a static image-guided game model with no built interior, not CAD or calibrated photogrammetry. Preserve these limitations when sharing the example.
