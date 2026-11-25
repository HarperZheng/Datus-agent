# Datus Agent 可编辑部署步骤（含数据库连接测试）

> **适用环境**：Ubuntu 20.04+（glibc 2.28+，满足内置引擎 wheel 要求），x86_64/aarch64。
> **占位符**：`<path>`（部署父目录）、`<你的fork地址>`、`<数据源名>`、`<db_type>`。
> **部署完成标准**：`uv run datus --help` 正常执行 + 目标数据库连通测试通过。
> **范围说明**：运行托管（systemd 等）不在本清单内，部署完成后按需另定。

## 方案要点

| 决策 | 说明 |
|---|---|
| 可编辑安装 | `uv sync` 以 editable 模式安装源码，`git pull` 后代码改动即时生效，无需重装 |
| 全局 uv | 独立于 conda/python，各项目 `.venv` 互相隔离，无污染 |
| 分支部署 | 开发不能基于 main 分支，统一在 `separate_treasury_dataset` 分支进行 |
| 跳过 dev 组 | 服务器执行 `uv sync --no-dev`，不装 pytest/ruff/mypy 等开发工具 |

## 1. 全局安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc && uv --version
```

## 2. 新建二开分支 separate_treasury_dataset

```bash
cd <path>/Datus-agent
git checkout -b separate_treasury_dataset
git push -u origin separate_treasury_dataset
```

## 3. 运行时目录项目化

把全局运行时根从 `~/.datus` 调整到项目内。

```bash
cd <path>/Datus-agent

# 首次：从仓库模板创建项目配置（conf/agent.yml 已被 .gitignore 忽略，不会提交）
cp conf/agent.yml.example conf/agent.yml
```

在项目配置 `<path>/Datus-agent/conf/agent.yml` 中加入：

```yaml
agent:
  home: <path>/Datus-agent/.datus
```

生效后 sessions / data / workspace / cache 等运行时目录全部落在 `<path>/Datus-agent/.datus/` 下，与项目级覆盖配置（`.datus/config.yml`）、技能、日志同处一目录——Datus 在这台机器上的全部状态收敛进项目目录。

**.gitignore**：仓库自带的 `.gitignore` 已包含 `.datus/`（克隆后即生效），确认 fork 中保留了该行；若被删除则补回：

```bash
grep -q '^\.datus/$' .gitignore || echo '.datus/' >> .gitignore
```

## 4. 可编辑安装

```bash
# 显式固定 Python 3.12（项目要求 >=3.12，且部分 C 扩展依赖对新版本无预编译
# wheel，源码编译会因缺系统头文件失败——3.14 实测翻车；3.12 全部免编译）
uv python install 3.12
uv sync --no-dev -p 3.12

# 验证 editable 生效：输出应指向 <path>/Datus-agent/datus/...
uv run python -c "import datus; print(datus.__file__)"
uv run datus --help
```

## 5. 配置LLM 

配置文件在**项目内**：`<path>/Datus-agent/conf/agent.yml`（已在步骤 3 从模板创建；已被 `.gitignore` 忽略，各服务器独立、不会提交）。

编辑 `conf/agent.yml`，在 `agent:` 下写入 `models` 段（与步骤 3 的 `home` 同级；自部署端点不在 `conf/providers.yml` 清单内，走 `models` 自定义段）：

```yaml
agent:
  models:
    glm:
      type: openai
      base_url: http://112.49.22.42:18304/v1
      api_key: dummy
      model: GLM-5.3-Flash
```

激活该模型——在项目根 `.datus/config.yml` 中把 target 指向该自定义条目：

```bash
mkdir -p .datus && cat > .datus/config.yml <<'EOF'
target:
  custom: glm
EOF
```

## 6. 数据库连接测试

### 写入数据源配置

数据源直接写进项目配置 `<path>/Datus-agent/conf/agent.yml` 的 `services` 段，不走向导、不写脚本：

```yaml
services:
  datasources:
    yunnan0508:
      type: clickhouse
      host: 172.18.166.126
      port: 8123
      username: fujian1105
      password: "${CLICKHOUSE_PASSWORD}"   # 实际值放环境变量（见下），勿明文写入仓库
      database: fujian1105
```

> ClickHouse 不是内置连接器，需先安装适配器插件。用 `uv add`（同时写入 `pyproject.toml` + `uv.lock`，后续 `uv sync` 不会移除；**不要用 `uv pip install`**，下次 sync 会被清掉）：
>
> ```bash
> # --no-sync 先只登记依赖不安装，再由 uv sync --no-dev 统一安装，
> # 避免裸 uv add 顺带装回 dev 组工具（pytest/ruff/mypy 等）
> uv add --no-sync datus-clickhouse
> uv sync --no-dev
> ```

### 直接测试

```bash
cd <path>/Datus-agent
uv run datus-agent check-db --datasource yunnan0508
```

项目内置的连通性检查子命令：加载 `agent.yml` → 初始化 Agent → 对目标数据源执行 `test_connection`，成功输出 `Database connection test successful`，失败按输出排查地址/端口/凭据/防火墙。该命令会完整初始化 Agent，等于顺带验证了整份配置（含 LLM provider）。

- 密码环境变量注入：交互 shell 用 `set -a; source /etc/datus.env; set +a`（或写进 `~/.bashrc`）；systemd 场景由 `EnvironmentFile` 自动注入
- 冒烟（可选）：`uv run datus` 进 REPL 提问一条 SQL，LLM 与数据库两端同时验证
- ClickHouse 23.3 环境可能踩到兼容性 bug——`check-db` 连通通过也不代表没有，见文末「附录：已知 Bug」

## 7. 日常更新

```bash
cd <path>/Datus-agent
git pull origin separate_treasury_dataset
uv sync --no-dev            # 仅 uv.lock 变化时才真正装东西；--no-dev 保持不装 dev 组工具
# 更新后建议重跑步骤 6 的连接测试
# Bug 1 的兼容层在仓库代码内（见附录），更新后自动生效，无需任何手工操作
```

## 8. 启动步骤

### 启动 Web 界面

```bash
cd <path>/Datus-agent
uv run datus --web --datasource yunnan0508 --host 0.0.0.0
```

- 数据源密码已写在 `conf/agent.yml` 中，无需额外环境变量，直接启动即可
- 启动成功标志：日志出现 `Uvicorn running on http://0.0.0.0:8501`
- 默认端口 **8501**；`--host 0.0.0.0` 允许局域网其他机器通过服务器 IP 访问——**不加这个参数只能本机访问**（默认绑 127.0.0.1）
- 临时后台运行：`nohup uv run datus --web --datasource yunnan0508 --host 0.0.0.0 &` 或放进 tmux；systemd 常驻按"范围说明"另定

### 访问与验证（三步，从浅到深）

1. 浏览器打开 `http://<服务器IP>:8501`
2. 界面的库表目录应显示 `fujian1105` 的表清单——元数据链路 OK（ClickHouse 23.3 兼容层自动生效，无需人工干预）
3. 聊天框输入自然语言问题，如：

   > 统计 fab_item 表有多少行，并给我前 5 条数据看看

   返回行数和数据即全链路验证通过（GLM 生成 SQL → ClickHouse 真实执行）

### 注意

1. `--host 0.0.0.0` 意味着**局域网内任何人可访问**（当前无认证）——内网临时验证没问题，长期运行需收敛绑定地址或加网关层鉴权
2. **指标类问题**（走 `query_metrics` 路径）会触发附录 Bug 2（`Code 115 UNKNOWN_SETTING`），普通 SQL 问答不受影响
3. 若浏览器打不开但服务已启动，检查服务器防火墙是否放行 8501 端口

## 运行方式（部署之外，按需选择）

| 用途 | 方式 |
|---|---|
| 交互式 CLI | 直接 `uv run datus` |
| API/MCP 常驻后台 | systemd / tmux / supervisor 任选（另定） |
| 开发调试 | 终端随用随启 |

## 注意事项

1. **永远通过 `uv run <cmd>` 调用命令**：若机器上有 `~/.local/bin/datus` shim（一键脚本装的发布版），裸敲 `datus` 会运行发布版代码而非二开源码；拿不准就 `which datus` 检查。
2. **部署目录路径务必一致**（同为 `<path>/Datus-agent`），便于脚本化运维。
3. **首次 `uv sync` 需要联网**；之后 `uv run` 优先使用本地 `.venv`，如需严格离线可设 `UV_OFFLINE=1`。

## 附录：已知 Bug（ClickHouse 23.3）

> 以下问题在 **ClickHouse 23.3**（172.18.166.126 实测）出现，≥23.5 不受影响。**`check-db` 连通测试通过不代表没有这些坑**。

### Bug 1：`/tables` 元数据查询报 UNKNOWN_TABLE

- **触发**：REPL `/tables`、补全后台同步等一切元数据查询
- **原因**：`datus-clickhouse` 查元数据的 SQL 有三处不被 23.3 接受（2026-11-25 在 23.3.15.29 实测确认）：
  1. `FROM information_schema.TABLES`——23.3 只认大写 `INFORMATION_SCHEMA`
  2. WHERE 里大写列名 `TABLE_SCHEMA`——23.3 视图列名是小写
  3. `table_type in ('BASE TABLE')`——23.3 该列是 `Enum8('BASE TABLE'=1, 'VIEW'=2, ...)`，比较只认数字索引，传字符串报 TYPE_MISMATCH
- **修复**（已实现）：兼容代码在 separate_treasury_dataset 分支的 `datus/compat/clickhouse_233.py`，挂在 `DBManager._build_conn`（所有连接器创建的唯一出口）。程序建连接时自动探测服务器版本——<23.5 才把适配器的 `_get_metadata` 方法替换为兼容实现（大写库表名 + 小写列名 + Enum8 数字编码），≥23.5 原样放行
- **说明**：
  - 修复随 separate_treasury_dataset 分支分发，`uv sync` 不会冲掉，换服务器/升级 CH 自动适配，**无需任何手工补丁**
  - 适配器（`datus-clickhouse`）将来升级时需核对兼容层：它复刻了 `_get_metadata` 的签名与返回契约，单测 `tests/unit_tests/compat/test_clickhouse_233.py` 会在不匹配时报警

### Bug 2：query_metrics 报 Code 115 UNKNOWN_SETTING

- **触发**：dosi-engine 执行 query_metrics
- **现象**：`Code 115: Unknown setting session_timezone (UNKNOWN_SETTING)`
- **原因**：dosi-engine 0.1.13（Rust 原生扩展）执行 SQL 前硬编码追加 `SETTINGS session_timezone = 'UTC'`；该设置 ClickHouse 23.5 才引入，23.3 按设置名直接拒绝，与值无关（改时区无效）
- **定位**：二进制分析 `_native.abi3.so` 确认：值是写死的常量，dosi-engine 不读系统时区；`dry_run` 只编译不执行，所以测不出该问题
- **修复**：尚未实现。此前记录的实现（`dosi/engine.py` 挂兼容切面 + `ch_compat.py` 进程内反代）未进入当前 separate_treasury_dataset 分支，待按原设计重新实现：非本机 CH 连接时 dosi 的 HTTP 流量改走进程内反代（`ch_compat.py`，127.0.0.1 临时端口 daemon 线程），转发时剥掉 URL 里的 `session_timezone` 参数、把 body 里的 `dateTrunc('month',col)` 改写为 `toStartOfMonth(col)` 等 23.3 兼容函数
- **现状**：修复待实现，实现后需在真机 CH（172.18.166.126）完成三基准值验证
