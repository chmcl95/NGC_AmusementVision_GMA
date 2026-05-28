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
from .gcmf_node import GCMFTextureNode, collect_gcmf_texture_nodes

# Messages
MSG_INFO_INIT    = '---- {0} ----'
MSG_INFO_DATA    = '{0}: {1}'
MSG_WARN_TOO_MANY = 'Detect too many {0}s ({1}). Ignored {0}[{2}] and mores.'
MSG_WARN_NONE_MAT = 'Detect none Material Object. "{0}" is ignored.'
MSG_WARN_NONE_UV  = 'Detect UV not exist. exported any UV is (0.0, 0.0)'


def convert_flags2value(src_flags) -> int:
    max_bit = len(src_flags) - 1
    val = 0
    for i, flag in enumerate(src_flags):
        val += int(flag) << (max_bit - i)
    return val


# ---------------------------------------------------------------------------
# Texture  (GCMFTextureNode → GCMF Texture struct)
# ---------------------------------------------------------------------------
def generate_texture(gcmf_texture_node: GCMFTextureNode, idx: int) -> Texture:
    """
    2.79版の generate_texture(tex, idx) に相当。
    bpy.data.textures[name].gcmf_texture.* の代わりに
    GCMFTextureNode のプロパティを直接参照する。
    """
    texture = Texture()
    texture.index         = idx
    texture.unk0x00       = convert_flags2value(gcmf_texture_node.unk0x00)
    texture.mipmap        = convert_flags2value(gcmf_texture_node.mipmap)
    texture.uv_wrap       = convert_flags2value(gcmf_texture_node.uv_wrap)
    # image.name から texture_index を逆算（手動設定値をフォールバックに使用）
    texture.texture_index = gcmf_texture_node.texture_index
    texture.unk0x06       = gcmf_texture_node.unk0x06
    texture.anisotropy    = convert_flags2value(gcmf_texture_node.anisotropy)
    texture.unk0x0C       = convert_flags2value(gcmf_texture_node.unk0x0C)
    texture.is_swappable  = convert_flags2value(gcmf_texture_node.is_swappable)
    texture.unk0x10       = convert_flags2value(gcmf_texture_node.unk0x10)
    return texture


# ---------------------------------------------------------------------------
# TransformMatrix
# ---------------------------------------------------------------------------
def generate_matrix() -> TransformMatrix:
    matrix = TransformMatrix()
    mtx = mathutils.Matrix()
    mtx[0][0]=1;  mtx[0][1]=2;  mtx[0][2]=3;  mtx[0][3]=4
    mtx[1][0]=5;  mtx[1][1]=6;  mtx[1][2]=7;  mtx[1][3]=8
    mtx[2][0]=9;  mtx[2][1]=10; mtx[2][2]=11; mtx[2][3]=12
    matrix.mtx = mtx
    return matrix


# ---------------------------------------------------------------------------
# Vertex Attribute Table
# ---------------------------------------------------------------------------
def generate_vat(bl_mat: bpy.types.Material, bm: bmesh.types.BMesh) -> VertexAttribute:
    vat = VertexAttribute()
    val = 0
    for i, b in enumerate(bl_mat.gcmf_material.vtx_descriptor):
        val += int(b) << (31 - i)
    vat.unpack(val)
    return vat


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------
def generate_material(bm: bmesh.types.BMesh, bl_mat: bpy.types.Material,
                     all_gcmf_mat_nodes: list[GCMFTextureNode]) -> Material:
    material  = Material()
    vtx_attr  = generate_vat(bl_mat, bm)
    vtx_render = VertexRenderFlag()
    vtx_render.dlist0_0 = True

    gcmf_mat = bl_mat.gcmf_material

    # GCMFTextureNode をノードツリーから収集
    gcmf_nodes = collect_gcmf_texture_nodes(bl_mat)
    tex_count  = len(gcmf_nodes)
    if tex_count > 3:
        print(MSG_WARN_TOO_MANY.format('TEXTURE', tex_count, 3))
        tex_count = 3

    texture_indexs = [-1, -1, -1]
    for i in range(tex_count):
        texture_indexs[i] = all_gcmf_mat_nodes.index(gcmf_nodes[i])

    val = sum(int(b) << (7 - i) for i, b in enumerate(gcmf_mat.unk0x02))
    material.unk0x02 = val
    val = sum(int(b) << (7 - i) for i, b in enumerate(gcmf_mat.unk0x03))
    material.unk0x03 = val

    material.color0          = gcmf_mat.color0
    material.color1          = gcmf_mat.color1
    material.color2          = gcmf_mat.color2
    material.emission        = gcmf_mat.emission
    material.transparency    = gcmf_mat.transparency
    material.material_count  = tex_count
    material.unk0x14         = gcmf_mat.unk0x14
    material.unk0x15         = gcmf_mat.unk0x15
    material.vtx_render      = vtx_render
    material.texture_indexs  = texture_indexs
    material.vtx_descriptor  = vtx_attr

    return material


# ---------------------------------------------------------------------------
# Vertex
# ---------------------------------------------------------------------------
def generate_vertex(bm_vtx, loop, bl_loops, bm, gcmf_nodes, obj) -> Vertex:
    vtx = Vertex()
    vtx.pos = [bm_vtx.co.x, bm_vtx.co.y, bm_vtx.co.z]
    nrm = bl_loops[loop.index].normal
    vtx.nrm = [nrm[0], nrm[1], nrm[2]]

    clr_count = len(bm.loops.layers.color)
    for i in range(min(clr_count, 2)):
        clr_lay = bm.loops.layers.color[i]
        clr = loop[clr_lay]
        rgba = [int(clr[c] * 0xFF) for c in range(4)]
        if i == 0: vtx.clr0 = rgba
        if i == 1: vtx.clr1 = rgba

    vtx.tex0 = [0.0, 0.0]
    for i in range(min(len(gcmf_nodes), 8)):
        uv_layer = bm.loops.layers.uv[min(i, len(bm.loops.layers.uv)-1)]
        y   = -(loop[uv_layer].uv[1] - 1.0)
        uv  = [loop[uv_layer].uv[0], y]
        if   i == 0: vtx.tex0 = uv
        elif i == 1: vtx.tex1 = uv
        elif i == 2: vtx.tex2 = uv
        elif i == 3: vtx.tex3 = uv
        elif i == 4: vtx.tex4 = uv
        elif i == 5: vtx.tex5 = uv
        elif i == 6: vtx.tex6 = uv
        elif i == 7: vtx.tex7 = uv
    return vtx


def generate_strip(bm, face, bl_loops, gcmf_nodes, obj, attribute: Attribute) -> Strip:
    strip = Strip()
    strip.cmd = 0x99 if attribute.is_16bit else 0x98
    strip.vertexs = [
        generate_vertex(loop.vert, loop, bl_loops, bm, gcmf_nodes, obj)
        for loop in face.loops
    ]
    strip.count = len(strip.vertexs)
    return strip


def generate_displaylist(bm, mat_idx, bl_loops, gcmf_nodes, obj, attribute: Attribute) -> DisplayList:
    dlist = DisplayList()
    for face in bm.faces:
        if face.material_index == mat_idx:
            dlist.strips.append(
                generate_strip(bm, face, bl_loops, gcmf_nodes, obj, attribute))
    return dlist


def generate_displaylistheader() -> DisplatListHeader:
    h = DisplatListHeader()
    h.trans_mtxs  = [-1] * 8
    h.dlist_sizes = [0x00, 0x00]
    return h


def generate_submesh(attribute, bm, obj, bl_mat, all_gcmf_mat_nodes, mat_idx, bl_loops) -> Submesh:
    submesh = Submesh()
    submesh.dlist_headers = [generate_displaylistheader()]

    gcmf_nodes = collect_gcmf_texture_nodes(bl_mat)

    submesh.material = generate_material(bm, bl_mat, all_gcmf_mat_nodes)
    submesh.boundingsphere_origin = bl_mat.gcmf_material.boundingsphere_origin
    submesh.unk0x3C = bl_mat.gcmf_material.unk0x3C
    val = sum(int(b) << (31 - i) for i, b in enumerate(bl_mat.gcmf_material.unk0x40))
    submesh.unk0x40 = val

    submesh.dlists.append(
        generate_displaylist(bm, mat_idx, bl_loops, gcmf_nodes, obj, attribute))
    return submesh


# ---------------------------------------------------------------------------
# Attribute
# ---------------------------------------------------------------------------
def generate_attribute(bl_gcfm_attribute) -> Attribute:
    attr = Attribute()
    if   bl_gcfm_attribute == 'is_16bit':    attr.is_16bit    = True
    elif bl_gcfm_attribute == 'is_stiching': attr.is_stiching = True
    elif bl_gcfm_attribute == 'is_skin':     attr.is_skin     = True
    elif bl_gcfm_attribute == 'is_effective':attr.is_effective= True
    return attr


# ---------------------------------------------------------------------------
# GCMF object
# ---------------------------------------------------------------------------
def generate_gcmf(obj: bpy.types.Object, idx: int) -> Gcmf:
    print(MSG_INFO_INIT.format('Generate GCMF'))
    gcmf = Gcmf()
    gcmf.attribute        = generate_attribute(obj.gcmf_object.attribute)
    gcmf.origin           = list(obj.location)
    gcmf.boundspher_radius= max(obj.dimensions)

    curr_idx      = 0
    all_gcmf_mat_nodes = []
    gcmf_textures = []

    for mat_slot in obj.material_slots:
        bl_mat = mat_slot.material
        if bl_mat is None:
            continue

        # GCMFTextureNode をノードツリーから収集してテクスチャ構造体を生成
        gcmf_mat_nodes = collect_gcmf_texture_nodes(bl_mat)
        for i, gcmf_mat_node in enumerate(gcmf_mat_nodes):
            if i >= 3:
                print(MSG_WARN_TOO_MANY.format('TEXTURE', i, 3))
                break
            all_gcmf_mat_nodes.append(gcmf_mat_node)

    all_gcmf_mat_nodes.sort(key=lambda n: n.order_index)
    for gcmf_mat_node in all_gcmf_mat_nodes:
        texture = generate_texture(gcmf_mat_node, curr_idx)
        gcmf_textures.append(texture)
        curr_idx += 1

    gcmf.textures = sorted(gcmf_textures, key=lambda t: t.index)

    # Submesh
    bm = bmesh.new()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval  = obj.evaluated_get(depsgraph)
    bl_mesh   = obj_eval.to_mesh()

    bm.from_mesh(bl_mesh)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    rot = mathutils.Matrix.Rotation(math.radians(-90), 4, (1.0, 0.0, 0.0))
    bmesh.ops.rotate(bm, cent=(0.0,0.0,0.0), matrix=rot, verts=bm.verts)
    bmesh.ops.triangulate(bm, faces=bm.faces)

    if hasattr(bl_mesh, 'use_auto_smooth'):
        bl_mesh.use_auto_smooth = True
    bl_loops = bl_mesh.loops

    for mat_idx, mat_slot in enumerate(obj.material_slots):
        submesh = generate_submesh(
            gcmf.attribute, bm, obj, mat_slot.material,
            all_gcmf_mat_nodes, mat_idx, bl_loops)
        gcmf.submeshs.append(submesh)

    gcmf.mtx_idxs         = [-1] * 8
    gcmf.texture_count    = len(gcmf.textures)
    transparent_count = obj.gcmf_object.transparent_count
    gcmf.opaque_count     = len(obj.material_slots) - transparent_count
    gcmf.transparent_count= transparent_count

    obj_eval.to_mesh_clear()
    del bm
    return gcmf


def generate_gcmfentry(obj, idx) -> GcmfEntry:
    entry = GcmfEntry()
    entry.gcmf = generate_gcmf(obj, idx)
    entry.name = obj.name
    return entry


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def save(filepath, little_endian=False):
    with open(filepath, 'wb') as file:
        sel_endian = '<' if little_endian else '>'
        gma = Gma()
        sorted_objs = sorted(
            bpy.context.selected_objects,
            key=lambda o: o.gcmf_object.index)
        for i, obj in enumerate(sorted_objs):
            if len(obj.material_slots) < 1:
                print(MSG_WARN_NONE_MAT.format(obj.name))
                continue
            gma.entrys.append(generate_gcmfentry(obj, i))
        gma.pack(file, sel_endian)
