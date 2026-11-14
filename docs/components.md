# 试点组件

只记录 Modern Desktop Workbench 这一阶段要用的控件。色板尚未冻结。

| 控件 | 导入 | 何时用 | 不要用它代替 |
| --- | --- | --- | --- |
| `Workspace` | `psi6.ui.workspace` | 一页里的工具栏、面包屑和左中右栏。`set_stretch` 决定还没拖过时的宽度；`set_pane_visible` 显隐栏，拖过的宽度按**栏名**记住，`state()` / `set_state()` 导出与恢复，`save_state()` / `restore_state()` 走 `ConfigStore`。留白跟随当前主题间距 | 侧栏换页（换页用 `AppShell`）、浮动或自由停靠窗口 |
| `TabView` | `psi6.ui.tab_view` | 多视图文档：按 `key` 复用控件，`add_tab` / `close_tab` 增删，可关闭、可拖动重排，全部关掉显示空态。`state()` 只记 `keys` 顺序和 `current`，`save_state()` / `restore_state()` 持久化到 `ConfigStore`；恢复时先用 `add_tab` 放回控件，再对齐顺序。`context_menu()` 挂页签右键菜单 | 侧栏换页（`AppShell`）或单页分栏（`Workspace`） |
| `ToolBar` | `psi6.ui.workspace` | 主要动作在左，次要动作在右 | 把开始、取消和进度排成任务条 |
| `Breadcrumb` | `psi6.ui.workspace` | 只显示当前位置 | 页面切换 |
| `DataTable` | `psi6.ui.data_table` | 结果预览。`sort_by` 或点击表头排序，`set_filter` 按显示文本筛选；排序和筛选保留选中行、当前行和滚动位置。双击发 `record_activated`（记录副本），需要行号时接 `row_activated`。行只存一份，筛选/排序只重排原始行索引，视图通过 `fetchMore` 分批取行，几万行不卡首屏。`set_reorderable(True)` 后可拖动一行改变原始顺序；有排序或筛选时拖动无效。`set_history` 后这次移动可以撤销 | 现在不要拿它当树表、分页网格或单元格编辑。那些如果要做，另起控件 |
| `ColumnPicker` | `psi6.ui.column_picker` | 列管理面板：勾选显隐、上下移动调序，`required` 的列不可隐藏。发 `columns_changed(keys)`，直接接 `DataTable.set_visible_columns`。`state()` / `set_state()` / `save_state()` / `restore_state()` 持久化到 `ConfigStore`。数据刷新（`set_rows`）后显隐与顺序仍在 | 塞进 `DataTable` 里做列菜单。列头右键用 `column_toggle_menu(...)`，完整面板才用 `ColumnPicker` |
| `pydantic_form` | `psi6.ui.form` | 由模型生成字段。`group` 分组，`search` 让选项可输入筛选 | 手写每个输入框。嵌套模型不会生成半截表单 |

校验错误显示在字段下面。控件里能选的值仍以模型校验为准。Qt 已经能表达的行为不再包一层；表格继续是结果表，不做成可编辑单元格。分组用 `Card`（弱边，需要时 `elevated=True`）。平面分区用 `Panel`。文件索引和设置页仍然不是卡片墙。

页内文字页签用 `UnderlineTabs`：底部主色条滑到当前项。可关闭的文档页签仍是 `TabView`，选中项底部也有同样的滑动条。

按钮正在提交时用 `set_loading(button, True)`。左侧转圈，文字还在，颜色不变，点击被挡住。`is_loading(button)` 读取这个状态。

窗口藏起后的入口不放进这张表：系统托盘用 `app.run(window, tray=True)`，没有托盘时用 `app.run(window, float_ball=True)`。悬浮球是置顶圆标，单击显示或隐藏主窗口，拖动换位置，不放进页面布局。

`TabView` 与 `Workspace` 的状态只记 **key / 栏名、顺序、显隐和宽度**，不记控件本身，所以文件里少写或多写几个 key 都不会丢掉已打开的文档；关闭标签只是把控件交还调用方（`setParent(None)`，不销毁）。布局写进应用数据目录的 `tabs.json` / `layout.json`，与窗口几何的 `window.json` 分开。两者都只做分栏与标签，不引入 `QDockWidget` 浮动窗口。

右键菜单：`DataTable` / `TreeView` / `TabView` 都提供 `context_menu(builder)`，用 `MenuAction` 描述项（图标、快捷键提示、危险项、勾选 / 单选、分隔线），`builder` 收到 `MenuTarget`（`kind` / `key` / `data` / `hit`）。右键落在未选中的行上会先选中它，菜单里的「选中项」才和行为一致。行数据是命中时的**快照**，别存下来当状态。要自己控制弹出时机（托盘、标题栏）时用 `build_menu(actions, host=...)`。菜单上的 `shortcut` 只显示文字。真正按键用 `ShortcutBook`，同一个窗口、同一个序列只登记一次；命令面板调用 `install(window)`（可传入同一本 `ShortcutBook`）。撤销用 `EditHistory`，`install` 接 Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z。

页签的关闭按钮用主题图形（`x` 字形，按当前 token 着色），不是 Qt 原生的方块：QSS 一旦写 `background` / `border` / `image` 就会接管 `QTabBar::close-button` 并吃掉 Qt 自带的叉号，所以图形由 `chrome.qss_icon_ref()` 统一生成。

## 动效

自绘控件要动画时用 `psi6.ui.motion`，不要各自建 `QPropertyAnimation`：

| 函数 | 用途 |
| --- | --- |
| `animate(obj, prop, start, end, speed=...)` | 给 Qt 属性做动画。`speed` 取 `fast` / `normal`，毫秒来自当前主题 |
| `animate_value(owner, start, end, on_value=...)` | 逐帧回调一个浮点值，用于不是 Qt 属性的量 |
| `stop(obj, prop=None)` / `stop_all()` | 停掉指定或全部动画 |
| `motion_enabled()` | 当前主题是否允许动画 |
| `easing(name)` | `standard` / `exit` / `emphasized` / `in_out` / `linear` |

统一入口做四件事：`reduced_motion` 打开时直接置终值不建动画；同一对象同一属性的旧动画先停，快速进出悬停不抖；运行中的动画登记在模块级列表，`finished` 后出队，不会因为 Python 回收而崩；时长只从 token 取，控件里不写毫秒。

`App.set_reduced_motion(True)` 是运行时的总开关：它把 `Tokens.reduced_motion` 置 1 后重套主题，两档时长归零，`motion` 随之走减少动效路径。功能不变，只是没有过渡。工作台的主题页有对应开关。

QSS 的 `:hover` 不能做过渡，所以悬停只改填充、不做淡入。这不是遗漏，见 [01 §组件动画清单](../design/0.7.0/01-visual-language.md)。

列管理按 ADR 0003 的约定**单独成控件**，不塞进 `DataTable`：`DataTable` 只提供 `columns()` / `visible_columns()` / `set_visible_columns(keys)` / `column_menu(builder)` 四个读写口，显隐走视图层 `setColumnHidden`、不动 `_columns`，所以 `cell_text(row, column)` 的列号语义不变；调序才改 `_columns` 顺序。`ColumnPicker` 负责面板与状态，`column_toggle_menu(columns, visible, on_toggle=...)` 生成「勾选每一列」的菜单项，适合挂列头右键。

## 机器可读索引

`python -m psi6 catalog` 列出全部公开控件，`--json` 输出名称、导入位置、构造参数、适用场景和替代关系，`python -m psi6 catalog DataTable` 查看单个控件。索引以 `psi6.ui.__all__` 为准，构造参数取自真实签名；新增公开名字却漏写说明时测试会失败。

`python -m psi6 check <目录>` 用 AST 检查业务代码是否绕开框架：直接创建 `QApplication`、手写 `QThread`、直接调用 `QFileDialog`、内联 QSS、`processEvents`，以及从 `psi6` 私有模块导入。`as` 别名按原名字判断；路径不存在或不是 `.py` 文件时报 `PSI007`。模板的 `python app.py --check` 已内置这组检查。

`python -m psi6 theme <名称> --check` 检查主题对比度，`--json` 输出全部 token 与诊断；自定义主题用 `模块:类名`。状态色 token 留空会自动推导，不必自己混色。控件描边是 `color_control_border`，留空时等于 `color_border`。

