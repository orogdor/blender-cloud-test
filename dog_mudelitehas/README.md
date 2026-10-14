# Mudelitehas sitting dog realism test

Separate test pipeline preserving the existing 2D -> four views -> point cloud -> mesh -> rig -> animation sequence.

The generated point cloud is saved before Poisson meshing. PBR UV maps, a canine sitting rig, skin motion checks, silhouette comparisons and a game LOD are produced by the Blender workflow. The anatomy and unseen depth are estimated; this is not a measured scan.

Run the `Mudelitehas Dog SitPretty realism test` workflow. The output includes animated GLB and BLEND files, a GIF rendered from the actual model, intermediate point cloud and all scripts.
