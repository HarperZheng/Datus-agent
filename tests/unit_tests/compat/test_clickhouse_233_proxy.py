"""Unit tests for the ClickHouse <23.5 HTTP compat proxy (Bug 2).

A mock upstream HTTP server records forwarded requests and returns canned
responses, so rewrite/strip/passthrough behaviour is verified without a real
ClickHouse. Gating branches are exercised via monkeypatched version probing.
"""

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from datus.compat import clickhouse_233_proxy as mod
from datus.compat.clickhouse_233_proxy import (
    ensure_clickhouse_233_proxy,
    probe_clickhouse_version,
    rewrite_query_body,
    rewrite_sql,
    strip_session_timezone_param,
)

# ---------- 纯函数：SQL 改写 ----------


def test_strip_session_timezone_item_keeps_others():
    sql = "SELECT 1 FROM t SETTINGS join_use_nulls = 1, session_timezone = 'UTC'"
    assert rewrite_sql(sql) == "SELECT 1 FROM t SETTINGS join_use_nulls = 1"


def test_strip_dangling_settings_clause():
    sql = "SELECT 1 FROM t SETTINGS session_timezone = 'UTC'"
    assert rewrite_sql(sql) == "SELECT 1 FROM t "


def test_datetrunc_rewritten():
    sql = "SELECT dateTrunc('month', d), dateTrunc('year', x) FROM t"
    assert rewrite_sql(sql) == "SELECT toStartOfMonth( d), toStartOfYear( x) FROM t"


def test_rewrite_is_idempotent():
    sql = "SELECT dateTrunc('month', d) FROM t SETTINGS session_timezone = 'UTC'"
    assert rewrite_sql(rewrite_sql(sql)) == rewrite_sql(sql)


def test_unknown_datetrunc_unit_passthrough():
    sql = "SELECT dateTrunc('fortnight', d) FROM t"
    assert rewrite_sql(sql) == sql


def test_rewrite_query_body_skips_non_text():
    assert rewrite_query_body(b"\x00\x01") == b"\x00\x01"
    assert rewrite_query_body(b"") == b""


def test_strip_session_timezone_param():
    path, query = strip_session_timezone_param("/?database=fujian1105&session_timezone=UTC&wait_end_of_query=1").split(
        "?", 1
    )
    assert path == "/"
    assert "session_timezone" not in query
    assert "database=fujian1105" in query and "wait_end_of_query=1" in query


# ---------- mock 上游 + 反代转发 ----------


class _Upstream(BaseHTTPRequestHandler):
    """记录请求并按 body 回复的最小上游。"""

    requests = []  # [(method, path, body)]，由测试断言

    def log_message(self, fmt, *args):
        pass

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        type(self).requests.append((self.command, self.path, body))
        payload = json.dumps({"echo": body.decode("utf-8", "replace"), "path": self.path}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Upstream", "yes")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _handle


@pytest.fixture
def upstream():
    _Upstream.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Upstream)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "127.0.0.1", server.server_address[1]
    server.shutdown()


def test_proxy_strips_and_forwards(upstream):
    host, port = upstream
    handle = mod.start_compat_proxy(host, port)
    try:
        conn = http.client.HTTPConnection(handle.host, handle.port, timeout=10)
        body = "SELECT 1 SETTINGS join_use_nulls = 1, session_timezone = 'UTC'"
        conn.request(
            "POST", "/?session_timezone=UTC&database=db", body=body, headers={"Authorization": "Basic dXNlcjpwdw=="}
        )
        resp = conn.getresponse()
        resp.read()
        conn.close()
        assert resp.getheader("X-Upstream") == "yes"  # 响应头透传
        method, path, sent = _Upstream.requests[-1]
        assert "session_timezone" not in path  # URL 参数剥离
        assert "session_timezone" not in sent.decode()  # body SETTINGS 项剥离
        assert "join_use_nulls = 1" in sent.decode()  # 其余 SETTINGS 保留
        assert sent.strip() == b"SELECT 1 SETTINGS join_use_nulls = 1"  # 重算长度正确（尾随空格无害）
    finally:
        mod._PROXIES.clear()


# ---------- 门控 ensure_clickhouse_233_proxy ----------


def _conn(**kw):
    base = {
        "type": "clickhouse",
        "host": "10.0.0.8",
        "port": 8123,
        "username": "u",
        "password": "p",
        "database": "db",
        "default": True,
    }
    base.update(kw)
    return base


def test_gate_env_off(monkeypatch, upstream):
    monkeypatch.setenv("DATUS_CH_COMPAT", "off")
    c = ensure_clickhouse_233_proxy(_conn())
    assert c["host"] == "10.0.0.8"  # 原样直连


def test_gate_localhost_passthrough(monkeypatch):
    monkeypatch.delenv("DATUS_CH_COMPAT", raising=False)
    c = ensure_clickhouse_233_proxy(_conn(host="localhost"))
    assert c["host"] == "localhost"


def test_gate_non_clickhouse_passthrough(monkeypatch):
    monkeypatch.delenv("DATUS_CH_COMPAT", raising=False)
    c = ensure_clickhouse_233_proxy(_conn(type="duckdb"))
    assert c["host"] == "10.0.0.8"


def test_gate_probe_failure_passthrough(monkeypatch):
    monkeypatch.delenv("DATUS_CH_COMPAT", raising=False)
    monkeypatch.setattr(mod, "probe_clickhouse_version", lambda *a, **k: None)
    c = ensure_clickhouse_233_proxy(_conn())
    assert c["host"] == "10.0.0.8"


def test_gate_modern_version_passthrough(monkeypatch):
    monkeypatch.delenv("DATUS_CH_COMPAT", raising=False)
    monkeypatch.setattr(mod, "probe_clickhouse_version", lambda *a, **k: (23, 5))
    c = ensure_clickhouse_233_proxy(_conn())
    assert c["host"] == "10.0.0.8"


def test_gate_old_version_routes_to_proxy(monkeypatch, upstream):
    monkeypatch.delenv("DATUS_CH_COMPAT", raising=False)
    monkeypatch.setattr(mod, "probe_clickhouse_version", lambda *a, **k: (23, 3))
    c = ensure_clickhouse_233_proxy(_conn())
    assert c["host"] == "127.0.0.1"
    assert c["port"] != 8123  # 反代随机端口
    assert c["username"] == "u" and c["password"] == "p"  # 凭据原样保留
    # 入参字典不被修改
    assert c is not _conn()


def test_gate_idempotent(monkeypatch, upstream):
    monkeypatch.delenv("DATUS_CH_COMPAT", raising=False)
    monkeypatch.setattr(mod, "probe_clickhouse_version", lambda *a, **k: (23, 3))
    c1 = ensure_clickhouse_233_proxy(_conn())
    c2 = ensure_clickhouse_233_proxy(c1)  # 已指向 127.0.0.1，直接返回
    assert c2["host"] == "127.0.0.1" and c2["port"] == c1["port"]


# ---------- 版本探测解析 ----------


def test_probe_parses_version(upstream, monkeypatch):
    host, port = upstream

    class _VersionHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            payload = b"23.3.15.29"
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _VersionHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        mod._PROBE_CACHE.clear()
        assert probe_clickhouse_version("127.0.0.1", server.server_address[1], "u", "p") == (23, 3)
    finally:
        server.shutdown()
        mod._PROBE_CACHE.clear()
