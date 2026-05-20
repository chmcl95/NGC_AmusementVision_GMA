"""
gcmf_node.py  –  GCMFTextureNode (ShaderNodeCustomGroup)

2.79版の bpy.types.Texture + gcmf_texture PropertyGroup を
Blender 4.2 のカスタムノードとして再現する。

データ配置の対応:
  2.79                               4.2
  ─────────────────────────────────────────────────────
  bpy.data.textures["gxtex_000"]  →  GCMFTextureNode インスタンス
    .image                        →    .image        (PointerProperty)
    .gcmf_texture.uv_wrap         →    .uv_wrap      (ノード自身のプロパティ)
    .gcmf_texture.texture_index   →    .texture_index
    ... (全フィールド同様)
  material.texture_slots[i]       →  ノードツリー上のリンク接続
"""

import bpy
import re

# ---------------------------------------------------------------------------
# 内部 NodeGroup の名前
# ---------------------------------------------------------------------------
_NODEGROUP_NAME = ".GCMFTextureNodeGroup"   # 先頭 . でアセットブラウザから非表示

NAME_GXMDLVIEW_OBJ_BOUND_SPHERE = 'Bounding Spher Center (X, Y, Z)'
NAME_GXMDLVIEW_OBJ_UNK3C = 'Unknown (0x3C)'
NAME_GXMDLVIEW_OBJ_UNK40 = 'Unknown (0x40)'
NAME_GXMDLVIEW_TEX_MAT_FLAG = 'Material Flags (0x00)'
NAME_GXMDLVIEW_TEX_TPL_IDX = 'TPL / Texture Index (0x04)'
NAME_GXMDLVIEW_TEX_UNK06 = 'Unknown (0x06)'
NAME_GXMDLVIEW_TEX_ANISO = 'Anisotropy Level (0x07)'
NAME_GXMDLVIEW_TEX_UNK0C = 'Unknown (0x0C)'
NAME_GXMDLVIEW_TEX_UNK10 = 'Unknown (0x10)'

MSG_LABEL_EDIT = '{0}:'


def draw_checkbox_row(box: bpy.types.UILayout, data: bpy.types.AnyType, show_propertys: list[bool], show_property_keys: list[str], label_texts: list[str], data_masks: list[bool], property :str, label_text: str):
    """Convert a list of boolean flags to a column of checkboxes with labels."""
    idx = show_property_keys.index(property)
    show_property = show_propertys[idx]
    box.prop(data, 'show_propertys', index=idx, text=label_text, icon='TRIA_DOWN' if show_property else 'TRIA_RIGHT', emboss=False)
    if show_property:
        _checkbox = box.box()
        for i, _label_text in enumerate(label_texts):
            if not data_masks[i]:
                continue
            row = _checkbox.row()
            row.prop(data, property, index=i, text=_label_text)

def draw_checkbox_column(box: bpy.types.UILayout, data: bpy.types.AnyType, show_propertys: list[bool], show_property_keys: list[str], flags: list[bool], property :str, label_text: str):
    idx = show_property_keys.index(property)
    show_property = show_propertys[idx]
    box.prop(data, 'show_propertys', index=idx, text=label_text, icon='TRIA_DOWN' if show_property else 'TRIA_RIGHT', emboss=False)
    if show_property:
        _checkbox = box.box()
        length= len(flags)
        col = _checkbox.column_flow(columns=length)
        for i in range(length):
            col.prop(data, property, index=i, text='')

# ---------------------------------------------------------------------------
# 内部 NodeGroup の生成・取得
# ---------------------------------------------------------------------------

def _ensure_nodegroup() -> bpy.types.NodeGroup:
    """
    GCMFTextureNode が内部で使う ShaderNodeTree を生成/再利用する。
    ノード構成:
        [NodeGroupInput(なし)] → ShaderNodeTexImage → [NodeGroupOutput]
                                                           Color (NodeSocketColor)
                                                           Alpha (NodeSocketFloat)
    """
    if _NODEGROUP_NAME in bpy.data.node_groups:
        return bpy.data.node_groups[_NODEGROUP_NAME]

    group = bpy.data.node_groups.new(_NODEGROUP_NAME, 'ShaderNodeTree')

    # 出力ソケット定義 (Blender 4.x API)
    group.interface.new_socket('Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    group.interface.new_socket('Alpha', in_out='OUTPUT', socket_type='NodeSocketFloat')

    nodes = group.nodes
    links = group.links

    tex = nodes.new('ShaderNodeTexImage')
    tex.name = 'Image'
    tex.location = (-200, 0)

    out = nodes.new('NodeGroupOutput')
    out.location = (200, 0)

    links.new(tex.outputs['Color'], out.inputs['Color'])
    links.new(tex.outputs['Alpha'], out.inputs['Alpha'])

    return group


# ---------------------------------------------------------------------------
# カスタムノードクラス
# ---------------------------------------------------------------------------

class GCMFTextureNode(bpy.types.ShaderNodeCustomGroup):
    """
    GCMF Texture ノード。
    2.79版の bpy.data.textures 要素に相当するデータをノード自身に保持する。
    """

    bl_name  = 'GCMFTextureNode'
    bl_label = 'GCMF Texture'
    bl_icon  = 'TEXTURE'
    bl_description = "GCMF Texture – holds image and GCMF metadata (uv_wrap, mipmap, etc.)"

    # ---- Image ----
    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        description="Texture image",
    )

    # ---- GCMF Texture Properties ----
    unk0x00: bpy.props.BoolVectorProperty(
        name="unk0x00", default=(False,) * 16, size=16,
    )
    _mipmap_default = [False] * 8
    _mipmap_default[5] = _mipmap_default[6] = _mipmap_default[7] = True
    mipmap: bpy.props.BoolVectorProperty(
        name="Mipmap", default=tuple(_mipmap_default), size=8,
    )
    _uv_wrap_default = [False] * 8
    _uv_wrap_default[0] = _uv_wrap_default[1] = True   # unknown7, unknown6
    _uv_wrap_default[3] = _uv_wrap_default[5] = True   # Y-Repeat, X-Repeat
    uv_wrap: bpy.props.BoolVectorProperty(
        name="UV Wrap", default=tuple(_uv_wrap_default), size=8,
    )
    texture_index: bpy.props.IntProperty(
        name="TPL / Texture Index",
        description="TPL texture index (gcmf_texture.texture_index)",
        default=0, min=0, max=0x7FFF,
    )
    unk0x06: bpy.props.IntProperty(
        name="unk0x06", default=0, min=0, max=0xFF,
    )
    anisotropy: bpy.props.BoolVectorProperty(
        name="Anisotropy", default=(False,) * 8, size=8,
    )
    unk0x0C: bpy.props.BoolVectorProperty(
        name="unk0x0C", default=(False,) * 8, size=8,
    )
    is_swappable: bpy.props.BoolVectorProperty(
        name="Is Swappable", default=(False,) * 8, size=8,
    )
    _unk0x10_default = [False] * 32
    _unk0x10_default[26] = _unk0x10_default[27] = True
    unk0x10: bpy.props.BoolVectorProperty(
        name="unk0x10", default=tuple(_unk0x10_default), size=32,
    )

    order_index: bpy.props.IntProperty(
        name="Order Index",
        description="GCMF texture order index",
        default=-1, min=-0x7FFF, max=0x7FFF,
    )

    # UI
    show_propertys: bpy.props.BoolVectorProperty(
        name="Edit Boxs", default=(False, ) * 7, size=7,
    )
    # sub box
    show_gcmf_textures: bpy.props.BoolProperty(name="Textures", default=False)
    show_gcmf_textures_edit: bpy.props.BoolProperty(name="Textures Edit", default=False)


    # ------------------------------------------------------------------
    # ライフサイクル
    # ------------------------------------------------------------------

    def init(self, context):
        """ノード新規作成時に内部 NodeGroup をアタッチする。"""
        self.node_tree = _ensure_nodegroup()

    def copy(self, node):
        """ノード複製時も同じ NodeGroup を参照する（共有）。"""
        self.node_tree = _ensure_nodegroup()

    def free(self):
        """
        ノード削除時。NodeGroup は共有リソースなので削除しない。
        Blender がゼロ参照になれば自動削除する。
        """
        pass

    # ------------------------------------------------------------------
    # 内部 ShaderNodeTexImage への image 同期
    # ------------------------------------------------------------------

    def _sync_image(self):
        """self.image を内部 NodeGroup の ShaderNodeTexImage に反映する。"""
        if self.node_tree is None:
            return
        tex_node = self.node_tree.nodes.get('Image')
        if tex_node:
            tex_node.image = self.image

    # ------------------------------------------------------------------
    # ノード上の UI
    # ------------------------------------------------------------------

    def draw_buttons(self, context, layout):
        # 画像選択
        layout.template_ID(self, "image", open="image.open")

        # texture_index
        layout.prop(self, "texture_index")

    def draw_buttons_ext(self, context, layout):
        """サイドバー（N パネル）に詳細を表示。"""
        self.draw_buttons(context, layout)
        layout.prop(self, "order_index")

        layout.separator()
        layout.label(text="Advanced:")

        show_property_keys = [
            'unk0x00', 'mipmap', 'uv_wrap','anisotropy',
            'unk0x0C', 'is_swappable', 'unk0x10'
        ]

        box = layout.box()
        # unk0x00
        unk0x00_labels = ['',] * len(self.unk0x00)
        unk0x00_labels[10] = 'Enable carcmntex.tpl Texture (F-ZERO GX)'
        unk0x00_labels[11] = 'Enable normal reflection'
        unk0x00_labels_mask = [False,] * len(self.unk0x00)
        unk0x00_labels_mask[10] = True
        unk0x00_labels_mask[11] = True
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys, label_texts=unk0x00_labels, data_masks=unk0x00_labels_mask, property='unk0x00', label_text='unk0x00')
        # mipmap
        mip_map_labels = [
            'unknown7', 'unknown6', 'unknown5', 'unknown4',
            'near', 'unknown2', 'unknown1', 'enable'
        ]
        mip_map_mask = [True,] * len(self.mipmap)
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys, label_texts=mip_map_labels, data_masks=mip_map_mask, property='mipmap', label_text='MIPMAP')
        # uv_wrap
        uv_wrap_labels = [
            'unknown7', 'unknown6', 'Y-Mirror', 'Y-Repeat',
            'X-Mirror', 'X-Repeat', 'unknown1', 'unknown0'
        ]
        uv_wrap_mask = [True,] * len(self.uv_wrap)
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys, label_texts=uv_wrap_labels, data_masks=uv_wrap_mask, property='uv_wrap', label_text='UV WRAP')
        # texture_index
        box.label(text=NAME_GXMDLVIEW_TEX_TPL_IDX)
        box.prop(self, "texture_index", text="value")
        # unk0x06
        box.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_TEX_UNK06))
        box.prop(self, "unk0x06", text="value")
        # Anisotropy
        anisotropy_labels = [
            'unknown7','unknown6', 'unknown5', 'unknown4',
            'unknown3', 'aniso4', 'aniso2', 'aniso1'
        ]
        anisotropy_mask = [True,] * len(self.anisotropy)
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys, label_texts=anisotropy_labels, data_masks=anisotropy_mask, property='anisotropy', label_text='Anisotropy')
        # unk0x0C
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys, flags=self.unk0x0C, property='unk0x0C', label_text=NAME_GXMDLVIEW_TEX_UNK0C)
        # is Swappable
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys, flags=self.is_swappable, property='is_swappable', label_text='is Swappable (0x0D)')
        # unk0x10
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys, flags=self.unk0x10, property='unk0x10', label_text=NAME_GXMDLVIEW_TEX_UNK10)

# ---------------------------------------------------------------------------
# ヘルパー: マテリアルから GCMFTextureNode を順番通りに収集
# ---------------------------------------------------------------------------

def collect_gcmf_texture_nodes(mat: bpy.types.Material) -> list:
    """
    ノードツリーから GCMFTextureNode を最大3つ収集して返す。
    order_index が設定されていればそれでソート、未設定は接続順。

    Returns:
        list[GCMFTextureNode]  (最大3要素)
    """
    if not mat.use_nodes or mat.node_tree is None:
        return []

    nodes = [n for n in mat.node_tree.nodes if n.bl_idname == 'GCMFTextureNode']

    # order_index が -1（未設定）のノードはリスト末尾に置く
    # nodes.sort(key=lambda n: n.order_index if n.order_index >= 0 else 0x7FFF)
    nodes.sort(key=lambda n: n.order_index)

    return nodes[:3]


# ---------------------------------------------------------------------------
# ヘルパー: texture_index を image.name から逆算
# ---------------------------------------------------------------------------

def resolve_texture_index_from_image(node: GCMFTextureNode) -> int:
    """
    node.image.name 末尾の数字から texture_index を逆算する。
    例: "tpl_005" → 5、"tpl_common_012" → 12
    取得できない場合は node.texture_index の保存値を返す。
    """
    if node.image is None:
        return node.texture_index
    m = re.search(r'(\d+)$', node.image.name)
    return int(m.group(1)) if m else node.texture_index


# ---------------------------------------------------------------------------
# ノードエディタの Add メニューへの登録
# ---------------------------------------------------------------------------

def _add_node_menu(self, context):
    """NODE_MT_add に 'GCMF Texture' エントリを追加する。"""
    if context.space_data.tree_type == 'ShaderNodeTree':
        self.layout.separator()
        self.layout.operator(
            "node.add_node",
            text="GCMF Texture",
            icon='TEXTURE',
        ).type = 'GCMFTextureNode'
