import bmesh
import bpy
import math
import mathutils
import struct

from .gma import Gma, GcmfEntry
from .gcmf import Gcmf, Attribute, \
    Texture_Flags0x00, Texture_Mipmap, Texture_Wrap, Texture, TransformMatrix, \
    Submesh, Material, \
    VertexAttribute, VertexRenderFlag, DisplatListHeader, \
    DisplayList, Vertex, Strip
from .gcmf_setting import GCMF_TextureSetting


# Messages
MSG_INFO_INIT = '---- {0} ----'
MSG_INFO_DATA = '{0}: {1}'
MSG_WARN_NONE_UV = 'Detect UV not exsit. exported any UV is (0.0, 0.0)'
MSG_WARN_MANY = 'Detect greater than {0} {1}s ({2}). Maybe this GCMF not works correct in Amusement Vision Games.'
MSG_WARN_TOO_MANY = 'Detect too many {0}s ({1}). Ignored {0}[{2}] and mores.'
MSG_WARN_NONE_MAT = 'Detect none Material Object. "{0}" is ignored. Mesh without Material Export is not support.'
MSG_WARN_FLAG_NONE = 'Detect {0}. But Check-Box is not checked. {1}'


def convert_flags2value(src_flags):
    max_bit = len(src_flags) - 1
    val = 0x00
    for i, flag in enumerate(src_flags):
        val += flag.real << (max_bit - i)
    return val


# ---------------------------------------------------------------------------
# Generate Texture
# ---------------------------------------------------------------------------
def generate_texture(gcmf_texture_property: GCMF_TextureSetting, idx: int):
    """Convert a GCMF_TextureSetting into a GCMF Texture struct."""
#    print('-Texture')
    texture = Texture()
    texture.index = idx if gcmf_texture_property.order_index < 0 else gcmf_texture_property.order_index
    texture.unk0x00 = convert_flags2value(gcmf_texture_property.unk0x00)
    texture.mipmap = convert_flags2value(gcmf_texture_property.mipmap)
    texture.uv_wrap = convert_flags2value(gcmf_texture_property.uv_wrap)
    texture.texture_index = gcmf_texture_property.texture_index
    texture.unk0x06 = gcmf_texture_property.unk0x06
    texture.anisotropy = convert_flags2value(gcmf_texture_property.anisotropy)
    texture.unk0x0C = convert_flags2value(gcmf_texture_property.unk0x0C)
    texture.is_swappable = convert_flags2value(gcmf_texture_property.is_swappable)
    texture.unk0x10 = convert_flags2value(gcmf_texture_property.unk0x10)
    return texture


# ---------------------------------------------------------------------------
# TransformMatrix
# ---------------------------------------------------------------------------
def generate_matrix():
    matrix = TransformMatrix()
    mtx = mathutils.Matrix()
    
    #TODO: Convert from Blender's ...?
    #Node or Armature ???
    mtx[0][0] = 1
    mtx[0][1] = 2
    mtx[0][2] = 3
    mtx[0][3] = 4
    
    mtx[1][0] = 5
    mtx[1][1] = 6
    mtx[1][2] = 7
    mtx[1][3] = 8
    
    mtx[2][0] = 9
    mtx[2][1] = 10
    mtx[2][2] = 11
    mtx[2][3] = 12
    
    matrix.mtx = mtx
    return matrix


# ---------------------------------------------------------------------------
# Vertex Attribute Table
# ---------------------------------------------------------------------------
# TODO: QUIT THIS. VAT must follwing "GCMF VAT setting" values.
def generate_vat(bl_mat, bm: bmesh.types.BMesh) -> VertexAttribute:
    vat = VertexAttribute()
    
    val = 0x00
    for i, _unk0x02 in enumerate(bl_mat.gcmf_material.vtx_descriptor):
        val += (int(_unk0x02) << (31 - i))
    vat.unpack(val)

    return vat


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

def generate_matrial(bm: bmesh.types.BMesh, bl_mat: bpy.types.Material, tex_idx: int) -> Material:
#    print('-Material')
    material = Material()

    vtx_attr = generate_vat(bl_mat, bm)

    vtx_render = VertexRenderFlag()
    vtx_render.dlist0_0 = True

    gcmf_material_property = bl_mat.gcmf_material

    tex_count = 0
    tex_count = len(gcmf_material_property.gcmf_textures)
    if tex_count > 3:
        print(MSG_WARN_TOO_MANY.format('TEXTURE', tex_count, 3))
    texture_indexs = gcmf_material_property.texture_indexes
    for i, _tex_idx in enumerate(texture_indexs):
        if i > tex_count:
            continue
        if _tex_idx < 0:
            _tex_idx = tex_idx
    
    val = (int(gcmf_material_property.unk0x02[0].real) << 7)\
        + (int(gcmf_material_property.unk0x02[1].real) << 6)\
        + (int(gcmf_material_property.unk0x02[2].real) << 5)\
        + (int(gcmf_material_property.unk0x02[3].real) << 4)\
        + (int(gcmf_material_property.unk0x02[4].real) << 3)\
        + (int(gcmf_material_property.unk0x02[5].real) << 2)\
        + (int(gcmf_material_property.unk0x02[6].real) << 1)\
        + int(gcmf_material_property.unk0x02[7].real)
    material.unk0x02 = val
    val = (int(gcmf_material_property.unk0x03[0].real) << 7)\
        + (int(gcmf_material_property.unk0x03[1].real) << 6)\
        + (int(gcmf_material_property.unk0x03[2].real) << 5)\
        + (int(gcmf_material_property.unk0x03[3].real) << 4)\
        + (int(gcmf_material_property.unk0x03[4].real) << 3)\
        + (int(gcmf_material_property.unk0x03[5].real) << 2)\
        + (int(gcmf_material_property.unk0x03[6].real) << 1)\
        + int(gcmf_material_property.unk0x03[7].real)
    material.unk0x03 = val
    material.color0 = gcmf_material_property.color0
    material.color1 = gcmf_material_property.color1
    material.color2 = gcmf_material_property.color2
    material.emission = gcmf_material_property.emission
    material.transparency = gcmf_material_property.transparency
    material.material_count = tex_count
    material.unk0x14 = gcmf_material_property.unk0x14
    material.unk0x15 = gcmf_material_property.unk0x15

    material.vtx_render = vtx_render
    material.texture_indexs = texture_indexs
    material.vtx_descriptor = vtx_attr

    return material


# ---------------------------------------------------------------------------
# Vertex / Strip / DisplayList
# ---------------------------------------------------------------------------

def generate_vertex(bm_vtx: bmesh.types.BMVert, loop: bmesh.types.BMLoop, bl_loops: bpy.types.MeshLoops, bm: bmesh.types.BMesh, gcmf_texture_propertys: list[GCMF_TextureSetting], obj: bpy.types.Object) -> Vertex:
    vtx = Vertex()
    
    #Position
    vtx.pos = [bm_vtx.co.x, bm_vtx.co.y, bm_vtx.co.z]

    vtx_idx = loop.index
    nrm = bl_loops[vtx_idx].normal
    vtx.nrm = [nrm[0], nrm[1], nrm[2]]

    clr_count = len(bm.loops.layers.color)
    for i in range(2 if clr_count > 1 else clr_count):
        clr_lay = bm.loops.layers.color[i]
        clr = loop[clr_lay]
        if i == 0:
            vtx.clr0 = [int(clr[0] * 0xFF), int(clr[1] * 0xFF),
                        int(clr[2] * 0xFF), int(clr[3] * 0xFF)]
        if i == 1:
            vtx.clr1 = [int(clr[0] * 0xFF), int(clr[1] * 0xFF),
                        int(clr[2] * 0xFF), int(clr[3] * 0xFF)]

    vtx.tex0 = [0.0, 0.0]
    #TODO: This must be controlled by "GCMF VAT" of GCMF_MaterialSetting.
    for i, ts in enumerate(gcmf_texture_propertys):
        if i > 7:
            break
        uv_layer = bm.loops.layers.uv[0]
        if len(bm.loops.layers.uv) > i:
            uv_layer = bm.loops.layers.uv[i]
        # If a named UV map is stored in the tex_setting, try to use it
        # (old texture_slots had a uv_layer field; we approximate with index)
        y = -(loop[uv_layer].uv[1] - 1.0)
        uv = [loop[uv_layer].uv[0], y]
        if i == 0:
            vtx.tex0 = uv
        elif i == 1:
            vtx.tex1 = uv
        elif i == 2:
            vtx.tex2 = uv
        elif i == 3:
            vtx.tex3 = uv
        elif i == 4:
            vtx.tex4 = uv
        elif i == 5:
            vtx.tex5 = uv
        elif i == 6:
            vtx.tex6 = uv
        elif i == 7:
            vtx.tex7 = uv

    return vtx


def generate_strip(bm: bmesh.types.BMesh, face: bmesh.types.BMFace, bl_loops: bpy.types.MeshLoops, gcmf_texture_propertys: list[GCMF_TextureSetting], obj: bpy.types.Object, attribute: Attribute) -> Strip:
#    print('-Strip')
    strip = Strip()
    strip.cmd = 0x99 if attribute.is_16bit else 0x98
    vertexs = []
    vtx_cnt = len(bl_loops)
#    print(MSG_INFO_DATA.format('Vertex Count', vtx_cnt))
    for loop in face.loops:
        vtx = generate_vertex(loop.vert, loop, bl_loops, bm, gcmf_texture_propertys, obj)
        vertexs.append(vtx)
    strip.vertexs = vertexs
    strip.count = len(vertexs)
    return strip


def generate_displaylist(bm: bmesh.types.BMesh, mat_idx: int, bl_loops: bpy.types.MeshLoops, gcmf_texture_propertys: list[GCMF_TextureSetting], obj: bpy.types.Object, attribute: Attribute) -> DisplayList:
    dlist = DisplayList()
    for face in bm.faces:
        if face.material_index == mat_idx:
            strip = generate_strip(bm, face, bl_loops, gcmf_texture_propertys, obj, attribute)
            dlist.strips.append(strip)
    return dlist


def generate_displaylistheader():
    dlist_header = DisplatListHeader()
    trans_mtxs = [-1] * 8
    sizes = [0x00, 0x00]
    dlist_header.trans_mtxs = trans_mtxs
    dlist_header.dlist_sizes = sizes
    return dlist_header


def generate_submesh(attribute: Attribute, bm: bmesh.types.BMesh, obj: bpy.types.Object, bl_mat: bpy.types.Material, tex_idx: int, mat_idx: int, bl_loops: bpy.types.MeshLoops) -> Submesh:
#    print('-Submesh')
    submesh = Submesh()

    dlist_header = generate_displaylistheader()
    submesh.dlist_headers = [dlist_header]

    submesh.material = generate_matrial(bm, bl_mat, tex_idx)
    submesh.boundingsphere_origin = bl_mat.gcmf_material.boundingsphere_origin
    submesh.unk0x3C = bl_mat.gcmf_material.unk0x3C
    val = 0x00
    max_bit = len(bl_mat.gcmf_material.unk0x40) - 1
    for i, b in enumerate(bl_mat.gcmf_material.unk0x40):
        val += (int(b) << (max_bit - i))
    submesh.unk0x40 = val

    dlist = generate_displaylist(bm, mat_idx, bl_loops, bl_mat.gcmf_material.gcmf_textures, obj, attribute)
    submesh.dlists.append(dlist)

    return submesh


# ---------------------------------------------------------------------------
# GCMF Attribute
# ---------------------------------------------------------------------------

def generate_attribute(bl_gcfm_attribute: str) -> Attribute:
    attribute = Attribute()
    if bl_gcfm_attribute == 'is_16bit':
        attribute.is_16bit = True
    elif bl_gcfm_attribute == 'is_stiching':
        attribute.is_stiching = True
    elif bl_gcfm_attribute == 'is_skin':
        attribute.is_skin = True
    elif bl_gcfm_attribute == 'is_effective':
        attribute.is_effective = True
    return attribute


# ---------------------------------------------------------------------------
# GCMF object
# ---------------------------------------------------------------------------
def generate_gcmf(obj: bpy.types.Object, idx: int) -> Gcmf:
    print(MSG_INFO_INIT.format('Generate GCMF'))
    gcmf = Gcmf()

    gcmf.attribute = generate_attribute(obj.gcmf_object.attribute)
    gcmf.origin = [obj.location[0], obj.location[1], obj.location[2]]
    gcmf.boundspher_radius = max(obj.dimensions)

    curr_idx = 0

    img_names = [img.name for img in bpy.data.images]

    gcmf_textures = []
    for bl_mat_slot in bpy.data.objects[obj.name].material_slots:
        bl_mat = bl_mat_slot.material
        if bl_mat is None:
            continue

        for i, gcmf_texture in enumerate(bl_mat.gcmf_material.gcmf_textures):
            if i > 2:
                print(MSG_WARN_TOO_MANY.format('TEXTURE', i, 3))
                break
            texture = generate_texture(gcmf_texture, curr_idx)
            gcmf_textures.append(texture)
            curr_idx += 1

    sorted_textures = sorted(gcmf_textures, key=lambda t: t.index)
    gcmf.textures = sorted_textures

    # Submesh
    bm = bmesh.new()

    # Triangulate via evaluated mesh
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    bl_mesh = obj_eval.to_mesh()

    # Generate Bmesh
    bm.from_mesh(bl_mesh)
    # Apply Transform (Scale/Rotation/Translation)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    # Rotate -90 deg (Swap Y-axis and Z-axis)
    rot = mathutils.Matrix.Rotation(math.radians(-90), 4, (1.0, 0.0, 0.0))
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=rot, verts=bm.verts)
    # Convert to Triangles
    bmesh.ops.triangulate(bm, faces=bm.faces)

    bm.to_mesh(bl_mesh)

    # Normals
    if hasattr(bl_mesh, 'use_auto_smooth'):
        bl_mesh.use_auto_smooth = True
    bl_loops = bl_mesh.loops

    tex_idx = 0
    for mat_idx, mat_slot in enumerate(obj.material_slots):
        submesh = generate_submesh(gcmf.attribute, bm, obj, mat_slot.material, tex_idx, mat_idx, bl_loops)
        gcmf.submeshs.append(submesh)
        tex_idx = tex_idx + submesh.material.material_count

#    # Matrix
#    for i in range(1):
#        mtx = generate_matrix()
#        gcmf.mtxs.append(mtx)
    
    mtx_idxs = [-1] * 8
    
    gcmf.mtx_idxs = mtx_idxs

    obj_eval.to_mesh_clear()
    del bm

    print(MSG_INFO_DATA.format('Texture Count', len(gcmf.textures)))
    gcmf.texture_count = len(gcmf.textures)
    gcmf.transparent_count = obj.gcmf_object.transparent_material_count
    gcmf.opaque_count = len(gcmf.submeshs) - obj.gcmf_object.transparent_material_count

    return gcmf


def generate_gcmfentry(obj: bpy.types.Object, idx: int) -> GcmfEntry:
    entry = GcmfEntry()
    entry.gcmf = generate_gcmf(obj, idx)
    entry.name = obj.name
    return entry


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def save(filepath: str, little_endian=False):
    with open(filepath, 'wb') as file:
        sel_endian = '<' if little_endian else '>'

        gma = Gma()
        # Sorting by index of GCMF_Object
        sorted_bl_objs = sorted(
            bpy.context.selected_objects,
            key=lambda bl_obj: bl_obj.gcmf_object.index
        )
        for i, obj in enumerate(sorted_bl_objs):
            if len(obj.material_slots) < 1:
                print(MSG_WARN_NONE_MAT.format(obj.name))
                # Skip Mesh Export
                continue
                # gcmf entry
            entry = generate_gcmfentry(obj, i)
            gma.entrys.append(entry)

        gma.pack(file, sel_endian)
