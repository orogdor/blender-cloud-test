# Blender Cloud + Three.js

This repository runs Blender inside GitHub Actions, generates an armored soldier as GLB and BLEND, renders previews, and publishes a mobile Three.js viewer using GitHub Pages.

## Steps
1. GitHub repository Settings → Pages → Build and deployment → Source: GitHub Actions.
2. Actions → Blender soldier and Three.js → Run workflow (or push to main).
3. See the 3D viewer at https://orogdor.github.io/blender-cloud-test/ after successful deployment.
4. Download source `.blend`, `.glb`, and PNG previews from the workflow artifact `soldier-build-output`.

This is a procedural prototype, without realistic anatomy or animation. The full Blender script is in `scripts/create_soldier.py`.
