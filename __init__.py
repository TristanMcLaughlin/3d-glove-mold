# Register the classes
from . createShellMold import CreateConeOperator, CreateGloveMold, MakeGloveMold
import bpy

bl_info = {
    "name": "Create shell for matrix molds",
    "author": "Tristan McLaughlin",
    "location": "View3D  -> Tool -> Create Glove Mold Panel",
    "version": (0, 0, 3),
    "blender": (2, 90, 0),
    "description": "Create shell for matrix molds",
    'tracker_url': "https://github.com/TristanMcLaughlin/3d-glove-mold/issues",
    "category": "Mesh"
}

def register():
    bpy.utils.register_class(CreateConeOperator)
    bpy.utils.register_class(MakeGloveMold)
    bpy.utils.register_class(CreateGloveMold)
    bpy.types.Scene.glove_mold_thickness = bpy.props.FloatProperty(name="Glove Mold Thickness",min=0)
    bpy.types.Scene.shell_thickness = bpy.props.FloatProperty(name="Shell Thickness",min=0)

def unregister():
    bpy.utils.unregister_class(CreateConeOperator)
    bpy.utils.unregister_class(MakeGloveMold)
    bpy.utils.unregister_class(CreateGloveMold)
    del bpy.types.Scene.glove_mold_thickness
    del bpy.types.Scene.shell_thickness

# Run the script when Blender loads the plugin
if __name__ == "__main__":
    register()