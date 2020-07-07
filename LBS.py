import bpy
from bpy import data as D
from bpy import context as C
from mathutils import *
from math import *

# For each bone, it's vertex weights
class Bone:
    def __init__(self, obj):
        self.w = []
        # Transform from skin to bones
        self.T_sINb = Matrix()
        self.T_bINw = Matrix()
        # Blender object held by this bone DS
        self.obj = obj
        

class LBS:
    def __init__(self):
        self.skin = D.objects['Skin']
        self.bones = [Bone(D.objects['Bone1']), Bone(D.objects['Bone2']), Bone(D.objects['Bone3'])]
        self.joints = [D.objects['j1'], D.objects['j2'], D.objects['j3']]  
        # Sum total which is used to normalize bone weights
        self._net_w = []
        # Original Position of Vertices in the Mesh
        self._P_vINs = []
        
    def is_point_inside(self, vtx_pos, obj, bound_type='BOX', scale=Vector((1.0, 1.0, 1.0)) ):
        if bound_type == 'BOX':
            dims = Vector((1, 1, 1))
            dims.x = obj.dimensions.x * scale.x
            dims.y = obj.dimensions.y * scale.y
            dims.z = obj.dimensions.z * scale.z
            if abs(vtx_pos.x) <= dims.x/2.0 and abs(vtx_pos.y) <= dims.y/2.0 and abs(vtx_pos.z) <= dims.z/2.0:
                print('Vtx Pos :', vtx_pos.x, vtx_pos.y, vtx_pos.z)
                print('Dim Len: ', dims.x, dims.y, dims.z)
                print('----')
                return True
            else:
                return False
                                  
    def print_weights(self):
        for i in range(len(self.bones)):
            b = self.bones[i]
            print('Bone (', i, '):')
            total_w = len(b.w)
            zero_w = 0
            positive_w = 0
            for j in range(len(b.w)):
                 print('\tWeight [', j, '] = ', b.w[j])
                 if b.w[j] <= 0.001:
                     zero_w = zero_w + 1
                 else:
                     positive_w = positive_w + 1
            print('Total Weights: ', total_w, ' Zeros: ', zero_w, ' Positive: ', positive_w)
            print('*******\n*******')
               
    def generate_bind_mats(self):
        T_sINw = self.skin.matrix_world.copy()
        for bone in self.bones:
            T_wINb = bone.obj.matrix_world.inverted()
            T_sINb = T_wINb @ T_sINw
            bone.T_sINb = T_sINb
            bone.T_bINw = bone.obj.matrix_world.copy()         
        
    def generate_weights(self):
        
        # Record the original local position of vertices
        self._P_vINs = [Vector((0,0,0))]*len(self.skin.data.vertices)
        for i in range(len(self.skin.data.vertices)):
            self._P_vINs[i] = self.skin.data.vertices[i].co.copy()
            
        self._net_w = [0.0]*len(self.skin.data.vertices)
        for bone in self.bones:
            bone.w = [0.0]*len(self.skin.data.vertices)   
            for i in range(len(bone.w)):
                P_vINs = self.skin.data.vertices[i].co
                P_vINb = bone.T_sINb @ P_vINs
                inside = self.is_point_inside(P_vINb, bone.obj, 'BOX', Vector((1.8, 1.3, 1.8)))         
                if inside:
                    # Define a minimum distance metric.
                    if P_vINb.length < 0.001:
                        dist = 0.001
                    else:
                        dist = P_vINb.length
                    bone.w[i] = 1.0/dist
                    self._net_w[i] += 1.0/dist
                else:
                    bone.w[i] = 0.0
        
                    
        self.normalize_bone_weights()
            
    def normalize_bone_weights(self):
        for b in self.bones:
            for i in range(len(b.w)):
                b.w[i] = b.w[i] / self._net_w[i]
#                if b.w[i] <= 0.0001:
#                    # Do nothing
#                    pass
#                else:
#                    b.w[i] = b.w[i] / self._net_w[i]
#                    if b.w[i] < 0.999:
#                        b.w[i] = 1.0 - b.w[i]
        
        
    def update_skin(self):
        P_vINw = [Vector((0,0,0))]*len(self.skin.data.vertices)
        T_wINs = self.skin.matrix_world.inverted()
        
        for bone in self.bones:
            T_bINw = bone.obj.matrix_world.copy()
            T_wINb = T_bINw.inverted()
            T_sINw = self.skin.matrix_world.copy()
            T_sINb = T_wINb @ T_sINw
#            M = T_bINw @ T_sINb
            M = T_bINw @ bone.T_sINb
#            M = bone.T_bINw @ bone.T_sINb
#            M = bone.T_bINw.inverted() @ T_bINw @ bone.T_sINb
            
            for i in range(len(self.skin.data.vertices)):
#                P_vINs = self.skin.data.vertices[i].co
                P_vINs = self._P_vINs[i]
                P_vINw[i] = P_vINw[i] + bone.w[i] * (M @ P_vINs)
                
        for i in range(len(self.skin.data.vertices)):
            self.skin.data.vertices[i].co = T_wINs @ P_vINw[i]
            pass
        return 0.01
                
lbs = None
                
class GenerateBindMatsOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.lbs_generate_bind_mats"
    bl_label = "Gen Bind Mats + Bone Weights"

    def execute(self, context):
        global lbs
        if lbs is not None:
            del lbs
        lbs = LBS()
        lbs.generate_bind_mats()
        lbs.generate_weights()
        lbs.print_weights()
        return {'FINISHED'}
    
class UpdateSkinOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.lbs_update_skin_once"
    bl_label = "Update Skin Once"

    def execute(self, context):
        global lbs
        if lbs is not None:
            lbs.update_skin()
            print('Updating Skin Once')
        else:
            print('Click Gen Bind Mats + Bone Weights Btn First')
        return {'FINISHED'}
    
fn_handle = None
    
class StartUpdateSkinOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.lbs_start_update_skin"
    bl_label = "Start Skin Update (Continuous)"

    def execute(self, context):
        global lbs, fn_handle
        if lbs is not None:
            fn_handle = lbs.update_skin
            bpy.app.timers.register(fn_handle)
            print('Registered Skin Update Func to Timer')
        else:
            print('Click Gen Bind Mats + Bone Weights Btn First')
        return {'FINISHED'}
    
class StopUpdateSkinOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "scene.lbs_stop_update_skin"
    bl_label = "Stop Skin Update"

    def execute(self, context):
        global lbs, fn_handle
        if bpy.app.timers.is_registered(fn_handle):
            bpy.app.timers.unregister(fn_handle)
            print('Unregistered Skin Update Func')
        else:
            print('Function not registered. Nothing to do')
        return {'FINISHED'}


class LayoutDemoPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Layout Demo"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "LBS"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        # Create a simple row.
        layout.label(text="Generate Bind Mats and Bone Weights:")
        col = layout.column()
        col.operator("scene.lbs_generate_bind_mats")

        # Create a simple row.
        layout.label(text="Update only once:")
        col = layout.column()
        col.operator("scene.lbs_update_skin_once")

        # Create a simple row.
        layout.label(text="Continuous update:")
        col = layout.column()
        col.operator("scene.lbs_start_update_skin")
        
        # Create a simple row.
        layout.label(text="Stop continuous update:")
        col = layout.column()
        col.operator("scene.lbs_stop_update_skin")

def register():
    bpy.utils.register_class(LayoutDemoPanel) 
    bpy.utils.register_class(GenerateBindMatsOperator)
    bpy.utils.register_class(UpdateSkinOperator)
    bpy.utils.register_class(StartUpdateSkinOperator)
    bpy.utils.register_class(StopUpdateSkinOperator)


def unregister():
    bpy.utils.unregister_class(LayoutDemoPanel)
    bpy.utils.unregister_class(GenerateBindMatsOperator)
    bpy.utils.unregister_class(UpdateSkinOperator)
    bpy.utils.unregister_class(StartUpdateSkinOperator)
    bpy.utils.unregister_class(StopUpdateSkinOperator)


if __name__ == "__main__":
    register()
