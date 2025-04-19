import bpy
import datetime
import os

def get_addon_log_path():
    temp_dir = bpy.app.tempdir if bpy.app.tempdir else os.path.expanduser("~")
    log_dir = os.path.join(temp_dir, "pose_converter_logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "pose_converter_log.txt")

def write_log(message: str):
    log_path = get_addon_log_path()
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")

def print_and_log(report_fn, level: str, message: str):
    report_fn({level}, message)
    write_log(f"{level.upper()}: {message}")

def get_shape_key_values(obj):
    if not obj.data.shape_keys:
        return {}
    return {kb.name: kb.value for kb in obj.data.shape_keys.key_blocks}

def restore_shape_key_values(obj, key_values):
    if not obj.data.shape_keys:
        return
    for name, value in key_values.items():
        if name in obj.data.shape_keys.key_blocks:
            obj.data.shape_keys.key_blocks[name].value = value

def find_related_mesh_objects(arm_obj):
    """
    アーマチュアモディファイアで関連付けられたメッシュオブジェクトを検索
    
    Parameters:
        arm_obj: アーマチュアオブジェクト
        
    Returns:
        関連するメッシュオブジェクトのリスト
    """
    related_meshes = []
    
    # アーマチュアモディファイアで関連付けられたメッシュを検索
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object == arm_obj:
                    if obj not in related_meshes:
                        related_meshes.append(obj)
    
    return related_meshes

def apply_shape_key_as_basis(obj, key_name):
    """
    指定したシェイプキーをBasisとして適用し、
    他のすべてのシェイプキーを新しいBasisに対する相対変形として再構築する
    """
    if not obj.data.shape_keys:
        write_log("No shape keys found")
        return
        
    kb = obj.data.shape_keys.key_blocks
    if key_name not in kb:
        raise ValueError(f"Shape key '{key_name}' not found")
    
    write_log(f"Applying shape key '{key_name}' as new Basis")
    
    # 新しいBasisとなるシェイプキーをアクティブにする
    new_basis_key = kb[key_name]
    new_basis_key.value = 1.0
    
    # Basisキーを取得（通常は最初のキー）
    basis_key = kb[0] if len(kb) > 0 else None
    
    # 保存対象のシェイプキーリストを作成（BassiとnewBasis以外）
    shape_keys_to_process = [
        key for key in kb 
        if key != new_basis_key and key != basis_key and key.name != 'Basis'
    ]
    
    write_log(f"Found {len(shape_keys_to_process)} shape keys to rebuild")
    
    # 各シェイプキーに対して処理
    for shape_key in shape_keys_to_process:
        # 元の値を保存
        original_name = shape_key.name
        original_value = shape_key.value
        write_log(f"Rebuilding shape key: {original_name}")
        
        # すべてのシェイプキーを非アクティブにする
        for k in kb:
            k.value = 0.0
            
        # 処理対象のシェイプキーをアクティブにする
        shape_key.value = 1.0
        
        # 現在の混合形状で一時キーを作成
        bpy.ops.object.shape_key_add(from_mix=True)
        # 最後に追加されたシェイプキーを取得
        temp_key = kb[-1]
        # 名前を変更
        temp_key.name = "temp"
        
        # 元のシェイプキーを削除
        obj.active_shape_key_index = kb.find(original_name)
        bpy.ops.object.shape_key_remove()
        
        # 一時キーを元の名前にリネーム
        temp_key.name = original_name
        temp_key.value = original_value
    
    # 最後に新しいBasisを作成
    # すべてのキーを非アクティブにする
    for k in kb:
        k.value = 0.0
        
    # 新しいBasisとなるキーをアクティブにする
    new_basis_key.value = 1.0
    
    # 現在のアクティブシェイプキーを先頭に移動
    obj.active_shape_key_index = kb.find(key_name)
    bpy.ops.object.shape_key_move(type='TOP')
    
    # 元のBasisを削除
    bpy.ops.object.shape_key_remove()
    
    # 現在の形状で新しいBasisを作成
    bpy.ops.object.shape_key_add(from_mix=True)
    # 最後に追加されたシェイプキーを最初に移動
    bpy.ops.object.shape_key_move(type='TOP')
    # 名前をBasisに変更
    kb[0].name = 'Basis'
    
    write_log("Shape key basis rebuilt with all dependent keys adjusted")

def remove_shape_key(obj, key_name):
    """シェイプキーを削除"""
    if not obj.data.shape_keys:
        return
    idx = obj.data.shape_keys.key_blocks.find(key_name)
    if idx != -1:
        obj.active_shape_key_index = idx
        bpy.ops.object.shape_key_remove()

def rename_shape_key(obj, old_name, new_name):
    """シェイプキーの名前を変更"""
    if not obj.data.shape_keys:
        return
    kb = obj.data.shape_keys.key_blocks
    if old_name in kb:
        kb[old_name].name = new_name

def apply_new_armature_modifier(mesh_obj, arm_obj, report_fn):
    """
    既存のアーマチュアモディファイアはそのままにし、新しいモディファイアを追加して適用する
    
    Parameters:
        mesh_obj: メッシュオブジェクト
        arm_obj: アーマチュアオブジェクト
        report_fn: レポート用関数
    """
    # オブジェクトモードに切り替え
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # メッシュオブジェクトをアクティブに
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    
    # アーマチュアオブジェクトは選択しない
    arm_obj.select_set(False)
    
    write_log("Adding new armature modifier for application...")
    
    # 新しいアーマチュアモディファイアを追加
    mod = mesh_obj.modifiers.new(name="ArmatureTemp", type='ARMATURE')
    mod.object = arm_obj
    
    # 新しく追加したモディファイアを適用
    try:
        write_log(f"Applying new armature modifier: {mod.name}")
        bpy.ops.object.modifier_apply(modifier=mod.name)
        print_and_log(report_fn, 'INFO', f"Applied new armature modifier")
    except Exception as e:
        print_and_log(report_fn, 'WARNING', f"Failed to apply modifier: {e}")
        # 失敗時も続行
        
    write_log("New armature modifier applied, original modifiers preserved")
    
    return True