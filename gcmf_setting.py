import bpy

# GCMF Object Property
class GCMF_ObjectSetting(bpy.types.PropertyGroup):
    gcmf_attribute_enum = [
        ("default",      "Basic Model",     "", 0),
        ("is_16bit",     "16Bit",           "", 1),
        ("is_stiching",  "Stitching Model", "not supports", 2),
        ("is_skin",      "Skin Model",      "not supports", 3),
        ("is_effective", "Effective Model", "not supports", 4)
    ]

    index: bpy.props.IntProperty(name="gcmf order index", default=0x00, min=-0x7FFF, max=0x7FFF)
    attribute: bpy.props.EnumProperty(items=gcmf_attribute_enum, default="default")

    transparent_count: bpy.props.IntProperty(name="transparent_material_count", default=0, min=0, max=0x7FFF)

# GCMF Material Property
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

    _vtx_descriptor = [False] * 32
    # UV0
    _vtx_descriptor[18] = True
    # Normal
    _vtx_descriptor[21] = True
    # Position
    _vtx_descriptor[22] = True
    vtx_descriptor: bpy.props.BoolVectorProperty(name="vtx_descriptor", default=_vtx_descriptor,
                                                    subtype='NONE', size=32)
    texture_indexes: bpy.props.IntVectorProperty(name="texture_indices", default=(-1, -1, -1),
                                                 min=-1, max=0x7F, subtype='NONE', size=3)
    order_index: bpy.props.IntProperty(name="gcmf material order index", default=0x00, min=-0x7FFF, max=0x7FFF)


    # These are not strictly Material properties but are kept here for round-trip
    boundingsphere_origin: bpy.props.FloatVectorProperty(name="boundingsphere_origin",
                                                          default=(0.0, 0.0, 0.0))
    unk0x3C: bpy.props.FloatProperty(name="unk0x3C", default=0.0)
    _unk0x40_default = [False] * 32
    _unk0x40_default[21] = True
    _unk0x40_default[22] = True
    unk0x40: bpy.props.BoolVectorProperty(name="unk0x40",
                                           default=tuple(_unk0x40_default),
                                           subtype='NONE', size=32)
    
    # UI
    _show_propertys_default = [False] * 4
    # Vertex Descriptor
    _show_propertys_default[0] = True
    show_propertys: bpy.props.BoolVectorProperty(name="Edit Boxs", default=tuple(_show_propertys_default),
                                           subtype='NONE', size=4)
