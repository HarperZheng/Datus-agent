# Dosi 语义建模参考文档清单

> 以下文档均在 Datus-agent 仓库内，中文版文件名以 `.zh.md` 结尾（同目录有对应英文版）。
> 阅读顺序即序号顺序。

1. **`nontax_product/docs/语义层建模设计手册-国库独立-fujian.xlsx`** —— 项目专属建模手册（fujian 库），建模范围与口径以此为准，最优先阅读。

2. **`docs/subagent/semantic_modeling.zh.md`** —— 核心工作流：`semantic_modeling` 子代理如何建模。定义四类对象（Dataset / Field / Relationship / Metric）、如何提供来源（表名 / SQL / 需求文档）、如何校验（`validate_semantic` / `query_metrics` / `verify_semantic_outputs`）。建模实操就是在聊天里驱动这个子代理完成。

3. **`docs/getting_started/contextual_data_engineering.zh.md`** —— 端到端实战教程：从建库到"通过校验的 Dosi YAML 写入 `subject/semantic_models/`"的完整流程。

4. **`docs/knowledge_base/semantic_model.zh.md`** —— 语义模型结构：模型 / dataset / field / relationship / metric 各自的作用。模型文件存放路径为 `subject/semantic_models/<datasource>/<模型名>.yml`（本项目即 `subject/semantic_models/yunnan0508/`）。

5. **`docs/knowledge_base/metrics.zh.md`** —— 指标定义规范：name、expression、三级 subject_path 分类、时间维度、窗口行为等字段。

6. **`docs/semantic/dosi_engine.zh.md`** —— Dosi 引擎机制：模型文件如何被发现、每个模型文件一个引擎实例、文件变化自动刷新、大盘指标查询的编译逻辑。

7. **`docs/subagent/ask_metrics.zh.md`** —— 建模完成后的"问数"：`ask_metrics` 子代理如何做指标问答。

8. **`docs/subagent/ontology_analyst.zh.md`** —— （可选）Apache Ossie ontology 映射文档，多个数据源需要共享业务概念时才需要。

9. **`docs/subagent/gen_dashboard.zh.md`** —— （可选）建模完成后生成看板。

## 实操提示

- 建模不需要手写 YAML：在 Web 界面（`http://<服务器IP>:8501`）里让 `semantic_modeling` 子代理对照上面第 1 项手册和 fujian 库的真实表结构建模，产出自动落到 `subject/semantic_models/yunnan0508/` 并同步 Knowledge Base。
- 已知限制：建模后的校验环节会调用 `query_metrics`，而部署文档附录 Bug 2（dosi-engine 在 ClickHouse 23.3 上报 `Code 115 UNKNOWN_SETTING`）尚未修复，校验会因此失败。普通 SQL 问答不受影响；Bug 2 修复完成前，指标校验环节会被挡住。
