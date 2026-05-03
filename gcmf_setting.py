import bpy

# ---- Texture Settings (formerly bpy.types.Texture.gcmf_texture) ----
# bpy.types.Texture was removed in Blender 4.x.
# Each material now holds a collection of GCMF_TextureSetting via tex_settings[].

class GCMF_TextureSetting(bpy.types.PropertyGroup):
    unk0x00: bpy.props.BoolVectorProperty(name="unk0x00",
                                           default=(False,) * 16,
                                           subtype='NONE', size=16)
    _mipmap_default = [False] * 8
    _mipmap_default[5] = True
    _mipmap_default[6] = True
    _mipmap_default[7] = True
    mipmap: bpy.props.BoolVectorProperty(name="mipmap",
                                          default=tuple(_mipmap_default),
                                          subtype='NONE', size=8)
    _uv_wrap_default = [False] * 8
    _uv_wrap_default[0] = True
    _uv_wrap_default[1] = True
    _uv_wrap_default[3] = True
    _uv_wrap_default[5] = True
    uv_wrap: bpy.props.BoolVectorProperty(name="uv_wrap",
                                           default=tuple(_uv_wrap_default),
                                           subtype='NONE', size=8)
    texture_index: bpy.props.IntProperty(name="texture_index", default=0x00, min=0, max=0x7FFF)
    unk0x06: bpy.props.IntProperty(name="unk0x06", default=0x00, min=0x00, max=0xFF)
    anisotropy: bpy.props.BoolVectorProperty(name="anisotropy",
                                              default=(False,) * 8,
                                              subtype='NONE', size=8)
    unk0x0C: bpy.props.BoolVectorProperty(name="unk0x0C",
                                           default=(False,) * 8,
                                           subtype='NONE', size=8)
    is_swappable: bpy.props.BoolVectorProperty(name="is_swappable",
                                                default=(False,) * 8,
                                                subtype='NONE', size=8)
    _unk0x10_default = [False] * 32
    _unk0x10_default[26] = True
    _unk0x10_default[27] = True
    unk0x10: bpy.props.BoolVectorProperty(name="unk0x10",
                                           default=tuple(_unk0x10_default),
                                           subtype='NONE', size=32)
    # Image name reference (replaces bpy.types.Texture image link)
    image_name: bpy.props.StringProperty(name="image_name", default="")
    # UV wrap mode cached for convenience
    extension: bpy.props.StringProperty(name="extension", default="EXTEND")
    use_mirror_x: bpy.props.BoolProperty(name="use_mirror_x", default=False)
    use_mirror_y: bpy.props.BoolProperty(name="use_mirror_y", default=False)

# GCMF Object Setting
class GCMF_ObjectSetting(bpy.types.PropertyGroup):
    gcmf_attribute_enum = [
        ("default",      "Basic Model",     "", 0),
        ("is_16bit",     "16Bit",           "", 1),
        ("is_stiching",  "Stitching Model", "not supports", 2),
        ("is_skin",      "Skin Model",      "not supports", 3),
        ("is_effective", "Effective Model", "not supports", 4)
    ]

    index: bpy.props.IntProperty(name="index", default=0x00, min=-0xFFFF, max=0xFFFF)
    attribute: bpy.props.EnumProperty(items=gcmf_attribute_enum, default="default")

# GCMF Material Setting
class GCMF_MaterialSetting(bpy.types.PropertyGroup):
    unk0x02: bpy.props.BoolVectorProperty(name="unk0x02", default=(False,) * 8,
                                           subtype='NONE', size=8)
    unk0x03: bpy.props.BoolVectorProperty(name="unk0x03", default=(False,) * 8,
                                           subtype='NONE', size=8)
    color0: bpy.props.IntVectorProperty(name="color0", default=(0xFF, 0xFF, 0xFF, 0xFF),
                                         min=0x00, max=0xFF, subtype='NONE', size=4)
    color1: bpy.props.IntVectorProperty(name="color1", default=(0x7F, 0x7F, 0x7F, 0xFF),
                                         min=0x00, max=0xFF, subtype='NONE', size=4)
    color2: bpy.props.IntVectorProperty(name="color2", default=(0x00, 0x00, 0x00, 0x00),
                                         min=0x00, max=0xFF, subtype='NONE', size=4)
    emission: bpy.props.IntProperty(name="emission", default=0x00, min=0x00, max=0xFF)
    transparency: bpy.props.IntProperty(name="transparency", default=0xFF, min=0x00, max=0xFF)
    unk0x14: bpy.props.IntProperty(name="unk0x14", default=0xFF, min=0x00, max=0xFF)
    unk0x15: bpy.props.IntProperty(name="unk0x15", default=0x00, min=0x00, max=0xFF)

    # These are not strictly Material properties but are kept here for round-trip
    boundingsphere_origin: bpy.props.FloatVectorProperty(name="boundingsphere_origin",
                                                          default=(0.0, 0.0, 0.0))
    unk0x3C: bpy.props.FloatProperty(name="unk0x3C", default=0.0)
    _unk0x40_default = [False] * 32
    _unk0x40_default[27] = True
    _unk0x40_default[29] = True
    unk0x40: bpy.props.BoolVectorProperty(name="unk0x40",
                                           default=tuple(_unk0x40_default),
                                           subtype='NONE', size=32)
""""
    # Flag: whether GCMF values were loaded from file (keep_values branch)
    is_keep: bpy.props.BoolProperty(name="is_keep", default=False)

    # Per-texture settings stored as a CollectionProperty
    # (replaces the old bpy.types.Texture approach)
    tex_settings: bpy.props.CollectionProperty(type=GCMF_TextureSetting)
"""