import bpy

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
NAME_GXMDLVIEW_TEX_TPL_IDX = 'Texture Index (0x04)'
NAME_GXMDLVIEW_TEX_UNK06 = 'Unknown (0x06)'
NAME_GXMDLVIEW_TEX_ANISO = 'Anisotropy Level (0x07)'
NAME_GXMDLVIEW_TEX_UNK0C = 'Unknown (0x0C)'
NAME_GXMDLVIEW_TEX_UNK10 = 'Unknown (0x10)'

MSG_NOT_FOUND_MATERIAL = 'Press \"New\" Button'
MSG_NOT_FOUND_TEXTURE = 'Press \"New\" Button'
MSG_HEX_NOALIGN = '{0}: {1:0X}'
MSG_HEX_2 = '{0}: {1:02X}'
MSG_HEX_4 = '{0}: {1:04X}'
MSG_HEX_8 = '{0}: {1:08X}'
MSG_LABEL_SHOW = '{0}: {1}'
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
        length=len(flags)
        col = _checkbox.column_flow(columns=length)
        for i in range(length):
            col.prop(data, property, index=i, text='')

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
            # box_attribute = self.layout.box()
            # col_attribute = box_attribute.column_flow(columns=8)
            # texts = ['flags',\
            #         'is_effective', 'is_skin', 'is_stiching', 'is_unk0x01',
            #         'is_16bit']
            # for text in texts:
            #    col_attribute.label(text)
            self.layout.prop(gcmf_object, "transparent_materil_count", text="Transparent Material Count")

        # If faild to get "gcmf_object" from active Object
        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")
#            pass #do nothing

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
        try:
            gcmf_material = bpy.context.active_object.active_material.gcmf_material

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

            for i, texture_idx_label in enumerate(NAME_GXMDLVIEW_MAT_TEXTURE_INDEXS):
                _texture_idx_text = '{}: None'.format(texture_idx_label) if gcmf_material.texture_indexes[i] < 0 else MSG_HEX_NOALIGN.format(texture_idx_label, gcmf_material.texture_indexes[i])
                self.layout.label(text=_texture_idx_text)

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
#            self.layout.label(text=MSG_NOT_FOUND_MATERIAL)

# GCMF Material Setting Edit Panel
class OBJECT_PT_GCMF_Material_Editor(bpy.types.Panel):
    bl_parent_id = NAME_ID_PROPERTY_VIEWER_BASE.format('Material')
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Material')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Material Editor')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        try:
            gcmf_material = bpy.context.active_object.active_material.gcmf_material
            show_property_keys = [
                'unk0x02', 'unk0x03','unk0x40', 'vertex_descriptor'
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
            vtx_descriptor_label = [
                'unused0 (NOT support)', 'unused1 (NOT support)', 'unused2 (NOT support)', 'unused3 (NOT support)',
                'unused4 (NOT support)', 'unused5 (NOT support)', 'NBT(NOT support)', 'light (NOT support)',
                'tex_mtx_array (NOT support)', 'nrm_mtx_array (NOT support)', 'pos_mtx_array (NOT support)', 'tex7 (NOT work on GxModelViewer)',
                'tex6 (NOT work on GxModelViewer)', 'tex5 (NOT work on GxModelViewer)', 'tex4 (NOT work on GxModelViewer)', 'tex3 (NOT work on GxModelViewer)',
                'UV2', 'UV1', 'UV0', 'Vertex Color 1 (NOT work on GxModelViewer)',
                'Vertex Color 0', 'Normal', 'Position', 'tex7mtxidx (NOT support)',
                'tex6mtxidx (NOT support)', 'tex5mtxidx (NOT support)', 'tex4mtxidx (NOT support)', 'tex3mtxidx (NOT support)',
                'tex2mtxidx (NOT support)', 'tex1mtxidx (NOT support)', 'tex0mtxidx (NOT support)', 'pnmtxidx (NOT support)'
            ]
            vtx_descriptor_mask = [False,] * len(gcmf_material.vertex_descriptor)
            vtx_descriptor_mask[16] = True
            vtx_descriptor_mask[17] = True
            vtx_descriptor_mask[18] = True
            vtx_descriptor_mask[19] = True
            vtx_descriptor_mask[20] = True
#            vtx_descriptor_mask[21] = True
#            vtx_descriptor_mask[22] = True
            draw_checkbox_row(self.layout, gcmf_material, gcmf_material.show_propertys, show_property_keys, label_texts=vtx_descriptor_label, data_masks=vtx_descriptor_mask, property='vertex_descriptor', label_text='Vertex Descriptor')
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
# bpy.types.Texture is gone in Blender 4.x.
# These panels now show texture settings from the active material's gcmf_textures collection.

class OBJECT_PT_GCMF_Texture_Viewer(bpy.types.Panel):
    bl_idname = NAME_ID_PROPERTY_VIEWER_BASE.format('Texture')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Texture Viewer')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        try:
            mat = bpy.context.active_object.active_material
            _gcmf_material = mat.gcmf_material
            _gcmf_textures = _gcmf_material.gcmf_textures
            if len(_gcmf_textures) == 0:
                self.layout.label(text=MSG_NOT_FOUND_TEXTURE)
                return

            for idx, gcmf_texture in enumerate(_gcmf_textures):
                self.layout.prop(_gcmf_material, "show_gcmf_textures", index=idx,
                                 icon='TRIA_DOWN' if _gcmf_material.show_gcmf_textures[idx] else 'TRIA_RIGHT',
                                 emboss=False, text="Texture [{}]".format(idx))
                if _gcmf_material.show_gcmf_textures[idx]:
                    box = self.layout.box()
                    box.label(text="GCMF Texture [{}]".format(idx))

                    # unk0x00
                    val = 0x00
                    for i, b in enumerate(gcmf_texture.unk0x00):
                        val += (int(b) << (15 - i))
                    val = val << 8
                    for i, b in enumerate(gcmf_texture.mipmap):
                        val += (int(b) << (7 - i))
                    val = val << 8
                    for i, b in enumerate(gcmf_texture.uv_wrap):
                        val += (int(b) << (7 - i))
                    box.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_TEX_MAT_FLAG, val))
                    # texture_index
                    box.label(text=MSG_HEX_NOALIGN.format(NAME_GXMDLVIEW_TEX_TPL_IDX,
                                                    gcmf_texture.texture_index))
                    # unk0x06
                    box.label(text=MSG_HEX_2.format(NAME_GXMDLVIEW_TEX_UNK06, gcmf_texture.unk0x06))
                    # anisotropy
                    val = 0x00
                    for i, b in enumerate(gcmf_texture.anisotropy):
                        val += (int(b) << (7 - i))
                    box.label(text=MSG_HEX_2.format(NAME_GXMDLVIEW_TEX_ANISO, val))
                    # unk0x0C
                    val = 0x00
                    for i, b in enumerate(gcmf_texture.unk0x0C):
                        val += (int(b) << (7 - i))
                    val = val << 8
                    for i, b in enumerate(gcmf_texture.is_swappable):
                        val += (int(b) << (7 - i))
                    box.label(text=MSG_HEX_4.format(NAME_GXMDLVIEW_TEX_UNK0C, val))
                    # unk0x10
                    val = 0x00
                    for i, b in enumerate(gcmf_texture.unk0x10):
                        val += (int(b) << (31 - i))
                    box.label(text=MSG_HEX_8.format(NAME_GXMDLVIEW_TEX_UNK10, val))

        # If faild to get "gcmf_textures" from active Texture
        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")
#            self.layout.label(text=MSG_NOT_FOUND_TEXTURE)

class OBJECT_PT_GCMF_Texture_Editor(bpy.types.Panel):
    bl_parent_id = NAME_ID_PROPERTY_VIEWER_BASE.format('Texture')
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Texture')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Texture Editor')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        try:
            mat = bpy.context.active_object.active_material
            _gcmf_material = mat.gcmf_material
            _gcmf_textures = _gcmf_material.gcmf_textures

            if len(_gcmf_textures) == 0:
                self.layout.label(text=MSG_NOT_FOUND_TEXTURE)
                return

            show_property_keys = [
                'unk0x00', 'mipmap', 'uv_wrap','anisotropy',
                'unk0x0C', 'is_swappable', 'unk0x10'
            ]
            for idx, gcmf_texture in enumerate(_gcmf_textures):
                self.layout.prop(_gcmf_material, "show_gcmf_textures_edit", index=idx,
                                 icon='TRIA_DOWN' if _gcmf_material.show_gcmf_textures_edit[idx] else 'TRIA_RIGHT',
                                 emboss=False, text="Edit GCMF Texture [{}]".format(idx))
                if _gcmf_material.show_gcmf_textures_edit[idx]:
                    box = self.layout.box()
                    # unk0x00
                    unk0x00_labels = ['',] * len(gcmf_texture.unk0x00)
                    unk0x00_labels[10] = 'Enable carcmntex.tpl Texture (F-ZERO GX)'
                    unk0x00_labels[11] = 'Enable normal reflection'
                    unk0x00_labels_mask = [False,] * len(gcmf_texture.unk0x00)
                    unk0x00_labels_mask[10] = True
                    unk0x00_labels_mask[11] = True
                    draw_checkbox_row(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, label_texts=unk0x00_labels, data_masks=unk0x00_labels_mask, property='unk0x00', label_text='unk0x00')
                    # mipmap
                    mip_map_labels = [
                        'unknown7', 'unknown6', 'unknown5', 'unknown4',
                        'near', 'unknown2', 'unknown1', 'enable'
                    ]
                    mip_map_mask = [True,] * len(gcmf_texture.mipmap)
                    draw_checkbox_row(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, label_texts=mip_map_labels, data_masks=mip_map_mask, property='mipmap', label_text='MIPMAP')
                    # uv_wrap
                    uv_wrap_labels = [
                        'unknown7', 'unknown6', 'Y-Mirror', 'Y-Repeat',
                        'X-Mirror', 'X-Repeat', 'unknown1', 'unknown0'
                    ]
                    uv_wrap_mask = [True,] * len(gcmf_texture.uv_wrap)
                    draw_checkbox_row(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, label_texts=uv_wrap_labels, data_masks=uv_wrap_mask, property='uv_wrap', label_text='UV WRAP')
                    # texture_index
                    box.label(text=NAME_GXMDLVIEW_TEX_TPL_IDX)
                    box.prop(gcmf_texture, "texture_index", text="value")
                    # unk0x06
                    box.label(text=MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_TEX_UNK06))
                    box.prop(gcmf_texture, "unk0x06", text="value")
                    # Anisotropy
                    anisotropy_labels = [
                        'unknown7','unknown6', 'unknown5', 'unknown4',
                        'unknown3', 'aniso4', 'aniso2', 'aniso1'
                    ]
                    anisotropy_mask = [True,] * len(gcmf_texture.anisotropy)
                    draw_checkbox_row(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, label_texts=anisotropy_labels, data_masks=anisotropy_mask, property='anisotropy', label_text='Anisotropy')
                    # unk0x0C
                    draw_checkbox_column(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, flags=gcmf_texture.unk0x0C, property='unk0x0C', label_text=NAME_GXMDLVIEW_TEX_UNK0C)
                    # is Swappable
                    draw_checkbox_column(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, flags=gcmf_texture.is_swappable, property='is_swappable', label_text='is Swappable (0x0D)')
                    # unk0x10
                    draw_checkbox_column(box, gcmf_texture, gcmf_texture.show_propertys, show_property_keys, flags=gcmf_texture.unk0x10, property='unk0x10', label_text=NAME_GXMDLVIEW_TEX_UNK10)

        # If faild to get "gcmf_texture" from active Texture
        except Exception as e:
            self.layout.label(text=f"Error occurred: {e}")
