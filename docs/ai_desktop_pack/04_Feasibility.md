# AI Desktop Development Infrastructure

可行性评估与实验方案

# 1. 评估目标

回答一个产品经理最关心的问题：这套基础设施是否真的让 AI 开发 Python 桌面工具更快、更稳、更容易维护，而不仅是“架构看起来漂亮”。

# 2. 最小实验集

| **实验** | **需求** | **难点** |
| --- | --- | --- |
| E1 Excel 批量工具 | 选择多个文件→处理→结果表→导出 | 文件、任务、表格、异常 |
| E2 PDF 工具 | 多文件→合并/拆分→进度→结果 | 文件、任务、预览 |
| E3 数据清洗工具 | 导入 CSV/Excel→参数→预览→导出 | Schema、表格、数据 |
| E4 RPA 工具 | 参数→步骤→执行→日志→截图 | 长任务、取消、状态 |
| E5 API 批处理 | 导入数据→请求→重试→结果 | 网络、重试、并发、日志 |

# 3. A/B 实验设计

A 组：直接让 Coding Agent 使用 PySide6 从零实现。B 组：限制其优先使用 AI Desktop SDK、Template、Skills 和 Registry。需求描述、模型、机器配置尽可能一致。

| **指标** | **采集方式** |
| --- | --- |
| 从开始到首次运行 | 计时 |
| 首次运行成功/失败 | 自动测试 |
| 人工修复次数 | 记录 commit/对话 |
| 基础代码行数 | 静态统计 |
| 重复代码比例 | 与 SDK 相比计算 |
| UI 问题数 | 人工 checklist + screenshot review |
| AI token/context | 记录 agent 输入输出 |
| 维护成本 | 追加一个需求后重新计时 |

# 4. Go / No-Go 标准

| **结果** | **建议** |
| --- | --- |
| ≥50% 开发时间下降，且质量不下降 | 继续投入，并扩大模板与领域 SDK。 |
| 20%~50% 时间下降 | 继续小规模验证，优化抽象和上下文。 |
| <20% 时间下降 | 暂停扩张，检查是否应该聚焦具体领域，而非通用 GUI 基础设施。 |
| 速度提升但 Bug/维护显著增加 | 判定抽象失败，优先简化 API 和 Runtime。 |

# 5. 外部竞品/方向验证

| **项目/方向** | **观察点** | **对本项目的启示** |
| --- | --- | --- |
| AI Elements | React AI-native components、CLI、源码直接进入项目 | 组件 + source-first + AI context 已被验证。 |
| Vayu UI | AI-readable architecture、MCP、CLI、design tokens | Registry/MCP/Token 是可产品化能力。 |
| OpenUISpec | 语义 UI spec + MCP/CLI + 多 renderer | 长期可考虑 UI Schema，而不是绑定 PySide6。 |

# 6. 差异化机会

- Python Desktop + AI Coding；
- Office/PDF/File/RPA 领域原语；
- 单进程 PySide6 + Worker 的简单可靠运行时；
- 面向真实小工具的业务模板，而非只做基础控件；
- 本地离线优先，适合企业内部工具；
- 把组件、领域能力、Skills、模板和测试数据沉淀为可复用资产。

# 7. 产品路线选择建议

阶段 1：AI Desktop SDK / PySide6\
阶段 2：Registry + CLI/MCP + Visual QA\
阶段 3：Excel/PDF/RPA/Browser Domain SDK\
阶段 4：抽象 UI Schema\
阶段 5：按实际需求评估 QML / Web renderer

# 8. 最大的战略风险

最大的风险不是“PySide6 会不会过时”，而是把大量精力投入到一个 AI 轻易可以重新生成的低层封装层。为了规避这一点，所有研发优先级应按“真实项目复用率”和“AI 交付指标”决定，而不是按“组件数量”决定。

# 9. 建议产品经理最终输出

1. 明确目标用户与首发场景；
2. 确认 MVP 是否聚焦 Python Desktop/RPA；
3. 确定是否按内部研发基础设施还是对外产品推进；
4. 确定 5 个实验项目和成功阈值；
5. 确定 SDK API 的开放/开源策略；
6. 形成 Go/No-Go 结论与下一阶段预算。
