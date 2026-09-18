# AI Desktop Development Infrastructure 0.1

AI Skills / Context / Registry 规范

# 1. 目的

让 Coding Agent 能稳定发现、理解、选择和正确使用 AI Desktop SDK，而不是依赖模型对 PySide6 或项目历史代码的记忆。

# 2. Skills 分层

| **Skill** | **作用** | **典型内容** |
| --- | --- | --- |
| gui-fundamentals | 总体 UI 规则 | 布局、信息层级、状态、可用性 |
| pyside6-architecture | 工程规则 | App、Worker、Signal、生命周期 |
| component-selection | 选组件 | 何时用 FileInput/DataTable/TaskPanel |
| pattern-batch-tool | 批处理模板 | 文件→参数→执行→结果 |
| design-system | 视觉规范 | tokens、间距、Typography、状态 |
| python-project | 代码规范 | 类型、日志、异常、配置、测试 |
| visual-qa | UI 检查 | 启动、截图、常见回归检查 |

# 3. Component Registry 建议格式

name: FileInput\
kind: component\
description: 选择一个或多个本地文件并进行路径校验\
when_to_use:\
\- 用户需要输入文件\
avoid_when:\
\- 只需要一个字符串参数\
api:\
\- FileInput(...)\
states:\
\- empty\
\- selected\
\- invalid\
examples:\
\- examples/file_input_basic.py\
antipatterns:\
\- 直接在业务代码中调用 QFileDialog 并重复实现状态处理

# 4. AI 生成规则

1. 先搜索 Registry，再决定是否需要新建组件。
2. 已有组件能满足 80% 需求时优先复用，不复制实现。
3. 耗时操作必须通过 TaskRunner，不允许阻塞 UI 线程。
4. 表单优先从 Pydantic Model 生成。
5. 视觉样式优先使用 Design Tokens，不直接硬编码大量 QSS。
6. 错误处理、日志和用户通知必须使用 Runtime 统一能力。
7. 模板提供了整体页面结构时，不重新手写骨架。
8. 生成后必须运行 smoke test；核心 UI 任务尽量采集截图。

# 5. Context 注入策略

- 短任务：注入 global rules + 目标组件 manifest + 1 个示例；
- 中任务：加入对应 template + domain SDK manifest；
- 大任务：使用检索式上下文，仅注入当前任务相关能力；
- 避免把整个 SDK 源码一次性塞进上下文；
- 把“什么时候不要用某组件”作为一等知识。

# 6. MCP / CLI 入口建议

gui.list_components(query)\
gui.get_component(name)\
gui.list_templates(query)\
gui.get_template(name)\
gui.get_skill(name)\
gui.validate_project()\
gui.run_smoke_test()\
gui.capture_screenshot()

MVP 可先从本地 CLI 开始，再将同一 Registry 暴露为 MCP。这样可以避免先做协议、后找实际使用场景。

# 7. Skill 质量标准

| **标准** | **验收** |
| --- | --- |
| 可执行 | 规则能转化为具体代码选择，而不是泛泛而谈。 |
| 可验证 | 有 examples/test，AI 生成后可运行。 |
| 可检索 | 有明确 tags、name、when_to_use。 |
| 可演进 | 版本化，破坏性变更有迁移说明。 |
| 短上下文 | 单个任务只需要注入相关内容。 |

# 8. 反模式库

- 每个页面自己写 QSS；
- 每个工具自己实现进度/取消/日志；
- UI 线程执行文件扫描、Excel 解析、HTTP、浏览器操作；
- 为了一个小变化复制整套组件；
- 直接使用不稳定的内部组件属性；
- 没有示例就加入 Registry；
- 让 Agent 依赖“猜测”组件 API。
