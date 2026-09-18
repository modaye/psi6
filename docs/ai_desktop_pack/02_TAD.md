# AI Desktop Development Infrastructure 0.1

技术架构设计（TAD）

# 1. 架构原则

- 业务代码与 UI 基础设施解耦；
- AI 优先消费“语义 API + 示例 + 机器可读元数据”；
- 组件可组合、可观察、可测试；
- Schema 优先于手写表单；
- Runtime 统一处理任务、日志、错误和配置；
- 先单进程 PySide6，只有明确需要时再引入多进程；
- 保留未来 QML/Web renderer 的抽象边界，但不提前实现。

# 2. 分层架构

AI Agent / Coding Agent\
│\
├── Skills / Rules\
├── Registry / Manifest\
└── Examples / Templates\
│\
▼\
AI Desktop SDK\
├── ui        UI 组件与页面模式\
├── forms     Pydantic → UI\
├── runtime   App/Task/Log/Config/Error\
├── domain    Excel/PDF/File/Browser/RPA 能力\
└── theme     Design Tokens\
│\
▼\
Renderer Adapter\
│\
└── PySide6（MVP）\
│\
▼\
Desktop Application

# 3. 推荐代码组织

ai_desktop/\
├── core/\
│   ├── app.py\
│   ├── lifecycle.py\
│   └── exceptions.py\
├── runtime/\
│   ├── tasks.py\
│   ├── logging.py\
│   ├── config.py\
│   ├── notifications.py\
│   └── storage.py\
├── ui/\
│   ├── inputs/\
│   ├── data/\
│   ├── task/\
│   ├── dialogs/\
│   ├── forms/\
│   └── pages/\
├── theme/\
├── registry/\
├── templates/\
└── skills/

# 4. 核心技术设计

## 4.1 TaskRunner

统一后台任务抽象。UI 线程只负责状态展示；业务工作在 Worker/QThread 中执行。Task 必须具备 queued/running/succeeded/failed/cancelled 等状态。

## 4.2 Pydantic Form

读取 BaseModel、Field metadata、Enum/Literal 等信息，映射为输入控件；模型负责最终校验。

## 4.3 DataTable

优先支持 DataFrame/Model 列定义、分页/排序/筛选，避免每个工具重新实现。

## 4.4 Theme

所有视觉属性由 token 提供；组件不直接散落硬编码 QSS。

## 4.5 Registry

每个能力有 name、description、when_to_use、api、examples、dependencies、anti_patterns 等信息。

## 4.6 Template

模板是“可运行的业务骨架”，而不是静态代码片段；必须经过真实项目验证。

## 4.7 Renderer Boundary

上层对象只描述语义，不直接依赖 QWidget 实现细节，为后续 QML/Web 留接口。

# 5. 组件 Contract

| **字段** | **要求** |
| --- | --- |
| 名称 | 稳定、语义化，例如 FileInput 而不是 CustomWidget12。 |
| 用途 | 明确 what/when/why。 |
| Props/API | 尽量少而稳定；提供类型提示。 |
| States | 明确 loading/disabled/error/empty/success 等。 |
| Example | 必须有最小可运行示例。 |
| Test | 至少有 smoke test；核心组件有行为测试。 |
| AI Metadata | 提供机器可读描述，避免 AI 只能猜。 |

# 6. 进程模型

MVP 推荐“单 UI 进程 + Worker/QThread 任务隔离”。不要为了架构先进而把每个工具或每个插件都拆成独立进程。未来只对高风险、崩溃敏感、第三方运行时冲突等能力增加可选子进程执行器。

# 7. 领域 SDK

| **领域** | **推荐能力** |
| --- | --- |
| Excel | 读写、预览、列映射、批处理、结果导出 |
| PDF | 合并、拆分、提取文字/图片、预览 |
| File | 批量选择、拖拽、目录扫描、路径校验 |
| Browser/RPA | 任务状态、步骤展示、截图、日志 |
| Office | Excel/Word/Outlook 常见自动化封装 |
| AI | ChatPanel、ToolCallViewer、ApprovalPanel 等（可后续单独扩展） |

# 8. 发布与版本

建议采用语义化版本。SDK API 分为 public/private；模板与组件都必须有兼容性标记。对于破坏性变更，提供 codemod/迁移说明。基础设施升级前运行所有 Demo Project contract test。

# 9. 技术选型结论

| **方案** | **MVP 判断** | **理由** |
| --- | --- | --- |
| PySide6 | 首选 | 与 Python/RPA/Office/数据处理天然衔接，降低开发复杂度。 |
| QML | 第二阶段评估 | 适合现代动画/视觉，但不是解决 AI 重复造轮子的首要问题。 |
| React/Web | 长期可选 | 适合平台化/Agent UI，但会引入 Python ↔ Web 通信复杂度。 |
| Tauri/Flutter | 暂不优先 | 需要较强理由才能抵消 Python 领域能力复用损失。 |
