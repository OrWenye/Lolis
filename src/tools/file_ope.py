# -*- coding: UTF-8 -*-
'''
@Project ：Lolis
@File ：file_ope.py
@IDE ：PyCharm
@Author ：苦瓜
@Date ：2026/4/29 16:42
@Note: Something beautiful is about to happen !
'''

import os
import shutil
from pathlib import Path


def file_read(file_path: str, encoding: str = "utf-8", binary: bool = False) -> str | bytes:
    """
    读取文件内容。

    Args:
        file_path: 文件路径（绝对或相对项目根目录）
        encoding: 文本编码，仅当 binary=False 时生效
        binary: True 返回 bytes，False 返回 str

    Returns:
        文件内容（str 或 bytes）

    Raises:
        FileNotFoundError: 文件不存在
        IsADirectoryError: 路径为目录
        PermissionError: 权限不足
        UnicodeDecodeError: 编码错误（非二进制模式）
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if path.is_dir():
        raise IsADirectoryError(f"路径为目录，无法读取: {file_path}")

    mode = "rb" if binary else "r"
    try:
        with open(path, mode, encoding=None if binary else encoding) as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise ValueError(f"编码错误，尝试指定正确 encoding 或使用 binary=True。原始错误: {e}") from e
    except PermissionError as e:
        raise PermissionError(f"无权限读取文件: {file_path}") from e



def file_write(file_path: str, content: str | bytes, encoding: str = "utf-8",
               binary: bool = False, create_dirs: bool = True,
               append: bool = False) -> None:
    """
    将内容写入文件。

    Args:
        file_path: 目标文件路径
        content: 要写入的内容（str 或 bytes）
        encoding: 文本编码，仅当 binary=False 且 content 为 str 时生效
        binary: True 表示以二进制模式写入，此时 content 应为 bytes
        create_dirs: 是否自动创建不存在的父目录
        append: True 表示追加写入，False 表示覆盖写入

    Raises:
        TypeError: content 类型与 binary 不匹配
        OSError: 文件写入失败
    """
    if binary and not isinstance(content, bytes):
        raise TypeError("binary=True 时 content 必须为 bytes 类型")
    if not binary and not isinstance(content, str):
        raise TypeError("binary=False 时 content 必须为 str 类型")

    path = Path(file_path).resolve()
    if create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)

    mode = "ab" if (binary and append) else "a" if append else "wb" if binary else "w"
    try:
        with open(path, mode, encoding=None if binary else encoding) as f:
            f.write("\n"+content)
    except OSError as e:
        raise OSError(f"写入文件失败 {file_path}: {e}") from e


def file_patch(file_path: str, patches: list[dict], encoding: str = "utf-8", backup: bool = True) -> dict:
    """
    对文件应用一系列补丁操作（按顺序执行）。

    每个 patch 为一个字典，支持以下类型：
    - 类型 "replace": 替换字符串
        {"type": "replace", "old": "被替换的内容", "new": "新内容"}
    - 类型 "insert_line": 在指定行号前/后插入
        {"type": "insert_line", "line_no": 5, "position": "before", "content": "插入的行"}
    - 类型 "delete_line": 删除指定行号
        {"type": "delete_line", "line_no": 10}
    - 类型 "regex_replace": 正则替换
        {"type": "regex_replace", "pattern": r"old_pattern", "repl": r"new_sub", "flags": 0}

    Args:
        file_path: 要修改的文件路径
        patches: 补丁列表，按顺序应用
        encoding: 文件编码（仅文本模式，二进制不支持 patch）
        backup: 是否在修改前创建 .bak 备份文件

    Returns:
        dict: {"success": True/False, "message": str, "backup_path": str or None}

    Raises:
        ValueError: 补丁定义无效或应用失败
        FileNotFoundError: 文件不存在
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if path.is_dir():
        raise IsADirectoryError(f"路径为目录，无法 Patch: {file_path}")

    # 创建备份
    backup_path = None
    if backup:
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)

    # 读取原始内容并按行分割（保留换行符）
    original_text = path.read_text(encoding=encoding)
    lines = original_text.splitlines(keepends=True)

    # 深拷贝一份用于修改
    modified_text = original_text

    # 按顺序应用补丁
    for i, patch in enumerate(patches):
        patch_type = patch.get("type")
        if patch_type == "replace":
            old = patch.get("old")
            new = patch.get("new")
            if old is None or new is None:
                raise ValueError(f"补丁 {i}: replace 需要 old 和 new 字段")
            if old not in modified_text:
                raise ValueError(f"补丁 {i}: 未找到要替换的字符串: {old[:50]}...")
            modified_text = modified_text.replace(old, new)

        elif patch_type == "insert_line":
            line_no = patch.get("line_no")
            position = patch.get("position", "before")  # "before" 或 "after"
            content = patch.get("content")
            if not isinstance(line_no, int) or line_no < 1:
                raise ValueError(f"补丁 {i}: line_no 必须是 >=1 的整数")
            if position not in ("before", "after"):
                raise ValueError(f"补丁 {i}: position 必须是 'before' 或 'after'")
            if content is None:
                raise ValueError(f"补丁 {i}: insert_line 需要 content 字段")
            # 确保内容以换行结尾（文本行）
            if not content.endswith('\n'):
                content += '\n'
            # 将 lines 列表切分
            if line_no - 1 < 0 or line_no - 1 > len(lines):
                raise ValueError(f"补丁 {i}: 行号 {line_no} 超出范围 (1~{len(lines)})")
            insert_idx = line_no - 1 if position == "before" else line_no
            lines.insert(insert_idx, content)
            # 重新构建 modified_text
            modified_text = ''.join(lines)

        elif patch_type == "delete_line":
            line_no = patch.get("line_no")
            if not isinstance(line_no, int) or line_no < 1:
                raise ValueError(f"补丁 {i}: line_no 必须是 >=1 的整数")
            if line_no - 1 < 0 or line_no - 1 >= len(lines):
                raise ValueError(f"补丁 {i}: 行号 {line_no} 超出范围 (1~{len(lines)})")
            del lines[line_no - 1]
            modified_text = ''.join(lines)

        elif patch_type == "regex_replace":
            import re
            pattern = patch.get("pattern")
            repl = patch.get("repl")
            flags = patch.get("flags", 0)
            if pattern is None or repl is None:
                raise ValueError(f"补丁 {i}: regex_replace 需要 pattern 和 repl")
            modified_text = re.sub(pattern, repl, modified_text, flags=flags)

        else:
            raise ValueError(f"补丁 {i}: 未知类型 '{patch_type}'")

    # 写回文件
    path.write_text(modified_text, encoding=encoding)

    return {
        "success": True,
        "message": f"成功应用 {len(patches)} 个补丁",
        "backup_path": str(backup_path) if backup_path else None
    }


if __name__ == '__main__':pass
    # ++++++++++++++++++ 测试文件读取 +++++++++++++++++++++++++++
    # print(file_read("F:\Agent\Lolis\README.md"))  # 测试文件读写
    # print(file_read("F:\Agent\Lolis"))  # 测试文件读写

    # ++++++++++++++++++ 测试文件写入 +++++++++++++++++++++++++++
    # file_write(r"C:\Users\lenovo\Desktop\test_text.txt", "test: Hello World ! two",
    #            append=True)  # 成功

    # ++++++++++++++++++ 测试文件修改 +++++++++++++++++++++++++++
    # result = file_patch(
    #     file_path=r"C:\Users\lenovo\Desktop\test_text.txt",  # 文件路径
    #     patches=[
    #         # 示例1: 替换文本
    #         # {"type": "replace", "old": "test", "new": "Test"},
    #
    #         # 示例2: 在第3行前面插入一行
    #         # {"type": "insert_line", "line_no": 3, "position": "before", "content": "插入的行"},
    #
    #         # 示例3: 在第5行后面插入一行
    #         # {"type": "insert_line", "line_no": 5, "position": "after", "content": "尾部插入"},
    #
    #         # 示例4: 删除第2行
    #         # {"type": "delete_line", "line_no": 2},
    #
    #         # 示例5: 正则替换（将所有数字替换为 #）
    #         {"type": "regex_replace", "pattern": r"\d+", "repl": "#", "flags": 0}
    #     ],
    #     encoding="utf-8",
    #     backup=False  # 修改前自动创建 test.txt.bak 备份
    # )
    #
    # print(result)

