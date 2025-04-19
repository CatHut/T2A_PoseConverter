bl_info = {
    "name": "T2A PoseConverter",
    "author": "CatHut",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Tool Shelf > CatHut",
    "description": "Convert pose between T-pose and A-pose",
    "category": "Rigging",
}

import bpy

from .ui_panel import PoseToolPanel, PoseConverterProperties
from .ops_convert_pose import POSECONV_OT_ConvertPose, POSECONV_OT_SetRestPose
from .bone_finder import POSECONV_OT_DetectBones

classes = (
    PoseConverterProperties,
    PoseToolPanel,
    POSECONV_OT_ConvertPose,
    POSECONV_OT_SetRestPose,
    POSECONV_OT_DetectBones,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pose_converter_props = bpy.props.PointerProperty(type=PoseConverterProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.pose_converter_props

if __name__ == "__main__":
    register()
