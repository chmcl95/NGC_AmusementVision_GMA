import bpy
import importlib

from . import export_gma
from . import import_gma
from .gcmf import GCMFError
from . import gcmf_editor
from . import gcmf_props
from . import gcmf_shader_node

bl_info = {
    "name": "Amusement Vision GMA format",
    "author": "chmcl95",
    "version": (1, 0, 420, 0),
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
    if "gcmf_shader_node" in locals():
        importlib.reload(gcmf_shader_node)
    if "gcmf_props" in locals():
        importlib.reload(gcmf_props)
    if "gcmf_editor" in locals():
        importlib.reload(gcmf_editor)

from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class IMPORT_UL_GMA(bpy.types.Operator, ImportHelper):
    """Import an Amusement Vision 3D model (.gma)."""

    bl_idname    = "import_scene.gma"
    bl_label     = "Import GMA"
    bl_description = "Import a Amusement Vision 3D model"
    bl_options   = {'REGISTER', 'UNDO'}

    filename_ext = ".gma"
    filter_glob: StringProperty(default="*.gma", options={'HIDDEN'})

    little_endian: BoolProperty(
        name="Little Endian",
        description=(
            "Read file as Little Endian. "
            "Required for Super Monkey Ball Deluxe."
        ),
        default=False,
    )

    def execute(self, context: bpy.types.Context) -> set:
        try:
            warnings = import_gma.load(self.filepath, self.little_endian)
        except GCMFError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Unexpected error: {e}")
            return {'CANCELLED'}
        for w in warnings:
            self.report({'WARNING'}, w)
        return {'FINISHED'}


class EXPORT_UL_GMA(bpy.types.Operator, ExportHelper):
    """Export selected objects to an Amusement Vision 3D model (.gma)."""

    bl_idname    = "export_scene.gma"
    bl_label     = "Export GMA"
    bl_description = "Export a Amusement Vision model"
    bl_options   = {'REGISTER', 'UNDO'}

    filename_ext = ".gma"
    filter_glob: StringProperty(default="*.gma", options={'HIDDEN'})

    little_endian: BoolProperty(
        name="Little Endian",
        description=(
            "Write as Little Endian. "
            "Required for Super Monkey Ball Deluxe."
        ),
        default=False,
    )

    def execute(self, context: bpy.types.Context) -> set:
        try:
            warnings = export_gma.save(self.filepath, self.little_endian)
        except GCMFError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Unexpected error: {e}")
            return {'CANCELLED'}
        for w in warnings:
            self.report({'WARNING'}, w)
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


# ---------------------------------------------------------------------------
# Menu callbacks
# ---------------------------------------------------------------------------

def menu_func_import(self, context: bpy.types.Context) -> None:
    self.layout.operator(IMPORT_UL_GMA.bl_idname,
                         text="Amusement Vision Model (.gma)")


def menu_func_export(self, context: bpy.types.Context) -> None:
    self.layout.operator(EXPORT_UL_GMA.bl_idname,
                         text="Amusement Vision Model (.gma)")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = (
    # Import / Export operators
    IMPORT_UL_GMA,
    EXPORT_UL_GMA,
#    IMPORT_UL_GML,
    # Custom shader node
    gcmf_shader_node.GCMFTextureNode,
    # Property groups
    gcmf_props.GCMF_ObjectSetting,
    gcmf_props.GCMF_MaterialSetting,
    # UI panels
    gcmf_editor.OBJECT_PT_GCMF_Object_Viewer,
    gcmf_editor.OBJECT_PT_GCMF_Object_Editor,
    gcmf_editor.OBJECT_PT_GCMF_Material_Viewer,
    gcmf_editor.OBJECT_PT_GCMF_Material_Editor,
    gcmf_editor.OBJECT_PT_GCMF_Texture_Viewer,
)


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.NODE_MT_add.append(gcmf_shader_node._add_node_menu)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

    bpy.types.Object.gcmf_object = bpy.props.PointerProperty(
        type=gcmf_props.GCMF_ObjectSetting)
    bpy.types.Material.gcmf_material = bpy.props.PointerProperty(
        type=gcmf_props.GCMF_MaterialSetting)


def unregister() -> None:
    bpy.types.NODE_MT_add.remove(gcmf_shader_node._add_node_menu)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    del bpy.types.Object.gcmf_object
    del bpy.types.Material.gcmf_material

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
