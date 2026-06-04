"""
gcmf_shader_node.py  -  GCMFTextureNode (ShaderNodeCustomGroup)

Provides a custom Blender shader node that stores GCMF texture metadata
(uv_wrap, mipmap, anisotropy, etc.) alongside the image reference.
This replaces the legacy bpy.types.Texture approach used in Blender 2.79.

Note: bone/armature-related nodes are intentionally kept in a separate module
to avoid naming confusion with this shader-specific node.
"""

import bpy
from .ui import draw_checkbox_row, draw_checkbox_column

NAME_GXMDLVIEW_TEX_TPL_IDX = 'TPL / Texture Index (0x04)'
NAME_GXMDLVIEW_TEX_UNK06   = 'Unknown (0x06)'
NAME_GXMDLVIEW_TEX_ANISO   = 'Anisotropy Level (0x07)'
NAME_GXMDLVIEW_TEX_UNK0C   = 'Unknown (0x0C)'
NAME_GXMDLVIEW_TEX_UNK10   = 'Unknown (0x10)'

MSG_LABEL_EDIT = '{0}:'


# ---------------------------------------------------------------------------
# Internal NodeGroup creation (one per instance)
# ---------------------------------------------------------------------------

def _create_nodegroup() -> bpy.types.NodeGroup:
    """
    Create a new ShaderNodeTree for a single GCMFTextureNode instance.

    Each instance owns its own NodeGroup so that the internal
    ShaderNodeTexImage is not shared between nodes. Sharing a NodeGroup
    would force all instances to reference the same image, making it
    impossible to assign different textures to different nodes.
    """
    group = bpy.data.node_groups.new(".GCMFTextureNodeGroup", 'ShaderNodeTree')

    group.interface.new_socket('Color', in_out='OUTPUT', socket_type='NodeSocketColor')
    group.interface.new_socket('Alpha', in_out='OUTPUT', socket_type='NodeSocketFloat')

    nodes = group.nodes
    links = group.links

    tex          = nodes.new('ShaderNodeTexImage')
    tex.name     = 'Image'
    tex.location = (-200, 0)

    out          = nodes.new('NodeGroupOutput')
    out.location = (200, 0)

    links.new(tex.outputs['Color'], out.inputs['Color'])
    links.new(tex.outputs['Alpha'], out.inputs['Alpha'])

    return group


# ---------------------------------------------------------------------------
# Update callback: sync self.image into the internal ShaderNodeTexImage
# ---------------------------------------------------------------------------

def _on_image_update(self: 'GCMFTextureNode', context: bpy.types.Context) -> None:
    """Called whenever self.image is changed; forwards the value to the internal node."""
    self._sync_image()


# ---------------------------------------------------------------------------
# Custom shader node
# ---------------------------------------------------------------------------

class GCMFTextureNode(bpy.types.ShaderNodeCustomGroup):
    """
    Custom shader node that holds a texture image and its GCMF metadata.

    Each instance has a dedicated NodeGroup containing a ShaderNodeTexImage
    so that every node can reference a different image independently.
    """

    bl_name        = 'GCMFTextureNode'
    bl_label       = 'GCMF Texture'
    bl_icon        = 'TEXTURE'
    bl_description = "GCMF Texture - holds image and GCMF metadata (uv_wrap, mipmap, etc.)"

    # ---- Image ----
    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        description="Texture image",
        update=_on_image_update,
    )

    # ---- GCMF Texture Properties ----
    unk0x00: bpy.props.BoolVectorProperty(
        name="unk0x00", default=(False,) * 16, size=16)

    _mipmap_default = [False] * 8
    _mipmap_default[5] = _mipmap_default[6] = _mipmap_default[7] = True
    mipmap: bpy.props.BoolVectorProperty(
        name="Mipmap", default=tuple(_mipmap_default), size=8)

    _uv_wrap_default = [False] * 8
    _uv_wrap_default[0] = _uv_wrap_default[1] = True   # unknown7, unknown6
    _uv_wrap_default[3] = _uv_wrap_default[5] = True   # Y-Repeat, X-Repeat
    uv_wrap: bpy.props.BoolVectorProperty(
        name="UV Wrap", default=tuple(_uv_wrap_default), size=8)

    texture_index: bpy.props.IntProperty(
        name="TPL / Texture Index",
        description="TPL texture index (gcmf_texture.texture_index)",
        default=0, min=0, max=0x7FFF,
    )
    unk0x06: bpy.props.IntProperty(
        name="unk0x06", default=0, min=0, max=0xFF)
    anisotropy: bpy.props.BoolVectorProperty(
        name="Anisotropy", default=(False,) * 8, size=8)
    unk0x0C: bpy.props.BoolVectorProperty(
        name="unk0x0C", default=(False,) * 8, size=8)
    is_swappable: bpy.props.BoolVectorProperty(
        name="Is Swappable", default=(False,) * 8, size=8)

    _unk0x10_default = [False] * 32
    _unk0x10_default[26] = _unk0x10_default[27] = True
    unk0x10: bpy.props.BoolVectorProperty(
        name="unk0x10", default=tuple(_unk0x10_default), size=32)

    order_index: bpy.props.IntProperty(
        name="Order Index",
        description="GCMF texture order index used for sorting during export",
        default=100, min=-0x7FFF, max=0x7FFF,
    )

    # UI state
    show_propertys: bpy.props.BoolVectorProperty(
        name="Edit Boxes", default=(False,) * 7, size=7)
    show_gcmf_textures: bpy.props.BoolProperty(
        name="Textures", default=False)
    show_gcmf_textures_edit: bpy.props.BoolProperty(
        name="Textures Edit", default=False)

    # ------------------------------------------------------------------
    # Blender node lifecycle
    # ------------------------------------------------------------------

    def init(self, context: bpy.types.Context) -> None:
        """Create a fresh NodeGroup for this instance on node creation."""
        self.node_tree = _create_nodegroup()

    def copy(self, node: 'GCMFTextureNode') -> None:
        """Create a new NodeGroup on duplication to keep images independent."""
        self.node_tree = _create_nodegroup()
        if node.image:
            self.image = node.image
            self._sync_image()

    def free(self) -> None:
        """Remove the instance-owned NodeGroup when this node is deleted."""
        if self.node_tree:
            bpy.data.node_groups.remove(self.node_tree, do_unlink=True)

    # ------------------------------------------------------------------
    # Image sync
    # ------------------------------------------------------------------

    def _sync_image(self) -> None:
        """Forward self.image to the internal ShaderNodeTexImage."""
        if self.node_tree is None:
            return
        tex_node = self.node_tree.nodes.get('Image')
        if tex_node:
            tex_node.image = self.image

    # ------------------------------------------------------------------
    # Node UI
    # ------------------------------------------------------------------

    def draw_buttons(self, context: bpy.types.Context,
                     layout: bpy.types.UILayout) -> None:
        layout.template_ID(self, "image", open="image.open")
        layout.prop(self, "texture_index")

    def draw_buttons_ext(self, context: bpy.types.Context,
                         layout: bpy.types.UILayout) -> None:
        """Extended panel shown when the N-key sidebar is open."""
        self.draw_buttons(context, layout)
        layout.prop(self, "order_index")
        layout.separator()
        layout.label(text="Advanced:")

        show_property_keys = [
            'unk0x00', 'mipmap', 'uv_wrap', 'anisotropy',
            'unk0x0C', 'is_swappable', 'unk0x10',
        ]
        box = layout.box()

        unk0x00_labels      = [''] * len(self.unk0x00)
        unk0x00_labels[10]  = 'Enable carcmntex.tpl Texture (F-ZERO GX)'
        unk0x00_labels[11]  = 'Enable normal reflection'
        unk0x00_labels_mask = [False] * len(self.unk0x00)
        unk0x00_labels_mask[10] = True
        unk0x00_labels_mask[11] = True
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys,
                          label_texts=unk0x00_labels, data_masks=unk0x00_labels_mask,
                          property='unk0x00', label_text='unk0x00')

        mip_map_labels = [
            'unknown7', 'unknown6', 'unknown5', 'unknown4',
            'near', 'unknown2', 'unknown1', 'enable',
        ]
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys,
                          label_texts=mip_map_labels,
                          data_masks=[True] * len(self.mipmap),
                          property='mipmap', label_text='MIPMAP')

        uv_wrap_labels = [
            'unknown7', 'unknown6', 'Y-Mirror', 'Y-Repeat',
            'X-Mirror', 'X-Repeat', 'unknown1', 'unknown0',
        ]
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys,
                          label_texts=uv_wrap_labels,
                          data_masks=[True] * len(self.uv_wrap),
                          property='uv_wrap', label_text='UV WRAP')

        box.label(text=NAME_GXMDLVIEW_TEX_TPL_IDX)
        box.prop(self, "texture_index", text="value")

        box.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_TEX_UNK06))
        box.prop(self, "unk0x06", text="value")

        anisotropy_labels = [
            'unknown7', 'unknown6', 'unknown5', 'unknown4',
            'unknown3', 'aniso4', 'aniso2', 'aniso1',
        ]
        draw_checkbox_row(box, self, self.show_propertys, show_property_keys,
                          label_texts=anisotropy_labels,
                          data_masks=[True] * len(self.anisotropy),
                          property='anisotropy', label_text=NAME_GXMDLVIEW_TEX_ANISO)

        draw_checkbox_column(box, self, self.show_propertys, show_property_keys,
                             flags=self.unk0x0C, property='unk0x0C',
                             label_text=NAME_GXMDLVIEW_TEX_UNK0C)
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys,
                             flags=self.is_swappable, property='is_swappable',
                             label_text='is Swappable (0x0D)')
        draw_checkbox_column(box, self, self.show_propertys, show_property_keys,
                             flags=self.unk0x10, property='unk0x10',
                             label_text=NAME_GXMDLVIEW_TEX_UNK10)


# ---------------------------------------------------------------------------
# Helper: collect GCMFTextureNode instances from a material's node tree
# ---------------------------------------------------------------------------

def collect_gcmf_texture_nodes(mat: bpy.types.Material) -> list:
    """
    Return up to three GCMFTextureNode instances from *mat*, sorted by order_index.
    Returns an empty list if the material has no node tree.
    """
    if not mat.use_nodes or mat.node_tree is None:
        return []
    nodes = [n for n in mat.node_tree.nodes if n.bl_idname == 'GCMFTextureNode']
    nodes.sort(key=lambda n: n.order_index)
    return nodes[:3]


# ---------------------------------------------------------------------------
# Add-menu entry for the Node Editor
# ---------------------------------------------------------------------------

def _add_node_menu(self: bpy.types.Menu, context: bpy.types.Context) -> None:
    """Append a 'GCMF Texture' entry to the shader node Add menu."""
    if context.space_data.tree_type == 'ShaderNodeTree':
        self.layout.separator()
        self.layout.operator(
            "node.add_node",
            text="GCMF Texture",
            icon='TEXTURE',
        ).type = 'GCMFTextureNode'
