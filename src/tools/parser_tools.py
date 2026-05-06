import csv
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from jsonschema import Draft7Validator, ValidationError, validate
except ModuleNotFoundError:
    Draft7Validator = None
    ValidationError = Exception
    validate = None


def json_read(file_path: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    读取 JSON 文件。

    Args:
        file_path: JSON 文件路径。支持普通 JSON，也支持被 Markdown
            代码块包裹的 JSON，例如 ```json ... ```。

    Returns:
        读取成功返回 dict 或 list。
        读取失败返回 None。

    Raises:
        FileNotFoundError: 文件不存在时会被捕获，并返回 None。
        PermissionError: 权限不足时会被捕获，并返回 None。
        json.JSONDecodeError: JSON 格式错误时会被捕获，并返回 None。
        OSError: 文件读取异常时会被捕获，并返回 None。
    """
    if not os.path.exists(file_path):
        print(f"[parser_tools.json_read] ERROR 文件不存在: {file_path}")
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = _clean_markdown_json(content)
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[parser_tools.json_read] ERROR JSON 解析失败: {e}")
        return None
    except OSError as e:
        print(f"[parser_tools.json_read] ERROR 文件读取失败: {e}")
        return None


def json_write(data: Any, file_path: str) -> bool:
    """
    写入 JSON 文件。

    Args:
        data: 要写入的 Python 数据，通常是 dict 或 list。
        file_path: 输出 JSON 文件路径。父目录不存在时会自动创建。

    Returns:
        写入成功返回 True。
        写入失败返回 False。

    Raises:
        TypeError: data 无法 JSON 序列化时会被捕获，并返回 False。
        PermissionError: 权限不足时会被捕获，并返回 False。
        OSError: 文件写入异常时会被捕获，并返回 False。
    """
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except (TypeError, OSError) as e:
        print(f"[parser_tools.json_write] ERROR JSON 写入失败: {e}")
        return False


def csv_read(file_path: str) -> List[Dict[str, str]]:
    """
    读取 CSV 文件。

    Args:
        file_path: CSV 文件路径。第一行会被作为表头，每一行返回一个 dict。

    Returns:
        读取成功返回 list[dict]。
        文件不存在、权限不足或解析失败时返回空列表 []。

    Raises:
        FileNotFoundError: 文件不存在时会被捕获，并返回 []。
        PermissionError: 权限不足时会被捕获，并返回 []。
        csv.Error: CSV 解析异常时会被捕获，并返回 []。
        OSError: 文件读取异常时会被捕获，并返回 []。
    """
    if not os.path.exists(file_path):
        print(f"[parser_tools.csv_read] ERROR 文件不存在: {file_path}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except (csv.Error, OSError) as e:
        print(f"[parser_tools.csv_read] ERROR CSV 读取失败: {e}")
        return []


def csv_write(
    data: List[Dict[str, Any]],
    file_path: str,
    fieldnames: Optional[List[str]] = None,
) -> bool:
    """
    写入 CSV 文件。

    Args:
        data: 要写入的行数据。每一行是一个 dict。
        file_path: 输出 CSV 文件路径。父目录不存在时会自动创建。
        fieldnames: CSV 表头。为 None 时会从 data 第一行的 key 自动推导。

    Returns:
        写入成功返回 True。
        data 为空、权限不足或写入失败时返回 False。

    Raises:
        ValueError: data 为空且无法推导表头时会被捕获，并返回 False。
        PermissionError: 权限不足时会被捕获，并返回 False。
        csv.Error: CSV 写入异常时会被捕获，并返回 False。
        OSError: 文件写入异常时会被捕获，并返回 False。
    """
    if not data:
        print("[parser_tools.csv_write] ERROR data 不能为空")
        return False

    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        if fieldnames is None:
            fieldnames = list(data[0].keys())

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        return True
    except (ValueError, csv.Error, OSError) as e:
        print(f"[parser_tools.csv_write] ERROR CSV 写入失败: {e}")
        return False


def schema_validate(data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
    """
    校验数据是否符合 JSON Schema 结构定义。

    Args:
        data: 要校验的数据，通常是从 JSON 文件读取出来的 dict。
        schema: JSON Schema 规则，定义字段类型、必填字段、数组元素结构等。

    Returns:
        (是否通过, 结果消息)
        通过时返回 (True, "验证通过")。
        失败时返回 (False, "具体错误原因")。

    Raises:
        ValidationError: 字段类型错误、必填字段缺失等会被捕获，并返回 False。
        Exception: Schema 定义错误或其他校验异常会被捕获，并返回 False。
    """
    if validate is None or Draft7Validator is None:
        return _schema_validate_basic(data, schema)

    try:
        Draft7Validator.check_schema(schema)
        validate(instance=data, schema=schema)
        return True, "验证通过"
    except ValidationError as e:
        field = ".".join(map(str, list(e.path))) or "<root>"
        return False, f"字段 '{field}' 错误: {e.message}"
    except Exception as e:
        return False, f"Schema 定义错误: {str(e)}"


def _clean_markdown_json(content: str) -> str:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content).strip()
    return content


def _schema_validate_basic(
    data: Any,
    schema: Dict[str, Any],
    path: str = "<root>",
) -> Tuple[bool, str]:
    expected_type = schema.get("type")
    if expected_type and not _matches_schema_type(data, expected_type):
        return False, f"字段 '{path}' 错误: expected {expected_type}, got {type(data).__name__}"

    if expected_type == "object":
        if not isinstance(data, dict):
            return False, f"字段 '{path}' 错误: expected object, got {type(data).__name__}"

        for field in schema.get("required", []):
            if field not in data:
                return False, f"字段 '{path}' 错误: '{field}' is a required property"

        for field, field_schema in schema.get("properties", {}).items():
            if field in data:
                child_path = field if path == "<root>" else f"{path}.{field}"
                ok, message = _schema_validate_basic(data[field], field_schema, child_path)
                if not ok:
                    return ok, message

    if expected_type == "array":
        if not isinstance(data, list):
            return False, f"字段 '{path}' 错误: expected array, got {type(data).__name__}"

        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(data):
                ok, message = _schema_validate_basic(item, item_schema, f"{path}[{index}]")
                if not ok:
                    return ok, message

    return True, "验证通过"


def _matches_schema_type(value: Any, expected_type: str) -> bool:
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
    }
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "null":
        return value is None

    python_type = type_map.get(expected_type)
    if python_type is None:
        return True
    return isinstance(value, python_type)

