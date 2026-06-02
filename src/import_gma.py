import array
import bmesh
import bpy
import mathutils
import numpy

from .gma import Gma
from .gcmf import VertexAttribute, Texture_Flags0x00, Texture_Wrap, Material
from .gcmf_node import GCMFTextureNode

# Messages
MSG_INFO_INIT = '---- {0} ----'
MSG_INFO_DATA = '{0}: {1}'
MSG_INFO_DATA_HEX = '{0}: {1:#X}'

# Names
NAME_MATERIAL   = 'material_{0:03}'
NAME_TPL_COMMON = 'tpl_common_{0:03}'
NAME_TPL        = 'tpl_{0:03}'
NAME_POLYGON    = 'polygon_{0}'
NAME_ARMATURE   = '{0}_armature'
NAME_NODE       = 'node_{0}'
NAME_VERTEXCOLOR = 'color{0}'
NAME_UV         = 'uv{0}'


# ---------------------------------------------------------------------------
# Mesh data container
# ---------------------------------------------------------------------------
class Mesh_data:
    def __init__(self):
        self.normals  = []
        self.color0s  = []
        self.color1s  = []
        self.tex0s    = []
        self.tex1s    = []
        self.tex2s    = []
        self.tex3s    = []
        self.tex4s    = []
        self.tex5s    = []
        self.tex6s    = []
        self.tex7s    = []


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def convert_value2flags(value, dest_flags):
    max_bit = len(dest_flags)
    flags = [False] * max_bit
    for i in range(max_bit):
        val = value >> ((max_bit - 1) - i)
        flags[i] = (val & 0x01) == 1
    return flags


def _get_or_create_image(images: dict, name: str) -> bpy.types.Image:
    if name not in images:
        img = bpy.data.images.new(name, width=1, height=1)
        img.source   = 'FILE'
        img.filepath = name
        images[name] = img
    return images[name]


# ---------------------------------------------------------------------------
# Generate Blender Material  (カスタムノード版)
# ---------------------------------------------------------------------------
def generate_material(material: Material, mat_idx: int, gcmf_texs_data: list,
                      images: dict, is_alpha: bool) -> bpy.types.Material:

    mat = bpy.data.materials.new(name=NAME_MATERIAL.format(mat_idx))
    mat.use_nodes = True

    # ---- GCMF_MaterialSetting ----
    gcmf_material = mat.gcmf_material
    gcmf_material.unk0x02        = convert_value2flags(material.unk0x02, gcmf_material.unk0x02)
    gcmf_material.unk0x03        = convert_value2flags(material.unk0x03, gcmf_material.unk0x03)
    gcmf_material.color0         = material.color0
    gcmf_material.color1         = material.color1
    gcmf_material.color2         = material.color2
    gcmf_material.emission       = material.emission
    gcmf_material.transparency   = material.transparency
    gcmf_material.unk0x14        = material.unk0x14
    gcmf_material.unk0x15        = material.unk0x15
    gcmf_material.texture_indexes = material.texture_indexs
    gcmf_material.vtx_descriptor = convert_value2flags(
        material.vtx_descriptor.pack(), gcmf_material.vtx_descriptor)
    gcmf_material.order_index    = mat_idx

    # ---- Initialize Node Tree ----
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Principled BSDF + Output
    bsdf   = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # ベースカラーをマテリアルの color0 で初期化
    r = material.color0[0] / 0xFF
    g = material.color0[1] / 0xFF
    b = material.color0[2] / 0xFF
    a = material.transparency / 0xFF if not is_alpha else 0.0
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
    bsdf.inputs['Alpha'].default_value = a
    if is_alpha or material.transparency < 0xFF:
        mat.blend_method = 'BLEND'

    # ---- Generate GCMFTextureNode ----
    tex_x = -400
    first_gcmf_node = None

    for i, texid in enumerate(material.texture_indexs):
        if texid < 0:
            continue
        raw_tex = gcmf_texs_data[texid] if texid < len(gcmf_texs_data) else None
        if raw_tex is None:
            continue

        # --- Generate GCMFTextureNode ---
        gcmf_node = nodes.new('GCMFTextureNode')
        gcmf_node.location  = (tex_x, 300 - i * 320)
        gcmf_node.label     = f'GCMF Tex [{i}]'

        # --- save as Properties ---
        gcmf_node.unk0x00       = convert_value2flags(raw_tex.unk0x00,    gcmf_node.unk0x00)
        gcmf_node.mipmap        = convert_value2flags(raw_tex.mipmap,     gcmf_node.mipmap)
        gcmf_node.uv_wrap       = convert_value2flags(raw_tex.uv_wrap,    gcmf_node.uv_wrap)
        gcmf_node.texture_index = raw_tex.texture_index
        gcmf_node.order_index   = texid
        gcmf_node.unk0x06       = raw_tex.unk0x06
        gcmf_node.anisotropy    = convert_value2flags(raw_tex.anisotropy,    gcmf_node.anisotropy)
        gcmf_node.unk0x0C       = convert_value2flags(raw_tex.unk0x0C,       gcmf_node.unk0x0C)
        gcmf_node.is_swappable  = convert_value2flags(raw_tex.is_swappable,  gcmf_node.is_swappable)
        gcmf_node.unk0x10       = convert_value2flags(raw_tex.unk0x10,       gcmf_node.unk0x10)

        # --- 画像を設定 (2.79版 tex.image = img 相当) ---
        img_id = raw_tex.texture_index
        if img_id >= 0:
            is_common = gcmf_node.unk0x00[Texture_Flags0x00.COMMON_TEX]
            img_name  = NAME_TPL_COMMON.format(img_id) if is_common else NAME_TPL.format(img_id)
            img = _get_or_create_image(images, img_name)
            gcmf_node.image = img
            # 内部 NodeGroup の ShaderNodeTexImage にも反映
            gcmf_node._sync_image()

        # --- BSDF に接続 (2.79版 mat.texture_slots[i] = tex 相当) ---
        # スロット0のみ Base Color に直結（プレビュー用）
        # 2枚目以降は接続するがユーザーが自由に組み替え可能
        if i == 0:
            links.new(gcmf_node.outputs['Color'], bsdf.inputs['Base Color'])
            if is_alpha:
                links.new(gcmf_node.outputs['Alpha'], bsdf.inputs['Alpha'])
            first_gcmf_node = gcmf_node
        # 2枚目以降はノードを配置するが接続はユーザーに委ねる
        # （接続したい場合は gcmf_node.outputs['Color'] → MixRGB などへ）

    return mat


# ---------------------------------------------------------------------------
# UV / VertexColor
# ---------------------------------------------------------------------------
def generate_uv(mesh, channel_name, uvs):
    if channel_name not in mesh.uv_layers:
        mesh.uv_layers.new(name=channel_name)
    uv_layer = mesh.uv_layers[channel_name]
    for i, loop in enumerate(mesh.loops):
        uv_layer.data[i].uv = uvs[loop.vertex_index]


def generate_vertexcolor(mesh, color_name, vcolors):
    if color_name not in mesh.vertex_colors:
        mesh.vertex_colors.new(name=color_name)
    vc_layer = mesh.vertex_colors[color_name]
    for i, loop in enumerate(mesh.loops):
        vc_layer.data[i].color = vcolors[loop.vertex_index]


# ---------------------------------------------------------------------------
# Mesh generation
# ---------------------------------------------------------------------------
def generate_mesh(mesh, bm, matid, mesh_data, dlist, mtxidxs, mtxs, first_iscw):
    v0 = mathutils.Vector((0, 0, 0))
    v1 = mathutils.Vector((0, 0, 0))
    v2 = mathutils.Vector((0, 0, 0))
    iscw = first_iscw
    for strip in dlist.strips:
        for i, vertex in enumerate(strip.vertexs):
            vtx = mathutils.Vector((vertex.pos[0], vertex.pos[1], vertex.pos[2]))
            pnmtxidx = vertex.pnmtxidx
            if pnmtxidx >= 0:
                if not ((pnmtxidx > 0x18) or ((pnmtxidx % 3) != 0)):
                    ridx = int((pnmtxidx / 3) - 1)
                    idx  = mtxidxs[ridx]
                    if idx >= 0:
                        vtx = mtxs[idx].mtx @ vtx
            v = bm.verts.new(vtx)
            vec = mathutils.Vector((vertex.nrm[0], vertex.nrm[1], vertex.nrm[2]))
            v.normal = vec
            mesh_data.normals.append(vec.normalized())
            mesh_data.color0s.append(mathutils.Vector((
                vertex.clr0[0] / 0xFF, vertex.clr0[1] / 0xFF,
                vertex.clr0[2] / 0xFF, vertex.clr0[3] / 0xFF)))
            mesh_data.color1s.append(mathutils.Vector((
                vertex.clr1[0] / 0xFF, vertex.clr1[1] / 0xFF,
                vertex.clr1[2] / 0xFF, vertex.clr1[3] / 0xFF)))
            mesh_data.tex0s.append(mathutils.Vector((vertex.tex0[0], -(vertex.tex0[1] - 1.0))))
            mesh_data.tex1s.append(mathutils.Vector((vertex.tex1[0], -(vertex.tex1[1] - 1.0))))
            mesh_data.tex2s.append(mathutils.Vector((vertex.tex2[0], -(vertex.tex2[1] - 1.0))))
            mesh_data.tex3s.append(mathutils.Vector((vertex.tex3[0], -(vertex.tex3[1] - 1.0))))
            mesh_data.tex4s.append(mathutils.Vector((vertex.tex4[0], -(vertex.tex4[1] - 1.0))))
            mesh_data.tex5s.append(mathutils.Vector((vertex.tex5[0], -(vertex.tex5[1] - 1.0))))
            mesh_data.tex6s.append(mathutils.Vector((vertex.tex6[0], -(vertex.tex6[1] - 1.0))))
            mesh_data.tex7s.append(mathutils.Vector((vertex.tex7[0], -(vertex.tex7[1] - 1.0))))

            if i == 0:
                iscw = first_iscw
            if i > 1:
                v2 = v
                face = bm.faces.new((v2, v1, v0) if iscw else (v0, v1, v2))
                iscw = not iscw
                face.material_index = matid
                v0 = v1
                v1 = v2
            elif i == 1:
                v1 = v
            elif i == 0:
                v0 = v
    bm.to_mesh(mesh)


def generate_attribute(attribute):
    if attribute.is_16bit:      return 'is_16bit'
    if attribute.is_stiching:   return 'is_stiching'
    if attribute.is_skin:       return 'is_skin'
    if attribute.is_effective:  return 'is_effective'
    return "default"


# ---------------------------------------------------------------------------
# Import entry point
# ---------------------------------------------------------------------------
def load(filepath, little_endian=False):
    # NodeGroup を事前に準備

    with open(filepath, 'rb') as file:
        sel_endian = '<' if little_endian else '>'
        gma    = Gma()
        gma.unpack(file, sel_endian)
        images = {}

        for i, entry in enumerate(gma.entrys):
            print(MSG_INFO_INIT.format('Generate Blender Mesh'))
            print(MSG_INFO_DATA.format('Mesh Name', entry.name))

            mesh = bpy.data.meshes.new(NAME_POLYGON.format(i))
            obj  = bpy.data.objects.new(entry.name, mesh)

            scene = bpy.context.scene
            scene.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            bm        = bmesh.new()
            gcmf      = entry.gcmf
            mesh_data = Mesh_data()

            obj.gcmf_object.index     = i
            obj.gcmf_object.attribute = generate_attribute(gcmf.attribute)
            obj.gcmf_object.transparent_count = gcmf.transparent_count

            total_flags = numpy.array(0x00, dtype='i4')
            gcmf_texs_data = gcmf.textures
            mtxidxs        = gcmf.mtx_idxs
            mtxs           = gcmf.mtxs

            for matid, submesh in enumerate(gcmf.submeshs):
                attribute   = submesh.material.vtx_descriptor
                flags       = attribute.pack()
                total_flags = flags | total_flags
                for j, dlist in enumerate(submesh.dlists):
                    generate_mesh(mesh, bm, matid, mesh_data, dlist,
                                  mtxidxs, mtxs, (j % 2 == 1))

            all_attribute = VertexAttribute()
            all_attribute.unpack(total_flags)
            mesh.update()

            # Normals
            if all_attribute.gx_va_nrm:
                mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
                try:
                    mesh.normals_split_custom_set_from_vertices(mesh_data.normals)
                except AttributeError:
                    if hasattr(mesh, 'use_auto_smooth'):
                        mesh.use_auto_smooth = True
                        mesh.normals_split_custom_set_from_vertices(mesh_data.normals)

            if all_attribute.gx_va_clr0: generate_vertexcolor(mesh, NAME_VERTEXCOLOR.format(0), mesh_data.color0s)
            if all_attribute.gx_va_clr1: generate_vertexcolor(mesh, NAME_VERTEXCOLOR.format(1), mesh_data.color1s)
            if all_attribute.gx_va_tex0: generate_uv(mesh, NAME_UV.format(0), mesh_data.tex0s)
            if all_attribute.gx_va_tex1: generate_uv(mesh, NAME_UV.format(1), mesh_data.tex1s)
            if all_attribute.gx_va_tex2: generate_uv(mesh, NAME_UV.format(2), mesh_data.tex2s)
            if all_attribute.gx_va_tex3: generate_uv(mesh, NAME_UV.format(3), mesh_data.tex3s)
            if all_attribute.gx_va_tex4: generate_uv(mesh, NAME_UV.format(4), mesh_data.tex4s)
            if all_attribute.gx_va_tex5: generate_uv(mesh, NAME_UV.format(5), mesh_data.tex5s)
            if all_attribute.gx_va_tex6: generate_uv(mesh, NAME_UV.format(6), mesh_data.tex6s)
            if all_attribute.gx_va_tex7: generate_uv(mesh, NAME_UV.format(7), mesh_data.tex7s)

            # マテリアル生成
            for matid, submesh in enumerate(gcmf.submeshs):
                is_alpha = matid >= gcmf.opaque_count
                mat = generate_material(submesh.material, matid,
                                        gcmf_texs_data, images, is_alpha)
                mat.gcmf_material.unk0x3C  = submesh.unk0x3C
                mat.gcmf_material.unk0x40  = convert_value2flags(
                    submesh.unk0x40, mat.gcmf_material.unk0x40)
                mat.gcmf_material.boundingsphere_origin = submesh.boundingsphere_origin
                obj.data.materials.append(mat)

            bm.free()
            mesh.update()
            bpy.context.object.rotation_euler[0] = 1.5708

            if bpy.context.mode == 'EDIT_ARMATURE':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

            if len(gcmf.mtxs) > 0:
                bpy.ops.object.add(type='ARMATURE', location=(0,0,0), enter_editmode=False)
                bpy.context.object.name = NAME_ARMATURE.format(entry.name)
                for j, matrix in enumerate(gcmf.mtxs):
                    bpy.ops.object.mode_set(mode='EDIT')
                    b = bpy.context.object.data.edit_bones.new(NAME_NODE.format(j))
                    b.head = mathutils.Vector((0.0, 0.0, 0.0))
                    b.tail = mathutils.Vector((0.0, 0.1, 0.0))
                    b.transform(matrix.mtx, scale=True, roll=True)
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy.context.object.rotation_euler[0] = 1.5708

    bpy.ops.object.shade_smooth()
