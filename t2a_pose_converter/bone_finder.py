import bpy
from bpy.types import Operator
from .utils import write_log

def find_bone_by_keywords(armature, keywords, debug=False):
    """
    指定されたキーワードに基づいてアーマチュア内のボーンを検索します
    
    Parameters:
        armature: アーマチュアオブジェクト
        keywords: 検索キーワードのリスト
        debug: デバッグ出力を有効にするかどうか
    
    Returns:
        見つかったボーン名または空文字列
    """
    if debug:
        write_log(f"Searching for bones with keywords: {keywords}")
        
    for bone in armature.pose.bones:
        name_lower = bone.name.lower()
        if debug:
            write_log(f"Checking bone: {bone.name}")
            
        for k in keywords:
            if k in name_lower:
                if debug:
                    write_log(f"Match found: {bone.name} contains {k}")
                return bone.name
                
    if debug:
        write_log(f"No bones found matching keywords: {keywords}")
    return ""

class POSECONV_OT_DetectBones(Operator):
    bl_idname = "poseconv.detect_bones"
    bl_label = "Detect Bones"
    bl_description = "Automatically detect shoulder and upper arm bones from known patterns"

    def execute(self, context):
        obj = context.object
        props = context.scene.pose_converter_props

        if not obj or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid Armature object.")
            write_log("Bone detection failed: No valid armature selected")
            return {'CANCELLED'}

        write_log("Starting bone detection...")
        arm = obj
        
        # 日本語の命名規則を含むキーワードセット
        props.shoulder_l = find_bone_by_keywords(arm, [
            "shoulder_l", "leftshoulder", "肩_l", "shoulder.l", "l_shoulder", 
            "shoulderl", "clavicle_l", "clavicle.l", "肩.l", "肩l", "左肩"
        ], debug=True)
        
        props.shoulder_r = find_bone_by_keywords(arm, [
            "shoulder_r", "rightshoulder", "肩_r", "shoulder.r", "r_shoulder", 
            "shoulderr", "clavicle_r", "clavicle.r", "肩.r", "肩r", "右肩"
        ], debug=True)
        
        props.upperarm_l = find_bone_by_keywords(arm, [
            "upperarm_l", "leftupperarm", "上腕_l", "upperarm.l", "l_upperarm", 
            "uppearml", "arm_l", "arm.l", "腕_l", "腕.l", "腕l", "左腕", "左上腕"
        ], debug=True)
        
        props.upperarm_r = find_bone_by_keywords(arm, [
            "upperarm_r", "rightupperarm", "上腕_r", "upperarm.r", "r_upperarm", 
            "upperarmr", "arm_r", "arm.r", "腕_r", "腕.r", "腕r", "右腕", "右上腕"
        ], debug=True)

        # ボーン検出結果をログに記録
        detection_result = {
            "shoulder_l": props.shoulder_l,
            "shoulder_r": props.shoulder_r,
            "upperarm_l": props.upperarm_l,
            "upperarm_r": props.upperarm_r
        }
        
        write_log(f"Bone detection results: {detection_result}")
        
        detected_count = sum(1 for v in detection_result.values() if v)
        
        if detected_count == 0:
            self.report({'WARNING'}, "No bones detected. Please manually specify bone names.")
            write_log("Bone detection failed: No bones matched the known patterns")
        elif detected_count < 4:
            self.report({'INFO'}, f"Partial detection: {detected_count}/4 bones found. Please check or specify the remaining bones.")
            write_log(f"Partial bone detection: {detected_count}/4 bones detected")
        else:
            self.report({'INFO'}, "Bone detection complete: All bones successfully detected!")
            write_log("Bone detection complete: All bones successfully detected")
            
        return {'FINISHED'}

def register():
    bpy.utils.register_class(POSECONV_OT_DetectBones)

def unregister():
    bpy.utils.unregister_class(POSECONV_OT_DetectBones)