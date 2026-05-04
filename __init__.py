import bpy
import importlib

from . import export_gma
from . import import_gma
#from . import import_gml
from . import gcmf_editor
# TODO: rename setting to property 
from . import gcmf_setting

bl_info = {
    "name": "Amusement Vision GMA format",
    "author": "CH-MCL",
    "version": (0, 4, 420, 0),
    "blender": (4, 2, 0),
    "location": "File > Import-Export > Amusement Vision Model (.gma)",
    "description": "Imports a Amusement Vision 3d model.",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    if "import_gma" in locals():
        importlib.reload(import_gma)
    if "export_gma" in locals():
        importlib.reload(export_gma)
    # TODO:remove import_gml
#    if "import_gml" in locals():
#        importlib.reload(import_gml)
    if "gcmf_setting" in locals():
        importlib.reload(gcmf_setting)
    if "gcmf_editor" in locals():
        importlib.reload(gcmf_editor)

from bpy.props import (
        BoolProperty,
        StringProperty,
        )
from bpy_extras.io_utils import (
        ExportHelper,
        ImportHelper,
        )


# Import GMA
class IMPORT_UL_GMA(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.gma"
    bl_label = "Import GMA"
    bl_description = "Import a Amusement Vision 3D model"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".gma"
    filter_glob: StringProperty(default="*.gma", options={'HIDDEN'})

    little_endian: BoolProperty(
            name="Little Endian",
            description="Read file as Little Endian. Super Monkey Ball Delux's gma must Enable this. ",
            default=False,
            )

    def execute(self, context):
        import_gma.load(self.filepath, self.little_endian)
        return {'FINISHED'}


# Export GMA
class EXPORT_UL_GMA(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.gma"
    bl_label = "Export GMA"
    bl_description = "Export a Amusement Vision model"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".gma"
    filter_glob: StringProperty(default="*.gma", options={'HIDDEN'})

    little_endian: BoolProperty(
            name="Little Endian",
            description="Write as Little Endian. Super Monkey Ball Delux's gma must Enable this.",
            default=False,
            )

    def execute(self, context):
        export_gma.save(self.filepath, self.little_endian)
        return {'FINISHED'}

# TODO: enable GML Import AGAIN
"""
# Import GML
class IMPORT_UL_GML(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.gml"
    bl_label = "Import GML"
    bl_description = "Import a Amusement Vision 3D model (alt). This file is used at Virtua Striker."
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".gml"
    filter_glob: StringProperty(default="*.gml", options={'HIDDEN'})

    little_endian: BoolProperty(
            name="Little Endian",
            description="Read file as Little Endian. Super Monkey Ball Delux's gma must Enable this.",
            default=False,
            )

    def execute(self, context):
        import_gml.load(self.filepath, self.little_endian)
        return {'FINISHED'}
"""
# no plans exporting GML


def menu_func_import(self, context):
    self.layout.operator(IMPORT_UL_GMA.bl_idname, text="Amusement Vision Model (.gma)")
#    self.layout.operator(IMPORT_UL_GML.bl_idname, text="Amusement Vision Model alt(.gml)")


def menu_func_export(self, context):
    self.layout.operator(EXPORT_UL_GMA.bl_idname, text="Amusement Vision Model (.gma)")
    #no plans export GML


classes = (
    #Import/Export
    IMPORT_UL_GMA,
    EXPORT_UL_GMA,
#    IMPORT_UL_GML,
    #CustomProperty
    gcmf_setting.GCMF_ObjectSetting,
    gcmf_setting.GCMF_TextureSetting,
    gcmf_setting.GCMF_MaterialSetting,
    #Panel
    gcmf_editor.OBJECT_PT_GCMF_Object_Viewer,
    gcmf_editor.OBJECT_PT_GCMF_Object_Editor,
    gcmf_editor.OBJECT_PT_GCMF_Material_Viewer,
    gcmf_editor.OBJECT_PT_GCMF_Material_Editor,
    gcmf_editor.OBJECT_PT_GCMF_Texture_Viewer,
    gcmf_editor.OBJECT_PT_GCMF_Texture_Editor,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    # Custom PropertyGroup
    bpy.types.Object.gcmf_object = \
        bpy.props.PointerProperty(type=gcmf_setting.GCMF_ObjectSetting)
    bpy.types.Material.gcmf_material = \
        bpy.props.PointerProperty(type=gcmf_setting.GCMF_MaterialSetting)
    

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    del bpy.types.Object.gcmf_object
    del bpy.types.Material.gcmf_material

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
