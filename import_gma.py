import array

import bmesh
import bpy
import mathutils
import numpy

from .gma import Gma
from .gcmf import VertexAttribute, Texture_Flags0x00, Texture_Wrap, Material, DisplayList, Attribute
from .gml import Gml

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

def convert_value2flags(value: int, dest_flags: list):
    max_bit = len(dest_flags)
    flags = [False] * max_bit
    for i in range(max_bit):
        val = value >> ((max_bit - 1) - i)
        flags[i] = (val & 0x01) == 1
    return flags


def _get_or_create_image(images: bpy.types.BlendDataImages, name: str):
    """Return a bpy.data.images entry, creating a placeholder if absent."""
    if name not in images:
        img = bpy.data.images.new(name, width=1, height=1)
        img.source = 'FILE'
        img.filepath = name
        images[name] = img
    return images[name]


# ---------------------------------------------------------------------------
# Generate Blender's Material
# ---------------------------------------------------------------------------

def generate_material(material: Material, mat_idx: int, gcmf_texs_data: list, images, is_alpha: bool):
    """
    Create a Blender material and populate gcmf_material custom properties.
    Textures are stored in gcmf_material.gcmf_textures collection; images are
    wired into a Principled BSDF node tree for basic viewport preview.
    """
    mat = bpy.data.materials.new(name=NAME_MATERIAL.format(mat_idx))
    mat.use_nodes = True

    # ---- Store original GCMF values ----
    gcmf_material = mat.gcmf_material
    gcmf_material.unk0x02 = convert_value2flags(material.unk0x02, gcmf_material.unk0x02)
    gcmf_material.unk0x03 = convert_value2flags(material.unk0x03, gcmf_material.unk0x03)
    gcmf_material.color0 = material.color0
    gcmf_material.color1 = material.color1
    gcmf_material.color2 = material.color2
    gcmf_material.emission = material.emission
    gcmf_material.transparency = material.transparency
    gcmf_material.unk0x14 = material.unk0x14
    gcmf_material.unk0x15 = material.unk0x15
    gcmf_material.texture_indexes = material.texture_indexs
    gcmf_material.vtx_descriptor = convert_value2flags(material.vtx_descriptor.pack(), gcmf_material.vtx_descriptor)
    gcmf_material.order_index = mat_idx

    # ---- Basic node setup ----
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Diffuse colour from color0
    r = material.color0[0] / 0xFF
    g = material.color0[1] / 0xFF
    b = material.color0[2] / 0xFF
    a = material.transparency / 0xFF if not is_alpha else 0.0
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
    bsdf.inputs['Alpha'].default_value = a

    if is_alpha or material.transparency < 0xFF:
        mat.blend_method = 'BLEND'

    # ---- Per-texture settings (replaces old texture_slots) ----
    tex_x_offset = -600
    for i, texid in enumerate(material.texture_indexs):
        if texid < 0:
            continue

        # Append a new slot in the collection
        ts = gcmf_material.gcmf_textures.add()
        raw_tex = gcmf_texs_data[texid] if texid < len(gcmf_texs_data) else None
        if raw_tex is not None:
            ts.unk0x00 = convert_value2flags(raw_tex.unk0x00, ts.unk0x00)
            ts.mipmap = convert_value2flags(raw_tex.mipmap, ts.mipmap)
            ts.uv_wrap = convert_value2flags(raw_tex.uv_wrap, ts.uv_wrap)
            ts.texture_index = raw_tex.texture_index
            ts.unk0x06 = raw_tex.unk0x06
            ts.anisotropy = convert_value2flags(raw_tex.anisotropy, ts.anisotropy)
            ts.unk0x0C = convert_value2flags(raw_tex.unk0x0C, ts.unk0x0C)
            ts.is_swappable = convert_value2flags(raw_tex.is_swappable, ts.is_swappable)
            ts.unk0x10 = convert_value2flags(raw_tex.unk0x10, ts.unk0x10)
            ts.order_index = texid

            # Image name
            img_id = raw_tex.texture_index
            if img_id >= 0:
                if ts.unk0x00[Texture_Flags0x00.COMMON_TEX]:
                    img_name = NAME_TPL_COMMON.format(img_id)
                else:
                    img_name = NAME_TPL.format(img_id)
                img = _get_or_create_image(images, img_name)

                # Wire first texture into the BSDF for a basic preview
                if i == 0:
                    tex_node = nodes.new('ShaderNodeTexImage')
                    tex_node.image = img
                    tex_node.location = (tex_x_offset, 200)
                    links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
                    if is_alpha:
                        links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
                    tex_x_offset -= 300

    return mat


# ---------------------------------------------------------------------------
# Generate Blender's UV
# ---------------------------------------------------------------------------

def generate_uv(mesh: bpy.types.Mesh, channel_name: str, uvs: list):
    if channel_name not in mesh.uv_layers:
        mesh.uv_layers.new(name=channel_name)
    uv_layer = mesh.uv_layers[channel_name]
    for i, loop in enumerate(mesh.loops):
        uv_layer.data[i].uv = uvs[loop.vertex_index]


# Generate Blender's VertexColor
def generate_vertexcolor(mesh: bpy.types.Mesh, color_name: str, vcolors: list):
    if color_name not in mesh.vertex_colors:
        mesh.vertex_colors.new(name=color_name)
    vc_layer = mesh.vertex_colors[color_name]
    for i, loop in enumerate(mesh.loops):
        vc_layer.data[i].color = vcolors[loop.vertex_index]


# Generate mesh from Gcmf Object
def generate_mesh(mesh: bpy.types.Mesh, bm: bmesh.types.BMesh, matid: int, mesh_data: Mesh_data, dlist: DisplayList, mtxidxs: list, mtxs: list, first_iscw: bool):
    v0 = mathutils.Vector((0, 0, 0))
    v1 = mathutils.Vector((0, 0, 0))
    v2 = mathutils.Vector((0, 0, 0))
    iscw = first_iscw
    for strip in dlist.strips:
        for i, vertex in enumerate(strip.vertexs):
            vtx = mathutils.Vector((vertex.pos[0], vertex.pos[1], vertex.pos[2]))
            # Point_Normal_Matrix Index
            pnmtxidx = vertex.pnmtxidx
            if pnmtxidx >= 0:
                if (pnmtxidx > 0x18) or ((pnmtxidx % 3) != 0):
#                    print(MSG_INFO_DATA.format('pnmtxidx', pnmtxidx))
                    pass
                else:
                    ridx = int((pnmtxidx / 3) - 1)
#                    print(ridx)
                    idx = mtxidxs[ridx]
                    if idx < 0:
#                        print(MSG_INFO_DATA.format('matrix_index', idx))
                        pass
                    else:
                        mtx = mtxs[idx].mtx
                        vtx = mtx @ vtx  # '@' replaces '*' for matrix-vector in 2.80+
            v = bm.verts.new(vtx)
            vec = mathutils.Vector((vertex.nrm[0], vertex.nrm[1], vertex.nrm[2]))
            v.normal = vec
            mesh_data.normals.append(vec.normalized())
            clr = mathutils.Vector((vertex.clr0[0] / 0xFF, vertex.clr0[1] / 0xFF,
                                    vertex.clr0[2] / 0xFF, vertex.clr0[3] / 0xFF))
            mesh_data.color0s.append(clr)
            clr = mathutils.Vector((vertex.clr1[0] / 0xFF, vertex.clr1[1] / 0xFF,
                                    vertex.clr1[2] / 0xFF, vertex.clr1[3] / 0xFF))
            mesh_data.color1s.append(clr)
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


# ---------------------------------------------------------------------------
# Generate GCMF Attribute
# ---------------------------------------------------------------------------

def generate_attribute(attribute: Attribute):
    if attribute.is_16bit:
        return 'is_16bit'
    elif attribute.is_stiching:
        return 'is_stiching'
    elif attribute.is_skin:
        return 'is_skin'
    elif attribute.is_effective:
        return 'is_effective'
    else:
        return "default"


# Import gma
def load(filepath: str, little_endian=False):
    with open(filepath, 'rb') as file:
        sel_endian = '<' if little_endian else '>'

        gma = Gma()
        gma.unpack(file, sel_endian)
        images = {}

        texid = 0
        entrys = gma.entrys

        for i, entry in enumerate(entrys):
#            print(MSG_INFO_INIT.format('Generate Blender Mesh'))
#            print(MSG_INFO_DATA.format('Mesh Name', entry.name))
            mesh_name = NAME_POLYGON.format(i)
            mesh = bpy.data.meshes.new(mesh_name)
            obj = bpy.data.objects.new(entry.name, mesh)

            scene = bpy.context.scene
            scene.collection.objects.link(obj)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            bm = bmesh.new()
            gcmf = entry.gcmf
            # Store Normals, UVs, VertexColors, etc
            mesh_data = Mesh_data()

            obj.gcmf_object.index = i
            obj.gcmf_object.attribute = generate_attribute(gcmf.attribute)
            obj.gcmf_object.transparent_material_count = gcmf.transparent_count

            flags = numpy.array(0x00, dtype='i4')
            total_flags = numpy.array(0x00, dtype='i4')

            # Texture
#            print(MSG_INFO_DATA.format('Texture Count', len(gcmf.textures)))
            # Keep raw GCMF texture structs for property population
            gcmf_texs_data = gcmf.textures

            mtxidxs = gcmf.mtx_idxs
            mtxs = gcmf.mtxs

#            print(MSG_INFO_DATA.format('Submesh Count', len(gcmf.submeshs)))
            for mat_idx, submesh in enumerate(gcmf.submeshs):
                #Vertex Attribute
                attribute = submesh.material.vtx_descriptor
                flags = attribute.pack()
                #Store all submesh's attribute
                total_flags = flags | total_flags
                for j, dlist in enumerate(submesh.dlists):
                    is_cw = (j % 2 == 1)
                    # even : ccw
                    # odd  : cw
                    generate_mesh(mesh, bm, mat_idx, mesh_data, dlist, mtxidxs, mtxs, is_cw)

            #Generate Vertex_Attribute from all submeshs's vertex_attribute
            all_attribute = VertexAttribute()
            all_attribute.unpack(total_flags)
            mesh.update()

            # Normals (Blender 4.1+ dropped normals_split_custom_set_from_vertices)
            if all_attribute.gx_va_nrm:
                mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
                try:
                    # Blender 4.1+
                    mesh.normals_split_custom_set_from_vertices(mesh_data.normals)
                except AttributeError:
                    # Blender 4.1 removed use_auto_smooth; normals set via corner_normals
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
            texid_offset = 0
            for mat_idx, submesh in enumerate(gcmf.submeshs):
                material = submesh.material
                is_alpha = mat_idx >= gcmf.opaque_count
                mat = generate_material(material, mat_idx, gcmf_texs_data, images, is_alpha)
                mat.gcmf_material.unk0x3C = submesh.unk0x3C
                mat.gcmf_material.unk0x40 = convert_value2flags(
                    submesh.unk0x40, mat.gcmf_material.unk0x40)
                obj.data.materials.append(mat)

            bm.free()
            mesh.update()
            # Rotate X-axis 90 deg
            bpy.context.object.rotation_euler[0] = 1.5708

            #Transform to Node
            if bpy.context.mode == 'EDIT_ARMATURE':
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

            if(len(gcmf.mtxs) > 0):
                #Add Armature
                bpy.ops.object.add(type='ARMATURE', location=(0, 0, 0), enter_editmode=False)
                armature_name = NAME_ARMATURE.format(entry.name)
                bpy.context.object.name = armature_name

                for j, matrix in enumerate(gcmf.mtxs):
                    #Edit Mode
                    bpy.ops.object.mode_set(mode='EDIT')
                    #Instatiate Bone
                    name = NAME_NODE.format(j)
                    b = bpy.context.object.data.edit_bones.new(name)
                    #Apply Matrix to EditBone object
                    b.head = mathutils.Vector((0.0, 0.0, 0.0))
                    b.tail = mathutils.Vector((0.0, 0.1, 0.0))
                    b.transform(matrix.mtx, scale=True, roll=True)

                # Object Mode
                bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                bpy.context.object.rotation_euler[0] = 1.5708

    bpy.ops.object.shade_smooth()
