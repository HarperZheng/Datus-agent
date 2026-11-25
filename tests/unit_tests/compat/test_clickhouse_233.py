"""Unit tests for the ClickHouse 23.3 metadata compat shim.

These tests never touch a real ClickHouse server: the fake connector mimics
only the surface the compat code relies on (_execute_pandas, _sys_databases,
identifier, database_name, connect). All version gating is driven through the
same _execute_pandas channel the production code uses.
"""

from types import MethodType
from unittest.mock import patch

import pandas as pd
import pytest

from datus.compat.clickhouse_233 import (
    _PATCHED_FLAG,
    _get_metadata_compat,
    ensure_clickhouse_233_compat,
)
from datus.utils.exceptions import DatusException

# 让假连接器"伪装"成适配器产品——ensure() 按所属模块判断目标
FAKE_MODULE = "datus_clickhouse.connector"


class FakeConnector:
    """仅实现兼容代码所依赖表面的假连接器。"""

    __module__ = FAKE_MODULE

    def __init__(self, version: str = "23.3.15.29"):
        self.database_name = "fujian1105"
        self.version = version
        self.executed_sql: list = []

    def connect(self):
        return None

    def _sys_databases(self):
        return {"INFORMATION_SCHEMA", "information_schema", "system"}

    def identifier(self, database_name: str, table_name: str) -> str:
        return f"{database_name}.{table_name}"

    def _execute_pandas(self, sql: str) -> pd.DataFrame:
        self.executed_sql.append(sql)
        if "SELECT version()" in sql:
            return pd.DataFrame({"v": [self.version]})
        return pd.DataFrame({"table_schema": ["fujian1105"], "table_name": ["orders"], "table_type": [1]})


@pytest.fixture
def fake_cls():
    """每个用例拿一个干净的假类（去掉上一用例留下的补丁痕迹）。"""

    class FakeConnectorForTest(FakeConnector):
        def _get_metadata(self, table_type="table", catalog_name="", database_name=""):
            return [{"original": True}]  # 原版实现标记，用于断言"替换是否发生"

    FakeConnectorForTest.__module__ = FAKE_MODULE
    return FakeConnectorForTest


class TestVersionGate:
    """版本门控：只有老版本才替换。"""

    def test_patches_on_23_3(self, fake_cls):
        conn = fake_cls("23.3.15.29")
        assert ensure_clickhouse_233_compat(conn) is True
        # 替换后调用走的是兼容实现，不再是原版标记
        assert "original" not in conn._get_metadata()

    @pytest.mark.parametrize("version", ["23.5.1.1", "24.8.1.1", "25.3.1.1"])
    def test_skips_on_modern_versions(self, fake_cls, version):
        conn = fake_cls(version)
        assert ensure_clickhouse_233_compat(conn) is False
        assert conn._get_metadata() == [{"original": True}]  # 原版原封不动

    def test_skips_when_version_probe_fails(self, fake_cls):
        conn = fake_cls("23.3.15.29")

        def broken_probe(sql):
            raise RuntimeError("network down")

        conn._execute_pandas = broken_probe
        assert ensure_clickhouse_233_compat(conn) is False
        assert conn._get_metadata() == [{"original": True}]

    def test_skips_unparseable_version(self, fake_cls):
        conn = fake_cls("not-a-version")
        assert ensure_clickhouse_233_compat(conn) is False

    def test_skips_non_adapter_connector(self, fake_cls):
        conn = fake_cls("23.3.15.29")
        conn.__class__ = type("OtherConnector", fake_cls.__bases__, dict(fake_cls.__dict__))
        conn.__class__.__module__ = "some_other_pkg.connector"
        assert ensure_clickhouse_233_compat(conn) is False


class TestIdempotency:
    """幂等：重复调用不产生二次包装。"""

    def test_double_call_patches_once(self, fake_cls):
        conn = fake_cls("23.3.15.29")
        assert ensure_clickhouse_233_compat(conn) is True
        first = conn._get_metadata
        assert ensure_clickhouse_233_compat(conn) is True
        assert conn._get_metadata is first  # 同一个绑定方法，没有被再包一层
        assert getattr(conn, _PATCHED_FLAG) is True

    def test_bound_method_passes_self(self, fake_cls):
        conn = fake_cls("23.3.15.29")
        ensure_clickhouse_233_compat(conn)
        assert isinstance(conn._get_metadata, MethodType)
        # 调用能拿到实例状态（database_name 来自 self）
        conn._get_metadata(database_name="fujian1105")
        assert any("fujian1105" in sql for sql in conn.executed_sql)


class TestAdapterUpgradeDefense:
    """防御：适配器升级导致原方法消失时，告警并放弃，不崩溃。"""

    def test_skips_when_original_method_missing(self, fake_cls):
        conn = fake_cls("23.3.15.29")
        with patch.object(fake_cls, "_get_metadata", None):
            assert ensure_clickhouse_233_compat(conn) is False


class TestCompatSqlContract:
    """兼容实现生成的 SQL 与返回结构契约。"""

    def test_table_sql_is_233_compatible(self):
        conn = FakeConnector("23.3.15.29")
        _get_metadata_compat(conn, "table", "", "fujian1105")
        sql = conn.executed_sql[-1]
        assert "FROM INFORMATION_SCHEMA.TABLES" in sql  # 大写库表名
        assert "table_schema = 'fujian1105'" in sql  # 小写列名
        assert "table_type in (1)" in sql  # Enum8 数字编码
        assert "information_schema" not in sql  # 不再出现小写库名

    def test_view_sql_has_no_type_filter(self):
        conn = FakeConnector("23.3.15.29")
        _get_metadata_compat(conn, "view", "", "fujian1105")
        sql = conn.executed_sql[-1]
        assert "FROM INFORMATION_SCHEMA.VIEWS" in sql
        assert "table_type" not in sql  # view 路径不过滤类型（与适配器 METADATA_DICT 对齐）

    def test_return_shape_matches_adapter_contract(self):
        conn = FakeConnector("23.3.15.29")
        result = _get_metadata_compat(conn, "table", "", "fujian1105")
        assert result == [
            {
                "identifier": "fujian1105.orders",
                "catalog_name": "",
                "schema_name": "",
                "database_name": "fujian1105",
                "table_name": "orders",
                "table_type": "table",
            }
        ]

    def test_empty_database_uses_sys_filter(self):
        conn = FakeConnector("23.3.15.29")
        conn.database_name = ""  # 连接器自身也无默认库，才会走系统库过滤分支
        _get_metadata_compat(conn, "table", "", "")
        sql = conn.executed_sql[-1]
        assert "table_schema not in" in sql

    def test_unknown_table_type_fails_loudly(self):
        conn = FakeConnector("23.3.15.29")
        with pytest.raises(DatusException):
            _get_metadata_compat(conn, "mv", "", "fujian1105")
