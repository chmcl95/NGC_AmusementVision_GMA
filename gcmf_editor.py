import bpy
from .gcmf_node import GCMFTextureNode, collect_gcmf_texture_nodes
from .ui import draw_checkbox_row, draw_checkbox_column

NAME_ID_PROPERTY_VIEWER_BASE = 'OBJECT_PT_GCMF_{0}_Viewer'
NAME_ID_PROPERTY_EDITOR_BASE = 'OBJECT_PT_GCMF_{0}_Editor'
NAME_LABEL_PROPERTY_BASE = 'GCMF {0}'

# Names called on GxModelViewer
NAME_OBJ_INDEX = 'Index of Object'
NAME_GXMDLVIEW_OBJ_ATTRIBUTE = 'Section Flags (0x00)'

NAME_GXMDLVIEW_MAT_RENDER_FLAG = 'Render Flags (0x00)'
NAME_GXMDLVIEW_MAT_COLOR0 = 'Vertex Shading A (0x04)'
NAME_GXMDLVIEW_MAT_COLOR1 = 'Vertex Shading B (0x08)'
NAME_GXMDLVIEW_MAT_COLOR2 = 'Specular Tint (0x0C)'
NAME_GXMDLVIEW_MAT_TRANSPARENCY = 'Transparency (0x10)'
NAME_GXMDLVIEW_MAT_UNK14 = 'Unknown (0x14)'
NAME_GXMDLVIEW_MAT_TEXTURE_INDEXS = [
    'Primary Material Index (Dec) (0x16)',
    'Secondary Material Index (Dec) (0x18)',
    'Tertiary Material Index (Dec) (0x1A)'
]
NAME_GXMDLVIEW_OBJ_BOUND_SPHERE = 'Bounding Spher Center (X, Y, Z)'
NAME_GXMDLVIEW_OBJ_UNK3C = 'Unknown (0x3C)'
NAME_GXMDLVIEW_OBJ_UNK40 = 'Unknown (0x40)'
NAME_GXMDLVIEW_TEX_MAT_FLAG = 'Material Flags (0x00)'
NAME_GXMDLVIEW_TEX_TPL_IDX = 'TPL / Texture Index (0x04)'
NAME_GXMDLVIEW_TEX_UNK06 = 'Unknown (0x06)'
NAME_GXMDLVIEW_TEX_ANISO = 'Anisotropy Level (0x07)'
NAME_GXMDLVIEW_TEX_UNK0C = 'Unknown (0x0C)'
NAME_GXMDLVIEW_TEX_UNK10 = 'Unknown (0x10)'

MSG_NOT_FOUND_MATERIAL = 'Press \"New\" Button'
MSG_NOT_FOUND_TEXTURE = 'Add \"GCMF Texture\" on Material Node Tree'
MSG_HEX_NOALIGN = '{0}: {1:0X}'
MSG_HEX_2 = '{0}: {1:02X}'
MSG_HEX_4 = '{0}: {1:04X}'
MSG_HEX_8 = '{0}: {1:08X}'
MSG_LABEL_SHOW = '{0}: {1}'
MSG_LABEL_EDIT = '{0}:'


# GCMF Object Setting Show Panel
class OBJECT_PT_GCMF_Object_Viewer(bpy.types.Panel):
    bl_idname = NAME_ID_PROPERTY_VIEWER_BASE.format('Object')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Object Viewer')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        try:
            gcmf_object = bpy.context.active_object.gcmf_object

            # val = 0x00
            # # attribute
            # self.layout.label('attribute supports 0x00 and 0x01. not supports 0x02, 0x04, 0x08 and 0x10.')
            # val = 0x00
            # for i, attribute in enumerate(gcmf_object.attribute):
            #     val += (attribute.real << (4-i))
            # self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_OBJ_ATTRIBUTE, val))

        # If faild to get "gcmf_object" from active Object
        except:
            pass # do nothing


# GCMF Object Setting Edit Panel
class OBJECT_PT_GCMF_Object_Editor(bpy.types.Panel):
    bl_parent_id = NAME_ID_PROPERTY_VIEWER_BASE.format('Object')
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Object')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Object Editor')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        try:
            gcmf_object = bpy.context.active_object.gcmf_object

            # index
            self.layout.prop(gcmf_object, "index", text="object index")
            # attribute
            self.layout.prop(gcmf_object, "attribute", text="attribute")

            self.layout.prop(gcmf_object, "transparent_count", text="Transparent Material Count")

        # If faild to get "gcmf_object" from active Object
        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")


# GCMF Material Setting Show Panel
class OBJECT_PT_GCMF_Material_Viewer(bpy.types.Panel):
    bl_idname = NAME_ID_PROPERTY_VIEWER_BASE.format('Material')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Material Viewer')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def calc_color(self, color):
        val = (color[0].real << 24)\
            + (color[1].real << 16)\
            + (color[2].real << 8)\
            + color[3].real
        return val

    def draw(self, context):
        if not hasattr(bpy.context.active_object.active_material, 'gcmf_material'):
            self.layout.label(text=MSG_NOT_FOUND_MATERIAL)
            return
        try:
            gcmf_material = bpy.context.active_object.active_material.gcmf_material
            show_property_keys = [
                'vtx_descriptor', 'unk0x02', 'unk0x03','unk0x40'
            ]
            # unk0x02, unk0x03
            val = 0x00
            for i, _unk0x02 in enumerate(gcmf_material.unk0x02):
                val += (int(_unk0x02) << (7 - i))
            val = val << 8
            for i, _unk0x03 in enumerate(gcmf_material.unk0x03):
                val += (int(_unk0x03) << (7 - i))
            self.layout.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_RENDER_FLAG, val))
            # color0
            self.layout.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_COLOR0,
                                                     self.calc_color(gcmf_material.color0)))
            # color1
            self.layout.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_COLOR1,
                                                     self.calc_color(gcmf_material.color1)))
            # color2
            self.layout.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_COLOR2,
                                                     self.calc_color(gcmf_material.color2)))
            # emission, transparency
            val = (gcmf_material.emission << 8) + gcmf_material.transparency
            self.layout.label(text=MSG_HEX_4.format(NAME_GXMDLVIEW_MAT_TRANSPARENCY, val))
            # unk0x14, unk0x15
            val = (gcmf_material.unk0x14 << 8) + gcmf_material.unk0x15
            self.layout.label(text=MSG_HEX_4.format(NAME_GXMDLVIEW_MAT_UNK14, val))

            # Vertex Descriptor (Actual this is Edit. But it relates Exporting attribute control. This is reason why placed viewer box.)
            vtx_descriptor_label = [
                'unused0 (NOT support)', 'unused1 (NOT support)', 'unused2 (NOT support)', 'unused3 (NOT support)',
                'unused4 (NOT support)', 'unused5 (NOT support)', 'NBT(NOT support)', 'light (NOT support)',
                'tex_mtx_array (NOT support)', 'nrm_mtx_array (NOT support)', 'pos_mtx_array (NOT support)', 'tex7 (NOT work on GxModelViewer)',
                'tex6 (NOT work on GxModelViewer)', 'tex5 (NOT work on GxModelViewer)', 'tex4 (NOT work on GxModelViewer)', 'tex3 (NOT work on GxModelViewer)',
                'UV2', 'UV1', 'UV0', 'Vertex Color 1',
                'Vertex Color 0', 'Normal', 'Position', 'tex7mtxidx (NOT support)',
                'tex6mtxidx (NOT support)', 'tex5mtxidx (NOT support)', 'tex4mtxidx (NOT support)', 'tex3mtxidx (NOT support)',
                'tex2mtxidx (NOT support)', 'tex1mtxidx (NOT support)', 'tex0mtxidx (NOT support)', 'pnmtxidx (NOT support)'
            ]
            vtx_descriptor_mask = [False,] * len(gcmf_material.vtx_descriptor)
            vtx_descriptor_mask[16] = True
            vtx_descriptor_mask[17] = True
            vtx_descriptor_mask[18] = True
            vtx_descriptor_mask[19] = True
            vtx_descriptor_mask[20] = True
#            vtx_descriptor_mask[21] = True
#            vtx_descriptor_mask[22] = True
            draw_checkbox_row(self.layout, gcmf_material, gcmf_material.show_propertys, show_property_keys, label_texts=vtx_descriptor_label, data_masks=vtx_descriptor_mask, property='vtx_descriptor', label_text='Export Attribute')

            # These are not "Material"
            # unk0x3C
            self.layout.label(text=MSG_LABEL_SHOW.format(NAME_GXMDLVIEW_OBJ_UNK3C,
                                                          gcmf_material.unk0x3C))
            # unk0x40
            val = 0x00
            for i, _unk0x40 in enumerate(gcmf_material.unk0x40):
                val += (int(_unk0x40) << (31 - i))
            self.layout.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_OBJ_UNK40, val))
            
        # If faild to get "gcmf_material" from active Material
        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")


# GCMF Material Setting Edit Panel
class OBJECT_PT_GCMF_Material_Editor(bpy.types.Panel):
    bl_parent_id = NAME_ID_PROPERTY_VIEWER_BASE.format('Material')
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Material')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Material Editor')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        if not hasattr(bpy.context.active_object.active_material, 'gcmf_material'):
            self.layout.label(text=MSG_NOT_FOUND_MATERIAL)
            return
        try:
            gcmf_material = bpy.context.active_object.active_material.gcmf_material
            show_property_keys = [
                'vtx_descriptor', 'unk0x02', 'unk0x03','unk0x40'
            ]
            draw_checkbox_column(self.layout, gcmf_material, gcmf_material.show_propertys, show_property_keys, flags=gcmf_material.unk0x02, property='unk0x02', label_text='unk0x02')
            draw_checkbox_column(self.layout, gcmf_material, gcmf_material.show_propertys, show_property_keys, flags=gcmf_material.unk0x03, property='unk0x03', label_text='unk0x03')
            self.layout.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_COLOR0))
            self.layout.prop(gcmf_material, "color0", text="values")
            self.layout.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_COLOR1))
            self.layout.prop(gcmf_material, "color1", text="values")
            self.layout.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_COLOR2))
            self.layout.prop(gcmf_material, "color2", text="values")
            self.layout.prop(gcmf_material, "emission", text="emission")
            self.layout.prop(gcmf_material, "transparency", text="transparency")
            self.layout.prop(gcmf_material, "unk0x14", text="unk0x14")
            self.layout.prop(gcmf_material, "unk0x15", text="unk0x15")
            self.layout.label(text=MSG_LABEL_EDIT.format('Texture Indexes'))
            self.layout.prop(gcmf_material, "texture_indexes", text="values")

            #These are not actual "gcmf Material"
            self.layout.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_OBJ_BOUND_SPHERE))
            self.layout.prop(gcmf_material, "boundingsphere_origin", text="values")
            self.layout.prop(gcmf_material, "unk0x3C", text="unk0x3C")
            draw_checkbox_column(self.layout, gcmf_material, gcmf_material.show_propertys, show_property_keys, flags=gcmf_material.unk0x40, property='unk0x40', label_text='unk0x40')
        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")


# GCMF Texture Setting Show Panel
# These panels now show texture settings from the active material's gcmf_textures collection.

class OBJECT_PT_GCMF_Texture_Viewer(bpy.types.Panel):
    bl_idname = NAME_ID_PROPERTY_VIEWER_BASE.format('Texture')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Texture Viewer')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        mat = bpy.context.active_object.active_material
        if not hasattr(mat, 'use_nodes'):
            self.layout.label(text=MSG_NOT_FOUND_MATERIAL)
            return
        try:
            gcmf_nodes = collect_gcmf_texture_nodes(mat)

            if len(gcmf_nodes) == 0:
                self.layout.label(text=MSG_NOT_FOUND_TEXTURE)
                return

            for idx, gcmf_node in enumerate(gcmf_nodes):
                header = self.layout.row()
                is_open = gcmf_node.show_gcmf_textures
                header.prop(gcmf_node, "show_gcmf_textures", index=0,
                            icon='TRIA_DOWN' if is_open else 'TRIA_RIGHT',
                            emboss=False,
                            text=f"GCMF Texture [{idx}]  node: {gcmf_node.name}")
                if is_open:
                    box = self.layout.box()
                    # image
                    box.label(text=f"Image: {gcmf_node.image.name if gcmf_node.image else '(none)'}")
                    # unk0x00 / mipmap / uv_wrap
                    val = 0x00
                    for i, b in enumerate(gcmf_node.unk0x00):
                        val += (int(b) << (15 - i))
                    val = val << 8
                    for i, b in enumerate(gcmf_node.mipmap):
                        val += (int(b) << (7 - i))
                    val = val << 8
                    for i, b in enumerate(gcmf_node.uv_wrap):
                        val += (int(b) << (7 - i))
                    box.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_TEX_MAT_FLAG, val))
                    box.label(text=MSG_HEX_NOALIGN.format(NAME_GXMDLVIEW_TEX_TPL_IDX,
                                                          gcmf_node.texture_index))
                    box.label(text=MSG_HEX_2.format(NAME_GXMDLVIEW_TEX_UNK06, gcmf_node.unk0x06))
                    val = sum(int(b) << (7 - i) for i, b in enumerate(gcmf_node.anisotropy))
                    box.label(text=MSG_HEX_2.format(NAME_GXMDLVIEW_TEX_ANISO, val))
                    val = sum(int(b) << (7 - i) for i, b in enumerate(gcmf_node.unk0x0C))
                    val = (val << 8) + sum(int(b) << (7 - i) for i, b in enumerate(gcmf_node.is_swappable))
                    box.label(text=MSG_HEX_4.format(NAME_GXMDLVIEW_TEX_UNK0C, val))
                    val = sum(int(b) << (31 - i) for i, b in enumerate(gcmf_node.unk0x10))
                    box.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_TEX_UNK10, val))

        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")