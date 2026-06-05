import bmesh
import bpy
import math
import mathutils
import numpy as np
import struct

from .gma import Gma, GcmfEntry
from .gcmf import Gcmf, Attribute, GCMFError, \
    Texture_Flags0x00, Texture_Mipmap, Texture_Wrap, Texture, TransformMatrix, \
    Submesh, Material, \
    VertexAttribute, VertexRenderFlag, DisplatListHeader, \
    DisplayList, Vertex, Strip
from .gcmf_shader_node import GCMFTextureNode, collect_gcmf_texture_nodes

# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
MSG_INFO_INIT        = '---- {0} ----'
MSG_INFO_DATA        = '{0}: {1}'
MSG_WARN_TOO_MANY    = 'Detect too many {0}s ({1}). Ignored {0}[{2}] and mores.'
MSG_WARN_NONE_MAT    = 'Ignored "{0}". Detect none Material Object.'
MSG_WARN_NO_SUPPORT  = 'Ignored "{0}". Detect unsupported GCMF Attribute.'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def convert_flags2value(src_flags: list) -> int:
    """Convert a list of boolean flags to a packed integer value."""
    max_bit = len(src_flags) - 1
    val = 0
    for i, flag in enumerate(src_flags):
        val += int(flag) << (max_bit - i)
    return val


# ---------------------------------------------------------------------------
# Texture  (GCMFTextureNode -> GCMF Texture struct)
# ---------------------------------------------------------------------------
def generate_texture(gcmf_texture_node: GCMFTextureNode, idx: int) -> Texture:
    """
    Build a GCMF Texture struct from a GCMFTextureNode instance.
    Replaces the legacy generate_texture(tex, idx) that used bpy.data.textures.
    """
    texture = Texture()
    texture.index         = idx
    texture.unk0x00       = convert_flags2value(gcmf_texture_node.unk0x00)
    texture.mipmap        = convert_flags2value(gcmf_texture_node.mipmap)
    texture.uv_wrap       = convert_flags2value(gcmf_texture_node.uv_wrap)
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
    """Build a placeholder TransformMatrix (identity-like stub)."""
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
    """Build a VertexAttribute from the material's vtx_descriptor flags."""
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
                      all_gcmf_mat_nodes: list,
                      warnings: list) -> Material:
    """Build a GCMF Material struct from a Blender material."""
    material   = Material()
    vtx_attr   = generate_vat(bl_mat, bm)
    vtx_render = VertexRenderFlag()
    vtx_render.dlist0_0 = True

    gcmf_mat   = bl_mat.gcmf_material
    gcmf_nodes = collect_gcmf_texture_nodes(bl_mat)
    tex_count  = len(gcmf_nodes)
    if tex_count > 3:
        warnings.append(MSG_WARN_TOO_MANY.format('TEXTURE', tex_count, 3))
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
def generate_vertex(bm_vtx: bmesh.types.BMVert,
                    loop: bmesh.types.BMLoop,
                    split_normal_map: dict,
                    tri_to_pre_poly: dict,
                    bm: bmesh.types.BMesh,
                    gcmf_nodes: list,
                    obj: bpy.types.Object) -> Vertex:
    """
    Build a GCMF Vertex from a BMesh vertex and its loop.

    Split normals are fetched from split_normal_map keyed by
    (pre_triangulate_poly_index, vert_index). The tri_to_pre_poly dict maps
    post-triangulate face indices back to their pre-triangulate poly indices,
    ensuring correct split normals even after Triangulate modifier is applied.
    """
    vtx = Vertex()
    vtx.pos = [bm_vtx.co.x, bm_vtx.co.y, bm_vtx.co.z]

    # Resolve the pre-triangulate polygon index for this face.
    # split_normal_map is built from the pre-triangulate mesh, so we must
    # convert the current (post-triangulate) face index before lookup.
    pre_poly_idx = tri_to_pre_poly.get(loop.face.index, loop.face.index)
    key = (pre_poly_idx, bm_vtx.index)
    if key in split_normal_map:
        nrm = split_normal_map[key]
    else:
        # Fallback: use vertex normal if the key is missing.
        nrm = bm_vtx.normal
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
        y  = -(loop[uv_layer].uv[1] - 1.0)
        uv = [loop[uv_layer].uv[0], y]
        if   i == 0: vtx.tex0 = uv
        elif i == 1: vtx.tex1 = uv
        elif i == 2: vtx.tex2 = uv
        elif i == 3: vtx.tex3 = uv
        elif i == 4: vtx.tex4 = uv
        elif i == 5: vtx.tex5 = uv
        elif i == 6: vtx.tex6 = uv
        elif i == 7: vtx.tex7 = uv
    return vtx


# ---------------------------------------------------------------------------
# Triangle-Strip generation (greedy algorithm)
# ---------------------------------------------------------------------------

def _greedy_next_face(tail1_vert: bmesh.types.BMVert,
                      tail0_vert: bmesh.types.BMVert,
                      visited: set,
                      mat_idx: int):
    """
    Find an unvisited adjacent face that shares the edge (tail1, tail0).

    Only the edge connecting the current strip tail vertices is considered as
    a valid continuation edge. Sharp edges are skipped to prevent crossing
    normal-split boundaries, which would corrupt split normals in the GX strip.

    Returns: (next_face, shared_edge) or (None, None)
    """
    tail1_edges  = set(tail1_vert.link_edges)
    tail0_edges  = set(tail0_vert.link_edges)
    shared_edges = tail1_edges & tail0_edges

    for edge in shared_edges:
        # Skip sharp edges; crossing them would put the same vertex in two
        # different normal groups, which cannot be expressed in a GX strip.
        if edge.smooth is False:
            continue
        for linked_face in edge.link_faces:
            if linked_face.index not in visited \
                    and linked_face.material_index == mat_idx:
                return linked_face, edge

    return None, None


def _greedy_find_exit_edge(face: bmesh.types.BMFace,
                           visited: set,
                           mat_idx: int):
    """
    Find an edge of *face* that leads to an unvisited face of the same material.

    Sharp edges are excluded so that the strip never crosses a normal-split
    boundary. Returns None if no suitable exit edge exists.
    """
    for edge in face.edges:
        if edge.smooth is False:
            continue
        candidates = [f for f in edge.link_faces
                      if f is not face
                      and f.index not in visited
                      and f.material_index == mat_idx]
        if candidates:
            return edge
    return None


def _greedy_build_strip(start_face: bmesh.types.BMFace,
                        visited: set) -> list:
    """
    Build a GX triangle-strip greedily starting from *start_face*.

    Return value is a list of (BMFace, BMEdge|None, initial_loops|None):
      index 0: (start_face, None, [head_loop, tail1_loop, tail0_loop])
      index i: (face_i, shared_edge, None)

    Initialization strategy for tail1/tail0:
      An exit edge (one that leads to an unvisited face) is searched first.
      Its two vertices become tail1 and tail0 in CCW loop order so that the
      first triangle (head, tail1, tail0) is guaranteed CCW-wound.
      If no exit edge exists the face is isolated; loop order is used as-is.

    GX strip vertex sequence:
      [head, tail1, tail0, new0, new1, ...]
      face0 = (head, tail1, tail0)  CCW
      face1 = (tail0, tail1, new0)  CW   (opposite side of shared edge)
      face2 = (tail0, new0,  new1)  CCW
      (matches the iscw flag convention used in import_gma.py)
    """
    visited.add(start_face.index)

    exit_edge  = _greedy_find_exit_edge(start_face, visited, start_face.material_index)
    face_loops = list(start_face.loops)

    if exit_edge is not None:
        # Determine tail1/tail0 from the CCW loop order of start_face so that
        # the initial triangle winds correctly.
        exit_vert_set           = set(exit_edge.verts)
        head_loop = tail1_loop = tail0_loop = None
        for i in range(3):
            lp_a = face_loops[i]
            lp_b = face_loops[(i + 1) % 3]
            if lp_a.vert in exit_vert_set and lp_b.vert in exit_vert_set:
                tail1_loop = lp_a
                tail0_loop = lp_b
                head_loop  = face_loops[(i + 2) % 3]
                break
        tail1         = tail1_loop.vert
        tail0         = tail0_loop.vert
        initial_loops = [head_loop, tail1_loop, tail0_loop]
    else:
        # Isolated face: fall back to raw loop order.
        initial_loops = face_loops
        tail1         = face_loops[-2].vert
        tail0         = face_loops[-1].vert

    result = [(start_face, None, initial_loops)]

    # Track vertices already in the strip to detect cyclic meshes.
    # GX strips do not allow duplicate vertices; stop if one would be added.
    strip_verts = set(start_face.verts)

    while True:
        next_face, shared_edge = _greedy_next_face(
            tail1, tail0, visited, start_face.material_index)
        if next_face is None:
            break

        # Resolve the new vertex before appending to avoid adding a face
        # that would introduce a duplicate vertex into the strip.
        new_vert = next(
            (v for v in next_face.verts if v is not tail1 and v is not tail0),
            None
        )
        if new_vert is None:
            break
        if new_vert in strip_verts:
            break

        visited.add(next_face.index)
        result.append((next_face, shared_edge, None))
        strip_verts.add(new_vert)
        tail1 = tail0
        tail0 = new_vert

    return result


def _greedy_strip_to_loops(strip_entries: list) -> list:
    """
    Convert the result of _greedy_build_strip() into a loop list for a GX strip.

    The first face contributes three loops in CCW order (already stored as
    initial_loops in strip_entries[0]). Each subsequent face appends the one
    loop whose vertex is neither tail1 nor tail0 of the current strip tail.
    Because _greedy_build_strip guarantees strip continuity, new_loop is always
    uniquely determined.
    """
    if not strip_entries:
        return []

    _, _, initial_loops = strip_entries[0]
    loops = initial_loops

    for face, shared_edge, _ in strip_entries[1:]:
        if shared_edge is None:
            break

        tail1 = loops[-2].vert
        tail0 = loops[-1].vert

        new_loop = next(
            (lp for lp in face.loops
             if lp.vert is not tail1 and lp.vert is not tail0),
            None
        )
        if new_loop is None:
            break

        loops.append(new_loop)

    return loops


def generate_strip(loops: list,
                   split_normal_map: dict,
                   tri_to_pre_poly: dict,
                   bm: bmesh.types.BMesh,
                   gcmf_nodes: list,
                   obj: bpy.types.Object,
                   attribute: Attribute) -> Strip:
    """Build a Strip struct from a list of BMesh loops."""
    strip = Strip()
    strip.cmd     = 0x99 if attribute.is_16bit else 0x98
    strip.vertexs = [
        generate_vertex(lp.vert, lp, split_normal_map, tri_to_pre_poly, bm, gcmf_nodes, obj)
        for lp in loops
    ]
    strip.count = len(strip.vertexs)
    return strip


def generate_displaylist(bm: bmesh.types.BMesh,
                         mat_idx: int,
                         split_normal_map: dict,
                         tri_to_pre_poly: dict,
                         gcmf_nodes: list,
                         obj: bpy.types.Object,
                         attribute: Attribute) -> DisplayList:
    """
    Generate a DisplayList using the greedy triangle-strip algorithm.

    Faces are visited in index order. Sorting faces by topology in Blender
    before export tends to produce longer strips.
    """
    dlist        = DisplayList()
    target_faces = [f for f in bm.faces if f.material_index == mat_idx]
    if not target_faces:
        return dlist

    visited = set()

    for face in target_faces:
        if face.index in visited:
            continue
        strip_entries = _greedy_build_strip(face, visited)
        loops         = _greedy_strip_to_loops(strip_entries)
        strip         = generate_strip(
            loops, split_normal_map, tri_to_pre_poly, bm, gcmf_nodes, obj, attribute)
        dlist.strips.append(strip)

    return dlist


def generate_displaylistheader() -> DisplatListHeader:
    """Build a default DisplayListHeader."""
    h = DisplatListHeader()
    h.trans_mtxs  = [-1] * 8
    h.dlist_sizes = [0x00, 0x00]
    return h


def generate_submesh(attribute: Attribute,
                     bm: bmesh.types.BMesh,
                     obj: bpy.types.Object,
                     bl_mat: bpy.types.Material,
                     all_gcmf_mat_nodes: list,
                     mat_idx: int,
                     split_normal_map: dict,
                     tri_to_pre_poly: dict,
                     warnings: list) -> Submesh:
    """Build a Submesh struct for one material slot."""
    submesh = Submesh()
    submesh.dlist_headers = [generate_displaylistheader()]

    gcmf_nodes = collect_gcmf_texture_nodes(bl_mat)

    submesh.material              = generate_material(bm, bl_mat, all_gcmf_mat_nodes, warnings)
    submesh.boundingsphere_origin = bl_mat.gcmf_material.boundingsphere_origin
    submesh.unk0x3C               = bl_mat.gcmf_material.unk0x3C
    val = sum(int(b) << (31 - i) for i, b in enumerate(bl_mat.gcmf_material.unk0x40))
    submesh.unk0x40 = val

    submesh.dlists.append(
        generate_displaylist(
            bm, mat_idx, split_normal_map, tri_to_pre_poly, gcmf_nodes, obj, attribute))
    return submesh


# ---------------------------------------------------------------------------
# Attribute
# ---------------------------------------------------------------------------
def generate_attribute(bl_gcfm_attribute: str) -> Attribute:
    """Map the Blender attribute enum string to an Attribute struct."""
    attr = Attribute()
    if   bl_gcfm_attribute == 'is_16bit':    attr.is_16bit    = True
    elif bl_gcfm_attribute == 'is_stiching': attr.is_stiching = True
    elif bl_gcfm_attribute == 'is_skin':     attr.is_skin     = True
    elif bl_gcfm_attribute == 'is_effective':attr.is_effective= True
    return attr


# ---------------------------------------------------------------------------
# GCMF object
# ---------------------------------------------------------------------------
def generate_gcmf(obj: bpy.types.Object, idx: int,
                  warnings: list) -> Gcmf:
    """
    Build a complete GCMF struct from a Blender mesh object.

    Normal extraction is performed in two passes:

    Pass 1 (pre-triangulate):
      Any user-added Triangulate modifiers are temporarily hidden so that
      the evaluated mesh still contains the original polygons. Split normals
      are read with foreach_get('normal') and stored in a dict keyed by
      (polygon_index, vertex_index). The world-space transform (matrix_world
      plus the -90 deg X-axis rotation used by this exporter) is applied to
      each normal so that the values match the coordinate system of the BMesh
      produced in Pass 2.

    Pass 2 (post-triangulate):
      A temporary Triangulate modifier is appended and the depsgraph is
      updated. The triangulated mesh is loaded into a BMesh and transformed.
      A mapping from post-triangulate face indices to pre-triangulate polygon
      indices is built so that generate_vertex() can look up the correct split
      normal for every loop.
    """
    print(MSG_INFO_INIT.format('Generate GCMF'))
    gcmf = Gcmf()
    gcmf.attribute         = generate_attribute(obj.gcmf_object.attribute)
    gcmf.origin            = list(obj.location)
    gcmf.boundspher_radius = max(obj.dimensions)

    curr_idx           = 0
    all_gcmf_mat_nodes = []
    gcmf_textures      = []

    for mat_slot in obj.material_slots:
        bl_mat = mat_slot.material
        if bl_mat is None:
            continue
        gcmf_mat_nodes = collect_gcmf_texture_nodes(bl_mat)
        for i, gcmf_mat_node in enumerate(gcmf_mat_nodes):
            if i >= 3:
                warnings.append(MSG_WARN_TOO_MANY.format('TEXTURE', i, 3))
                break
            all_gcmf_mat_nodes.append(gcmf_mat_node)

    all_gcmf_mat_nodes.sort(key=lambda n: n.order_index)
    for gcmf_mat_node in all_gcmf_mat_nodes:
        texture = generate_texture(gcmf_mat_node, curr_idx)
        gcmf_textures.append(texture)
        curr_idx += 1

    gcmf.textures = sorted(gcmf_textures, key=lambda t: t.index)

    # ------------------------------------------------------------------
    # Pass 1: collect split normals from the pre-triangulate evaluated mesh
    # ------------------------------------------------------------------

    # Hide any Triangulate modifiers the user may have added so that the
    # evaluated mesh still reflects the original polygon structure.
    user_tri_mods = [m for m in obj.modifiers if m.type == 'TRIANGULATE']
    for m in user_tri_mods:
        m.show_render   = False
        m.show_viewport = False

    depsgraph_pre = bpy.context.evaluated_depsgraph_get()
    depsgraph_pre.update()
    obj_eval_pre = obj.evaluated_get(depsgraph_pre)
    bl_mesh_pre  = obj_eval_pre.to_mesh()

    # In Blender 4.x, loops[i].normal is zero-initialized after to_mesh().
    # foreach_get('normal') returns the correct computed split normals.
    loop_count   = len(bl_mesh_pre.loops)
    loop_normals = np.zeros(loop_count * 3, dtype=np.float32)
    bl_mesh_pre.loops.foreach_get('normal', loop_normals)
    loop_normals = loop_normals.reshape(loop_count, 3)

    # Apply the same world-space transform used for vertex positions so that
    # normals are expressed in the exporter's coordinate system.
    rot_x    = mathutils.Matrix.Rotation(math.radians(-90), 4, (1.0, 0.0, 0.0))
    nrm_mat  = (rot_x @ obj.matrix_world).to_3x3().normalized()

    # Build: (pre_poly_index, vert_index) -> transformed split normal
    pre_split_normal_map = {}
    pre_poly_verts       = {}   # pre_poly_index -> set of vert indices
    for poly in bl_mesh_pre.polygons:
        pre_poly_verts[poly.index] = set(poly.vertices)
        for li in poly.loop_indices:
            vi  = bl_mesh_pre.loops[li].vertex_index
            raw = loop_normals[li]
            nrm = nrm_mat @ mathutils.Vector(
                (float(raw[0]), float(raw[1]), float(raw[2])))
            pre_split_normal_map[(poly.index, vi)] = nrm

    obj_eval_pre.to_mesh_clear()

    # Restore user Triangulate modifiers.
    for m in user_tri_mods:
        m.show_render   = True
        m.show_viewport = True

    # ------------------------------------------------------------------
    # Pass 2: build BMesh from the triangulated evaluated mesh
    # ------------------------------------------------------------------

    tri_mod = obj.modifiers.new('_gcmf_triangulate', 'TRIANGULATE')
    tri_mod.quad_method = 'BEAUTY'
    tri_mod.ngon_method = 'BEAUTY'

    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    obj_eval = obj.evaluated_get(depsgraph)
    bl_mesh  = obj_eval.to_mesh()

    # calc_normals_split() was removed in Blender 4.1; guard for older versions.
    if hasattr(bl_mesh, 'calc_normals_split'):
        bl_mesh.calc_normals_split()

    bm = bmesh.new()
    bm.from_mesh(bl_mesh)
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    rot = mathutils.Matrix.Rotation(math.radians(-90), 4, (1.0, 0.0, 0.0))
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=rot, verts=bm.verts)

    # Build post->pre polygon index mapping.
    # Each triangulated face's vertex set is a subset of exactly one
    # pre-triangulate polygon's vertex set.
    tri_to_pre_poly = {}
    for poly in bl_mesh.polygons:
        tri_verts = set(poly.vertices)
        for pre_idx, pre_verts in pre_poly_verts.items():
            if tri_verts.issubset(pre_verts):
                tri_to_pre_poly[poly.index] = pre_idx
                break

    split_normal_map = pre_split_normal_map

    for mat_idx, mat_slot in enumerate(obj.material_slots):
        submesh = generate_submesh(
            gcmf.attribute, bm, obj, mat_slot.material,
            all_gcmf_mat_nodes, mat_idx, split_normal_map, tri_to_pre_poly,
            warnings)
        gcmf.submeshs.append(submesh)

    obj.modifiers.remove(tri_mod)
    obj_eval.to_mesh_clear()

    gcmf.mtx_idxs          = [-1] * 8
    gcmf.texture_count     = len(gcmf.textures)
    transparent_count      = obj.gcmf_object.transparent_count
    gcmf.opaque_count      = len(obj.material_slots) - transparent_count
    gcmf.transparent_count = transparent_count

    obj_eval.to_mesh_clear()
    del bm
    return gcmf


def generate_gcmfentry(obj: bpy.types.Object, idx: int,
                       warnings: list) -> GcmfEntry:
    """Build a GcmfEntry from a Blender object."""
    entry      = GcmfEntry()
    entry.gcmf = generate_gcmf(obj, idx, warnings)
    entry.name = obj.name
    return entry


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def save(filepath: str, little_endian: bool = False) -> list:
    """Export selected objects to a GMA file at *filepath*.

    Returns a list of warning strings that occurred during export.
    Raises GCMFError on fatal errors.
    """
    warnings: list = []
    with open(filepath, 'wb') as file:
        sel_endian  = '<' if little_endian else '>'
        gma         = Gma()
        sorted_objs = sorted(
            bpy.context.selected_objects,
            key=lambda o: o.gcmf_object.index)
        for i, obj in enumerate(sorted_objs):
            if len(obj.material_slots) < 1:
                warnings.append(MSG_WARN_NONE_MAT.format(obj.name))
                continue
            if obj.gcmf_object.attribute in ('is_stiching', 'is_skin', 'is_effective'):
                warnings.append(MSG_WARN_NO_SUPPORT.format(obj.name))
                continue
            gma.entrys.append(generate_gcmfentry(obj, i, warnings))
        gma.pack(file, sel_endian)
    return warnings
