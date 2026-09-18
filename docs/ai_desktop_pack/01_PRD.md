# AI Desktop Development Infrastructure 0.1

产品需求文档（PRD）· 供产品经理立项/可行性评估

文档状态：评估稿  |  目标：验证“AI + Python Desktop + 领域工具基础设施”是否值得产品化。

# 1. 文档摘要

本项目不以“再做一个 PySide6 组件库”为目标，而是建设一套面向 AI Coding Agent 的 Python 桌面应用开发基础设施。第一阶段以 PySide6 为渲染层，向 AI 提供可机器理解、可组合、可验证的 UI 组件、页面模板、任务运行时、Pydantic 表单、主题系统、示例与 Skills/Context。长期可将 QML、Web 等作为替代渲染层。

# 2. 背景与问题

| **问题** | **现状** | **影响** |
| --- | --- | --- |
| 重复造轮子 | 每个小工具都重新写窗口、表单、文件选择、进度、日志、线程、错误处理。 | AI 生成快，但大量时间消耗在基础代码和调试。 |
| AI 上下文不足 | AI 知道 PySide6 API，但不知道团队自己的组件、规范、模板和项目约定。 | 生成代码不稳定，容易偏离设计与架构。 |
| UI 质量波动 | AI 容易产出“能运行”的 UI，但间距、层级、状态、异常、空态不一致。 | 工具可用但不够产品化。 |
| 跨项目复用困难 | 经验散落在历史项目里，缺少标准化能力注册与检索。 | 越做越多，却没有形成复利。 |
| 验证闭环缺失 | 代码生成后主要依靠人工运行和肉眼检查。 | AI 难以自动发现布局和交互问题。 |

# 3. 产品愿景

让 AI 从“从零编写桌面应用”转变为“根据需求选择并组合经过验证的 UI、任务、数据与领域能力”，使 Python 桌面工具从一次性脚本开发逐步变成可复用、可迭代、可验证的工程化生产流程。

自然语言需求\
↓\
需求理解 / 能力检索\
↓\
Template + Components + Domain SDK + Runtime\
↓\
AI 生成少量业务代码\
↓\
运行 / 截图 / 测试 / 修正\
↓\
可交付桌面工具

# 4. 产品定位

| **维度** | **定位** |
| --- | --- |
| 不是 | 单纯的 PySide6 Widget Library；不是单纯的 UI 设计系统；不是通用低代码平台。 |
| 是 | AI-native Python Desktop SDK + Skills/Context + Templates + Runtime。 |
| 首要用户 | 使用 AI 编程的 Python 开发者，尤其是频繁制作内部工具/RPA/Office/PDF/数据处理小工具的人。 |
| 首发技术 | Python + PySide6 + Pydantic；不在 MVP 阶段强行引入 QML/Web。 |
| 长期方向 | 统一抽象 UI Schema / Tool Definition，使 PySide6、QML、Web 可以共享上层语义。 |

# 5. 目标用户与典型场景

| **用户画像** | **核心诉求** | **典型项目** |
| --- | --- | --- |
| Python 工具开发者 | 快速交付桌面 GUI | Excel/PDF/Word/图片/文件批处理工具 |
| RPA 开发者 | 统一任务、日志、进度、参数界面 | 浏览器自动化、办公自动化、批量任务 |
| AI Coding 重度用户 | 让 Agent 更准确地复用已有能力 | Cursor/Claude Code/Codex 辅助开发桌面工具 |
| 内部工具团队 | 统一 UI、运行时和发布方式 | 内部数据工具、审核工具、转换工具 |

# 6. MVP 产品范围

| **模块** | **MVP 要求** | **优先级** |
| --- | --- | --- |
| App Runtime | 统一 App 生命周期、主窗口、通知、异常、日志、任务、配置。 | P0 |
| 基础 UI Kit | FileInput、FolderInput、Form、DataTable、TaskPanel、LogPanel、Dialog、PropertyEditor。 | P0 |
| Pydantic Form | 从 Pydantic Model/Field Metadata 生成基础表单与校验。 | P0 |
| Design Tokens | 颜色、间距、字体、圆角、阴影、状态等统一 token；避免散落 QSS。 | P0 |
| Templates | Batch Tool、Excel Tool、PDF Tool、Data Tool、Settings 五类模板。 | P0 |
| AI Skills | GUI 规则、组件用法、模板选择规则、代码规范、反模式。 | P0 |
| Registry | 组件/模板/能力的机器可读目录，支持按能力检索。 | P1 |
| AI Tooling | 提供本地文档/MCP/命令行上下文入口，便于 AI 获取组件信息。 | P1 |
| Visual QA | 启动工具并截图，形成基础 UI smoke test/人工复核流程。 | P1 |
| QML/Web Renderer | 不纳入 MVP，仅保留抽象层设计约束。 | P2 |

# 7. MVP 用户流程

1. 开发者提出自然语言需求，例如“做一个 Excel 批量合并工具”。
2. AI 识别场景并读取 Skills/Registry，发现 Excel Tool Template、FileInput、TaskRunner、DataTable 等能力。
3. AI 创建项目骨架，业务代码只负责 Excel 处理逻辑。
4. 运行项目，统一 Runtime 负责日志、任务状态、错误提示和配置。
5. 根据 UI smoke test 或人工反馈继续让 AI 修改。
6. 项目最终保留清晰的业务代码，并可脱离 AI 独立运行。

# 8. 功能需求明细

## 8.1 App Runtime

- 统一 QApplication 与窗口生命周期；
- 统一异常捕获、用户可读错误和日志；
- 统一 TaskRunner/QThread/Worker 模式，禁止阻塞 UI 线程；
- 提供通知、状态栏、配置、应用退出清理等基础能力。

## 8.2 UI Kit

- 采用“业务级原语”而非只封装 Button/Label；
- 组件必须有稳定默认值、状态定义、示例、类型提示；
- 组件 API 优先简单、可组合、便于 AI 生成。

## 8.3 Schema 驱动 UI

- Pydantic Model 是表单定义的重要来源；
- 支持字段描述、默认值、选项、文件类型、必填、敏感字段等 metadata；
- UI 校验逻辑与数据模型保持一致。

## 8.4 Templates

- 每个模板提供完整可运行示例；
- 模板优先覆盖高频工具场景；
- 模板必须允许 AI 只替换业务逻辑而不重写基础设施。

## 8.5 AI Context / Skills

- 提供规则、示例、组件能力说明、选择条件、反模式；
- 内容必须可被 CLI/MCP/Agent 上下文消费；
- 每个组件同时提供人类文档和机器可读描述。

## 8.6 Visual QA

- 启动应用并采集截图；
- 基础检查窗口尺寸、控件溢出、明显空白、错误状态；
- 高级视觉评分作为后续实验，不在 MVP 承诺完全自动设计。

# 9. 非功能需求

| **指标** | **MVP 目标** |
| --- | --- |
| 开发体验 | 安装 SDK 后 10 分钟内能生成第一个可运行 Tool。 |
| AI 成功率 | 标准 Demo 需求中，AI 首次生成即可运行的比例目标 ≥80%。 |
| 复用率 | Demo 项目基础代码中，至少 60% 来自 SDK/模板，而非重复手写。 |
| 稳定性 | 核心组件具备自动化单元/集成 smoke test。 |
| 启动体验 | 普通小工具不因 SDK 导致明显启动延迟或体积膨胀。 |
| 可维护性 | 业务层不直接依赖内部组件实现细节。 |

# 10. 成功指标与验证假设

核心假设：使用基础设施后，AI 开发桌面工具的“交付时间/可运行率/一致性”显著提升。建议以同一组需求进行 A/B 对照，而不是凭感觉判断。

| **指标** | **对照组** | **实验组** | **建议目标** |
| --- | --- | --- | --- |
| 首个可运行版本时间 | AI 从零写 PySide6 | 使用 SDK + Skills | 下降 ≥50% |
| 首次运行成功率 | 从零生成 | SDK 组合生成 | 提升至 ≥80% |
| 基础代码重复量 | 从零生成 | 模板/组件 | 下降 ≥60% |
| 人工修 UI 次数 | 从零生成 | Design Tokens + Patterns | 下降 ≥40% |
| AI 上下文长度 | 通用框架文档 | 本地 registry/context | 关键任务上下文明显缩短 |

# 11. 明确不做

- 第一阶段不重造 PySide6 原生控件生态；
- 第一阶段不追求全平台跨端；
- 第一阶段不做通用低代码/可视化拖拽设计器；
- 第一阶段不做完整自动 UI 设计生成平台；
- 第一阶段不为了“现代化”而强制切换 QML/Web；
- 不把组件封装成不可修改黑盒，优先保证 AI 和开发者都能阅读源码。

# 12. 风险

| **风险** | **说明** | **缓解** |
| --- | --- | --- |
| AI 进步导致差异缩小 | 通用代码生成能力继续提升。 | 竞争力从代码转向领域 SDK、验证数据、Skills 和 Runtime。 |
| 抽象过度 | 过早设计复杂 DSL，反而增加 AI 使用难度。 | 先从 5–10 个真实工具反向抽象。 |
| 生态不足 | 只有组件，没有真实场景模板。 | 优先建设 Excel/PDF/RPA 等高频业务模板。 |
| 维护成本 | 基础设施升级可能影响大量工具。 | 稳定 API、版本、迁移指南、contract tests。 |
| 视觉 QA 不可靠 | 截图检查容易出现误判。 | MVP 只做 smoke test；高级视觉评估保持实验性质。 |

# 13. 里程碑建议

| **阶段** | **交付** | **验收** |
| --- | --- | --- |
| M0 验证 | 5 个真实工具的 A/B 基线 | 证明至少一个场景时间下降 ≥50% |
| M1 SDK 0.1 | Runtime + 8~10 个核心组件 + 3 个模板 + Theme | 5 个 Demo 均能运行 |
| M2 AI Context | Skills + Registry + 示例 + MCP/CLI 入口 | AI 能准确发现并复用组件 |
| M3 Visual QA | 自动启动/截图/smoke test | 发现常见 UI 回归问题 |
| M4 扩展 | 领域 SDK + 更多模板 | 形成复用数据与版本化资产 |

# 14. 产品经理评审问题

7. 目标用户是否足够集中？是否应先聚焦 Python 内部工具/RPA 开发者？
8. “AI 开发效率提升”是否足以成为产品价值，还是必须绑定一个具体业务领域？
9. Registry/Skills/MCP 哪一个应成为核心入口？是否需要同时支持？
10. 第一阶段是否继续坚定使用 PySide6，还是需要并行验证 QML/Web？
11. 是否应开放为开源 SDK + 商业工具服务，还是完全内部使用？
12. 如何定义长期护城河：组件、领域 SDK、数据、工作流还是发布平台？

# 15. 外部趋势参考

当前 AI-native UI 生态已出现“组件源码进入项目、机器可读文档、CLI/MCP、设计 token、AI 专用组件”等实践。AI Elements 面向 React/Next.js，强调组件直接进入代码库；Vayu UI 强调 AI-readable architecture、CLI 与 MCP；OpenUISpec 则进一步探索用语义 UI specification 作为 AI-native app 的单一事实源。它们验证了“让 AI 更容易消费 UI 基础设施”这一方向，但主要集中在 Web/React，因此 Python Desktop/Automation 仍存在差异化空间。

- AI Elements: https://elements.ai-sdk.dev/docs
- Vayu UI: https://www.vayu.design/
- OpenUISpec: https://github.com/rsktash/openuispec

# 16. 结论（供立项评估）

建议立项为“探索性基础设施项目”，而不是立即立项为大型框架产品。最优验证路径是：以现有 Python/PySide6 实际小工具为数据集，先做 SDK + Templates + Skills，再用 A/B 实验验证效率。如果能够稳定把开发时间、重复代码和 UI 修正成本显著降低，再扩大到 Registry、MCP、Visual QA 以及其他渲染层。
