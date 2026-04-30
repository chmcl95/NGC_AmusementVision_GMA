import bpy

NAME_ID_PROPERTY_VIEWER_BASE = 'object_PT_GCMF_{0}_Viewer'
NAME_ID_PROPERTY_EDITOR_BASE = 'object_PT_GCMF_{0}_Editor'
NAME_LABEL_PROPERTY_BASE = 'GCMF {0}'

#Names called on GxModelViewer
NAME_OBJ_INDEX = 'Index of Object'
NAME_GXMDLVIEW_OBJ_ATTRIBUTE = 'Section Flags (0x00)'

NAME_GXMDLVIEW_MAT_RENDER_FLAG = 'Render Flags (0x00)'
NAME_GXMDLVIEW_MAT_COLOR0 = 'Vertex Shading A (0x04)'
NAME_GXMDLVIEW_MAT_COLOR1 = 'Vertex Shading B (0x08)'
NAME_GXMDLVIEW_MAT_COLOR2 = 'Specular Tint (0x0C)'
NAME_GXMDLVIEW_MAT_TRANSPARENCY = 'Transparency (0x10)'
NAME_GXMDLVIEW_MAT_UNK14 = 'Unknown (0x14)'
NAME_GXMDLVIEW_MAT_BOUND_SPHERE = 'Bounding Spher Center (X, Y, Z)'
NAME_GXMDLVIEW_MAT_UNK3C = 'Unknown (0x3C)'
NAME_GXMDLVIEW_MAT_UNK40 = 'Unknown (0x40)'
NAME_GXMDLVIEW_TEX_MAT_FLAG = 'Material Flags (0x00)'
NAME_GXMDLVIEW_TEX_TPL_IDX = 'Texture Index (0x04)'
NAME_GXMDLVIEW_TEX_UNK06 = 'Unknown (0x06)'
NAME_GXMDLVIEW_TEX_ANISO = 'Anisotropy Level (0x07)'
NAME_GXMDLVIEW_TEX_UNK0C = 'Unknown (0x0C)'
NAME_GXMDLVIEW_TEX_UNK10 = 'Unknown (0x10)'

MSG_NOT_FOUND_MATERIAL = 'Press \"New\" Button'
MSG_NOT_FOUND_TEXTURE = MSG_NOT_FOUND_MATERIAL
MSG_HEX_2 = '{0}: {1:02X}'
MSG_HEX_4 = '{0}: {1:04X}'
MSG_HEX_8 = '{0}: {1:08X}'
MSG_LABEL_SHOW = '{0}: {1}'
MSG_LABEL_EDIT = '{0}:'


#GCMF Object Setting Show Panel
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
            pass #do nothing


#GCMF Object Setting Edit Panel
class OBJECT_PT_GCMF_Object_Editor(bpy.types.Panel):
    #bl_parent_id = "OBJECT_PT_GCMF_Object_Viewer" # for2.8's submenu
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Object')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Object Editor')
    # bl_label = 'Edit' # for2.8's submenu
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        try:
            gcmf_object = bpy.context.active_object.gcmf_object

            # index
            self.layout.label( MSG_LABEL_EDIT.format('index') )
            self.layout.prop(gcmf_object, "index", text="values")
            # attribute
            self.layout.label( MSG_LABEL_EDIT.format('attribute') )
            self.layout.prop(gcmf_object, "attribute")
            # box_attribute = self.layout.box()
            # col_attribute = box_attribute.column_flow(columns=8)
            # texts = ['flags',\
            #         'is_effective', 'is_skin', 'is_stiching', 'is_unk0x01',
            #         'is_16bit']
            # for text in texts:
            #    col_attribute.label(text)

        # If faild to get "gcmf_object" from active Object
        except:
            pass #do nothing

#GCMF Material Setting Show Panel
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

            #unk0x02, unk0x03
            val = 0x00
            for i, unk0x02 in enumerate(gcmf_material.unk0x02):
                val += (unk0x02.real << (7-i))
            val = val << 8
            for i, unk0x03 in enumerate(gcmf_material.unk0x03):
                val += (unk0x03.real << (7-i))
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_RENDER_FLAG, val))
            #color0
            val = self.calc_color(gcmf_material.color0)
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_COLOR0, val))
            #color1
            val = self.calc_color(gcmf_material.color1)
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_COLOR1, val))
            #color2
            val = self.calc_color(gcmf_material.color2)
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_COLOR2, val))
            #emission, transparency
            val = (gcmf_material.emission << 8)\
                + gcmf_material.transparency
            self.layout.label(MSG_HEX_4.format(NAME_GXMDLVIEW_MAT_TRANSPARENCY, val))
            #unk0x14, unk0x15
            val = (gcmf_material.unk0x14 << 8)\
                + gcmf_material.unk0x15
            self.layout.label(MSG_HEX_4.format(NAME_GXMDLVIEW_MAT_UNK14, val))

            #These are not "Material"
            #unk0x3C
            self.layout.label(MSG_LABEL_SHOW.format(NAME_GXMDLVIEW_MAT_UNK3C, gcmf_material.unk0x3C))
            #unk0x40
            val = 0x00
            for i, unk0x40 in enumerate(gcmf_material.unk0x40):
                val += (unk0x40.real << (31-i))
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_MAT_UNK40, val))
            
        # If faild to get "gcmf_material" from active Material
        except:
            self.layout.label(MSG_NOT_FOUND_MATERIAL)

#GCMF Material Setting Edit Panel
class OBJECT_PT_GCMF_Material_Editor(bpy.types.Panel):
    #bl_parent_id = "OBJECT_PT_GCMF_Material_Viewer" # for2.8's submenu
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Material')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Material Editor')
    # bl_label = 'Edit' # for2.8's submenu
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    def draw(self, context):
        try:
            gcmf_material = bpy.context.active_object.active_material.gcmf_material

            self.layout.label( MSG_LABEL_EDIT.format('unk0x02') )
            self.layout.prop(gcmf_material, "unk0x02", text="values")
            self.layout.label( MSG_LABEL_EDIT.format('unk0x03') )
            self.layout.prop(gcmf_material, "unk0x03", text="values")
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_COLOR0) )
            self.layout.prop(gcmf_material, "color0", text="values")
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_COLOR1) )
            self.layout.prop(gcmf_material, "color1", text="values")
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_COLOR2) )
            self.layout.prop(gcmf_material, "color2", text="values")
            self.layout.prop(gcmf_material, "emission", text="emission")
            self.layout.prop(gcmf_material, "transparency", text="transparency")
            self.layout.prop(gcmf_material, "unk0x14", text="unk0x14")
            self.layout.prop(gcmf_material, "unk0x15", text="unk0x15")

            #These are not "Material"
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_MAT_BOUND_SPHERE) )
            self.layout.prop(gcmf_material, "boundingsphere_origin", text="values")
            self.layout.prop(gcmf_material, "unk0x3C", text="unk0x3C")
            self.layout.prop(gcmf_material, "unk0x40", text="unk0x40")
        # If faild to get "gcmf_material" from active Material
        except:
            pass #do nothing


#GCMF Texture Setting Show Panel
class OBJECT_PT_GCMF_Texture_Viewer(bpy.types.Panel):
    bl_idname = NAME_ID_PROPERTY_VIEWER_BASE.format('Texture')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Texture Viewer')
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"
    
    def draw(self, context):
        try:
            gcmf_texture = bpy.context.active_object.active_material.active_texture.gcmf_texture
            # unk0x00
            val = 0x00
            for i, unk0x00 in enumerate(gcmf_texture.unk0x00):
                val += (unk0x00.real << (15-i))
            val = val << 8
            for i, mipmap in enumerate(gcmf_texture.mipmap):
                val += (mipmap.real << (7-i))
            val = val << 8
            for i, uv_wrap in enumerate(gcmf_texture.uv_wrap):
                val += (uv_wrap.real << (7-i))
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_TEX_MAT_FLAG, val))
            # texture_index
            self.layout.label(MSG_HEX_4.format(NAME_GXMDLVIEW_TEX_TPL_IDX, gcmf_texture.texture_index))
            # unk0x06
            self.layout.label(MSG_HEX_2.format(NAME_GXMDLVIEW_TEX_UNK06, gcmf_texture.unk0x06))
            # anisotropy
            val = 0x00
            for i, anisotropy in enumerate(gcmf_texture.anisotropy):
                val += (anisotropy.real << (7-i))
            self.layout.label(MSG_HEX_2.format(NAME_GXMDLVIEW_TEX_ANISO, val))
            # unk0x0C
            val = 0x00
            for i, unk0x0C in enumerate(gcmf_texture.unk0x0C):
                val += (unk0x0C.real << (7-i))
            val = val << 8
            for i, is_swappable in enumerate(gcmf_texture.is_swappable):
                val += (is_swappable.real << (7-i))
            self.layout.label(MSG_HEX_4.format(NAME_GXMDLVIEW_TEX_UNK0C, val))
            # unk0x10
            val = 0x00
            for i, unk0x10 in enumerate(gcmf_texture.unk0x10):
                val += (unk0x10.real << (31-i))
            self.layout.label(MSG_HEX_8.format(NAME_GXMDLVIEW_TEX_UNK10, val))

            
        # If faild to get "gcmf_texture" from active Texture
        except:
            self.layout.label(MSG_NOT_FOUND_TEXTURE)

#GCMF Texture Setting Edit Panel
class OBJECT_PT_GCMF_Texture_Editor(bpy.types.Panel):
    #bl_parent_id = "OBJECT_PT_GCMF_Texture_Viewer" # for2.8's submenu
    bl_idname = NAME_ID_PROPERTY_EDITOR_BASE.format('Texture')
    bl_label = NAME_LABEL_PROPERTY_BASE.format('Texture Editor')
    # bl_label = 'Edit' # for2.8's submenu
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "texture"
    
    def draw(self, context):
        try:
            gcmf_texture = bpy.context.active_object.active_material.active_texture.gcmf_texture

            # unk0x00
            self.layout.label( MSG_LABEL_EDIT.format('unk0x00') )
            self.layout.prop(gcmf_texture, "unk0x00", text="value")
            box_unk0x00 = self.layout.box()
            col_unk0x00 = box_unk0x00.column_flow(columns=8)
            texts = ['flags',\
                     'unknown15', 'unknown14', 'unknown13', 'unknown12',
                     'unknown11', 'unknown10', 'unknown9', 'unknown8',
                     'unknown7',  'unknown6',  'commontex', 'unknown4',
                     'unknown3',  'unknown2',  'uv_scroll', 'unknown0']
            for text in texts:
                col_unk0x00.label(text)
            # mipmap
            self.layout.label( MSG_LABEL_EDIT.format('MIPMAP') )
            self.layout.prop(gcmf_texture, "mipmap", text="value")
            box_mipmap = self.layout.box()
            col_mipmap = box_mipmap.column_flow(columns=9)
            texts = ['flags',\
                     'unknown7', 'unknown6', 'unknown5', 'unknown4',\
                     'near',     'unknown2', 'unknown1', 'enable']
            for text in texts:
                col_mipmap.label(text)
            # uv_wrap
            self.layout.label( MSG_LABEL_EDIT.format('UV WRAP') )
            self.layout.prop(gcmf_texture, "uv_wrap", text="value")
            box_uv_wrap = self.layout.box()
            col_uv_wrap = box_uv_wrap.column_flow(columns=9)
            texts = ['flags',\
                     'unknown7', 'unknown6', 'Y-Mirror', 'Y-Repeat',\
                     'X-Mirror', 'Y-Repeat', 'unknown1', 'unknown0']
            for text in texts:
                col_uv_wrap.label(text)
            # texture_index
            self.layout.label(NAME_GXMDLVIEW_TEX_TPL_IDX)
            self.layout.prop(gcmf_texture, "texture_index", text="value")
            # unk0x06
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_TEX_UNK06) )
            self.layout.prop(gcmf_texture, "unk0x06", text="value")
            # anisotropys
            self.layout.label( MSG_LABEL_EDIT.format('Anisotropy') )
            self.layout.prop(gcmf_texture, "anisotropy", text="value")
            box_anisotropy = self.layout.box()
            col_anisotropy = box_anisotropy.column_flow(columns=9)
            texts = ['flags',\
                     'unknown7',\
                     'unknown6',\
                     'unknown5',\
                     'unknown4',\
                     'unknown3',\
                     'aniso4',\
                     'aniso2',\
                     'aniso1']
            for text in texts:
                col_anisotropy.label(text)
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_TEX_UNK0C) )
            self.layout.prop(gcmf_texture, "unk0x0C", text="value")
            self.layout.label( MSG_LABEL_EDIT.format('is Swappable (0x0D)') )
            self.layout.prop(gcmf_texture, "is_swappable", text="value")
            self.layout.label( MSG_LABEL_EDIT.format(NAME_GXMDLVIEW_TEX_UNK10) )
            self.layout.prop(gcmf_texture, "unk0x10", text="value")

        # If faild to get "gcmf_texture" from active Texture
        except:
            pass #do nothing