import os
import json
import shutil
from datetime import datetime

# ============================================================
# 快照模块 - 内部变量与辅助函数
# ============================================================
_CURRENT_FILE = os.path.abspath(__file__)
_TOOLS_DIR = os.path.dirname(_CURRENT_FILE)
_SRC_DIR = os.path.dirname(_TOOLS_DIR)
_PROJECT_ROOT = os.path.dirname(_SRC_DIR)
SNAPSHOT_DIR = os.path.join(_PROJECT_ROOT, ".snapshots")
RECORD_FILE = os.path.join(SNAPSHOT_DIR, "snapshots.json")


def _load_record():
    """[内部] 读取快照登记表"""
    if not os.path.exists(RECORD_FILE):
        return []
    with open(RECORD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_record(record):
    """[内部] 保存快照登记表"""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def _collect_all_files():
    """[内部] 收集项目下所有非隐藏文件"""
    files = []
    for root, dirs, filenames in os.walk(_PROJECT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in filenames:
            if not f.startswith("."):
                files.append(os.path.join(root, f))
    return files


def _expand_paths(paths):
    """[内部] 展开路径：目录→目录下所有文件，文件→保留"""
    result = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, filenames in os.walk(p):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in filenames:
                    if not f.startswith("."):
                        result.append(os.path.join(root, f))
        elif os.path.isfile(p):
            result.append(p)
    return result


def _copy_file(src, dst):
    """复制文件，兼容 Windows 下文件被占用的情况"""
    try:
        shutil.copy2(src, dst)
    except (PermissionError, OSError):
        with open(src, "rb") as f_src:
            content = f_src.read()
        with open(dst, "wb") as f_dst:
            f_dst.write(content)


# ============================================================
# 路径工具
# ============================================================

def path_exists(path: str) -> dict:
    """
    判断路径是否存在，及其类型。

    Args:
        path: 要检查的文件或目录路径。

    Returns:
        dict:
            - success (bool)
            - data (dict):
                - path (str)
                - exists (bool)
                - type (str | None): "file"、"directory" 或 None
    """
    exists = os.path.exists(path)
    return {
        'success': True,
        'data': {
            'path': path,
            'exists': exists,
            'type': 'file' if os.path.isfile(path) else ('directory' if os.path.isdir(path) else None)
        }
    }


def dir_scan(path: str, recursive: bool = True, max_depth: int = -1, include_hidden: bool = False) -> dict:
    """
    扫描目录结构，返回完整的目录树及统计信息。

    Args:
        path: 要扫描的目录路径。
        recursive: 是否递归展开子目录。
        max_depth: 最大递归深度，-1 表示无限制。
        include_hidden: 是否包含隐藏文件。

    Returns:
        dict:
            - success (bool)
            - data (dict):
                - root (str)
                - tree (dict)
                - file_count (int)
                - dir_count (int)
    """
    if not os.path.isdir(path):
        return {'success': False, 'error': f"不是有效目录：{path}"}

    def _scan(p, depth):
        node = {'name': os.path.basename(p), 'type': "directory", "children": []}
        if max_depth != -1 and depth >= max_depth:
            return node
        try:
            entries = sorted(os.listdir(p))
        except PermissionError:
            return node
        for entry in entries:
            if not include_hidden and entry.startswith('.'):
                continue
            full = os.path.join(p, entry)
            if os.path.isdir(full):
                if recursive:
                    node['children'].append(_scan(full, depth + 1))
                else:
                    node['children'].append({'name': entry, 'type': "directory"})
            else:
                node['children'].append({
                    'name': entry,
                    'type': "file",
                    'size_bytes': os.path.getsize(full)
                })
        return node

    tree = _scan(path, 0)

    def _count_type(t, node_type):
        """递归统计指定类型的节点数量"""
        count = 1 if t.get('type') == node_type else 0
        for c in t.get('children', []):
            count += _count_type(c, node_type)
        return count

    file_count = _count_type(tree, "file")
    dir_count = _count_type(tree, "directory") - 1

    return {
        'success': True,
        'data': {
            'root': path,
            'tree': tree,
            'file_count': file_count,
            'dir_count': dir_count
        }
    }


# ============================================================
# 快照工具
# ============================================================

def archive_pack(why: str, what: list = None) -> dict:
    """
    创建快照，保存指定文件的副本。

    Args:
        why: 创建原因。
        what: 要备份的文件或目录路径列表。

    Returns:
        dict:
            - success (bool)
            - data (dict):
                - snapshot_id (str)
                - path (str)
                - why (str)
                - file_count (int)
                - when (str)
    """
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    if what is None:
        what = _collect_all_files()
    else:
        what = _expand_paths(what)

    if not what:
        return {"success": False, "error": "没有找到需要备份的文件"}

    copied = []
    for filepath in what:
        if not os.path.exists(filepath):
            continue
        rel_path = os.path.relpath(filepath, _PROJECT_ROOT)
        dest = os.path.join(SNAPSHOT_DIR, snapshot_id, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        _copy_file(filepath, dest)
        copied.append(rel_path)

    record = _load_record()
    record.append({
        "snapshot_id": snapshot_id,
        "why": why,
        "when": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": copied
    })
    _save_record(record)

    return {
        "success": True,
        "data": {
            "snapshot_id": snapshot_id,
            "path": os.path.join(SNAPSHOT_DIR, snapshot_id),
            "why": why,
            "file_count": len(copied),
            "when": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }


def snapshot_list() -> dict:
    """
    列出所有已创建的快照。

    Returns:
        dict:
            - success (bool)
            - data (dict):
                - snapshots (list)
                - count (int)
    """
    record = _load_record()
    return {
        "success": True,
        "data": {
            "snapshots": record,
            "count": len(record)
        }
    }


def snapshot_restore(snapshot_id: str, what: list = None) -> dict:
    """
    从快照恢复文件。

    Args:
        snapshot_id: 快照ID。
        what: 要恢复的文件路径列表。

    Returns:
        dict:
            - success (bool)
            - data (dict):
                - restored (list)
                - failed (list)
                - restored_count (int)
                - failed_count (int)
    """
    record = _load_record()

    target = None
    for snap in record:
        if snap["snapshot_id"] == snapshot_id:
            target = snap
            break

    if target is None:
        return {"success": False, "error": f"快照 {snapshot_id} 不存在，请用 snapshot_list 查看可用快照"}

    files_to_restore = what if what else target["files"]

    restored = []
    failed = []
    for filepath in files_to_restore:
        src = os.path.join(SNAPSHOT_DIR, snapshot_id, filepath)
        if not os.path.exists(src):
            failed.append(filepath)
            continue
        dst = os.path.join(_PROJECT_ROOT, filepath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        _copy_file(src, dst)
        restored.append(filepath)

    return {
        "success": len(failed) == 0,
        "data": {
            "restored": restored,
            "failed": failed,
            "restored_count": len(restored),
            "failed_count": len(failed)
        }
    }


# ============================================================
# 测试
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("测试1: path_exists")
    print("=" * 50)
    print(path_exists("."))
    print(path_exists("不存在的路径"))

    print("\n" + "=" * 50)
    print("测试2: dir_scan（当前目录，不递归）")
    print("=" * 50)
    result = dir_scan(".", recursive=False)
    if result["success"]:
        print(f"文件数: {result['data']['file_count']}")
        print(f"目录数: {result['data']['dir_count']}")
        for child in result['data']['tree']['children'][:5]:
            print(f"  {child['type']}: {child['name']}")
    else:
        print(result)

    print("\n" + "=" * 50)
    print("测试3: archive_pack（备份指定文件）")
    print("=" * 50)
    result = archive_pack("测试快照", [__file__])
    print(result)

    print("\n" + "=" * 50)
    print("测试4: snapshot_list")
    print("=" * 50)
    result = snapshot_list()
    print(f"快照总数: {result['data']['count']}")
    for snap in result['data']['snapshots']:
        print(f"  {snap['snapshot_id']}: {snap['why']} ({snap['when']})")

    print("\n" + "=" * 50)
    print("测试5: snapshot_restore（恢复刚才的快照）")
    print("=" * 50)
    snap_id = snapshot_list()['data']['snapshots'][0]['snapshot_id']
    result = snapshot_restore(snap_id)
    print(result)

    print("\n全部测试完成")