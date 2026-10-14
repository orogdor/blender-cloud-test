# Four View Mesh for Blender (prototype v0.1)

This is a **real installable Blender add-on**, intended for Blender 4.0 or later. It reconstructs a **watertight quad-face starter mesh** from four mutually aligned orthographic **silhouette** images (front/back/left/right). Optionally a top view can be included. It is **not** a complete AI photo-to-3D reconstruction method.

## Input image requirements

- Render four aligned, *orthographic* views of exactly the same object, front/back/left/right, with no perspective distortions. Same image size, scale, vertical alignment and pose.
- Use transparent background PNG images (opaque foreground) or dark object on white background; the silhouette, not the drawing detail, determines the initial mesh.
- Front/back views must be mirrored relative to one another; left/right likewise. The plugin respects this mapping.
- For concave surfaces and intricate internal detail, supply a **top silhouette**, depth maps, annotated landmarks, or a separate detailed 3D reconstruction step. Four contour views alone cannot reveal these features.

## Install locally in Blender

Go to Edit -> Preferences -> Add-ons -> Install from Disk and select `fourview/four_view_mesh.py` (or place it in Blender's addons folder). Enable it. Open a 3D Viewport, press N, find **Four View Mesh**. Fill PNG file paths, set approximate object dimensions and voxel resolution, then click **Build 3D Mesh from Views**. You can edit the generated quads or run QuadriFlow remesh for more regular topology. Export GLB via File -> Export -> glTF 2.0.

## Phone-only GitHub Cloud demo

Run **Actions > Four-view mesh reconstruction demo > Run workflow** in `orogdor/blender-cloud-test`. This creates four synthetic matching silhouette PNGs to validate the pipeline, then reconstructs a grey sci-fi armor/body *placeholder* in Blender and exports `.glb` and `.blend` files. Download the `four-view-mesh-prototype` artifact.

For real image input, the four ChatGPT-generated views need to be converted to consistent masks and uploaded as source files. A later upgrade can generate images, alignment metadata, depth maps, per-part meshes, materials, and topology constraints automatically.

## Limits

The mesh is constructed from the intersection of view silhouettes (visual hull): it can reproduce **outer volume**, but not recesses, correct anatomy, interior surfaces, small equipment or fine topology. The base is made from closed quad surfaces; a smooth modifier softens the voxel grid but does not produce animation-ready edge loops. QuadriFlow retopology and guided landmark fitting are separate postprocessing steps. Automated topology cannot be certified as production-ready without inspection.