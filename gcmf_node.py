"""
gcmf_node.py  –  GCMFTextureNode (ShaderNodeCustomGroup)
"""

import bpy
import re
from .ui import draw_checkbox_row, draw_checkbox_column

NAME_GXMDLVIEW_TEX_TPL_IDX = 'TPL / Texture Index (0x04)'
NAME_GXMDLVIEW_TEX_UNK06 = 'Unknown (0x06)'
NAME_GXMDLVIEW_TEX_ANISO = 'Anisotropy Level (0x07)'
NAME_GXMDLVIEW_TEX_UNK0C = 'Unknown (0x0C)'
NAME_GXMDLVIEW_TEX_UNK10 = 'Unknown (0x10)'

MSG_LABEL_EDIT = '{0}:'


# ---------------------------------------------------------------------------
# 内部 NodeGroup の生成（インスタンスごとに個別生成）
# ---------------------------------------------------------------------------

def _create_nodegroup() -> bpy.types.NodeGroup:
    """
    GCMFTextureNode インスタンスごとの専用 ShaderNodeTree を新規作成する。

    【共有グループを使わない理由】
    ShaderNodeCustomGroup の node_tree を複数インスタンスで共有すると、
    内部の ShaderNodeTexImage も共有されるため、どのノードも同じ画像しか
    参照できず、ユーザーが個別に画像を指定してもレンダリングに反映されない。
    インスタンスごとに個別の NodeGroup を持つことで、
    それぞれ独立した ShaderNodeTexImage を保持できる。
    """
    group = bpy.data.node_groups.new(".GCMFTextureNodeGroup", 'ShaderNodeTree')

    # Output Sockets
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
# image 変更時に内部 ShaderNodeTexImage へ自動同期するコールバック
# ---------------------------------------------------------------------------

def _on_image_update(self, context):
    """
    self.image が変更されるたびに呼ばれる update コールバック。
    インスタンス固有の node_tree 内の ShaderNodeTexImage に画像を反映する。
    """
    self._sync_image()


# ---------------------------------------------------------------------------
# Custom Node
# ---------------------------------------------------------------------------

class GCMFTextureNode(bpy.types.ShaderNodeCustomGroup):
    bl_name  = 'GCMFTextureNode'
    bl_label = 'GCMF Texture'
    bl_icon  = 'TEXTURE'
    bl_description = "GCMF Texture – holds image and GCMF metadata (uv_wrap, mipmap, etc.)"

    # ---- Image ----
    # update コールバックで内部 ShaderNodeTexImage に自動同期する
    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        description="Texture image",
        update=_on_image_update,
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
    show_gcmf_textures: bpy.props.BoolProperty(name="Textures", default=False)
    show_gcmf_textures_edit: bpy.props.BoolProperty(name="Textures Edit", default=False)


    def init(self, context):
        """
        ノード新規作成時にインスタンス固有の NodeGroup を生成してアタッチする。
        共有グループを使わないことで、各インスタンスが独立した
        ShaderNodeTexImage を持ち、画像を個別に設定できる。
        """
        self.node_tree = _create_nodegroup()

    def copy(self, node):
        """
        ノード複製時も新しい NodeGroup を生成する。
        複製元と node_tree を共有しないことで画像の独立性を保つ。
        """
        self.node_tree = _create_nodegroup()
        # 複製元の画像を引き継ぐ
        if node.image:
            self.image = node.image
            self._sync_image()

    def free(self):
        """
        ノード削除時にインスタンス固有の NodeGroup も削除する。
        共有リソースではないため、ここで明示的に削除する。
        """
        if self.node_tree:
            bpy.data.node_groups.remove(self.node_tree, do_unlink=True)

    # ------------------------------------------------------------------
    # Sync self.image → 内部 ShaderNodeTexImage
    # ------------------------------------------------------------------
    def _sync_image(self):
        """
        self.image を内部 NodeGroup の ShaderNodeTexImage に反映する。
        init()/copy() 時や update コールバックから呼ばれる。
        """
        if self.node_tree is None:
            return
        tex_node = self.node_tree.nodes.get('Image')
        if tex_node:
            tex_node.image = self.image

    # ------------------------------------------------------------------
    # Node UI
    # ------------------------------------------------------------------
    def draw_buttons(self, context, layout):
        layout.template_ID(self, "image", open="image.open")
        layout.prop(self, "texture_index")

    def draw_buttons_ext(self, context, layout):
        """ side bar appears when press the N-key"""
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
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys, label_texts=anisotropy_labels, data_masks=anisotropy_mask, property='anisotropy', label_text=NAME_GXMDLVIEW_TEX_ANISO)
        # unk0x0C
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys, flags=self.unk0x0C, property='unk0x0C', label_text=NAME_GXMDLVIEW_TEX_UNK0C)
        # is Swappable
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys, flags=self.is_swappable, property='is_swappable', label_text='is Swappable (0x0D)')
        # unk0x10
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys, flags=self.unk0x10, property='unk0x10', label_text=NAME_GXMDLVIEW_TEX_UNK10)


# ---------------------------------------------------------------------------
# Helper: Collect GCMFTextureNode in order from material's node tree
# ---------------------------------------------------------------------------

def collect_gcmf_texture_nodes(mat: bpy.types.Material) -> list[GCMFTextureNode]:
    if not mat.use_nodes or mat.node_tree is None:
        return []
    nodes = [n for n in mat.node_tree.nodes if n.bl_idname == 'GCMFTextureNode']
    nodes.sort(key=lambda n: n.order_index)
    return nodes[:3]


# ---------------------------------------------------------------------------
# Adding to Add Menu on Node Editor
# ---------------------------------------------------------------------------
def _add_node_menu(self, context):
    if context.space_data.tree_type == 'ShaderNodeTree':
        self.layout.separator()
        self.layout.operator(
            "node.add_node",
            text="GCMF Texture",
            icon='TEXTURE',
        ).type = 'GCMFTextureNode'
