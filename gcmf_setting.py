import bpy

#GCMF Object Setting
class GCMF_ObjectSetting(bpy.types.PropertyGroup):
    gcmf_attribute_enum = [
        ("default",      "Basic Model",     "", 0),
        ("is_16bit",     "16Bit",           "", 1),
        ("is_stiching",  "Stitching Model", "not supports", 2),
        ("is_skin",      "Skin Model",      "not supports", 3),
        ("is_effective", "Effective Model", "not supports", 4)
    ]

    index = bpy.props.IntProperty(name="index", default=0x00, min=-0xFFFF, max=0xFFFF)
    attribute = bpy.props.EnumProperty(items=gcmf_attribute_enum, default="default")

#GCMF Material Setting
class GCMF_MaterialSetting(bpy.types.PropertyGroup):
    #unk0x02 = bpy.props.IntProperty(name="unk0x02", default=0x00, min=0x00, max=0xFF)
    unk0x02 = bpy.props.BoolVectorProperty(name="unk0x02", default=(False, )*8,\
                                         subtype='NONE', size=8)
    #unk0x03 = bpy.props.IntProperty(name="unk0x03", default=0x00, min=0x00, max=0xFF)
    unk0x03 = bpy.props.BoolVectorProperty(name="unk0x03", default=(False, )*8,\
                                         subtype='NONE', size=8)
    color0 = bpy.props.IntVectorProperty(name="color0", default=(0xFF, 0xFF, 0xFF, 0xFF),\
                                         min=0x00, max=0xFF, subtype='NONE', size=4)
    color1 = bpy.props.IntVectorProperty(name="color1", default=(0x7F, 0x7F, 0x7F, 0xFF),\
                                         min=0x00, max=0xFF, subtype='NONE', size=4)
    color2 = bpy.props.IntVectorProperty(name="color2", default=(0x00, 0x00, 0x00, 0x00),\
                                         min=0x00, max=0xFF, subtype='NONE', size=4)
    emission = bpy.props.IntProperty(name="emission", default=0x00, min=0x00, max=0xFF)
    transparency = bpy.props.IntProperty(name="emission", default=0xFF, min=0x00, max=0xFF)
    unk0x14 = bpy.props.IntProperty(name="unk0x14", default=0xFF, min=0x00, max=0xFF)
    unk0x15 = bpy.props.IntProperty(name="unk0x15", default=0x00, min=0x00, max=0xFF)

    #These are not Material
    boundingsphere_origin = bpy.props.FloatVectorProperty(name="boundingsphere_origin", default=(0.0, 0.0, 0.0))

    unk0x3C = bpy.props.FloatProperty(name="unk0x3C", default=0.0)
    unk0x40_defalut = [False, ]*32
    unk0x40_defalut[27] = True
    unk0x40_defalut[29] = True
    unk0x40 = bpy.props.BoolVectorProperty(name="unk0x40",\
                                           default=tuple(unk0x40_defalut),\
                                           subtype='NONE', size=32)


#GCMF Texture Setting
class GCMF_TextureSetting(bpy.types.PropertyGroup):
    unk0x00 = bpy.props.BoolVectorProperty(name="unk0x00",\
                                           default=(False, )*16,\
                                           subtype='NONE', size=16)
    mipmap_defalut = [False, ]*8
    mipmap_defalut[5] = True
    mipmap_defalut[6] = True
    mipmap_defalut[7] = True
    mipmap = bpy.props.BoolVectorProperty(name="mipmap",\
                                           default=tuple(mipmap_defalut),\
                                           subtype='NONE', size=8)
    uv_wrap_defalut = [False, ]*8
    uv_wrap_defalut[0] = True
    uv_wrap_defalut[1] = True
    uv_wrap_defalut[3] = True
    uv_wrap_defalut[5] = True
    uv_wrap = bpy.props.BoolVectorProperty(name="uv_wrap",\
                                           default=uv_wrap_defalut,\
                                           subtype='NONE', size=8)
    texture_index = bpy.props.IntProperty(name="texture_index", default=0x00, min=0, max=0x7FFF)
    unk0x06 = bpy.props.IntProperty(name="unk0x06", default=0x00, min=0x00, max=0xFF)
    anisotropy = bpy.props.BoolVectorProperty(name="anisotropy",\
                                           default=(False, )*8,\
                                           subtype='NONE', size=8)
    unk0x0C = bpy.props.BoolVectorProperty(name="unk0x10",\
                                           default=(False, )*8,\
                                           subtype='NONE', size=8)
    is_swappable = bpy.props.BoolVectorProperty(name="is_swappable",\
                                                default=(False, )*8,\
                                                subtype='NONE', size=8)
    unk0x10_defalut = [False, ]*32
    unk0x10_defalut[26] = True
    unk0x10_defalut[27] = True
    unk0x10 = bpy.props.BoolVectorProperty(name="unk0x10",\
                                           default=tuple(unk0x10_defalut),\
                                           subtype='NONE', size=32)
