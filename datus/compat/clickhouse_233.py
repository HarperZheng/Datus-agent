"""ClickHouse 23.3 元数据查询兼容层。

【问题背景】

datus-clickhouse 适配器查询元数据（表清单/视图清单）时生成的 SQL
在 ClickHouse < 23.5 上无法执行。2026-11-25 在 23.3.15.29 实测，
适配器发出的 SQL 是：

    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = 'fujian1105' and table_type in  ('BASE TABLE')

三处不兼容：
  1. ``information_schema``（小写）—— 23.3 只认大写 ``INFORMATION_SCHEMA``
  2. 列名 ``TABLE_SCHEMA``（大写）—— 23.3 视图里的列名是小写
  3. ``table_type in ('BASE TABLE')`` —— 23.3 该列是 Enum8 编码
     （Enum8('BASE TABLE'=1, 'VIEW'=2, 'FOREIGN TABLE'=3,
       'LOCAL TEMPORARY'=4, 'SYSTEM VIEW'=5)），比较只认数字索引，
     传字符串报 TYPE_MISMATCH

新版本（>=23.5）没有这些问题，适配器原生的 SQL 是正确的。

【方案：运行时替换（monkey patch），而不是手改 site-packages】

适配器包安装在 .venv/site-packages 里，不在任何 git 仓库中，手改会被
``uv sync`` 重装冲掉，且换服务器要重改。因此把修复写在本模块（随本仓库
分发），在"连接器创建后、首次使用前"这个空档，把适配器实例上出问题的
方法换掉。

替换的原理：Python 对象的方法本质是属性，实例属性会遮蔽类上的同名方法。
把兼容函数绑定为实例属性后，适配器内部代码照常调用 ``self._get_metadata(...)``
（属性查找先命中实例属性），实际执行的已是我们的兼容实现——适配器源码
一个字都不用动。

整个 bug 只存在于适配器的 ``_get_metadata`` 一个函数内（其余元数据路径
要么走 SHOW CREATE / DESCRIBE，要么内部转调它），所以只需替换这一个方法。
"""

import re
from types import MethodType
from typing import Any, Dict, List, Optional, Tuple

from datus.utils.exceptions import DatusException, ErrorCode
from datus.utils.loggings import get_logger

logger = get_logger(__name__)

# 23.3 的 INFORMATION_SCHEMA 中 table_type 列是 Enum8，比较只认数字索引。
# 2026-11-25 在 23.3.15.29 实测确认；若后续遇到其他 23.3.x 变体，以此为准微调。
_TABLE_TYPE_CODES = {
    "BASE TABLE": 1,
    "VIEW": 2,
    "FOREIGN TABLE": 3,
    "LOCAL TEMPORARY": 4,
    "SYSTEM VIEW": 5,
}

# 与适配器 METADATA_DICT 对齐：哪些对象类型带 table_type 过滤（view 不过滤）
_METADATA_TABLE_TYPES = {"table": ["BASE TABLE"], "view": None}

# 门控阈值：23.5 起适配器原生 SQL 可正常工作，不再替换
_COMPAT_MIN_VERSION = (23, 5)

# 适配器模块前缀：只对 datus_clickhouse 出品的连接器生效
_ADAPTER_MODULE_PREFIX = "datus_clickhouse"

# 实例属性名：标记"已替换过"，保证幂等
_PATCHED_FLAG = "_datus_ch233_patched"

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)")


def _is_target_connector(conn: Any) -> bool:
    """判断连接器是否为 datus_clickhouse 的产品（按所属模块判断）。"""
    return type(conn).__module__.startswith(_ADAPTER_MODULE_PREFIX)


def _server_version(conn: Any) -> Optional[Tuple[int, int]]:
    """探测服务器版本，返回 (主版本, 次版本)；探测失败返回 None。

    失败（网络抖动、权限等）时调用方会放弃替换——宁可退回原 bug，
    也不能在信息不足时盲目改行为。
    """
    try:
        # 与适配器内部一致，走 _execute_pandas，避免依赖不同执行通道的行为差异
        df = conn._execute_pandas("SELECT version() AS v")
        version_str = str(df["v"].iloc[0]).strip()
        match = _VERSION_RE.match(version_str)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception as exc:  # noqa: BLE001 —— 探测失败只影响是否打补丁，需吞掉
        logger.warning("ClickHouse compat: failed to probe server version: %s", exc)
    return None


def _get_metadata_compat(
    self: Any,
    table_type: str = "table",
    catalog_name: str = "",
    database_name: str = "",
) -> List[Dict[str, str]]:
    """``_get_metadata`` 的 23.3 兼容实现。

    函数签名与返回结构与适配器原版逐字段一致——本函数替换进去之后，
    适配器内部所有调用方（get_tables / get_tables_with_ddl /
    get_views_with_ddl / _get_objects_with_ddl）无需任何改动。

    与原版仅有的差异就是上文【问题背景】里的三处 SQL 写法。
    """
    self.connect()
    database_name = database_name or self.database_name

    # WHERE 条件：列名用小写（23.3 视图的列名就是小写，值部分照抄原版的转义逻辑）
    if database_name:
        safe_db = database_name.replace("'", "''")
        where = f"table_schema = '{safe_db}'"
    else:
        from datus_db_core import list_to_in_str  # 延迟导入，保持模块导入轻量

        where = f"{list_to_in_str('table_schema not in', list(self._sys_databases()))}"

    # 对象类型 -> INFORMATION_SCHEMA 里的表名（与适配器 METADATA_DICT 对齐）。
    # 未知类型直接报错——与适配器原版 _get_metadata_config 的行为一致，
    # 宁可显式失败，也不默默走错分支生成语义错误的查询。
    if table_type not in _METADATA_TABLE_TYPES:
        raise DatusException(
            ErrorCode.COMMON_FIELD_INVALID,
            message_args={"error_message": f"Invalid table type '{table_type}'"},
        )
    info_table = "VIEWS" if table_type == "view" else "TABLES"

    # table_type 过滤：把适配器配置里的类型名翻译成 23.3 认识的 Enum8 数字索引
    type_filter = ""
    type_names = _METADATA_TABLE_TYPES[table_type]
    if type_names:
        try:
            codes = ", ".join(str(_TABLE_TYPE_CODES[name]) for name in type_names)
        except KeyError as exc:
            raise DatusException(
                ErrorCode.COMMON_FIELD_INVALID,
                message_args={"error_message": f"Unknown table type for ClickHouse 23.3 compat: {exc}"},
            ) from exc
        type_filter = f"and table_type in ({codes})"

    query = (
        f"SELECT table_schema, table_name "
        f"FROM INFORMATION_SCHEMA.{info_table} "  # 23.3 只认大写 INFORMATION_SCHEMA
        f"WHERE {where} {type_filter}"
    )

    query_result = self._execute_pandas(query)

    # 与原版一致：把结果列名统一成大写，屏蔽不同版本返回列名的大小写差异
    query_result.columns = [c.upper() for c in query_result.columns]

    result = []
    for i in range(len(query_result)):
        db_name = query_result["TABLE_SCHEMA"][i]
        tb_name = query_result["TABLE_NAME"][i]
        result.append(
            {
                "identifier": self.identifier(database_name=db_name, table_name=tb_name),
                "catalog_name": "",
                "schema_name": "",
                "database_name": db_name,
                "table_name": tb_name,
                "table_type": table_type,
            }
        )
    return result


def ensure_clickhouse_233_compat(conn: Any) -> bool:
    """对单个连接器应用 23.3 兼容补丁（幂等，可重复调用）。

    调用时机：连接器创建之后、首次使用之前。本仓库统一挂在
    ``DBManager._build_conn``（所有数据库连接的唯一出口），因此
    check-db / REPL / 补全同步等所有路径自动覆盖。

    流程：
      1. 只处理 datus_clickhouse 的连接器（其他类型原样放行）
      2. 已替换过 -> 直接返回（幂等）
      3. 探测服务器版本，>=23.5 -> 不替换（适配器原生 SQL 本来就正确）
      4. 防御性检查适配器原方法还存在 -> 不存在说明适配器升级导致
         内部结构变化，告警并放弃（fail-open，让问题在日志里可见）
      5. 把兼容函数绑定为实例属性 —— Python 属性查找会先命中实例属性、
         遮蔽类上的原方法，此后适配器内部调 ``self._get_metadata`` 走的
         就是兼容实现

    返回 True 表示补丁已生效，False 表示未替换（环境不需要或前置不满足）。
    """
    # 1) 只针对 datus_clickhouse 的连接器
    if not _is_target_connector(conn):
        return False

    # 2) 幂等：同一实例只替换一次
    if getattr(conn, _PATCHED_FLAG, False):
        return True

    # 3) 版本门控：>=23.5 不需要兼容
    version = _server_version(conn)
    if version is None or version >= _COMPAT_MIN_VERSION:
        return False

    # 4) 防御：适配器升级若删除/改名了 _get_metadata（含被改成 None），放弃并告警
    if getattr(type(conn), "_get_metadata", None) is None:
        logger.warning(
            "ClickHouse compat: adapter no longer exposes _get_metadata; "
            "skip patching (datus-clickhouse may need a compat update)"
        )
        return False

    # 5) 执行替换：MethodType 把普通函数包成绑定方法，
    #    之后适配器调用 self._get_metadata(...) 时 self 会自动传入
    conn._get_metadata = MethodType(_get_metadata_compat, conn)
    setattr(conn, _PATCHED_FLAG, True)
    logger.info(
        "ClickHouse %s.%s detected: applied 23.3 metadata compat to connector",
        version[0],
        version[1],
    )
    return True
