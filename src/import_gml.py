# TODO: move load function into import_gma.py as load_gml.
"""
import array

import bmesh
import bpy
import mathutils
import numpy

from .gml import Gml
from .gcmf import VertexAttribute

# Messages
MSG_INFO_INIT = '---- {0} ----'
MSG_INFO_DATA = '{0}: {1}'
MSG_INFO_DATA_HEX = '{0}: {1:#X}'

# Names
NAME_MATERIAL = 'material_{0:03}'
NAME_TEXTURE = 'gxtex_{0:03}'
NAME_TPL_COMMON = 'tpl_common_{0:03}'
NAME_TPL = 'tpl_{0:03}'
NAME_POLYGON = 'polygon_{0}'
NAME_ARMATURE = '{0}_armature'
NAME_NODE = 'node_{0}'
NAME_VERTEXCOLOR = 'color{0}'
NAME_UV = 'uv{0}'


# Storage Mesh datas
class Mesh_data:
    def __init__(self):
        self.normals = []  # Collect for "Custom Split Normals"
        self.color0s = []
        self.color1s = []
        self.tex0s = []
        self.tex1s = []
        self.tex2s = []
        self.tex3s = []
        self.tex4s = []
        self.tex5s = []
        self.tex6s = []
        self.tex7s = []


def _get_or_create_image(images, name):
    if name not in images:
        img = bpy.data.images.new(name, width=1, height=1)
        img.source = 'FILE'
        img.filepath = name
        images[name] = img
    return images[name]


# Generate Blender's Material (Blender 4.x – node-based)
def generate_material(material, matid, gcmf_texs_data, images, is_alpha):
    mat = bpy.data.materials.new(name=NAME_MATERIAL.format(matid))
    mat.use_nodes = True

    gcmf_material = mat.gcmf_material
    gcmf_material.is_keep = True

    # unk0x02 / unk0x03 as bit-fields
    def byte_to_flags(byte_val):
        return [(((byte_val >> (7 - i)) & 0x01) == 1) for i in range(8)]

    gcmf_material.unk0x02 = byte_to_flags(material.unk0x02)
    gcmf_material.unk0x03 = byte_to_flags(material.unk0x03)
    gcmf_material.color0 = material.color0
    gcmf_material.color1 = material.color1
    gcmf_material.color2 = material.color2
    gcmf_material.emission = material.emission
    gcmf_material.transparency = material.transparency
    gcmf_material.unk0x14 = material.unk0x14
    gcmf_material.unk0x15 = material.unk0x15

    # Node setup
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    r = material.color0[0] / 0xFF
    g = material.color0[1] / 0xFF
    b = material.color0[2] / 0xFF
    a = material.transparency / 0xFF if not is_alpha else 0.0
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
    bsdf.inputs['Alpha'].default_value = a
    if is_alpha or material.transparency < 0xFF:
        mat.blend_method = 'BLEND'

    # Per-texture settings
    for i, texid in enumerate(material.texture_indexs):
        if texid < 0:
            continue
        ts = gcmf_material.tex_settings.add()
        raw_tex = gcmf_texs_data[texid] if texid < len(gcmf_texs_data) else None
        if raw_tex is None:
            continue

        # uv_wrap from GML uses attribute access (different from GMA struct)
        ext = 'EXTEND'
        mir_x = False
        mir_y = False
        try:
            if raw_tex.uv_wrap.repeat_x or raw_tex.uv_wrap.repeat_y or \
               raw_tex.uv_wrap.mirror_x or raw_tex.uv_wrap.mirror_y:
                ext = 'REPEAT'
            mir_x = bool(raw_tex.uv_wrap.mirror_x)
            mir_y = bool(raw_tex.uv_wrap.mirror_y)
        except AttributeError:
            pass
        ts.extension = ext
        ts.use_mirror_x = mir_x
        ts.use_mirror_y = mir_y

        # texture_index
        try:
            ts.texture_index = raw_tex.texture_index
        except AttributeError:
            pass

        # Image
        try:
            imgid = raw_tex.texture_index
            if imgid >= 0:
                try:
                    is_common = raw_tex.unk0x00.commontex
                except AttributeError:
                    is_common = False
                img_name = NAME_TPL_COMMON.format(imgid) if is_common else NAME_TPL.format(imgid)
                ts.image_name = img_name
                img = _get_or_create_image(images, img_name)
                if i == 0:
                    tex_node = nodes.new('ShaderNodeTexImage')
                    tex_node.image = img
                    tex_node.location = (-300, 200)
                    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
                    if is_alpha:
                        links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
        except AttributeError:
            pass

    return mat


# Generate Blender's UV
def generate_uv(mesh, channel_name, uvs):
    if channel_name not in mesh.uv_layers:
        mesh.uv_layers.new(name=channel_name)
    uv_layer = mesh.uv_layers[channel_name]
    for i, loop in enumerate(mesh.loops):
        uv_layer.data[i].uv = uvs[loop.vertex_index]


# Generate Blender's VertexColor
def generate_vertexcolor(mesh, color_name, vcolors):
    if color_name not in mesh.vertex_colors:
        mesh.vertex_colors.new(name=color_name)
    vc_layer = mesh.vertex_colors[color_name]
    for i, loop in enumerate(mesh.loops):
        vc_layer.data[i].color = vcolors[loop.vertex_index]


# Generate mesh from Gcmf Object
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
                if (pnmtxidx > 0x18) or ((pnmtxidx % 3) != 0):
                    print(MSG_INFO_DATA.format('pnmtxidx', pnmtxidx))
                else:
                    ridx = int((pnmtxidx / 3) - 1)
                    print(ridx)
                    idx = mtxidxs[ridx]
                    if idx < 0:
                        print(MSG_INFO_DATA.format('matrix_index', idx))
                    else:
                        mtx = mtxs[idx].mtx
                        vtx = mtx @ vtx  # '@' replaces '*' in 2.80+
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
                if iscw:
                    face = bm.faces.new((v2, v1, v0))
                    iscw = False
                else:
                    face = bm.faces.new((v0, v1, v2))
                    iscw = True
                face.material_index = matid
                v0 = v1
                v1 = v2
            elif i == 1:
                v1 = v
            elif i == 0:
                v0 = v
    bm.to_mesh(mesh)


# Import gml
def load(filepath, little_endian=False):
    with open(filepath, 'rb') as file:
        sel_endian = '<' if little_endian else '>'

        gml = Gml()
        gml.unpack(file, sel_endian)
        images = {}

        texid = 0

        for i, entry in enumerate(gml.entrys):
            print(MSG_INFO_INIT.format('Generate Blender Mesh'))
            print(MSG_INFO_DATA.format('Mesh Name', entry.name))
            mesh_name = NAME_POLYGON.format(i)
            mesh = bpy.data.meshes.new(mesh_name)
            obj = bpy.data.objects.new(entry.name, mesh)

            scene = bpy.context.scene
            scene.collection.objects.link(obj)           # 2.80+
            bpy.context.view_layer.objects.active = obj  # 2.80+
            obj.select_set(True)                         # 2.80+

            bm = bmesh.new()
            gcmf = entry.gcmf
            mesh_data = Mesh_data()

            flags = numpy.array(0x00, dtype='i4')
            total_flags = numpy.array(0x00, dtype='i4')

            print(MSG_INFO_DATA.format('Texture Count', len(gcmf.textures)))
            gcmf_texs_data = gcmf.textures

            mtxidxs = gcmf.mtx_idxs
            mtxs = gcmf.mtxs

            print(MSG_INFO_DATA.format('Submesh Count', len(gcmf.submeshs)))
            for matid, submesh in enumerate(gcmf.submeshs):
                attribute = submesh.material.vtx_descriptor
                flags = attribute.pack()
                total_flags = flags | total_flags
                for j, dlist in enumerate(submesh.dlists):
                    is_cw = (j % 2 == 1)
                    generate_mesh(mesh, bm, matid, mesh_data, dlist, mtxidxs, mtxs, is_cw)

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

            if all_attribute.gx_va_clr0:
                generate_vertexcolor(mesh, NAME_VERTEXCOLOR.format(0), mesh_data.color0s)
            if all_attribute.gx_va_clr1:
                generate_vertexcolor(mesh, NAME_VERTEXCOLOR.format(1), mesh_data.color1s)
            if all_attribute.gx_va_tex0:
                generate_uv(mesh, NAME_UV.format(0), mesh_data.tex0s)
            if all_attribute.gx_va_tex1:
                generate_uv(mesh, NAME_UV.format(1), mesh_data.tex1s)
            if all_attribute.gx_va_tex2:
                generate_uv(mesh, NAME_UV.format(2), mesh_data.tex2s)
            if all_attribute.gx_va_tex3:
                generate_uv(mesh, NAME_UV.format(3), mesh_data.tex3s)
            if all_attribute.gx_va_tex4:
                generate_uv(mesh, NAME_UV.format(4), mesh_data.tex4s)
            if all_attribute.gx_va_tex5:
                generate_uv(mesh, NAME_UV.format(5), mesh_data.tex5s)
            if all_attribute.gx_va_tex6:
                generate_uv(mesh, NAME_UV.format(6), mesh_data.tex6s)
            if all_attribute.gx_va_tex7:
                generate_uv(mesh, NAME_UV.format(7), mesh_data.tex7s)

            # Material
            for matid, submesh in enumerate(gcmf.submeshs):
                material = submesh.material
                is_alpha = matid >= gcmf.opaque_count
                mat = generate_material(material, matid, gcmf_texs_data, images, is_alpha)
                mat.gcmf_material.unk0x3C = submesh.unk0x3C
                obj.data.materials.append(mat)

            bm.free()
            mesh.update()
            bpy.context.object.rotation_euler[0] = 1.5708

            if bpy.context.mode == 'EDIT_ARMATURE':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

            if len(gcmf.mtxs) > 0:
                bpy.ops.object.add(type='ARMATURE', location=(0, 0, 0), enter_editmode=False)
                armature_name = NAME_ARMATURE.format(entry.name)
                bpy.context.object.name = armature_name

                for j, matrix in enumerate(gcmf.mtxs):
                    bpy.ops.object.mode_set(mode='EDIT')
                    name = NAME_NODE.format(j)
                    b = bpy.context.object.data.edit_bones.new(name)
                    b.head = mathutils.Vector((0.0, 0.0, 0.0))
                    b.tail = mathutils.Vector((0.0, 0.1, 0.0))
                    b.transform(matrix.mtx, scale=True, roll=True)

                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy.context.object.rotation_euler[0] = 1.5708

    bpy.ops.object.shade_smooth()
"""