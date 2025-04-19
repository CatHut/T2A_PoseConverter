import bpy
from bpy.types import Operator
from math import radians
import mathutils
from .utils import (
    get_shape_key_values,
    restore_shape_key_values,
    apply_shape_key_as_basis,
    remove_shape_key,
    write_log,
    find_related_mesh_objects,
    apply_new_armature_modifier
)

def rotate_bone_y_global(pbone, angle_deg, axis='Y'):
    """ボーン頭を支点にグローバル軸周りにボーンを回転させる関数
    
    Parameters:
        pbone: 回転させるポーズボーン
        angle_deg: 回転角度（度数法）
        axis: 回転軸 ('X', 'Y', 'Z'のいずれか)
    """
    # 角度をラジアンに変換
    angle_rad = radians(angle_deg)
    
    # アーマチュアオブジェクトを取得
    armature = pbone.id_data
    
    # グローバル軸での回転行列を作成
    rot_matrix = mathutils.Matrix.Rotation(angle_rad, 4, axis)
    
    # 現在のワールド行列とボーン頭のワールド座標を取得
    world_mat = armature.matrix_world @ pbone.matrix
    head_world = armature.matrix_world @ pbone.head  # 回転の支点
    
    # 支点を原点に移動 → 回転 → 元に戻す
    translate_to_origin = mathutils.Matrix.Translation(-head_world)
    translate_back = mathutils.Matrix.Translation(head_world)
    new_world_mat = translate_back @ rot_matrix @ translate_to_origin @ world_mat
    
    # ローカル座標に戻して適用
    pbone.matrix = armature.matrix_world.inverted() @ new_world_mat
    
    # デバッグログを追加
    write_log(f"Rotated bone {pbone.name} by {angle_deg} degrees around global {axis} axis")
    write_log(f"  Original matrix: {world_mat}")
    write_log(f"  New matrix: {new_world_mat}")


def apply_as_rest_pose(armature_obj):
    """現在のポーズをレストポーズとして適用する関数"""
    # 元のモードを保存
    original_mode = bpy.context.mode
    
    # アーマチュアをアクティブにする
    bpy.context.view_layer.objects.active = armature_obj
    
    # オブジェクトモードに切り替え
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # ポーズモードに切り替え
    bpy.ops.object.mode_set(mode='POSE')
    
    # 現在のポーズをレストポーズとして適用
    bpy.ops.pose.armature_apply()
    
    # オブジェクトモードに戻す
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 元のモードに戻す（ポーズモードだった場合）
    if original_mode == 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    
    write_log("Applied current pose as rest pose")

def rotate_bones_for_pose_conversion(arm_obj, bone_mapping, shoulder_angle, upperarm_angle):
    """ボーンの回転処理を行う関数
    
    Parameters:
        arm_obj: アーマチュアオブジェクト
        bone_mapping: 左右のボーン名マッピング辞書
        shoulder_angle: 肩ボーンの回転角度
        upperarm_angle: 上腕ボーンの回転角度
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        write_log("Rotating bones...")
        
        # 左側のボーンの回転処理（角度をそのまま使用）
        for bone_type in ["shoulder", "upperarm"]:
            bone_name = bone_mapping.get(f"{bone_type}_l", "")
            if bone_name and bone_name in arm_obj.pose.bones:
                write_log(f"Processing left {bone_type} bone: {bone_name}")
                bone = arm_obj.pose.bones[bone_name]
                
                # 回転前の状態をログ出力
                if bone.rotation_mode == 'QUATERNION':
                    write_log(f"  Before rotation - quaternion: {bone.rotation_quaternion}")
                else:
                    write_log(f"  Before rotation - euler: {bone.rotation_euler}")
                
                # 回転実行（左側は角度をそのまま使用）
                angle = shoulder_angle if bone_type == "shoulder" else upperarm_angle
                rotate_bone_y_global(bone, angle)
                
                # 回転後の状態をログ出力
                if bone.rotation_mode == 'QUATERNION':
                    write_log(f"  After rotation - quaternion: {bone.rotation_quaternion}")
                else:
                    write_log(f"  After rotation - euler: {bone.rotation_euler}")
        
        # 右側のボーンの回転処理（角度を反転）
        for bone_type in ["shoulder", "upperarm"]:
            bone_name = bone_mapping.get(f"{bone_type}_r", "")
            if bone_name and bone_name in arm_obj.pose.bones:
                write_log(f"Processing right {bone_type} bone: {bone_name}")
                bone = arm_obj.pose.bones[bone_name]
                
                # 回転前の状態をログ出力
                if bone.rotation_mode == 'QUATERNION':
                    write_log(f"  Before rotation - quaternion: {bone.rotation_quaternion}")
                else:
                    write_log(f"  Before rotation - euler: {bone.rotation_euler}")
                
                # 回転実行（右側は角度を反転）
                angle = shoulder_angle if bone_type == "shoulder" else upperarm_angle
                rotate_bone_y_global(bone, -angle)  # 右側は角度を反転
                
                # 回転後の状態をログ出力
                if bone.rotation_mode == 'QUATERNION':
                    write_log(f"  After rotation - quaternion: {bone.rotation_quaternion}")
                else:
                    write_log(f"  After rotation - euler: {bone.rotation_euler}")
        
        # ビューレイヤーの更新（重要）
        bpy.context.view_layer.update()
        write_log("View layer updated after bone rotation")
        return True
        
    except Exception as e:
        write_log(f"Error during bone rotation: {e}")
        return False

def save_mesh_as_shape_key(arm_obj, mesh_obj, report_fn):
    """メッシュの現在の変形をシェイプキーとして保存する（レストポーズ適用前の処理）
    
    Parameters:
        arm_obj: アーマチュアオブジェクト
        mesh_obj: メッシュオブジェクト
        report_fn: レポート関数
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        write_log(f"Saving mesh '{mesh_obj.name}' as shape key...")

        # オブジェクトモードに切り替え
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # メッシュオブジェクトをアクティブに
        bpy.context.view_layer.objects.active = mesh_obj
        mesh_obj.select_set(True)
        
        # アーマチュアモディファイアを探す
        arm_modifier = None
        for mod in mesh_obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object == arm_obj:
                arm_modifier = mod
                break
        
        if not arm_modifier:
            # アーマチュアモディファイアがない場合は作成
            arm_modifier = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
            arm_modifier.object = arm_obj
            write_log(f"Created new armature modifier for mesh '{mesh_obj.name}'")
        
        # 「シェイプキーとして保存」を実行
        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=True, modifier=arm_modifier.name)
        write_log(f"Saved current deformation as shape key for mesh '{mesh_obj.name}'")
        
        # 作成されたシェイプキーの名前を「CatHutBasicPose」に変更
        # 新しいシェイプキーは通常、最後に追加される
        if mesh_obj.data.shape_keys and len(mesh_obj.data.shape_keys.key_blocks) > 0:
            new_shape_key = mesh_obj.data.shape_keys.key_blocks[-1]
            original_shape_key_name = new_shape_key.name  # あとで使用するために保存
            new_shape_key.name = "CatHutBasicPose"
            write_log(f"Renamed shape key from '{original_shape_key_name}' to 'CatHutBasicPose' for mesh '{mesh_obj.name}'")
            return True
        else:
            report_fn({'WARNING'}, f"Failed to create shape key from armature modifier for mesh '{mesh_obj.name}'")
            write_log(f"Failed to create shape key from armature modifier for mesh '{mesh_obj.name}'")
            return False
            
    except Exception as e:
        write_log(f"Error during saving mesh as shape key for mesh '{mesh_obj.name}': {e}")
        report_fn({'ERROR'}, f"Failed to save mesh as shape key: {e}")
        return False

def process_shape_keys_after_rest_pose(mesh_obj, report_fn):
    """レストポーズ適用後のシェイプキー処理
    
    Parameters:
        mesh_obj: メッシュオブジェクト
        report_fn: レポート関数
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        write_log(f"Processing shape keys after rest pose for mesh '{mesh_obj.name}'...")
        
        # メッシュオブジェクトをアクティブに
        bpy.context.view_layer.objects.active = mesh_obj
        mesh_obj.select_set(True)
        
        # シェイプキーがあるか確認
        if not mesh_obj.data.shape_keys:
            report_fn({'WARNING'}, f"No shape keys found for processing in mesh '{mesh_obj.name}'")
            write_log(f"No shape keys found for processing in mesh '{mesh_obj.name}'")
            return False
        
        # 'CatHutBasicPose'シェイプキーと'ベース'シェイプキーを取得
        base_change_key = mesh_obj.data.shape_keys.key_blocks.get('CatHutBasicPose')
        if not base_change_key:
            report_fn({'WARNING'}, f"Could not find 'CatHutBasicPose' shape key in mesh '{mesh_obj.name}'")
            write_log(f"Could not find 'CatHutBasicPose' shape key in mesh '{mesh_obj.name}'")
            return False
        
        # 通常、最初のシェイプキーがBasis
        basis_key = mesh_obj.data.shape_keys.key_blocks[0]
        basis_key_name = basis_key.name  # 元のベース名を保存
        
        # CatHutBasicPoseを値1.0に設定
        base_change_key.value = 1.0
        
        # シェイプキーのリスト作成（Basisとbase_change_key以外）
        shape_keys_list = [
            key for key in mesh_obj.data.shape_keys.key_blocks 
            if key != base_change_key and key != basis_key
        ]
        
        write_log(f"Found {len(shape_keys_list)} shape keys to process in mesh '{mesh_obj.name}'")
        
        # 各シェイプキーを処理
        for shape_key in list(shape_keys_list):  # リストのコピーでループ
            # 元々のシェイプキーの値を保存
            original_name = shape_key.name
            original_value = shape_key.value
            write_log(f"Processing shape key: {original_name} in mesh '{mesh_obj.name}'")
            
            # 処理対象のシェイプキーを1.0に
            shape_key.value = 1.0
            
            # 現在の混合形状で一時キーを作成
            mesh_obj.shape_key_add(name="CatHutTemp", from_mix=True)
            temp_key = mesh_obj.data.shape_keys.key_blocks["CatHutTemp"]
            
            # 元のシェイプキーのインデックスを取得して削除
            idx = mesh_obj.data.shape_keys.key_blocks.find(original_name)
            if idx != -1:
                mesh_obj.active_shape_key_index = idx
                bpy.ops.object.shape_key_remove()
            
            # 一時キーを元の名前にリネームし、値を復元
            temp_key.name = original_name
            temp_key.value = original_value
            
            write_log(f"Processed shape key: {original_name} in mesh '{mesh_obj.name}'")
        
        # すべてのシェイプキーをゼロにリセット
        for k in mesh_obj.data.shape_keys.key_blocks:
            k.value = 0.0
        
        # 元のシェイプキーのベースを削除し、CatHutBasicPoseをベースとする
        # CatHutBasicPoseを値1.0に設定
        base_change_key.value = 1.0
        
        # CatHutBasicPoseを最上位に移動
        catbasis_idx = mesh_obj.data.shape_keys.key_blocks.find('CatHutBasicPose')
        mesh_obj.active_shape_key_index = catbasis_idx
        bpy.ops.object.shape_key_move(type='TOP')
        
        # 元のBasisを削除
        basis_idx = mesh_obj.data.shape_keys.key_blocks.find(basis_key_name)
        if basis_idx != -1:
            mesh_obj.active_shape_key_index = basis_idx
            bpy.ops.object.shape_key_remove()
        
        # CatHutBasicPoseを元のベース名にリネーム
        mesh_obj.data.shape_keys.key_blocks[0].name = basis_key_name
        write_log(f"Renamed CatHutBasicPose to {basis_key_name} and set as basis for mesh '{mesh_obj.name}'")
        
        return True
        
    except Exception as e:
        write_log(f"Error during shape key processing after rest pose for mesh '{mesh_obj.name}': {e}")
        report_fn({'ERROR'}, f"Shape key processing after rest pose failed: {e}")
        return False

def process_without_shape_keys(arm_obj, mesh_obj, report_fn):
    """シェイプキーがない場合の処理
    
    Parameters:
        arm_obj: アーマチュアオブジェクト
        mesh_obj: メッシュオブジェクト
        report_fn: レポート関数
    
    Returns:
        bool: 成功したかどうか
    """
    try:
        write_log(f"Processing mesh '{mesh_obj.name}' without shape keys...")
        
        # オブジェクトモードに切り替え
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # メッシュオブジェクトをアクティブに
        bpy.context.view_layer.objects.active = mesh_obj
        mesh_obj.select_set(True)
        arm_obj.select_set(False)
        
        # 重要: メッシュデータがsingle-userかチェックして、そうでなければsingle-userに変換
        if mesh_obj.data.users > 1:
            write_log(f"Making mesh data single-user for '{mesh_obj.name}' (current users: {mesh_obj.data.users})")
            # オブジェクトデータをsingle-userにする
            tempname = mesh_obj.data.name
            mesh_obj.data = mesh_obj.data.copy()
            mesh_obj.data.name = tempname
            write_log(f"Mesh data for '{mesh_obj.name}' is now single-user")
        
        # 現在のアーマチュアモディファイアを複製して適用
        write_log(f"Adding and applying new armature modifier to mesh '{mesh_obj.name}'...")
        if not apply_new_armature_modifier(mesh_obj, arm_obj, report_fn):
            report_fn({'ERROR'}, f"Failed to apply armature modifier to mesh '{mesh_obj.name}'")
            return False
        
        write_log(f"Successfully processed mesh '{mesh_obj.name}' without shape keys")
        return True
        
    except Exception as e:
        write_log(f"Error during processing mesh '{mesh_obj.name}' without shape keys: {e}")
        report_fn({'ERROR'}, f"Process failed for mesh '{mesh_obj.name}': {e}")
        return False

class POSECONV_OT_ConvertPose(Operator):
    bl_idname = "poseconv.convert_pose"
    bl_label = "Convert Pose (Safe for Shape Keys)"
    bl_description = "Convert T/A pose and rebuild shape key Basis if necessary"

    def execute(self, context):
        write_log("Starting pose conversion...")
        
        # アーマチュアオブジェクトの取得
        arm_obj = context.object
        props = context.scene.pose_converter_props

        # アーマチュアの検証
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid Armature object.")
            write_log("Pose conversion failed: No valid armature selected")
            return {'CANCELLED'}

        # 関連メッシュオブジェクトの検索
        related_meshes = find_related_mesh_objects(arm_obj)
        if not related_meshes:
            self.report({'WARNING'}, "No meshes found with Armature modifier targeting the selected armature.")
            write_log("Pose conversion failed: No related meshes found")
            return {'CANCELLED'}

        # ボーン名の検証と処理用マッピングの作成
        bone_mapping = {
            "shoulder_l": props.shoulder_l,
            "shoulder_r": props.shoulder_r,
            "upperarm_l": props.upperarm_l,
            "upperarm_r": props.upperarm_r
        }
        
        # ボーン検証
        valid_bones = [
            name for name in bone_mapping.values() 
            if name and name in arm_obj.pose.bones
        ]
        
        if not valid_bones:
            self.report({'WARNING'}, "No valid bones specified. Please run 'Detect Bones' first or manually specify bones.")
            write_log("Pose conversion failed: No valid bones specified")
            return {'CANCELLED'}
        
        # 変換モードと回転角度の取得
        shoulder_angle = props.shoulder_rotation_angle
        upperarm_angle = props.upperarm_rotation_angle
        
        if props.conversion_mode == 'A_TO_T':
            shoulder_angle = -shoulder_angle  # A→T変換の場合は角度を反転
            upperarm_angle = -upperarm_angle  # A→T変換の場合は角度を反転
        
        write_log(f"Conversion mode: {props.conversion_mode}")
        write_log(f"Shoulder rotation angle: {shoulder_angle}")
        write_log(f"UpperArm rotation angle: {upperarm_angle}")
        write_log(f"Valid bones: {valid_bones}")
        write_log(f"Processing {len(related_meshes)} related meshes")

        try:
            # 1. ポーズモードに切り替え
            bpy.ops.object.mode_set(mode='POSE')
            write_log("Switched to POSE mode")
            
            # 2. 各ボーンの回転処理
            if not rotate_bones_for_pose_conversion(arm_obj, bone_mapping, shoulder_angle, upperarm_angle):
                self.report({'ERROR'}, "Bone rotation failed.")
                return {'CANCELLED'}
            
            # シェイプキーを持つメッシュとシェイプキーを持たないメッシュを分類
            meshes_with_shape_keys = []
            meshes_without_shape_keys = []
            
            for mesh_obj in related_meshes:
                has_shape_keys = mesh_obj.data.shape_keys is not None and len(mesh_obj.data.shape_keys.key_blocks) > 0
                if has_shape_keys:
                    meshes_with_shape_keys.append(mesh_obj)
                else:
                    meshes_without_shape_keys.append(mesh_obj)
            
            write_log(f"Found {len(meshes_with_shape_keys)} meshes with shape keys")
            write_log(f"Found {len(meshes_without_shape_keys)} meshes without shape keys")
            
            # ステップ1: 全メッシュに対して現在の変形を保存（シェイプキーあり）
            successful_shape_key_saves = 0
            for mesh_obj in meshes_with_shape_keys:
                if save_mesh_as_shape_key(arm_obj, mesh_obj, self.report):
                    successful_shape_key_saves += 1
                else:
                    self.report({'WARNING'}, f"Failed to save shape key for mesh '{mesh_obj.name}'")
            
            # ステップ2: シェイプキーのないメッシュを処理
            successful_no_shape_keys = 0
            for mesh_obj in meshes_without_shape_keys:
                if process_without_shape_keys(arm_obj, mesh_obj, self.report):
                    successful_no_shape_keys += 1
                else:
                    self.report({'WARNING'}, f"Failed to process mesh '{mesh_obj.name}' without shape keys")
            
            # ステップ3: レストポーズを適用（すべてのメッシュの処理後に1回だけ実行）
            write_log("All meshes pre-processed, applying current pose as rest pose...")
            bpy.context.view_layer.objects.active = arm_obj
            arm_obj.select_set(True)
            for mesh_obj in related_meshes:
                mesh_obj.select_set(False)
            
            apply_as_rest_pose(arm_obj)
            
            # ステップ4: 各シェイプキーを処理（シェイプキーあり）
            successful_shape_key_processing = 0
            for mesh_obj in meshes_with_shape_keys:
                if process_shape_keys_after_rest_pose(mesh_obj, self.report):
                    successful_shape_key_processing += 1
                else:
                    self.report({'WARNING'}, f"Failed to process shape keys after rest pose for mesh '{mesh_obj.name}'")
            
            # オブジェクトモードに戻す
            bpy.ops.object.mode_set(mode='OBJECT')
            write_log("Switched back to OBJECT mode")
            
            # 最終更新を確実に反映
            bpy.context.view_layer.update()
            write_log("Final view layer update performed")
            
            # 処理結果をレポート
            total_success = successful_shape_key_processing + successful_no_shape_keys
            total_meshes = len(related_meshes)
            
            if total_success < total_meshes:
                self.report({'WARNING'}, 
                    f"Pose conversion completed with issues: {total_success}/{total_meshes} meshes processed successfully.")
            else:
                self.report({'INFO'}, 
                    f"Pose conversion ({props.conversion_mode}) completed: All {total_meshes} meshes processed successfully.")

        except Exception as e:
            self.report({'ERROR'}, f"Pose conversion failed: {e}")
            write_log(f"ERROR: Pose conversion failed: {e}")
            return {'CANCELLED'}

        write_log("Pose conversion completed")
        return {'FINISHED'}
    
class POSECONV_OT_SetRestPose(Operator):
    bl_idname = "poseconv.set_rest_pose"
    bl_label = "Set Current as Rest Pose"
    bl_description = "Set current pose as rest pose and update meshes"

    def execute(self, context):
        write_log("Starting set rest pose operation...")
        
        # アーマチュアオブジェクトの取得
        arm_obj = context.object
        
        # アーマチュアの検証
        if not arm_obj or arm_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Please select a valid Armature object.")
            write_log("Set rest pose failed: No valid armature selected")
            return {'CANCELLED'}

        # 関連メッシュオブジェクトの検索
        related_meshes = find_related_mesh_objects(arm_obj)
        if not related_meshes:
            self.report({'WARNING'}, "No meshes found with Armature modifier targeting the selected armature.")
            write_log("Set rest pose failed: No related meshes found")
            return {'CANCELLED'}

        try:
            # シェイプキーを持つメッシュとシェイプキーを持たないメッシュを分類
            meshes_with_shape_keys = []
            meshes_without_shape_keys = []
            
            for mesh_obj in related_meshes:
                has_shape_keys = mesh_obj.data.shape_keys is not None and len(mesh_obj.data.shape_keys.key_blocks) > 0
                if has_shape_keys:
                    meshes_with_shape_keys.append(mesh_obj)
                else:
                    meshes_without_shape_keys.append(mesh_obj)
            
            write_log(f"Found {len(meshes_with_shape_keys)} meshes with shape keys")
            write_log(f"Found {len(meshes_without_shape_keys)} meshes without shape keys")
            
            # ステップ1: 全メッシュに対して現在の変形を保存（シェイプキーあり）
            successful_shape_key_saves = 0
            for mesh_obj in meshes_with_shape_keys:
                if save_mesh_as_shape_key(arm_obj, mesh_obj, self.report):
                    successful_shape_key_saves += 1
                else:
                    self.report({'WARNING'}, f"Failed to save shape key for mesh '{mesh_obj.name}'")
            
            # ステップ2: シェイプキーのないメッシュを処理
            successful_no_shape_keys = 0
            for mesh_obj in meshes_without_shape_keys:
                if process_without_shape_keys(arm_obj, mesh_obj, self.report):
                    successful_no_shape_keys += 1
                else:
                    self.report({'WARNING'}, f"Failed to process mesh '{mesh_obj.name}' without shape keys")
            
            # ステップ3: レストポーズを適用（すべてのメッシュの処理後に1回だけ実行）
            write_log("All meshes pre-processed, applying current pose as rest pose...")
            bpy.context.view_layer.objects.active = arm_obj
            arm_obj.select_set(True)
            for mesh_obj in related_meshes:
                mesh_obj.select_set(False)
            
            apply_as_rest_pose(arm_obj)
            
            # ステップ4: 各シェイプキーを処理（シェイプキーあり）
            successful_shape_key_processing = 0
            for mesh_obj in meshes_with_shape_keys:
                if process_shape_keys_after_rest_pose(mesh_obj, self.report):
                    successful_shape_key_processing += 1
                else:
                    self.report({'WARNING'}, f"Failed to process shape keys after rest pose for mesh '{mesh_obj.name}'")
            
            # オブジェクトモードに戻す
            bpy.ops.object.mode_set(mode='OBJECT')
            write_log("Switched back to OBJECT mode")
            
            # 最終更新を確実に反映
            bpy.context.view_layer.update()
            write_log("Final view layer update performed")
            
            # 処理結果をレポート
            total_success = successful_shape_key_processing + successful_no_shape_keys
            total_meshes = len(related_meshes)
            
            if total_success < total_meshes:
                self.report({'WARNING'}, 
                    f"Rest pose set with issues: {total_success}/{total_meshes} meshes processed successfully.")
            else:
                self.report({'INFO'}, 
                    f"Rest pose set: All {total_meshes} meshes updated successfully.")

        except Exception as e:
            self.report({'ERROR'}, f"Set rest pose failed: {e}")
            write_log(f"ERROR: Set rest pose failed: {e}")
            return {'CANCELLED'}

        write_log("Set rest pose completed successfully")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(POSECONV_OT_ConvertPose)
    bpy.utils.register_class(POSECONV_OT_SetRestPose)

def unregister():
    bpy.utils.unregister_class(POSECONV_OT_SetRestPose)
    bpy.utils.unregister_class(POSECONV_OT_ConvertPose)