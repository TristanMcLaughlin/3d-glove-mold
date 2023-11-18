import bpy
import mathutils
import math

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

def makeCube(context, size, location, name):
    bpy.ops.mesh.primitive_cube_add(size=size,location=location)
    cube = context.active_object
    cube.name = name;
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
    
    #Remesh
    remeshMod = lowResObject.modifiers.new("Remesh", "REMESH")
    remeshMod.voxel_size = 1

    # Create a low res clone for working on
    # Decimate to 1k polys if over 1k polys
    decimateRatio = min(5000 / len(originalObject.data.polygons), 1)
    decimateMod = lowResObject.modifiers.new("Decimate", "DECIMATE")
    decimateMod.ratio = 0.1

    # Smooth mesh
    smoothMod = lowResObject.modifiers.new("Smooth", "SMOOTH")
    smoothMod.factor = 2
    smoothMod.iterations = 5

    applyModifiers(context, lowResObject)

    cone = bpy.data.objects["Cone Shell"]

    # Duplicate object for working with
    context.view_layer.objects.active = lowResObject
    innerShell = context.active_object.copy()
    innerShell.data = context.active_object.data.copy()
    innerShell.name = "Inner Shell"
    context.collection.objects.link(innerShell)
    context.view_layer.objects.active = innerShell

    # Make inner shell
    addSolidifyModifier(context, innerShell, gloveMoldThickness)
    
    smoothMod = innerShell.modifiers.new("Smooth", "SMOOTH")
    smoothMod.factor = 2
    smoothMod.iterations = 5
    
    applyModifiers(context, innerShell)
    
    # Duplicate object into outer shell and add solidify modifier
    outerShell = innerShell.copy()
    outerShell.data = innerShell.data.copy()
    outerShell.name = "Outer Shell"
    context.collection.objects.link(outerShell)
    
    addSolidifyModifier(context, outerShell, shellThickness)
    applyModifiers(context, outerShell)
    
    # Duplicate outerShell into the middle flange section
    middleSection = outerShell.copy()
    middleSection.data = outerShell.data.copy()
    middleSection.name = "Middle Flange"
    context.collection.objects.link(middleSection)
    context.view_layer.objects.active = middleSection

    addSolidifyModifier(context, middleSection, 5)

    # Attach cone to outerShell
    createBoolean(context, outerShell, cone, 'UNION')
    
    # Create inside cone
    innerCone = cone.copy()
    innerCone.data = cone.data.copy()
    innerCone.name = "Cone Inner"
    innerCone.location.z = cone.location.z + shellThickness
    context.collection.objects.link(innerCone)
    
    createBoolean(context, innerShell, innerCone, 'UNION')
    applyModifiers(context, innerShell)

    # Add the outer cone flange
    coneFlange = cone.copy()
    coneFlange.data = cone.data.copy()
    coneFlange.name = "Cone Flange"
    coneFlange.location.z = coneFlange.location.z - 5
    context.collection.objects.link(coneFlange)

    addSolidifyModifier(context, coneFlange, gloveMoldThickness)
    applyModifiers(context, coneFlange)
    cuboid = makeCube(context, 4, (0, 0, 0), 'Mid Cube')
    bpy.context.object.scale.yz = 500, 500
    
    createBoolean(context, middleSection, cuboid, 'INTERSECT')
    applyModifiers(context, middleSection)

    createBoolean(context, coneFlange, cuboid, 'INTERSECT')
    applyModifiers(context, coneFlange)

    # Attach middle flange to ouer shell shape
    createBoolean(context, outerShell, coneFlange, 'UNION', 'FAST')
    applyModifiers(context, outerShell)

    createBoolean(context, outerShell, middleSection, 'UNION', 'FAST')
    applyModifiers(context, outerShell)

    # Delete middle flange and cone flange
    bpy.data.objects.remove(bpy.data.objects["Middle Flange"], do_unlink=True)
    bpy.data.objects.remove(bpy.data.objects["Cone Flange"], do_unlink=True)

    # Delete cone
    bpy.data.objects.remove(bpy.data.objects["Cone Inner"], do_unlink=True)
    bpy.data.objects.remove(bpy.data.objects["Cone Shell"], do_unlink=True)
    
    # Delete objects that wont be used from here on out
    bpy.data.objects.remove(bpy.data.objects["Low Res Copy"], do_unlink=True)
    bpy.data.objects.remove(bpy.data.objects["Mid Cube"], do_unlink=True)

    # Subtract inner from outer shells
    createBoolean(context, outerShell, innerShell, 'DIFFERENCE')
    applyModifiers(context, outerShell)
    
    # Remove Inner Shell
    bpy.data.objects.remove(bpy.data.objects["Inner Shell"], do_unlink=True)

    # Make a cube to be used for floor boolean, 400mm dimension
    cube = makeCube(context, 1000, (0, 0, -499.9), 'Floor Cube')
    createBoolean(context, outerShell, cube, 'DIFFERENCE')
    applyModifiers(context, outerShell)
    
    bpy.data.objects.remove(bpy.data.objects["Floor Cube"], do_unlink=True)
    
    # Duplicated union mesh
    rightSide = outerShell.copy()
    rightSide.data = outerShell.data.copy()
    rightSide.name = "Right Side"
    context.collection.objects.link(rightSide)
    
    # Duplicated union mesh
    leftSide = outerShell.copy()
    leftSide.data = outerShell.data.copy()
    leftSide.name = "Left Side"
    context.collection.objects.link(leftSide)
    
    bpy.data.objects.remove(bpy.data.objects["Outer Shell"], do_unlink=True)
    
    cube = makeCube(context, 600, (-300, 0, 300), 'Splitter Cube')

    # Make a cube to intersect on each side of mesh
    createBoolean(context, rightSide, cube, 'INTERSECT')
    applyModifiers(context, rightSide)

    createBoolean(context, leftSide, cube, 'DIFFERENCE')
    applyModifiers(context, leftSide)
    
    bpy.data.objects.remove(bpy.data.objects["Splitter Cube"], do_unlink=True)

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
        bpy.ops.mesh.primitive_cone_add(vertices=64,radius1=coneRadius1,depth=coneRadius1 * 1.2,location=(0,0,originalObject.dimensions.z + coneRadius1),rotation=eul)
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
