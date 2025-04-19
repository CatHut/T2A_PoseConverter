import bpy
from bpy.props import PointerProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import Panel, PropertyGroup
from .utils import find_related_mesh_objects, write_log

# ────────────────────────────────────────────────────────────────
#  AddonPreferences と同期するための update コールバック
# ────────────────────────────────────────────────────────────────
ADDON_NAME = __package__.split('.')[0]  # "TA_PoseConverter"

def _sync_to_pref_shoulder(self, context):
    prefs = context.preferences.addons[ADDON_NAME].preferences
    prefs.shoulder_rotation_angle = self.shoulder_rotation_angle

def _sync_to_pref_upper(self, context):
    prefs = context.preferences.addons[ADDON_NAME].preferences
    prefs.upperarm_rotation_angle = self.upperarm_rotation_angle


class PoseConverterProperties(PropertyGroup):
    # プロパティ定義はそのまま
    conversion_mode: EnumProperty(
        name="Conversion Mode",
        description="Choose direction of pose conversion",
        items=[
            ('T_TO_A', "T → A", "Convert T-pose to A-pose"),
            ('A_TO_T', "A → T", "Convert A-pose to T-pose")
        ],
        default='A_TO_T'
    )

    shoulder_rotation_angle : FloatProperty(
        name = "Shoulder Y Rotation",
        description = "Rotation angle in degrees for shoulder bones",
        default = 0.0,
        min = -90.0,
        max = 90.0,
        update = _sync_to_pref_shoulder
    )

    upperarm_rotation_angle : FloatProperty(
        name = "UpperArm Y Rotation",
        description = "Rotation angle in degrees for upper arm bones",
        default = 30.0,
        min = -90.0,
        max = 90.0,
        update = _sync_to_pref_upper
    )

    shoulder_l: StringProperty(
        name="Shoulder L",
        description="Left shoulder bone"
    )
    
    shoulder_r: StringProperty(
        name="Shoulder R",
        description="Right shoulder bone"
    )
    
    upperarm_l: StringProperty(
        name="UpperArm L",
        description="Left upper arm bone"
    )
    
    upperarm_r: StringProperty(
        name="UpperArm R",
        description="Right upper arm bone"
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="デフォルトの回転角度")
        layout.prop(self, "shoulder_rotation_angle")
        layout.prop(self, "upperarm_rotation_angle")


class PoseToolPanel(Panel):
    bl_label = "T2A PoseConverter"
    bl_idname = "VIEW3D_PT_pose_converter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CatHut'

    def draw(self, context):
        layout = self.layout
        props = context.scene.pose_converter_props
        
        # アーマチュアオブジェクトの参照を取得
        armature = None
        if context.object and context.object.type == 'ARMATURE':
            armature = context.object
        
        # アーマチュア選択UI
        row = layout.row()
        row.label(text="Armature:")
        if armature:
            row.label(text=armature.name, icon='ARMATURE_DATA')
        else:
            row.label(text="No armature selected", icon='ERROR')
        
        # 関連メッシュの表示
        if armature:
            related_meshes = find_related_mesh_objects(armature)
            
            mesh_box = layout.box()
            mesh_box.label(text=f"Related Meshes ({len(related_meshes)})", icon='OUTLINER_OB_MESH')
            
            if related_meshes:
                mesh_col = mesh_box.column(align=True)
                for mesh in related_meshes:
                    mesh_row = mesh_col.row()
                    mesh_row.label(text=mesh.name, translate=False)
                    
                    # シェイプキーの有無を表示
                    has_shape_keys = mesh.data.shape_keys is not None and len(mesh.data.shape_keys.key_blocks) > 0
                    if has_shape_keys:
                        mesh_row.label(text="Has Shape Keys", icon='SHAPEKEY_DATA')
                    else:
                        mesh_row.label(text="No Shape Keys", icon='MESH_DATA')
            else:
                mesh_box.label(text="No meshes found with Armature modifier", icon='INFO')
        
        # 回転設定関連要素のボックス - ラベル変更
        pose_conversion_box = layout.box()
        pose_conversion_box.label(text="Pose Conversion", icon='DRIVER_ROTATIONAL_DIFFERENCE')
        
        # 変換モード設定
        pose_conversion_box.prop(props, "conversion_mode")
        
        # 回転角度設定
        pose_conversion_box.prop(props, "shoulder_rotation_angle")
        pose_conversion_box.prop(props, "upperarm_rotation_angle")
        
        # ボーン検出ボタン
        pose_conversion_box.operator("poseconv.detect_bones", text="Detect Bones", icon='ZOOM_SELECTED')
        
        # ボーンマッピング設定
        bone_col = pose_conversion_box.column()
        bone_col.label(text="Bone Mapping", icon='BONE_DATA')
        
        if armature:
            # prop_searchを使ってボーン選択UIを表示
            bone_col.prop_search(props, "shoulder_l", armature.pose, "bones", text="Shoulder L")
            bone_col.prop_search(props, "shoulder_r", armature.pose, "bones", text="Shoulder R")
            bone_col.prop_search(props, "upperarm_l", armature.pose, "bones", text="UpperArm L")
            bone_col.prop_search(props, "upperarm_r", armature.pose, "bones", text="UpperArm R")
        else:
            # アーマチュアが選択されていない場合は通常のプロパティを表示
            bone_col.prop(props, "shoulder_l")
            bone_col.prop(props, "shoulder_r")
            bone_col.prop(props, "upperarm_l")
            bone_col.prop(props, "upperarm_r")
            bone_col.label(text="Select an armature for bone picking", icon='INFO')
        
        # 変換実行ボタン - Pose Conversionボックス内に配置
        convert_row = pose_conversion_box.row()
        convert_row.scale_y = 1.5  # ボタンサイズを大きく
        convert_row.operator("poseconv.convert_pose", text="Convert Pose", icon='POSE_HLT')
        
        # Only Set Rest Pose ボックスを作成
        rest_box = layout.box()
        rest_box.label(text="Set Rest Pose Only", icon='ARMATURE_DATA')
        rest_row = rest_box.row()
        rest_row.scale_y = 1.2
        rest_row.operator("poseconv.set_rest_pose", text="Set as Rest Pose", icon='ARMATURE_DATA')
        rest_box.label(text="Set current pose as rest pose without conversion", icon='INFO')


def register():
    bpy.utils.register_class(PoseConverterProperties)
    bpy.utils.register_class(PoseToolPanel)

def unregister():
    bpy.utils.unregister_class(PoseToolPanel)
    bpy.utils.unregister_class(PoseConverterProperties)