bl_info = {
    'name': 'Four View Mesh (Visual Hull Prototype)',
    'author': 'OpenAI',
    'version': (0, 1, 0),
    'blender': (4, 0, 0),
    'location': 'View3D > Sidebar > Four View Mesh',
    'description': 'Create a starting watertight quad surface from aligned orthographic silhouette PNGs',
    'category': 'Mesh',
}

import bpy
from bpy.props import StringProperty, IntProperty, FloatProperty, BoolProperty
import numpy as np


def read_mask(filename, threshold=0.5):
    """Use PNG alpha when present, otherwise dark foreground on a light background."""
    if not filename:
        return None
    path = bpy.path.abspath(filename)
    image = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = image.size[:]
        pixels = np.empty(w * h * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        data = pixels.reshape((h, w, 4))
        alpha = data[:, :, 3]
        if float(np.min(alpha)) < 0.95:
            foreground = alpha >= threshold
        else:
            rgb = data[:, :, :3]
            intensity = rgb[:, :, 0] * .2126 + rgb[:, :, 1] * .7152 + rgb[:, :, 2] * .0722
            foreground = intensity < threshold
        if not np.any(foreground):
            raise ValueError('No silhouette pixels found in ' + path)
        return foreground
    finally:
        bpy.data.images.remove(image)


def sample_mask(mask, u, v):
    """Orthographic image coordinates u,v in [0,1] (image origin at bottom-left)."""
    h, w = mask.shape
    ui = np.clip(np.rint(u * (w - 1)).astype(np.int32), 0, w - 1)
    vi = np.clip(np.rint(v * (h - 1)).astype(np.int32), 0, h - 1)
    return mask[vi, ui]


# Each face is wound counter-clockwise when viewed from outside.
FACES = [
    ((1, 0, 0), [(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
    ((-1,0, 0), [(0,0,0),(0,0,1),(0,1,1),(0,1,0)]),
    ((0, 1, 0), [(0,1,0),(0,1,1),(1,1,1),(1,1,0)]),
    ((0,-1, 0), [(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
    ((0, 0, 1), [(0,0,1),(1,0,1),(1,1,1),(0,1,1)]),
    ((0, 0,-1), [(0,0,0),(0,1,0),(1,1,0),(1,0,0)]),
]


def make_occupancy(masks, resolution=48):
    # Grid coordinates: X width, Y depth, Z height.
    # F/B image: horizontal X, vertical Z. L/R: horizontal Y, vertical Z.
    # Opposite views mirror the horizontal axis; all use the same orthographic scale.
    nz = int(resolution)
    nx = max(12, int(round(resolution * .65)))
    ny = max(12, int(round(resolution * .5)))
    ix = (np.arange(nx, dtype=np.float32) + .5) / nx
    jy = (np.arange(ny, dtype=np.float32) + .5) / ny
    kz = (np.arange(nz, dtype=np.float32) + .5) / nz
    occ = np.ones((nx, ny, nz), dtype=np.bool_)
    if masks.get('front') is not None:
        occ &= sample_mask(masks['front'], 1-ix[:,None], kz[None,:])[:,None,:]
    if masks.get('back') is not None:
        occ &= sample_mask(masks['back'], ix[:,None], kz[None,:])[:,None,:]
    if masks.get('left') is not None:
        occ &= sample_mask(masks['left'], 1-jy[:,None], kz[None,:])[None,:,:]
    if masks.get('right') is not None:
        occ &= sample_mask(masks['right'], jy[:,None], kz[None,:])[None,:,:]
    if masks.get('top') is not None:
        occ &= sample_mask(masks['top'], ix[:,None], jy[None,:])[:,:,None]
    return occ


def occupancy_to_mesh(occ, name, width, depth, height):
    nx, ny, nz = occ.shape
    verts = []
    quads = []
    lookup = {}

    def vertex(cx, cy, cz):
        key = (cx, cy, cz)
        if key not in lookup:
            lookup[key] = len(verts)
            verts.append(((cx / nx - .5) * width,
                          (cy / ny - .5) * depth,
                          (cz / nz) * height))
        return lookup[key]

    for i, j, k in np.argwhere(occ):
        i, j, k = int(i), int(j), int(k)
        for (di,dj,dk), corners in FACES:
            ii,jj,kk = i+di,j+dj,k+dk
            if (0 <= ii < nx and 0 <= jj < ny and 0 <= kk < nz and occ[ii,jj,kk]):
                continue
            quads.append(tuple(vertex(i+dx,j+dy,k+dz) for dx,dy,dz in corners))
    if not quads:
        raise ValueError('Silhouettes do not overlap into a non-empty 3D volume. Align masks and scale.')
    mesh = bpy.data.meshes.new(name + ' geometry')
    mesh.from_pydata(verts, [], quads)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj['generator'] = 'Four View Mesh (visual hull v0.1)'
    obj['occupied_voxels'] = int(np.count_nonzero(occ))
    obj['resolution'] = int(nz)
    return obj


def build_mesh(paths, resolution=48, width=1.5, depth=1, height=2.3, smooth=True,
               name='FourView_Object'):
    masks = {key: read_mask(path) if path else None for key,path in paths.items()}
    if sum(mask is not None for mask in masks.values()) < 2:
        raise ValueError('At least two different views are required (front and side suggested).')
    if not (masks.get('front') is not None or masks.get('back') is not None):
        raise ValueError('Need front or back view.')
    if not (masks.get('left') is not None or masks.get('right') is not None):
        raise ValueError('Need left or right side view.')
    occ = make_occupancy(masks, resolution)
    obj = occupancy_to_mesh(occ, name, width, depth, height)
    if smooth:
        # Smooth (and optionally remesh) the block faces. Remesh can change topology,
        # so keep the original quad mesh as the editable starting point.
        mod = obj.modifiers.new('Voxel edge smoothing (optional)', 'SMOOTH')
        mod.factor = 1.15
        mod.iterations = 6
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


class FVM_OT_reconstruct(bpy.types.Operator):
    bl_idname='mesh.four_view_reconstruct'
    bl_label='Build 3D Mesh from Views'
    bl_options={'REGISTER', 'UNDO'}

    def execute(self, context):
        scene=context.scene
        paths = {k: getattr(scene, 'fvm_'+k) for k in ('front','back','left','right','top')}
        try:
            ob = build_mesh(paths, scene.fvm_resolution,
                            scene.fvm_width,scene.fvm_depth,scene.fvm_height,
                            scene.fvm_smooth)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        context.view_layer.objects.active = ob
        self.report({'INFO'}, 'Created %s: %d verts, %d quad faces' % (
            ob.name, len(ob.data.vertices), len(ob.data.polygons)))
        return {'FINISHED'}


class FVM_PT_panel(bpy.types.Panel):
    bl_label='Four View Mesh'
    bl_idname='FVM_PT_panel'
    bl_space_type='VIEW_3D'
    bl_region_type='UI'
    bl_category='Four View Mesh'

    def draw(self, context):
        l=self.layout
        s=context.scene
        l.label(text='Transparent silhouettes / white background:')
        l.prop(s,'fvm_front',text='Front')
        l.prop(s,'fvm_back',text='Back')
        l.prop(s,'fvm_left',text='Left')
        l.prop(s,'fvm_right',text='Right')
        l.prop(s,'fvm_top',text='Top (optional)')
        l.separator()
        l.prop(s,'fvm_resolution')
        l.prop(s,'fvm_width')
        l.prop(s,'fvm_depth')
        l.prop(s,'fvm_height')
        l.prop(s,'fvm_smooth')
        l.operator('mesh.four_view_reconstruct',icon='MESH_CUBE')
        l.label(text='Starting mesh, not full AI reconstruction')


CLASSES = (FVM_OT_reconstruct,FVM_PT_panel)

def register():
    for key in ('front','back','left','right','top'):
        setattr(bpy.types.Scene, 'fvm_'+key,
                StringProperty(name=key.capitalize()+' silhouette',subtype='FILE_PATH'))
    bpy.types.Scene.fvm_resolution=IntProperty(name='Height resolution',default=56,min=16,max=160)
    bpy.types.Scene.fvm_width=FloatProperty(name='Width (m)',default=1.5,min=.01)
    bpy.types.Scene.fvm_depth=FloatProperty(name='Depth (m)',default=1,min=.01)
    bpy.types.Scene.fvm_height=FloatProperty(name='Height (m)',default=2.3,min=.01)
    bpy.types.Scene.fvm_smooth=BoolProperty(name='Smooth modifier',default=True)
    for cls in CLASSES: bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
    for key in ('front','back','left','right','top','resolution','width','depth','height','smooth'):
        delattr(bpy.types.Scene,'fvm_'+key)

if __name__=='__main__':
    register()