from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass
class HttpFetchResult:
    ok: bool
    url: str
    final_url: str | None
    status_code: int | None
    content_type: str | None
    text: str
    headers: dict[str, str]
    error: str | None


def _is_private_host(hostname: str) -> bool:
    """
    防止 Agent 访问 localhost、内网地址、云元数据地址等敏感目标。
    """
    try:
        ip = ipaddress.ip_address(hostname)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
        )
    except ValueError:
        pass

    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
            ):
                return True
    except socket.gaierror:
        return False

    return False


def http_fetch(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | str | None = None,
    timeout: int = 20,
    max_bytes: int = 1_000_000,
) -> dict[str, Any]:
    """
    Tools / 网络请求类 / http_fetch

    Function:
    - 拉取单个网页、文档或 API 内容
    - 给 supervisor、Delivery Worker、QA Worker、Capability Worker 提供外部资料读取能力
    - 不负责自动遍历整个网站，V1 只做单次请求

    Args:
    - url: str, 请求 URL
    - method: str, default "GET", 请求方法
    - headers: dict[str, str] | None, default None, 请求头
    - params: dict[str, Any] | None, default None, 查询参数
    - body: dict[str, Any] | str | None, default None, 请求体
    - timeout: int, default 20, 请求超时时间，单位秒
    - max_bytes: int, default 1_000_000, 最大返回字节数，单位字节，默认 1MB。

    Returns:
    {
        "ok": bool,
        "url": 原始 URL,
        "final_url": 跳转后的 URL,
        "status_code": HTTP 状态码,
        "content_type": 响应类型,
        "text": 响应文本，最多 max_bytes,
        "headers": 响应头,
        "error": 错误信息
    }

    Raises:
    - ValueError: 如果 URL 格式错误
    - requests.exceptions.RequestException: 如果请求过程中发生错误      
    """

    # 校验 URL 格式
    if not isinstance(url, str) or not url.strip():
        return asdict(HttpFetchResult(
            ok=False,
            url=str(url),
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Invalid URL: url must be a non-empty string.",
        ))

    if not isinstance(method, str):
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Invalid method: method must be a string.",
        ))

    if headers is not None and not isinstance(headers, dict):
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Invalid headers: headers must be a dictionary.",
        ))

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Only http and https URLs are allowed.",
        ))

    if not parsed.hostname:
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Invalid URL: missing hostname.",
        ))

    if _is_private_host(parsed.hostname):
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Access to private, local, or reserved network addresses is blocked.",
        ))

    method = method.upper()

    if method not in {"GET", "POST"}:
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error="Only GET and POST methods are supported in V1.",
        ))

    request_headers = {
        "User-Agent": "SelfSkills-Agent/0.1",
        "Accept": "text/html,application/json,text/plain,*/*",
        **(headers or {}),
    }

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=request_headers,
            params=params,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, str) else None,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )

        chunks: list[bytes] = []
        total = 0

        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue

            total += len(chunk)

            if total > max_bytes:
                remaining = max_bytes - (total - len(chunk))
                if remaining > 0:
                    chunks.append(chunk[:remaining])
                break

            chunks.append(chunk)

        raw = b"".join(chunks)

        encoding = response.encoding or "utf-8"
        text = raw.decode(encoding, errors="replace")

        return asdict(HttpFetchResult(
            ok=response.ok,
            url=url,
            final_url=response.url,
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            text=text,
            headers=dict(response.headers),
            error=None if response.ok else f"HTTP {response.status_code}",
        ))

    except requests.RequestException as exc:
        return asdict(HttpFetchResult(
            ok=False,
            url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            text="",
            headers={},
            error=str(exc),
        ))


if __name__ == "__main__":
    print("\n-----------测试GET请求------------\n")
    res_get = http_fetch(url="https://httpbin.org/get?name=test&value=123", method="GET")  # 测试GET请求，返回JSON数据
    print(res_get)

    print("\n-----------测试POST请求------------\n")
    res_post = http_fetch(url="https://httpbin.org/post", method="POST", body={"name": "test", "value": 123})  # 测试POST请求，返回JSON数据
    print(res_post)
