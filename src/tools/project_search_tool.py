"""项目搜索工具。

这个文件只暴露两个公开函数：
1. ``code_search``：按文件名在项目中搜索代码文件、配置文件或文档文件。
2. ``symbol_search``：从文件内容中提取指定函数、类或模块相关内容。

设计上尽量保持简单：
- 公开接口少，便于直接调用
- 参数和返回值都有明确类型
- 需要扩展时，优先通过可选参数扩展，而不是改已有调用方式
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_EXCLUDE_DIRS: tuple[str, ...] = (".git", "__pycache__", ".venv", "node_modules")


@dataclass(frozen=True)
class SymbolMatch:
    """单条符号搜索结果。"""

    name: str
    symbol_type: str
    start_line: int
    end_line: int
    content: str


def code_search(
    file_name: str,
    search_root: str,
    *,
    exact_match: bool = True,
    case_sensitive: bool = False,
    allowed_extensions: Sequence[str] | None = None,
    exclude_dirs: Sequence[str] = DEFAULT_EXCLUDE_DIRS,
) -> list[str]:
    """按文件名在项目目录中搜索文件，并返回命中的文件地址列表。

    输入：
    - file_name: 需要搜索的文件名，例如 ``predict.py``、``settings.yaml``、``README.md``
    - search_root: 项目根目录

    参数：
    - exact_match: 是否按完整文件名精确匹配，默认 ``True``
    - case_sensitive: 是否区分大小写，默认 ``False``
    - allowed_extensions: 允许搜索的文件后缀列表，例如 ``[".py", ".md", ".yaml"]``；
      传 ``None`` 表示不过滤后缀
    - exclude_dirs: 需要跳过的目录名列表，默认会排除常见缓存和依赖目录

    输出：
    - ``list[str]``：命中文件的绝对路径列表；如果没有找到，返回空列表

    可能抛出的异常：
    - ValueError: ``file_name`` 或 ``search_root`` 为空
    - FileNotFoundError: ``search_root`` 不存在
    - NotADirectoryError: ``search_root`` 不是目录

    返回值：
    - 返回按路径排序后的绝对路径列表，方便上层稳定使用
    """

    normalized_name = file_name.strip()
    normalized_root = search_root.strip()
    if not normalized_name:
        raise ValueError("file_name 不能为空。")
    if not normalized_root:
        raise ValueError("search_root 不能为空。")

    root_path = Path(normalized_root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"搜索根目录不存在: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"搜索根目录不是目录: {root_path}")

    extension_filter = _normalize_extensions(allowed_extensions)
    matches: list[str] = []

    for candidate in _iter_candidate_files(root_path, exclude_dirs):
        if extension_filter and candidate.suffix.lower() not in extension_filter:
            continue
        if _match_file_name(candidate.name, normalized_name, exact_match=exact_match, case_sensitive=case_sensitive):
            matches.append(str(candidate.resolve()))

    return sorted(matches)


def symbol_search(
    file_content: str,
    query: str,
    *,
    language: str = "python",
    exact_match: bool = True,
    case_sensitive: bool = True,
) -> list[SymbolMatch]:
    """从文件内容中搜索指定符号，并返回该符号的完整内容。

    输入：
    - file_content: 文件完整内容字符串
    - query: 需要搜索的函数名、类名或模块名

    参数：
    - language: 文件语言类型，当前只支持 ``"python"``
    - exact_match: 是否精确匹配符号名，默认 ``True``
    - case_sensitive: 是否区分大小写，默认 ``True``

    输出：
    - ``list[SymbolMatch]``：所有命中的符号结果

    可能抛出的异常：
    - ValueError: ``file_content`` 或 ``query`` 为空，或者 ``language`` 不支持
    - SyntaxError: 当 ``language="python"`` 且传入的 Python 代码本身语法不合法时

    返回值：
    - 返回命中的全部符号内容列表
    - 每个结果包含符号名、符号类型、起止行号和完整源码内容
    - 如果没有找到，返回空列表
    """

    if not file_content.strip():
        raise ValueError("file_content 不能为空。")
    if not query.strip():
        raise ValueError("query 不能为空。")
    if language.lower() != "python":
        raise ValueError("当前仅支持 Python 文件内容搜索。")

    tree = ast.parse(file_content)
    matches: list[SymbolMatch] = []

    for node in ast.walk(tree):
        symbol_match = _build_symbol_match(
            node=node,
            file_content=file_content,
            query=query,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
        )
        if symbol_match is not None:
            matches.append(symbol_match)

    return sorted(matches, key=lambda item: (item.start_line, item.end_line, item.name))


def _normalize_extensions(extensions: Sequence[str] | None) -> set[str]:
    """把后缀列表统一整理成小写集合。"""

    if not extensions:
        return set()

    normalized: set[str] = set()
    for extension in extensions:
        if not extension:
            continue
        cleaned = extension if extension.startswith(".") else f".{extension}"
        normalized.add(cleaned.lower())
    return normalized


def _iter_candidate_files(root_path: Path, exclude_dirs: Sequence[str]) -> Iterable[Path]:
    """递归遍历候选文件，并跳过不需要搜索的目录。"""

    excluded = set(exclude_dirs)
    for current_root, dir_names, file_names in root_path.walk():
        dir_names[:] = [dir_name for dir_name in dir_names if dir_name not in excluded]
        for file_name in file_names:
            yield current_root / file_name


def _match_file_name(
    candidate_name: str,
    target_name: str,
    *,
    exact_match: bool,
    case_sensitive: bool,
) -> bool:
    """判断候选文件名是否匹配目标文件名。"""

    if case_sensitive:
        left = candidate_name
        right = target_name
    else:
        left = candidate_name.lower()
        right = target_name.lower()

    return left == right if exact_match else right in left


def _build_symbol_match(
    *,
    node: ast.AST,
    file_content: str,
    query: str,
    exact_match: bool,
    case_sensitive: bool,
) -> SymbolMatch | None:
    """把 AST 节点转换成可返回的符号结果；不匹配时返回 ``None``。"""

    named_node = _extract_named_node(node)
    if named_node is None:
        return None

    symbol_name, symbol_type = named_node
    if not _match_symbol_name(symbol_name, query, exact_match=exact_match, case_sensitive=case_sensitive):
        return None

    start_line = getattr(node, "lineno", None)
    end_line = getattr(node, "end_lineno", None)
    if start_line is None or end_line is None:
        return None

    content = _extract_node_content(file_content, node)
    return SymbolMatch(
        name=symbol_name,
        symbol_type=symbol_type,
        start_line=start_line,
        end_line=end_line,
        content=content,
    )


def _extract_named_node(node: ast.AST) -> tuple[str, str] | None:
    """从 AST 节点中提取可搜索的名称和符号类型。"""

    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return node.name, "function"
    if isinstance(node, ast.ClassDef):
        return node.name, "class"
    if isinstance(node, ast.Import):
        if not node.names:
            return None
        alias = node.names[0]
        return alias.asname or alias.name, "module"
    if isinstance(node, ast.ImportFrom):
        if node.module:
            return node.module, "module"
        if node.names:
            alias = node.names[0]
            return alias.asname or alias.name, "module"
    return None


def _match_symbol_name(
    symbol_name: str,
    query: str,
    *,
    exact_match: bool,
    case_sensitive: bool,
) -> bool:
    """判断符号名是否匹配目标查询。"""

    if case_sensitive:
        left = symbol_name
        right = query
    else:
        left = symbol_name.lower()
        right = query.lower()

    return left == right if exact_match else right in left


def _extract_node_content(file_content: str, node: ast.AST) -> str:
    """提取 AST 节点对应的源码文本。"""

    source_segment = ast.get_source_segment(file_content, node)
    if source_segment:
        return source_segment

    lines = file_content.splitlines()
    start_line = getattr(node, "lineno", 1)
    end_line = getattr(node, "end_lineno", start_line)
    return "\n".join(lines[start_line - 1 : end_line])


def _run_demo_test() -> None:
    """运行一个自包含的测试示例。"""

    sample_python = '''
import os
from pathlib import Path


class Predictor:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name


def predict(text: str) -> str:
    """Return a fake prediction."""
    return text.upper()


async def predict_async(text: str) -> str:
    return predict(text)
'''.strip()

    repo_root = Path(__file__).resolve().parent.parent

    code_result = code_search(
        file_name="project_search_tool.py",
        search_root=str(repo_root),
        allowed_extensions=[".py", ".yaml", ".md"],
    )
    symbol_result = symbol_search(
        file_content=sample_python,
        query="predict",
    )

    assert len(code_result) >= 1
    assert any(path.endswith("project_search_tool.py") for path in code_result)
    assert len(symbol_result) == 1
    assert symbol_result[0].symbol_type == "function"
    assert "def predict(text: str) -> str:" in symbol_result[0].content

    print("Demo test passed.")
    print("code_search result:")
    print(code_result)
    print("symbol_search result:")
    for item in symbol_result:
        print(item)


if __name__ == "__main__":
    _run_demo_test()
