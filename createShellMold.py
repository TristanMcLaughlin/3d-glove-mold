import bpy
import mathutils
import math

bl_info = {
    "name": "Create shell for matrix molds",
    "author": "Tristan McLaughlin",
    "location": "View3D  -> Tool -> Create Glove Mold Panel",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "description": "Create shell for matrix molds",
    'tracker_url': "https://github.com/TristanMcLaughlin/3d-glove-mold/issues",
    "category": "Mesh"
}

def applyModifiers(context, object):
    context.view_layer.objects.active = object
    for modifier in object.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

def createBoolean(context, duplicated, cube, type, solver='EXACT'):
    # Apply modifiers
    for modifier in duplicated.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        
    # Attach the cube as a bool
    booleanMod = duplicated.modifiers.new("Boolean", "BOOLEAN")
    booleanMod.object = cube
    booleanMod.operation = type
    booleanMod.use_self = True
    booleanMod.solver = solver
    return

def addSolidifyModifier(context, object, thickness):
    mod = object.modifiers.new("Solidify", "SOLIDIFY")
    mod.offset = 1
    mod.thickness = thickness
    mod.use_quality_normals = True
    mod.nonmanifold_thickness_mode = 'FIXED'
    mod.use_rim = True
    mod.use_rim_only = True
    return

def makeCube(context, size, location):
    bpy.ops.mesh.primitive_cube_add(size=size,location=location)
    cube = context.active_object
    cube.hide_set(True)
    return cube

def makeGloveMold(context):
    gloveMoldThickness = bpy.context.scene.glove_mold_thickness
    shellThickness = bpy.context.scene.shell_thickness
    flangeThickness = gloveMoldThickness + shellThickness + 5 # As thick as inner + outer + 5mm for clips

    originalObject = context.active_object

    lowResObject = originalObject.copy()
    lowResObject.data = originalObject.data.copy()
    lowResObject.name = "Low Res Copy"
    context.collection.objects.link(lowResObject)

    # Create a low res clone for working on
    # Decimate to 1k polys if over 1k polys
    decimateRatio = min(3000 / len(originalObject.data.polygons), 1)
    decimateMod = lowResObject.modifiers.new("Decimate", "DECIMATE")
    decimateMod.ratio = decimateRatio
    
    # Smooth mesh
    smoothMod = lowResObject.modifiers.new("CorrectiveSmooth", "CORRECTIVE_SMOOTH")
    smoothMod.factor = 0.8
    smoothMod.scale = 0

    applyModifiers(context, lowResObject)

    cone = bpy.data.objects["Cone Shell"]

    # Duplicate object for working with
    context.view_layer.objects.active = lowResObject
    duplicated = context.active_object.copy()
    duplicated.data = context.active_object.data.copy()
    duplicated.name = "Shell"
    context.collection.objects.link(duplicated)
    context.view_layer.objects.active = duplicated

    # Make thicker version of model as basis of shell
    addSolidifyModifier(context, duplicated, shellThickness + gloveMoldThickness)
    
    createBoolean(context, duplicated, cone, 'UNION')

    # Add the cone flange
    coneFlange = cone.copy()
    coneFlange.data = cone.data.copy()
    coneFlange.name = "Cone Flange"
    coneFlange.location.z = coneFlange.location.z - 5
    context.collection.objects.link(coneFlange)
    
    addSolidifyModifier(context, coneFlange, gloveMoldThickness)
    applyModifiers(context, coneFlange)
    cuboid = makeCube(context, 4, (0, 0, 0))
    bpy.context.object.scale.yz = 500, 500

    createBoolean(context, coneFlange, cuboid, 'INTERSECT')
    applyModifiers(context, coneFlange)
    createBoolean(context, duplicated, coneFlange, 'UNION')

    # Add the middle flange
    middleSection = lowResObject.copy()
    middleSection.data = lowResObject.data.copy()
    middleSection.name = "Middle Flange"
    context.collection.objects.link(middleSection)
    context.view_layer.objects.active = middleSection

    addSolidifyModifier(context, middleSection, flangeThickness)

    createBoolean(context, middleSection, cuboid, 'INTERSECT')
    applyModifiers(context, middleSection)

    # Attach middle flange to cone flange
    createBoolean(context, duplicated, middleSection, 'UNION')
    applyModifiers(context, duplicated)
    
    # Delete middle flange and cone flange
    bpy.data.objects.remove(bpy.data.objects["Middle Flange"], do_unlink=True)
    bpy.data.objects.remove(bpy.data.objects["Cone Flange"], do_unlink=True)
    
    ## Create inner shell to be subtracted from main shell
    innerShell = lowResObject.copy()
    innerShell.data = lowResObject.data.copy()
    innerShell.name = "Shell"
    context.collection.objects.link(innerShell)
    
    addSolidifyModifier(context, innerShell, gloveMoldThickness)

    innerCone = cone.copy()
    innerCone.data = cone.data.copy()
    innerCone.name = "Cone Inner"
    innerCone.location.z = cone.location.z + shellThickness
    context.collection.objects.link(innerCone)
    
    createBoolean(context, innerShell, innerCone, 'UNION')
    applyModifiers(context, innerShell)
    
    # Delete inner cone
    bpy.data.objects.remove(bpy.data.objects["Cone Inner"], do_unlink=True)
    bpy.data.objects.remove(bpy.data.objects["Cone Shell"], do_unlink=True)
    
    # Subtract inner from outer shells
    createBoolean(context, duplicated, innerShell, 'DIFFERENCE', 'FAST')
    applyModifiers(context, innerShell)
    applyModifiers(context, duplicated)
    
    # Hide inner shell
    # TODO: Boolean from low res object to create a weight/volume estimate
    innerShell.hide_set(True)
    lowResObject.hide_set(True)

    # Make a cube to be used for floor boolean, 400mm dimension
    cube = makeCube(context, 1000, (0, 0, -499.9))
    createBoolean(context, duplicated, cube, 'DIFFERENCE')

    # Duplicated union mesh
    leftSide = duplicated.copy()
    leftSide.data = duplicated.data.copy()
    leftSide.name = "Shell 2"
    context.collection.objects.link(leftSide)

    # Make a cube to intersect on each side of mesh
    cube = makeCube(context, 600, (300, 0, 300))
    createBoolean(context, duplicated, cube, 'DIFFERENCE')

    cube = makeCube(context, 600, (-300, 0, 300))
    createBoolean(context, leftSide, cube, 'DIFFERENCE')
    
    # Apply modifiers to each side of mesh
    applyModifiers(context, duplicated)
    applyModifiers(context, leftSide)

# Define the operator class to create a cone
class CreateConeOperator(bpy.types.Operator):
    bl_idname = "object.create_cone"
    bl_label = "Create Cone"

    def check(self, context):
        # Enable the button only if an object is selected
        return len(bpy.context.selected_objects) != 0

    @classmethod
    def makeCone(self, context):
        originalObject = context.active_object
        eul = mathutils.Euler((math.radians(180), 0.0, 0.0), 'XYZ')
        coneRadius1 = originalObject.dimensions.x * 0.8
        bpy.ops.mesh.primitive_cone_add(vertices=64,radius1=coneRadius1,depth=coneRadius1 * 1.2,location=(0,0,originalObject.dimensions.z + (coneRadius1 * 1.75)),rotation=eul)
        cone = context.active_object
        cone.name = 'Cone Shell'
        for obj in bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = obj
        return;
    
    def execute(self, context):
        self.makeCone(context)
        return {'FINISHED'}

# Define the operator class to create a cube
class MakeGloveMold(bpy.types.Operator):
    bl_idname = "object.make_glove_mold"
    bl_label = "Create glove mold for selected object"
    
    def check(self, context):
        # Enable the button only if an object is selected
        return len(bpy.context.selected_objects) != 0 and "Cone Shell" in bpy.data.objects

    def execute(self, context):
        makeGloveMold(context)
        return {'FINISHED'}

# Define the panel class
class CreateGloveMold(bpy.types.Panel):
    bl_label = "Create Glove Mold Panel"
    bl_idname = "PT_CreateGloveMold"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("object.create_cone")
        col.enabled = len(bpy.context.selected_objects) != 0
        
        col.separator()
        col.prop(context.scene, "glove_mold_thickness")
        col.prop(context.scene, "shell_thickness")
        
        col1 = layout.column(align=True)
        col1.separator()
        col1.operator("object.make_glove_mold")
        col1.enabled = len(bpy.context.selected_objects) != 0 and "Cone Shell" in bpy.data.objects

# Register the classes
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