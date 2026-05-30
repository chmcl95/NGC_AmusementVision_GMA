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
def generate_vertex(bm_vtx, loop, split_normal_map, tri_to_pre_poly, bm, gcmf_nodes, obj) -> Vertex:
    vtx = Vertex()
    vtx.pos = [bm_vtx.co.x, bm_vtx.co.y, bm_vtx.co.z]
    # split normal を bl_mesh.loops[loop.index].normal から取得する。
    # evaluated mesh を Triangulate モディファイア適用済みで to_mesh() しているため
    # bm.from_mesh 後の loop.index は bl_mesh.loops の index と一致する。
    # calc_normals_split() 呼び出し済みのため Sharp エッジが反映された法線が得られる。
    # split_normal_map[(face.index, vert.index)] で split normal を取得する。
    # loop.index による bl_mesh.loops 参照は使用しない。
    # 理由: bm.from_mesh 後の transform/rotate で bm の loop 順序が変わり
    # loop.index と bl_mesh.loops の index がずれるため。
    # Triangulate後のface_index → Triangulate前のpoly_indexに変換してkeyを引く
    pre_poly_idx = tri_to_pre_poly.get(loop.face.index, loop.face.index)
    key = (pre_poly_idx, bm_vtx.index)
    if key in split_normal_map:
        nrm = split_normal_map[key]
    else:
        # フォールバック: split_normal_map に存在しない場合は頂点法線を使用
        nrm = bm_vtx.normal
        print("[generate_vertex] WARNING: key={} not in split_normal_map, fallback to vert_normal".format(key))
    vtx.nrm = [nrm[0], nrm[1], nrm[2]]

    # --- 法線デバッグログ ---
    print("[generate_vertex] vert={} face={} pos=({:.3f},{:.3f},{:.3f})".format(
        bm_vtx.index, loop.face.index,
        bm_vtx.co.x, bm_vtx.co.y, bm_vtx.co.z))
    print("[generate_vertex]   bmesh_vert_normal   =({:+.4f},{:+.4f},{:+.4f})".format(
        bm_vtx.normal.x, bm_vtx.normal.y, bm_vtx.normal.z))
    print("[generate_vertex]   bmesh_face_normal   =({:+.4f},{:+.4f},{:+.4f})".format(
        loop.face.normal.x, loop.face.normal.y, loop.face.normal.z))
    print("[generate_vertex]   split_normal(export)=({:+.4f},{:+.4f},{:+.4f})".format(
        nrm[0], nrm[1], nrm[2]))
    print("[generate_vertex]   map_key={} pre_poly={} matched={}".format(
        (loop.face.index, bm_vtx.index), pre_poly_idx, key in split_normal_map))

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


# ---------------------------------------------------------------------------
# Triangle-Strip (Greedy)
# ---------------------------------------------------------------------------

def _greedy_next_face(tail1_vert, tail0_vert, visited: set, mat_idx: int):
    """
    strip 末尾2頂点 (tail1, tail0) を辺として持つ
    未訪問かつ同一マテリアルの隣接面を探す。

    mat_idx を追加して異なるマテリアルの face への侵入を防ぐ。

    Returns: (next_face, shared_edge) or (None, None)
    """
    print("[_greedy_next_face] start  tail1={} tail0={}".format(
        tail1_vert.index, tail0_vert.index))

    # tail1 と tail0 が共有する辺を取得する
    # この辺が GX strip の「継続辺」となる
    tail1_edges = set(tail1_vert.link_edges)
    tail0_edges = set(tail0_vert.link_edges)
    shared_edges = tail1_edges & tail0_edges   # strip末尾2頂点を繋ぐ辺

    print("[_greedy_next_face] scanning  tail1_edges={} tail0_edges={}".format(
        sorted([sorted([v.index for v in e.verts]) for e in tail1_edges]),
        sorted([sorted([v.index for v in e.verts]) for e in tail0_edges])))
    print("[_greedy_next_face] scanning  shared_edges(tail1-tail0)={}".format(
        sorted([sorted([v.index for v in e.verts]) for e in shared_edges])))

    for edge in shared_edges:
        edge_verts = sorted([v.index for v in edge.verts])
        # Sharp エッジを跨ぐ遷移は禁止する。
        # Sharp エッジを跨ぐと同一頂点で split_normal が異なる面グループに
        # 入ってしまい、GX strip として正しく表現できない。
        if edge.smooth is False:
            print("[_greedy_next_face] scanning  edge={} SHARP → skip".format(edge_verts))
            continue
        print("[_greedy_next_face] scanning  edge={} link_faces={}".format(
            edge_verts,
            [f.index for f in edge.link_faces]))
        for linked_face in edge.link_faces:
            if linked_face.index not in visited \
                    and linked_face.material_index == mat_idx:
                print("[_greedy_next_face] end    next_face.index={}  shared_edge={}".format(
                    linked_face.index, edge_verts))
                return linked_face, edge

    print("[_greedy_next_face] end    next_face=None")
    return None, None


def _greedy_find_exit_edge(face, visited: set, mat_idx: int):
    """
    face の3辺から「未訪問かつ同一マテリアルの隣接面を持つ辺」を1つ返す。
    strip の出口辺（継続辺）の候補を探す。
    見つからなければ None を返す。

    mat_idx を追加して異なるマテリアルの face への侵入を防ぐ。
    """
    print("[_greedy_find_exit_edge] start  face.index={}".format(face.index))
    for edge in face.edges:
        edge_verts = sorted([v.index for v in edge.verts])
        # Sharp エッジは出口辺にしない
        if edge.smooth is False:
            print("[_greedy_find_exit_edge] scanning  edge={}  SHARP → skip".format(edge_verts))
            continue
        candidates = [f for f in edge.link_faces
                      if f is not face
                      and f.index not in visited
                      and f.material_index == mat_idx]
        print("[_greedy_find_exit_edge] scanning  edge={}  candidates={}".format(
            edge_verts, [f.index for f in candidates]))
        if candidates:
            print("[_greedy_find_exit_edge] end    exit_edge={}".format(edge_verts))
            return edge
    print("[_greedy_find_exit_edge] end    exit_edge=None")
    return None


def _greedy_build_strip(start_face, visited: set) -> list:
    """
    start_face を起点に貪欲法で triangle-strip を構築する。

    戻り値: (BMFace, BMEdge or None) のリスト
      [0] = (start_face, None)         先頭は共有辺なし
      [i] = (face_i, shared_edge_i-1)  i番目の面と strip末尾を繋ぐ実際の共有辺

    【tail1/tail0 の初期化方針】
    start_face の loops[-2],loops[-1] を無条件に tail1,tail0 にすると
    その2頂点を繋ぐ辺が隣接面を持たない境界辺の場合に strip が延びない。
    そのため start_face の3辺から「隣接面を持つ辺（出口辺）」を先に探し
    その辺の2頂点を tail1,tail0 として採用し
    残りの頂点を strip 先頭(head)に置くよう loops を並び替える。

    GX triangle-strip の構造:
      頂点列 [head, tail1, tail0, new0, new1, ...]
      face0 = (head, tail1, tail0)  CCW
      face1 = (tail0, tail1, new0)  CW   共有辺(tail1,tail0)の反対側 new0
      face2 = (tail0, new0, new1)   CCW  共有辺(new0,tail0)の反対側 new1
      import_gma.py の iscw フラグと同じ規則に従う。
    """
    print("[_greedy_build_strip] start  start_face.index={}".format(start_face.index))
    visited.add(start_face.index)

    # start_face の出口辺（隣接面を持つ辺）を探して CCW 順に tail1,tail0 を決定する
    exit_edge = _greedy_find_exit_edge(start_face, visited, start_face.material_index)
    face_loops = list(start_face.loops)
    if exit_edge is not None:
        # start_face.loops の CCW 順で exit_edge の2頂点が連続する位置を探す
        # loops[i]=tail1, loops[(i+1)%3]=tail0 とすることで CCW 順を保証する
        exit_vert_set = set(exit_edge.verts)
        head_loop = tail1_loop = tail0_loop = None
        for i in range(3):
            lp_a = face_loops[i]
            lp_b = face_loops[(i + 1) % 3]
            if lp_a.vert in exit_vert_set and lp_b.vert in exit_vert_set:
                tail1_loop = lp_a
                tail0_loop = lp_b
                head_loop  = face_loops[(i + 2) % 3]
                break
        tail1 = tail1_loop.vert
        tail0 = tail0_loop.vert
        # 先頭 face の loop 順: [head, tail1, tail0] → CCW 保証
        initial_loops = [head_loop, tail1_loop, tail0_loop]
        print("[_greedy_build_strip] init  head={} tail1={} tail0={}".format(
            head_loop.vert.index, tail1.index, tail0.index))
    else:
        # 出口辺がない（孤立面）: loops 順のまま
        initial_loops = face_loops
        tail1 = face_loops[-2].vert
        tail0 = face_loops[-1].vert
        print("[_greedy_build_strip] init(no exit)  tail1={} tail0={}".format(
            tail1.index, tail0.index))

    # 戻り値: (face, shared_edge, initial_loops or None)
    # initial_loops は先頭 face のみ設定、以降は None
    result = [(start_face, None, initial_loops)]

    # strip 内で使用済みの頂点を追跡する
    # 環状メッシュで new_vert がすでに strip 内に存在する場合に打ち切るために使用する。
    # GX strip は頂点の重複を許容しないため、重複が発生したら終了する。
    strip_verts = set(v for v in start_face.verts)

    while True:
        next_face, shared_edge = _greedy_next_face(tail1, tail0, visited, start_face.material_index)
        if next_face is None:
            break

        # new_vert を先に確認する。
        # visited.add / result.append の前にチェックすることで
        # 重複頂点を持つ face が result に追加されるのを防ぐ。
        new_vert = next(
            (v for v in next_face.verts
             if v is not tail1 and v is not tail0),
            None
        )
        if new_vert is None:
            break

        # 新頂点が strip 内にすでに存在する場合は打ち切る
        # result に追加する前に判定することで _greedy_strip_to_loops への
        # 重複頂点の混入を防ぐ
        if new_vert in strip_verts:
            print("[_greedy_build_strip] break  new_vert={} already in strip".format(
                new_vert.index))
            break

        visited.add(next_face.index)
        result.append((next_face, shared_edge, None))
        strip_verts.add(new_vert)
        tail1 = tail0
        tail0 = new_vert

    face_indices = [f.index for f, _, _ in result]
    print("[_greedy_build_strip] end    strip_faces={}".format(face_indices))
    return result


def _greedy_strip_to_loops(strip_entries: list) -> list:
    """
    _greedy_build_strip() の結果を GX triangle-strip の loop 列に変換する。

    先頭 face の 3 loop を CCW 順で並べ、以降は strip 末尾の 2 頂点
    (tail1, tail0) と照合し、どちらでもない頂点の loop を新頂点として追加する。
    _greedy_build_strip 内で strip連続性が保証されているため
    new_loop は必ず一意に決まる。
    """
    print("[_greedy_strip_to_loops] start  entries={}".format(len(strip_entries)))
    if not strip_entries:
        print("[_greedy_strip_to_loops] end    loops=[]")
        return []

    first_face, _, initial_loops = strip_entries[0]

    # _greedy_build_strip が決定した initial_loops をそのまま使う
    # これにより head/tail1/tail0 の CCW 順が保証される
    loops = initial_loops
    print("[_greedy_strip_to_loops] head verts={}".format(
        [lp.vert.index for lp in loops]))

    for face, shared_edge, _ in strip_entries[1:]:
        if shared_edge is None:
            break

        tail1 = loops[-2].vert
        tail0 = loops[-1].vert

        # shared_edge が strip末尾2頂点を繋ぐ辺であることが保証されているため
        # new_loop は face の3 loop の中で tail1でもtail0でもない唯一の loop
        new_loop = next(
            (lp for lp in face.loops
             if lp.vert is not tail1 and lp.vert is not tail0),
            None
        )
        if new_loop is None:
            break

        print("[_greedy_strip_to_loops] append vert.index={}".format(new_loop.vert.index))
        loops.append(new_loop)

    vert_indices = [lp.vert.index for lp in loops]
    print("[_greedy_strip_to_loops] end    vert_indices={}".format(vert_indices))
    return loops


def generate_strip(loops: list, split_normal_map, tri_to_pre_poly, bm, gcmf_nodes, obj, attribute: Attribute) -> Strip:
    """
    loop リストから Strip を生成する。
    貪欲法導入により引数を face 単位から loop リスト単位に変更している。
    """
    print("[generate_strip] start  loop_count={} vert_indices={}".format(
        len(loops), [lp.vert.index for lp in loops]))
    strip = Strip()
    strip.cmd     = 0x99 if attribute.is_16bit else 0x98
    strip.vertexs = [
        generate_vertex(lp.vert, lp, split_normal_map, tri_to_pre_poly, bm, gcmf_nodes, obj)
        for lp in loops
    ]
    strip.count = len(strip.vertexs)
    # strip 全頂点の法線サマリー（generate_vertex の詳細ログの後に出力）
    print("[generate_strip] end    normal_summary:")
    for lp, vtx in zip(loops, strip.vertexs):
        print("[generate_strip]   vert={} split_nrm=({:+.4f},{:+.4f},{:+.4f})".format(
            lp.vert.index, vtx.nrm[0], vtx.nrm[1], vtx.nrm[2]))
    return strip


def generate_displaylist(bm, mat_idx, split_normal_map, tri_to_pre_poly, gcmf_nodes, obj, attribute: Attribute) -> DisplayList:
    """
    貪欲法 triangle-strip で DisplayList を生成する。

    フェースインデックス順に出発面を選択するため、
    Blender の Sort Elements (Faces → By Topology 等) で
    インデックスを整列させてからエクスポートすると
    より長い Strip が生成されやすい。
    """
    print("[generate_displaylist] start  mat_idx={}".format(mat_idx))
    dlist = DisplayList()

    target_faces = [f for f in bm.faces if f.material_index == mat_idx]
    if not target_faces:
        print("[generate_displaylist] end    no target faces")
        return dlist

    visited = set()

    for face in target_faces:           # フェースインデックス順に走査
        if face.index in visited:
            continue
        strip_entries = _greedy_build_strip(face, visited)
        loops         = _greedy_strip_to_loops(strip_entries)
        strip         = generate_strip(loops, split_normal_map, tri_to_pre_poly, bm, gcmf_nodes, obj, attribute)
        dlist.strips.append(strip)

    print("[generate_displaylist] end    strips={} total_verts={}".format(
        len(dlist.strips),
        sum(s.count for s in dlist.strips)))
    return dlist


def generate_displaylistheader() -> DisplatListHeader:
    h = DisplatListHeader()
    h.trans_mtxs  = [-1] * 8
    h.dlist_sizes = [0x00, 0x00]
    return h


def generate_submesh(attribute, bm, obj, bl_mat, all_gcmf_mat_nodes, mat_idx, split_normal_map, tri_to_pre_poly) -> Submesh:
    submesh = Submesh()
    submesh.dlist_headers = [generate_displaylistheader()]

    gcmf_nodes = collect_gcmf_texture_nodes(bl_mat)

    submesh.material = generate_material(bm, bl_mat, all_gcmf_mat_nodes)
    submesh.boundingsphere_origin = bl_mat.gcmf_material.boundingsphere_origin
    submesh.unk0x3C = bl_mat.gcmf_material.unk0x3C
    val = sum(int(b) << (31 - i) for i, b in enumerate(bl_mat.gcmf_material.unk0x40))
    submesh.unk0x40 = val

    submesh.dlists.append(
        generate_displaylist(bm, mat_idx, split_normal_map, tri_to_pre_poly, gcmf_nodes, obj, attribute))
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
    # Triangulate モディファイアを一時的に追加して depsgraph を更新する。
    # これにより evaluated mesh が三角形化済みの状態で to_mesh() される。
    # → bm.from_mesh 後に bmesh.ops.triangulate が不要になる
    # → bm の loop.index が bl_mesh.loops の index と一致する
    # → calc_normals_split() の split normal（Sharp エッジを反映）を
    #   bl_loops[loop.index].normal で正しく参照できる
    # ---- Step 1: Triangulate 前の evaluated mesh から split_normal を取得 ----
    # ユーザーが Triangulate モディファイアを持っている場合、
    # それを一時的に非表示にして Triangulate 前の mesh を取得する。
    user_tri_mods = [m for m in obj.modifiers if m.type == 'TRIANGULATE']
    for m in user_tri_mods:
        m.show_render = False
        m.show_viewport = False

    depsgraph_pre = bpy.context.evaluated_depsgraph_get()
    depsgraph_pre.update()
    obj_eval_pre  = obj.evaluated_get(depsgraph_pre)
    bl_mesh_pre   = obj_eval_pre.to_mesh()

    # Blender 4.x では to_mesh() 後に loops.normal が (0,0,0) のまま。
    # foreach_get で取得することで正しい split_normal が得られる。
    import numpy as np
    loop_count = len(bl_mesh_pre.loops)
    loop_normals = np.zeros(loop_count * 3, dtype=np.float32)
    bl_mesh_pre.loops.foreach_get('normal', loop_normals)
    loop_normals = loop_normals.reshape(loop_count, 3)

    # (poly_index, vert_index) → split_normal
    # split_normal は bl_mesh_pre の座標系（変換前）で格納されているため
    # generate_gcmf で適用する座標変換と同じ変換を法線に適用する。
    # 変換内容: obj.matrix_world の回転部分 + -90度 X軸回転
    import mathutils as _mu
    _rot_x = _mu.Matrix.Rotation(math.radians(-90), 4, (1.0, 0.0, 0.0))
    _nrm_mat = (_rot_x @ obj.matrix_world).to_3x3().normalized()

    pre_split_normal_map = {}
    pre_poly_verts = {}  # pre_poly_index → set of vert_indices
    for poly in bl_mesh_pre.polygons:
        vset = set(poly.vertices)
        pre_poly_verts[poly.index] = vset
        for i, li in enumerate(poly.loop_indices):
            vi = bl_mesh_pre.loops[li].vertex_index
            raw = loop_normals[li]
            # 座標変換を法線に適用（平行移動なし・回転のみ）
            nrm = _nrm_mat @ _mu.Vector((float(raw[0]), float(raw[1]), float(raw[2])))
            pre_split_normal_map[(poly.index, vi)] = nrm
    obj_eval_pre.to_mesh_clear()

    # ユーザーの Triangulate モディファイアを元に戻す
    for m in user_tri_mods:
        m.show_render = True
        m.show_viewport = True

    print("[generate_gcmf] pre_split_normal_map entries={} (before triangulate)".format(
        len(pre_split_normal_map)))

    # ---- Step 2: Triangulate モディファイアを追加してジオメトリを取得 ----
    smooth_mod = None
    tri_mod = obj.modifiers.new("_gcmf_triangulate", 'TRIANGULATE')
    tri_mod.quad_method = 'BEAUTY'
    tri_mod.ngon_method = 'BEAUTY'
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()

    obj_eval  = obj.evaluated_get(depsgraph)
    bl_mesh   = obj_eval.to_mesh()

    # Blender 4.1 以降は calc_normals_split() が廃止されており
    # loops[i].normal に split normal が自動で格納されている。
    # 4.0 以前との互換のため hasattr でガードする。
    if hasattr(bl_mesh, 'calc_normals_split'):
        bl_mesh.calc_normals_split()

    bm = bmesh.new()
    bm.from_mesh(bl_mesh)
    # triangulate は evaluated mesh 側で適用済みのため不要
    bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
    rot = mathutils.Matrix.Rotation(math.radians(-90), 4, (1.0, 0.0, 0.0))
    bmesh.ops.rotate(bm, cent=(0.0,0.0,0.0), matrix=rot, verts=bm.verts)

    # split_normal_map: (polygon_index, vert_index) → split_normal
    #
    # bl_loops[loop.index].normal による参照は使用しない。
    # 理由: bm.from_mesh 後に bmesh.ops.transform / rotate を実行すると
    # bm の face/loop の内部順序が変わり、bm の loop.index と
    # bl_mesh.loops の index がずれて別 face の split_normal を参照してしまう。
    #
    # 代わりに bl_mesh.polygons から (polygon_index, vert_index) のルックアップ
    # テーブルを構築し、bm の face.index と vert.index の組み合わせで引く。
    # bm.from_mesh 直後は bm の face.index = bl_mesh.polygons の index と一致する。
    # ---- Step 3: Triangulate後のface_index → Triangulate前のpoly_index の変換 ----
    # Triangulate後のbl_meshで各三角形の頂点集合を調べ、
    # その頂点集合がサブセットになるTriangulate前のpolyを探す。
    tri_to_pre_poly = {}
    for poly in bl_mesh.polygons:
        tri_verts = set(poly.vertices)
        for pre_idx, pre_verts in pre_poly_verts.items():
            if tri_verts.issubset(pre_verts):
                tri_to_pre_poly[poly.index] = pre_idx
                break
    print("[generate_gcmf] tri_to_pre_poly entries={} (Triangulate後→前の変換)".format(
        len(tri_to_pre_poly)))

    split_normal_map = pre_split_normal_map
    print("[generate_gcmf] split_normal_map entries={}".format(len(split_normal_map)))

    # bl_mesh.polygons と bm.faces の index 対応を確認するログ
    # bm.from_mesh 直後(transform前)の状態で face_index と頂点の対応を出力する
    print("[generate_gcmf] bl_mesh.polygons vs bm.faces 対応確認:")
    bm.faces.ensure_lookup_table()
    for i in range(min(len(bm.faces), 15)):   # 最大15面まで表示
        bm_f  = bm.faces[i]
        bm_vs = sorted([v.index for v in bm_f.verts])
        bm_fn = (round(bm_f.normal.x, 4), round(bm_f.normal.y, 4), round(bm_f.normal.z, 4))
        if i < len(bl_mesh.polygons):
            poly  = bl_mesh.polygons[i]
            bl_vs = sorted(list(poly.vertices))
            bl_fn = (round(poly.normal.x, 4), round(poly.normal.y, 4), round(poly.normal.z, 4))
        else:
            bl_vs = []
            bl_fn = (0,0,0)
        match = "OK" if bm_vs == bl_vs else "MISMATCH!"
        print("[generate_gcmf]   face={} bm_verts={} bl_verts={}  {}  bm_normal={} bl_normal={}".format(
            i, bm_vs, bl_vs, match, bm_fn, bl_fn))

    for mat_idx, mat_slot in enumerate(obj.material_slots):
        submesh = generate_submesh(
            gcmf.attribute, bm, obj, mat_slot.material,
            all_gcmf_mat_nodes, mat_idx, split_normal_map, tri_to_pre_poly)
        gcmf.submeshs.append(submesh)

    # 一時的に追加した Triangulate モディファイアを削除する
    obj.modifiers.remove(tri_mod)
    obj_eval.to_mesh_clear()

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
