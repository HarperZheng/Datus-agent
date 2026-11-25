"""ClickHouse <23.5 HTTP 流量兼容反代（部署文档附录 Bug 2）。

【问题背景】

dosi-engine（Rust 原生扩展）在**执行阶段**给 SQL 硬编码追加
``SETTINGS session_timezone = 'UTC'``（2026-11-25 于 dosi-engine 0.2.2 +
CH 23.3.15.29 实测复现）：编译产物不含该设置，Python 层改不了 Rust 内部的
SQL 拼装，23.3 按设置名直接拒绝（Code 115 UNKNOWN_SETTING，23.5 才引入）。

【方案：进程内 HTTP 反向代理】

引擎的连接参数（host/port）由 Python 侧传入——这是唯一可控的注入点。
本模块启动一个 127.0.0.1 本地反代，把引擎的所有 CH HTTP 流量透明转发到
真实服务器，转发前做两类改写：

  1. URL 参数剥离：``session_timezone=...`` 整个参数删掉
  2. body（SQL 文本）改写：SETTINGS 子句里的 session_timezone 项剥离；
     23.3 缺失/行为不同的函数按映射表替换（dateTrunc → toStartOfXxx 等）

其余请求与响应原样透传（含错误码）。引擎侧无感知。

用法见 :func:`ensure_clickhouse_233_proxy`（幂等入口，含版本与环境变量
门控）；纯反代能力见 :func:`start_compat_proxy`。环境变量
``DATUS_CH_COMPAT=off`` 可整体禁用。
"""

import http.client
import os
import re
import threading
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

from datus.utils.loggings import get_logger

logger = get_logger(__name__)

# 门控阈值：CH 23.5 起 session_timezone 与相关函数行为正常，直连即可
_COMPAT_MIN_VERSION = (23, 5)

# 日期截断函数映射：dateTrunc('unit', expr) → 23.3 等价函数（表驱动，可追加）
_DATETRUNC_MAP = {
    "second": "toStartOfSecond",
    "minute": "toStartOfMinute",
    "hour": "toStartOfHour",
    "day": "toDate",
    "week": "toMonday",
    "month": "toStartOfMonth",
    "quarter": "toStartOfQuarter",
    "year": "toStartOfYear",
}

_DATETRUNC_RE = re.compile(r"dateTrunc\s*\(\s*'(\w+)'\s*,", re.I)
# SETTINGS 子句里的 session_timezone 项（含值），前置逗号一并吞掉
_SESSION_TZ_ITEM_RE = re.compile(r"\s*,?\s*session_timezone\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s,;()]+)", re.I)


def rewrite_sql(sql: str) -> str:
    """对 SQL 文本做 23.3 兼容改写（幂等）。

    1. 剥离 SETTINGS 子句中的 session_timezone 项；若剥离后 SETTINGS 子句
       为空，则把悬挂的 SETTINGS 关键字一并删掉（空 SETTINGS 会被 23.3 拒绝）
    2. dateTrunc('unit', expr) → 等价函数：dateTrunc('month', d) 与
       toStartOfMonth(d) 共用同一个右括号，只需替换函数头
    """
    result = _SESSION_TZ_ITEM_RE.sub("", sql, count=1)
    result = re.sub(r"\bSETTINGS\s*$", "", result, flags=re.I)
    return _DATETRUNC_RE.sub(_replace_datetrunc, result)


def _replace_datetrunc(match: "re.Match[str]") -> str:
    fn = _DATETRUNC_MAP.get(match.group(1).lower())
    if not fn:
        return match.group(0)  # 未登记的 unit 原样放行，宁可报错也不猜语义
    return f"{fn}("


def rewrite_query_body(body: bytes) -> bytes:
    """对请求体做兼容改写（仅当看起来是 SQL 文本时才动手）。"""
    if not body:
        return body
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body  # 非文本（如 FORMAT Native）不碰
    if "session_timezone" not in text and "dateTrunc" not in text.lower():
        return body
    return rewrite_sql(text).encode("utf-8")


def strip_session_timezone_param(path: str) -> str:
    """剥掉 URL query 里的 session_timezone 参数，其余保持原样。"""
    parts = urllib.parse.urlsplit(path)
    params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    filtered = [(k, v) for k, v in params if k.lower() != "session_timezone"]
    new_query = urllib.parse.urlencode(filtered)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


@dataclass
class ProxyHandle:
    """一个运行中的反代实例；upstream 指向真实 CH。"""

    host: str
    port: int
    upstream_host: str
    upstream_port: int
    _server: ThreadingHTTPServer

    def shutdown(self) -> None:
        self._server.shutdown()


class _CompatHandler(BaseHTTPRequestHandler):
    """转发处理器：改写 → 转发 → 回传；其余原样透传。"""

    # 由 start_compat_proxy 注入
    upstream_host: str = ""
    upstream_port: int = 0

    def log_message(self, fmt, *args):  # 静默默认访问日志，避免刷屏
        pass

    def _forward(self):
        # 上游地址由 start_compat_proxy 注入到 server 对象上
        upstream_host = getattr(self.server, "upstream_host", "")
        upstream_port = int(getattr(self.server, "upstream_port", 0))
        # 1) URL：剥 session_timezone 参数
        path = strip_session_timezone_param(self.path)
        # 2) body：SQL 兼容改写
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        body = rewrite_query_body(body)
        # 3) 构造上游请求：逐头复制（跳过逐跳头与 Host/Content-Length）
        skip = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}
        headers = {k: v for k, v in self.headers.items() if k.lower() not in skip}
        try:
            conn = http.client.HTTPConnection(upstream_host, upstream_port, timeout=300)
            conn.request(self.command, path, body=body, headers=headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() in ("connection", "keep-alive", "transfer-encoding"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
            conn.close()
        except Exception as exc:  # noqa: BLE001 —— 反代自身故障要可见但不能挂死引擎
            logger.warning("ClickHouse compat proxy forward failed: %s", exc)
            self.send_response(502)
            msg = f"ch_compat proxy error: {exc}".encode()
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _forward


class _ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


_PROXY_LOCK = threading.Lock()
_PROXIES: Dict[Tuple[str, int], ProxyHandle] = {}
_PROBE_CACHE: Dict[Tuple[str, int, str], Optional[Tuple[int, int]]] = {}


def start_compat_proxy(upstream_host: str, upstream_port: int) -> ProxyHandle:
    """启动（或复用）指向指定上游的本地反代。按 (host, port) 幂等。"""
    key = (upstream_host, upstream_port)
    with _PROXY_LOCK:
        handle = _PROXIES.get(key)
        if handle is not None:
            return handle
        server = _ProxyServer(("127.0.0.1", 0), _CompatHandler)
        server.upstream_host = upstream_host
        server.upstream_port = upstream_port
        thread = threading.Thread(target=server.serve_forever, name="ch233-compat-proxy", daemon=True)
        thread.start()
        handle = ProxyHandle(
            host="127.0.0.1",
            port=server.server_address[1],
            upstream_host=upstream_host,
            upstream_port=upstream_port,
            _server=server,
        )
        _PROXIES[key] = handle
        logger.info(
            "ClickHouse <23.5 compat proxy started: 127.0.0.1:%s -> %s:%s",
            handle.port,
            upstream_host,
            upstream_port,
        )
        return handle


def stop_all_proxies() -> None:
    """关闭全部反代（进程退出或引擎池整体关闭时调用；通常无需手动调）。"""
    with _PROXY_LOCK:
        for handle in _PROXIES.values():
            handle.shutdown()
        _PROXIES.clear()


def probe_clickhouse_version(
    host: str, port: int, username: str = "", password: str = "", database: str = ""
) -> Optional[Tuple[int, int]]:
    """直连探测 CH 版本，返回 (主版本, 次版本)；探测失败返回 None。

    结果按 (host, port, user) 缓存——版本在进程生命周期内不变；
    若服务器中途升级，重启进程即可。
    """
    key = (host, port, username)
    if key in _PROBE_CACHE:
        return _PROBE_CACHE[key]
    version: Optional[Tuple[int, int]] = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        body = "SELECT version() FORMAT TabSeparated"
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        if username:
            import base64

            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
        conn.request("POST", "/", body=body, headers=headers)
        resp = conn.getresponse()
        text = resp.read().decode("utf-8", "replace").strip()
        conn.close()
        m = re.match(r"^(\d+)\.(\d+)", text)
        if m:
            version = (int(m.group(1)), int(m.group(2)))
    except Exception as exc:  # noqa: BLE001 —— 探测失败走不启用分支，需吞掉
        logger.warning("ClickHouse compat: version probe failed: %s", exc)
    _PROBE_CACHE[key] = version
    return version


def ensure_clickhouse_233_proxy(conn: Dict[str, Any]) -> Dict[str, Any]:
    """幂等入口（供 dosi/engine.py::_runtime_connections 调用）。

    门控顺序：
      1. ``DATUS_CH_COMPAT=off`` → 总开关关闭，原样返回
      2. 非 clickhouse 类型 / 本机地址 → 原样返回（本机不走反代）
      3. 已指向本地反代 → 幂等返回
      4. 版本探测失败或 ≥23.5 → 原样返回
      5. 命中 <23.5 → 返回 host/port 指向本地反代的**新**连接字典（不修改入参）
    """
    if os.environ.get("DATUS_CH_COMPAT", "").strip().lower() == "off":
        return conn
    if str(conn.get("type", "")).lower() != "clickhouse":
        return conn
    host = str(conn.get("host") or "")
    if host in ("127.0.0.1", "localhost", "::1", ""):
        return conn
    try:
        port = int(conn.get("port") or 8123)
    except (TypeError, ValueError):
        port = 8123
    version = probe_clickhouse_version(
        host,
        port,
        str(conn.get("username") or ""),
        str(conn.get("password") or ""),
        str(conn.get("database") or ""),
    )
    if version is None or version >= _COMPAT_MIN_VERSION:
        return conn
    handle = start_compat_proxy(host, port)
    new_conn = dict(conn)
    new_conn["host"] = handle.host
    new_conn["port"] = handle.port
    logger.info("ClickHouse %s.%s detected: routing engine traffic through local compat proxy", *version)
    return new_conn
