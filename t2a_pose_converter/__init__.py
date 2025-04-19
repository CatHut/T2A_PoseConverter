# ==============================================================================
#  CatHut ‑ T2A PoseConverter
#  __init__.py  ―  アドオンエントリポイント
# ==============================================================================

bl_info = {
    "name": "T2A PoseConverter",
    "author": "CatHut",
    "version": (1, 0, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Tool Shelf > CatHut",
    "description": "Convert pose between T‑pose and A‑pose",
    "category": "Rigging",
}

import bpy
from bpy.app.handlers import persistent
from bpy.types import AddonPreferences

# -----------------------------------------------------------------------------
#  内部モジュールインポート
# -----------------------------------------------------------------------------
from .ui_panel import PoseToolPanel, PoseConverterProperties
from .ops_convert_pose import (
    POSECONV_OT_ConvertPose,
    POSECONV_OT_SetRestPose,
)
from .bone_finder import POSECONV_OT_DetectBones

# -----------------------------------------------------------------------------
#  AddonPreferences  ―  セッションを跨いで保持したい値
# -----------------------------------------------------------------------------
class PoseConverterPreferences(AddonPreferences):
    """T2A PoseConverter アドオン設定（ユーザー設定ファイルに保存）"""
    bl_idname = __name__  # モジュール名をそのまま指定

    shoulder_rotation_angle: bpy.props.FloatProperty(
        name="Default Shoulder Y Rotation",
        description="デフォルトの肩回転角（Y 軸／度）",
        default=0.0,
        min=-90.0,
        max=90.0,
    )
    upperarm_rotation_angle: bpy.props.FloatProperty(
        name="Default UpperArm Y Rotation",
        description="デフォルトの上腕回転角（Y 軸／度）",
        default=30.0,
        min=-90.0,
        max=90.0,
    )

    # UI — ユーザー設定 (編集 > プリファレンス > アドオン)
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="デフォルト回転角度")
        box.prop(self, "shoulder_rotation_angle")
        box.prop(self, "upperarm_rotation_angle")


# -----------------------------------------------------------------------------
#  load_post ハンドラ  ―  .blend 読込時にプリファレンスを Scene へ反映
# -----------------------------------------------------------------------------
@persistent
def _load_post_sync_pref_to_scene(_):
    prefs = bpy.context.preferences.addons[__name__].preferences
    for scene in bpy.data.scenes:
        props = scene.pose_converter_props
        props.shoulder_rotation_angle = prefs.shoulder_rotation_angle
        props.upperarm_rotation_angle = prefs.upperarm_rotation_angle

# -----------------------------------------------------------------------------
#  アドオン登録 / 解除
# -----------------------------------------------------------------------------
_classes = (
    PoseConverterPreferences,
    PoseConverterProperties,
    PoseToolPanel,
    POSECONV_OT_ConvertPose,
    POSECONV_OT_SetRestPose,
    POSECONV_OT_DetectBones,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)

    # Scene にツール用プロパティを追加
    bpy.types.Scene.pose_converter_props = bpy.props.PointerProperty(
        type=PoseConverterProperties
    )

    # ハンドラ追加（重複登録ガード）
    if _load_post_sync_pref_to_scene not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post_sync_pref_to_scene)


def unregister():
    # ハンドラ除去
    if _load_post_sync_pref_to_scene in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post_sync_pref_to_scene)

    # Scene プロパティ削除
    del bpy.types.Scene.pose_converter_props

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
