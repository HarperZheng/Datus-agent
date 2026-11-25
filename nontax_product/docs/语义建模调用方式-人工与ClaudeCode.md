# 语义建模调用方式：人工与 Claude Code

> 前置：Web 服务已启动（`uv run datus --web --datasource yunnan0508 --host 0.0.0.0`，端口 8501，见部署文档第 8 章）。
> 建模材料：`nontax_product/docs/语义层建模设计手册-国库独立-fujian.xlsx`（xlsx 是二进制，agent 读不了，需整理成 md/txt 放进项目目录或直接粘贴在消息里）。
> 产出自动落盘：`subject/semantic_models/yunnan0508/<模型名>.yml`，并同步 Knowledge Base。

## 一、人工调用（推荐用于交互式建模、口径反复核对）

入口：浏览器打开 `http://<服务器IP>:8501`，三种方式：

1. **直接描述任务**：用自然语言描述建模需求，主 agent 自动派发给 `semantic_modeling`。首条消息把材料给足——表名、口径、参考 SQL，例如：

   > 请为 fujian1105 库建立语义模型：以 fab_item（物料项）为核心 dataset，关联 fne_paybook_full_high（支付台账）；参考口径：统计各月支付金额总额、支付笔数。相关表：fab_item、fne_paybook_full_high、fne_treasury_transfer_main。先用 describe_table 看清字段结构再建模，建完用 validate_semantic 校验。

2. **显式指定**：消息末尾加 `@Agent semantic_modeling`（怕自动派发不准时用）。

3. **切换当前 agent**：发送 `/agent semantic_modeling`，之后的消息都直接进建模子代理，适合连续多轮迭代。

   注意：旧的 `/semantic_modeling <消息>` 形式已废弃，会报未知命令。

## 二、Claude Code 调用（推荐用于批量、程序化推进）

Datus 提供三条被外部程序指挥的通道：

1. **CLI 单发模式（首选）**：`-p` 单条 prompt 跑完即退，`--subagent` 直接打开指定子代理，`--resume` 续接会话多轮迭代。

   ```bash
   uv run datus -p "为 fujian1105 建 fab_item 的语义模型，先 describe_table 看字段，定义 dataset 和两个指标：月支付金额总额、支付笔数" \
     --subagent semantic_modeling \
     --datasource yunnan0508 \
     --permission-mode auto
   ```

   Claude Code 的角色：读 xlsx 手册 → 拆解成一条条建模请求 → 逐条调上述命令 → 收集结果/报错 → 决定下一步。

2. **REST API**：`uv run datus-api` 起服务（Web 界面同款 `/api/v1/...`），聊天接口用 `subagent_id: semantic_modeling` 显式指定，适合可脚本化的建模流水线。

3. **MCP 工具**：`uv run datus-mcp` 只暴露工具层（查表、执行 SQL 等），不含 `semantic_modeling` 子代理的编排逻辑（创作规范、校验流程、KB 同步），不适合建模。

## 三、选择建议与已知限制

- 口径要反复对 → 人工（Web 界面人机对话最顺）；批量推进 → Claude Code 走 CLI 单发；集成进自动化系统 → API。
- 已知限制：`semantic_modeling` 的指标校验环节调用 `query_metrics`，在 ClickHouse 23.3 上触发部署文档附录 Bug 2（`Code 115 UNKNOWN_SETTING session_timezone`），修复未完成前指标执行校验会失败；`validate_semantic` 结构校验和普通 SQL 问答不受影响。
