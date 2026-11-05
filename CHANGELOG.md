# 变更

## 未发布

- **托盘单击与悬浮球**。托盘左键在窗口最小化时改为展开，双击不再连着再切换一次。菜单按窗口是否展开启用「显示 / 隐藏」，`add_action` 可在「退出」前追加动作，`set_status` 把短状态附在提示上，气泡改用当前主题图标。新增 `FloatBall`：置顶圆标，拖动换位置，单击显示或隐藏主窗口，右键退出。`App.run(..., float_ball=True)` 不依赖系统托盘，关窗口后进程仍留着。圆标自己就是窗口，摆好位置再显示，不放进页面布局。

- **`TaskRunner` 可观察，关闭后不再接收新任务**。`started` / `finished` 在界面线程给出这一次的 `TaskHandle`。`progress` 保留最新进度，界面回调仍按间隔合并。`on_finished` 声明一个参数时收到句柄，原来的无参回调不变。同一槽位的占用在锁里判断，两个线程同时提交只会跑一份。`shutdown` 之后 `submit` 抛 `RuntimeError`。跨线程信号在运行器已销毁时不再把工作线程带崩。任务依赖和退出后仍保留的队列仍不加入。

- **基础能力补齐**（国际化仍不做；任务持久队列仍等真实应用提出再加）：
  - `ShortcutBook` 把快捷键登记到窗口，同一序列只保留一条命令。`CommandPalette.install` 让条目上的 `shortcut` 真正按键触发并发出 `activated`。右键菜单里的 `shortcut` 仍只是提示，避免同一个动作在多处菜单里各注册一遍。
  - `EditHistory.push(label, apply=, revert=)` 提供撤销 / 重做。`install` 接上 Ctrl+Z、Ctrl+Y、Ctrl+Shift+Z；焦点在输入框里时，这些键仍留给输入框自己。
  - `ConfigMigrations` 按整数 `version` 把旧 JSON 升到当前模型，传给 `ConfigStore.load` / `load_data` 的 `migrate=`。迁移失败时备份原文件并退回默认值。
  - `LogJournal` 把操作日志追加成 JSON 行，写盘在后台线程。`TaskRunner.submit(..., journal=)` 在工作线程把每条日志送进去，界面线程不写盘。
  - `DataTable.set_reorderable(True)` 后可拖动一行，改变 `rows()` 的原始顺序。排序或筛选进行中时拖动无效。`set_history` 之后这一步可以撤销；`set_rows` / `clear` 会使旧步骤失效。

- **启动时不再弹出独立窗口**：控件先进布局，初始不显示的只用 `hide()`。`Banner.set_notice` / `TagRow.set_labels` 在还没有父控件时不再 `show()`。`Workspace` 摘下分栏时仍先 `hide()`，挂回分栏之后才显示。

- **控件描边 token**：新增 `color_control_border`。输入框、普通按钮、勾选框、进度条、幽灵按钮和标签的描边走它；分隔线、卡片、对话框、表格仍用 `color_border`。留空时在 `resolve_states()` 里收成 `color_border`，所以浅色、深色和只改了 `color_border` 的自定义主题外观不变，需要把控件边和结构边分开时再写值。

- **列管理（`ColumnPicker` 独立控件）**：按 ADR 0003「列管理单独成控件，不塞进结果表」的约定落地。
  - 新增 `psi6.ui.column_picker`：`ColumnPicker` 列出全部列，勾选框控制显隐、上下按钮调序；`required=True` 的列不可隐藏。发 `columns_changed(keys)`，可直接接 `DataTable.set_visible_columns`。
  - `ColumnState`（`key` / `title` / `visible` / `required`）、`column_toggle_menu(columns, visible, on_toggle=...)` 生成列头右键的勾选项。
  - `state()` / `set_state()` / `save_state()` / `restore_state()` 持久化到 `ConfigStore`（默认 `columns.json`）。`set_state` 只按文件里出现的 key 重排，文件没提到的列留在原位；未知 key 忽略。
  - `DataTable` 新增 `columns()` / `visible_columns()` / `set_visible_columns(keys)` / `column_menu(builder)`。**显隐走视图层 `setColumnHidden`、不改 `_columns`**，所以 `cell_text(row, column)` 的列号语义不变；调序才重排 `_columns`。
  - 修掉一个真实缺口：`set_rows` 在未锁定列时重建 `_columns`，原本会丢掉列管理设过的显隐与顺序，现在会重新套用。
  - `attach_context_menu()` 的内部事件处理器改为显式接收容器，不再靠 `owner.parent()` 猜，因此同一容器可以挂多个不同来源（表格本体 + 列头）。
  - `python -m psi6 kit` 的「数据」页加入演示：右侧 `ColumnPicker` 与列头右键共用一份状态。

- **右键上下文菜单**：新增 `psi6.ui.context_menu`，`DataTable` / `TreeView` / `TabView` 都能挂右键菜单。
  - `MenuAction` 描述一项：`icon`（按 token 着色，换肤自动重画）、`shortcut`（只做展示提示，不注册真实快捷键，避免同一动作出现在多个菜单里冲突）、`dangerous`（用 `color_error` 画图标）、`checked` + `group`（同组自动互斥并补分隔线）、`separator=True` / `MenuAction.line()`。
  - 首尾分隔线自动去掉，连续分隔线合并；组切换时自动补一条线，把「选哪个」和「做什么」分开。
  - `context_menu(builder)` 挂到容器上，`builder` 收到 `MenuTarget`：`kind`（`table` / `tree` / `tabs`）、`key`（可见行号 / 节点 id / 页签 key）、`data`（行副本 / `TreeNode` / 标题）、`hit`（右键是否落在真实条目上）。右键落在未选中的行 / 节点 / 页签上会**先选中它**，菜单里的「选中项」才和行为一致。返回 `None` 或空列表表示这次不弹。
  - `TabView` 右键落在页签条空白处时退回当前页签；`DataTable` / `TreeView` 落在空白处时 `hit` 为 `False`，由调用方决定弹不弹。
  - 菜单图标按 `PaletteChange` / 屏幕变化重画，`build_menu(actions, host=...)` 可用于托盘、标题栏等自己控制弹出时机的场景。
  - 组件目录 `python -m psi6 kit` 的「多视图」页加了页签右键：关闭 / 关闭其他 / 关闭全部（危险项）。

- **页签关闭按钮改为主题图形**：原先活动页签上的关闭按钮是 Qt / Fusion 默认的橙底方块，浅色皮肤下与整页配色冲突。
  - QSS 只要写了 `background` / `border` / `image` 就会接管 `QTabBar::close-button` 并吃掉 Qt 自带的叉号，所以图形必须自己提供：复用既有的 `chrome.qss_icon_ref()` 机制（SVG 写进临时缓存目录、按 `psi6icon:` 前缀引用、按当前 token 着色），新增 `tab_close` / `tab_close_on` 两张图（`x` 字形，`color_muted` / `color_text`）。
  - 基础态背景透明、无边框；悬停用 `color_hover` 底 + `color_text` 图形，按下用 `color_pressed`。选中态不再有独立的「更重」的方块，选中只由标签底色表达。
  - 新增 `tests/test_tab_close_button.py`（4 用例：基础态用主题图形且背景透明、悬停 / 按下色、图形随主题重新着色、实际 App 样式表包含该规则）。
- **多视图文档与可持久化面板布局**（0.6.x Workbench 第 2 项）：新增 `TabView`，扩展 `Workspace`。刻意不做 `QDockWidget` 浮动窗口 / 自由停靠，只做「一页多份文档 + 栏显隐与宽度下次还在」。
  - `src/psi6/ui/tab_view.py`：`QTabWidget` + `QStackedWidget` + `EmptyState`。按 `key` 复用控件（`add_tab` 重复 key 只切换），`close_tab` / `close_all` 关闭时把控件交还调用方（`setParent(None)`，不 `deleteLater`），支持可关闭、可拖动重排、改标题、`current_key()` / `set_current()`；全部关掉自动切到空态，重新打开再切回页签。信号 `current_changed` / `tab_closed` / `tab_moved` / `layout_changed`，`_current_emitted` 去重避免一次操作播两遍。
  - `TabView.state()` 只记 `keys` 顺序和 `current`，**不记控件**：应用启动时先 `add_tab` 放回控件，再 `set_state()` / `restore_state()` 对齐顺序。状态里未知的 key 忽略、重复 key 去重、当前多出来的标签追加到末尾，因此文件里少写几个 key 不会丢掉已打开的文档；`current` 指向不存在的 key 也安全跳过。`save_state()` / `restore_state()` 走 `ConfigStore`，默认 `tabs.json`，可用 `state_file` 覆盖；文件缺失 / 损坏返回 `False` 且布局不变。
  - `src/psi6/ui/workspace.py`：新增 `visible_panes()` / `is_pane_visible()` / `set_pane_visible()`，`layout_changed` 信号，以及 `state()` / `set_state()` / `save_state()` / `restore_state()`（默认 `layout.json`）。隐藏只从分栏摘下控件、不销毁，随时可再显示；`_hidden: set[str]` 记显隐，`_pane_sizes: dict[str, int]` **按栏名**记宽度，隐藏一栏后其余栏的宽度不会因下标错位串掉；拖动释放时 `update` 可见栏宽度、保留隐藏栏上次的值。无效字段（未知 place、负数 / 字符串 / 布尔宽度、无有效宽度却写 `dragged`）一律跳过并回落到权重分配。
  - 登记 `TabView` 到 `psi6.ui.__all__` 与 `catalog._USAGE`，`Workspace` 的索引说明补上显隐与持久化；新增 `tests/test_tab_view.py`（15 用例），`tests/test_workspace.py` 追加 12 个用例（显隐不销毁、信号去重、按栏名保存宽度、状态往返、ConfigStore 往返、损坏 JSON、拖动保留隐藏栏宽度等）。README 新增「多视图文档与面板布局」章节，`docs/components.md` / `docs/adr/0003-workbench.md` / 常用配方同步，ADR 明确「不引入浮动停靠窗口」的边界。
- **`DataTable` 改为按需增量渲染（`fetchMore`）**：用户反馈「全量存 `_visible`、每次排序筛选重建列表，几万行会卡」。
  - `_rows` 仍是唯一一份行字典；`_visible` 从「行字典列表」改为**原始行索引**的有序序列：无筛选无排序时直接是 `range`（零拷贝），筛选 / 排序后才落成 `list[int]`。排序只重排索引、不再复制行字典，每行只算一次排序键。
  - `_RowTableModel` 新增 `canFetchMore()` / `fetchMore()` / `ensure_rows()`：首屏只发布 512 行，滚到接近底部由 `QTableView` 每批再取 256 行；`reload()` 重建后仍只发布首批。按绝对行号选中 / 恢复视图状态时按需发布对应行。
  - 排序 / 筛选保留选中行、当前行和滚动位置：行身份改用 `_rows` 原始索引（比 `id(row)` 更稳定），`reload(initial=published)` 保持已发布行数不倒退，避免已滚到中部的视图被弹回顶部；换整批数据（`set_rows` / `clear`）从首批开始。
  - `cell_text()` 直接按索引取行，不走 `QAbstractTableModel.index()`，读第 3999 行不会触发全量发布；`visible_rows()` / `selected_rows()` / `record_activated` 的副本语义与 `display_text` 钩子保持不变。
  - 新增 6 个用例：分批发布到 4000 行、零拷贝 `range`、按绝对行号读取不发布、`select_row(3000)`、排序不回弹且滚动位置保持、视图滚到底自动触发 `fetchMore`。
- **焦点环改为默认关闭、可按需开启**（`App(..., focus_ring=False)` 为默认）：
  - 用户反馈现有焦点样式实现不够好。现在 `App` 默认只生成 `outline: none` 抑制 Qt 原生焦点框，`:focus` 规则不画彩色环、也不改 `border` / `padding` / `min-height`，聚焦不产生任何视觉变化或尺寸位移。
  - `App.focus_ring` 读当前状态，`app.set_focus_ring(True/False)` 运行时切换并立即重套主题；`set_theme`、系统浅深色跟随、响应式密度切换都保留开关。`App(..., focus_ring=True)` 可构造时开启。
  - `build_stylesheet(tokens, *, focus_ring=True)`、`psi6_button_stylesheet(kind, tokens, *, focus_ring=True)`、`apply_theme(app, tokens, *, focus_ring=True)` 三个纯函数默认仍是开启，既保留全部 a11y 断言与离屏视觉验证，也让单独预览焦点环成为可能。开关存成 `QApplication` 的 `psi6FocusRingEnabled` property，保证 `restyle_themed_buttons` 与 `PaletteChange` 事件过滤器这两条逐控件重刷路径读到同一份状态。
  - 全局 QSS 的 6 处焦点规则（输入族 / 通用按钮 / 拖放区 / 页签 / 图标按钮 / 勾选指示器）与 6 组主题按钮的 `:focus` 片段统一由 `_focus_rules()` 条件生成；开启路径输出与原先一致，关闭路径只替换声明、选择器原样保留。
  - 组件目录 `kit` 显式 `focus_ring=True`（否则「状态矩阵」页的焦点态无法展示），并在「主题」页加 关闭 / 开启 两个按钮与状态说明。`test_theme.py` / `test_design_system.py` 里两处断言 App 当前 QSS 含焦点环的用例改为显式 `focus_ring=True`，原有 a11y 覆盖不回退。
  - 新增 `tests/test_focus_ring.py`（5 用例：纯函数两种输出、6 组按钮同步、App 默认关闭、构造时开启、运行时切换 + 换主题不丢开关），`tests/test_gallery.py` 补组件目录开关按钮用例。
- 新增**响应式密度雏形**（`App(..., density=...)` / `app.set_density_mode(...)`）：让主题 `style`（modern / compact）随窗口空间自动切换，而不是再加一条 `density` 轴（0.4.0 已刻意用 `style` 取代 `Theme.density`）。这里的 `density` 是 app 级运行时策略，不是主题属性，也不新增 token 字段。
  - 三种模式：`auto`（默认）在主窗口逻辑宽 / 高不足（`compact_max_width` 默认 760、`compact_max_height` 默认 540）或高 DPI（像素比 ≥ 2，阈值放宽 1.25 倍）时，把 `compact` 尺寸预设压到当前主题上；`modern` / `compact` 为手动固定。只覆盖尺寸度量，配色与主题显式 token 不动。
  - `auto` **只收紧、不放宽**：空间充足时沿用主题自带尺寸，显式选了紧凑主题或写了自定义度量的主题不会被悄悄改掉；只有手动 `modern` 才主动放宽。密度随 `_resolve_current()` 叠加，所以 `set_theme` 与系统深浅色跟随重套后依然生效。
  - `psi6.theme.style_metrics(style)` 公开返回某风格全部尺寸预设的副本；主题合成时仍由内部 `merge_style` 叠加。
  - `App.run()` 起窗后给主窗口装 `Resize` 事件过滤器，去抖 120ms，且只在「生效密度真正翻转」时重套 `apply_theme`，拖动窗口不会反复重算整张 QSS。过滤器吞掉回调异常，避免在 Qt 事件派发里抛错污染状态（沿用 Toast 段错误复盘结论）。
  - 新增 `tests/test_density.py`（14 用例：预设副本与校验、默认 / 非法模式、手动两向、auto 不放宽紧凑主题、切模式双向还原、随主题切换存活、窗口尺寸与高 DPI 判定、Resize 双向重套、同尺寸不重绘、手动模式忽略 resize、事件过滤器只认 Resize 且吞异常）。
- **响应式密度补齐手动入口与尺寸重排**（雏形的两个已知边界 + 文档/示例）：
  - `App.density_changed` 信号可 `connect`，参数是当前生效的尺寸风格 `compact` / `modern` / `theme`（`auto` 且空间充足、沿用主题自带尺寸）。手动切换与窗口 Resize 自动翻转都发；换主题、跟随系统浅深色不发。初始化、换主题、跟随系统、手动切密度、Resize 翻转五条路径统一收敛到 `App._apply_tokens()`，不会再有路径漏刷新。
  - `apply_theme` 新增 `refresh_metrics(app)` 广播：遍历 `allWidgets()` 及每个控件的整棵布局树，调用**可无参调用**的 `apply_metrics()`，让构造时缓存了间距 / 固定宽高的控件和自定义 `QLayout`（不是 `QWidget`，收不到 `StyleChange`）跟着密度重排；签名不合约定、C++ 对象已销毁或 hook 抛错只跳过该项，不污染 Qt 事件派发。这就补掉了「密度切换只重设全局 QSS、缓存尺寸组件不重排」的边界。
  - `FlowLayout` / `Composer` / `DropZone` 补 `apply_metrics()`：自动间距改读 `space_sm`，留白、最小高度、图标边长按 `metrics_scale()` 缩放，`modern` 下尺寸与原先完全一致；显式传过 `spacing` 的 `FlowLayout` 是调用方的选择，不被覆盖。`Icon.set_size()` 公开用于改边长。
  - `psi6.theme.runtime.metrics_scale()` 返回当前控件高度相对 `modern` 预设的比例（钳在 0.5 ~ 2.0），供没有对应 token 的硬编码留白缩放。
  - 组件目录「主题」页增加 自动 / 宽松 / 紧凑 三个密度按钮与当前状态说明，状态随 `density_changed` 自动更新（窗口拖拽触发的自动翻转也会刷新）；README 新增「响应式密度」章节，模板 `app.py` 展示 `density="auto"`。
  - 高 DPI 仍只是启发式阈值放宽（像素比 ≥ 2 时阈值乘 1.25），没有测屏幕物理尺寸；这是刻意保留的边界。
- 视觉自查发现并修复若干外观缺陷（离屏渲染逐屏核对 + 像素取样）：
  - **运行时换主题后主题化按钮不再换色**。主题按钮按控件单独设置样式表（不随全局样式表级联），换肤需重刷，但 `apply_theme` 里 `setProperty(_RESOLVED_TOKENS_KEY, t)` 写在 `setPalette()` **之后**，过滤器读到的是上一套 token；同时 `apply.py` 漏了 `QPushButton` 导入，`isinstance` 抛 `NameError` 又被 `except Exception` 吞掉，子控件按钮因此一直停在旧主题色（深色下主按钮仍是浅色主题的 `#2b5cd7`、幽灵按钮文字几乎不可见）。现把 token 写入提前到 `setPalette` 之前，并在样式表生效后显式重刷全部主题化按钮；补 `tests/test_theme.py::test_theme_switch_restyles_themed_buttons` 防止复发。
  - 画廊品牌方块补 `WA_StyledBackground`：纯 `QWidget` 子类不设该属性时 QSS 的主色背景与圆角不绘制，首屏左上角的 logo 块此前是隐形的。
  - `SegmentedControl` 水平尺寸策略改 `Fixed`：原先是 `Preferred`，放进竖向布局会被拉满整行（组件目录页与数据看板的「今日 / 本周 / 本月」横跨整个面板）。分段开关本就该贴内容宽度。
  - `DataTable` 表头改为与单元格一致左对齐：默认居中会让被拉伸的宽列表头飘到面板中间，与左对齐的单元格内容对不上。
  - 画廊分类标题提级（`color_text` + 字号 +1），此前比卡片标题还弱，首屏层级是倒的。
- 标准化示例入口 `python -m psi6 gallery`：web UI 风格的首屏，按「入门 / 数据与任务 / 组件 / 场景」分组列出可点击用例卡片，点开即用同一个 `App` 打开对应窗口，主题切换时所有已开窗口一起换肤。覆盖现有示例（最小窗口、文件批处理、后台任务、任务状态、组件总览、主题定制），并新增三个组合场景（数据看板、偏好设置、即时对话），演示 `StatCard` / `Sparkline` / `DataTable` / `SegmentedControl` / `TagRow` / `SettingsPage` / `MessageList` / `Composer` 等组件怎么拼成真实界面。主题定制单独起进程以保留其绿色主题。
- `Toast`（`src/psi6/ui/toast.py`）补齐进出场动画与读屏播报：右上角浮层栈（`ToastHost`）按内容长高、互不挤压、超出上限丢最旧。卡片进出场用 `heightForWidth` 返回动画中的当前高度并 `updateGeometry()` 驱动布局（在 `QVBoxLayout` 里直接 `setFixedHeight` 会被布局覆盖、动画不生效），缓出曲线 `OutCubic`，时长走 `token_ms` 且与 `reduced_motion` 联动（关闭时直接显隐，不做动画）。push 时通过 `QAccessibleAnnouncementEvent` 以 polite live region 方式把通知播报给读屏软件，读屏桥缺失或抛错时静默失败不阻塞通知。新增 `tests/test_toast.py`（7 用例，含动画不位移到底、reduced-motion 直显、出场动画结束后才从控件树移除、读屏播报与无桥安全）。修复一处离屏段错误根因：`sizeHint()` 返回 `QSize` 但漏了 `QSize` 导入，导致布局每次调用 `sizeHint` 抛 `NameError` 污染 Qt 事件循环、最终 access violation——任何动画方式都会因此崩，补上导入即解（与动画实现无关）。
- 新增 `TreeView` 树形组件（`src/psi6/ui/tree_view.py`）：只读层级结果视图，用于文件树 / 依赖树 / 大纲（文档明确"树表另起控件"）。提供 `TreeNode` / `TreeColumn` 数据模型，支持多列、嵌套节点、选中与激活信号、展开折叠（`expand_all` / `collapse_all` / `expand_to`）、空态与忙态、筛选保留祖先链；并支持 `child_loader` 懒加载（展开节点时才取子节点，走 `QAbstractItemModel.fetchMore`，适配大目录等大数据）。视觉沿用离屏验证：light / modern-dark / obsidian 三套主题渲染正常，背景色分别为 `#f6f8fa` / `#161c26` / `#151722`。已登记进 `psi6.ui.__all__` 与 `catalog` 机器可读索引，新增 `tests/test_tree_view.py`（11 个用例，含三层层级父链回溯与懒加载；其中发现并修掉一处 `parent()` 在深层树（≥3 级）把祖父节点当字典键导致的 `TypeError`）。
- 新增视觉回归 CI 门禁 `tests/test_visual_regression.py`：不依赖像素级基线（跨平台易碎），改为断言**不变量**——每套内置配色下，`primary_button` 填充 ≈ `color_primary`、`danger_button` 填充 ≈ `color_danger`；并额外要求深色基调主按钮不得仍是浅色基调的蓝（`#2b5cd7`）。这直接拦住本次发现过的那类回归（运行时切到深色主题后主题化按钮仍停在浅色配色）。离屏渲染 8 套主题（light / modern-dark / compact-dark / obsidian / pine / brass / mono / compact），按会话实际 `devicePixelRatio` 校正取样坐标，断言容差 24（欧氏 RGB 距离）。`Tokens` 本身没有 `base` 字段，是否深色由对应 `Theme.base` 判定。注意不要在测试模块里设 `QT_SCALE_FACTOR`——收集阶段导入会污染整个会话的几何/像素断言测试。已并入全量 `pytest`，CI 自动把关。
- 主题按钮（主 / 危险 / 幽灵 / 链接 / 分段 / 标签 / 折叠头 / 导航项）从全局样式表改为**按控件单独设置**：psi6.ui 各控件构造时调用 `apply_psi6_button_style`。原因：Qt 的 QSS 引擎在大型全局样式表里会用约 7 条顶层规则的窗口静默丢弃落在通用 `QPushButton` 之后过远的 `QPushButton#psi6*` 规则，八组按钮规则（约 38 条顶层规则）永远装不下一个全局表，导致全部退化为普通次级按钮外观；且全局表里那段顶层 `#` 行注释会把其后所有规则一并吞掉（QSS 只认 `/* */`）。改为按控件 `setStyleSheet` 是独立解析、不受该缺陷影响，主题切换由 `PaletteChange` 事件过滤器重新套用。相关测试改为校验 `psi6_button_stylesheet` 与各控件。
- `Banner` / `EmptyState` / `ActionBar` 补 `WA_StyledBackground`：纯 `QWidget` 子类不设该属性时 QSS 的背景与边框不绘制，横幅底色此前一直是空的。
- 消除键盘焦点下的原生焦点框（"浅色内部线条"）：`QPushButton` / `QLineEdit` 族 / `QTabBar::tab` / `QToolButton#psi6IconButton` 以及全部 8 种主题按钮的 `:focus` 规则统一加 `outline: none;`。Fusion 会在焦点控件的文字外侧用 QSS 的 `outline` 属性画一圈 1px 浅灰框（`PE_FrameFocusRect`），叠在 psi6 用 `border` 画的彩色焦点环内侧，形成双框。注意这和之前"不用 outline 画焦点环"是两回事——`outline: none` 是关掉原生框，必需且正确。验证发现 `QProxyStyle` 包 `Fusion` 在 psi6 里无效：`setStyleSheet` 会用默认 style 重建 `QStyleSheetStyle` 丢掉代理层，故只能靠 QSS 解决；且 offscreen 渲染不画原生焦点框，须真实显示平台抓图验证。

- 视觉修正一批：表格 / 树 / 列表行悬停改回中性 `color_hover`（浅色下不再几乎不可见）；输入框、按钮、导航项和页签聚焦加宽焦点环时同步收紧 padding 与 min-height，聚焦不再引起内容跳动；按钮按下保留主色边框；`psi6Ghost` / `psi6Link` / `psi6Segment` / `psi6Tag` 补上禁用态；菜单项内边距走 token 并补禁用置灰；滚动条与滑块增加悬停反馈；表头分隔线从纯白改为 `color_border_subtle`；`IconButton` 禁用态在着色表面不再露出画布底色；`QGroupBox` 上边距改用间距 token。
- `TitleBar` 关闭按钮悬停时图标切换为 `on_primary`：红色底上不再是深色图标，对比度达标。
- 修掉无边框按钮（主按钮、危险按钮、链接按钮、导航项、分段项）聚焦时的位移：这些控件基础边框为 0，聚焦加宽到焦点环宽度时若用有边框按钮的补偿公式，整颗按钮会瞬间高 2px、文字横移。改为按基础边框 0 重新推导 padding / min-height，并为链接按钮、分段项补上原本缺失的焦点环样式；禁用态的主/危险按钮统一成 `border: none` 以保持高度一致。
- 焦点环改用 `border` 绘制（外加 padding / min-height 几何补偿，保持外框尺寸恒定）。一度尝试用 `outline` + `outline-offset` 画外圈，但 Qt 的 `outline` 在控件内容矩形内绘制、加 offset 会向内收缩并压住文字（实测"取消"按钮出现错位蓝框），故回退。链接按钮聚焦改用下划线而非方框，文字链不套框。
- 浅色默认主题与 `Brass` 主题的 `color_focus` 原本与 `color_primary` 同值，导致焦点环和悬停边框同色、且链接按钮悬停"看起来没变化"（悬停色就是文字色）。现改为更亮的蓝 `#1565ff` / 更亮的暖棕 `#7d5f33`：既和强调色区分，也满足文字级对比度（`dark` / `obsidian` / `pine` / `mono` 本就不同值，未动）。
- 填充按钮（主按钮、危险按钮）的焦点环改用 `color_on_primary`：焦点色（color_focus）与主色面同色相，压在蓝色 / 红色面上只有约 1.2:1，远低于 WCAG 2.4.11 的 3:1，键盘聚焦几乎不可见。`color_on_primary` 专为填充色面设计（已是这两种按钮上的文字色），与面色 ≥4.5:1，外圈才看得清。对比度断言补进 `tests/test_theme.py`。
- 任务回调抛错不再留下登记和互斥槽。进度、日志和收尾走同一套保护：控件已销毁或回调自己出错只记到 stderr。
- 句柄提交后是 `queued`，工作函数开始才是 `running`。排队期间取消会直接结束，不必先进入 `running`。
- 未捕获异常先变成文本，再在界面线程弹窗。再次安装钩子会改绑当前窗口。
- 退出时保存几何、停止任务、释放单实例锁、隐藏托盘彼此隔开。任务没在时限内结束会写一行 stderr，后面的清理仍然执行。
- `DataTable` 没指定列时，每次 `set_rows` 按当前数据重推列，`clear` 会丢掉自动列。`rows()` 返回副本。指定了列的表清空后列还在。
- 配置写入改为同目录临时文件再 `os.replace`。损坏备份和默认值回落保持不变。
- 悬停仍用中性灰。表格、页签、侧栏当前项和分段选择改用强调色浅底，菜单高亮不变。默认主色未改。
- 新增 `Workspace`、`ToolBar`、`Breadcrumb`。文件索引改为工具栏加左右栏。`DataTable` 可以按列排序。`pydantic_form` 支持 `group` 和 `search`，字段错误留在控件下。组件目录增加壳、表单、检查和密度四页。`Workspace.set_stretch` 在拖动前分配栏宽，页边距跟随主题间距。色板尚未冻结。
- 根包和 `psi6.runtime` 改为惰性导入，`import psi6` 不再拉起 Qt。`psi6.schema` 提供不依赖 Qt 的字段标记，`jobs` 层可以单独使用。
- `DataTable.rows()` 始终返回源顺序；筛选和排序只影响 `visible_rows()`，第三次点击表头恢复原顺序。排序混合类型时不再因比较失败而抛错。
- 可选标量字段能保留 `None`：可选布尔是半选复选框，可选整数和浮点数留空即为 `None`。`default_factory` 会回填到编辑器。
- 表单与设置页共用 `ModelFormController` 和字段编辑器；回填只挡住绑定控件的信号。
- `ConfigStore` 拒绝越出应用数据目录的路径组件，写入改为同目录临时文件加 `os.replace`。`Workspace` 替换栏时解除旧控件的父子关系，`PathPicker` 的磁盘检查改为输入停顿后触发。
- 增加 ruff 检查与格式门禁。
- 新增 `python -m psi6 catalog`（加 `--json` 输出机器可读清单）：列出 `psi6.ui` 全部公开控件的名称、导入位置、构造参数、适用场景和替代关系。索引从 `__all__` 和真实构造签名生成，测试保证新增名字不会漏写说明。
- 新增 `psi6.spec` 和 `python -m psi6 check`：用 AST 检查直接创建 `QApplication`、手写 `QThread`、直接调用 `QFileDialog`、内联 QSS、`processEvents` 以及从 `psi6` 私有模块导入。模板的 `python app.py --check` 会先跑这组检查，再核对主题和任务页。
- `DataTable` 排序、筛选后按行身份恢复选中行和当前行，滚动位置不再跳回顶部；筛选匹配显示文本。双击新增 `record_activated`（记录副本），`row_activated` 仍给可见行号。`Playlist` 按内部索引激活，重复曲目不再点错。
- 图标按控件所在屏幕的像素比绘制；主题、屏幕或缩放变化时 `Icon` 和 `IconButton` 会重画。QSS 图标文件名对 `rgba(...)` 等颜色安全，超过 30 天的缓存会被清理。
- 异常钩子按 owner 登记，卸载一个窗口不会拆掉另一个窗口的钩子。
- `ConfigStore` 拒绝 Windows 保留设备名（`CON`、`NUL`、`COM1` 等）；文件损坏时回落默认值并写 warning 日志；保存后对文件和目录 `fsync`。文档明确配置文件是明文 JSON，密码和令牌应放系统钥匙串。
- 单实例激活消息带版本前缀并限制在 256 字节内，其他进程写入任意内容不再触发 `activated`；退出后恢复 `quitOnLastWindowClosed` 的原值，不再影响后续窗口。
- `python -m psi6 check` 解析 `as` 导入别名；输入路径不存在或不是 `.py` 文件时报告 `PSI007`，命令行仍返回 2。
- CI 增加 mypy 类型检查；wheel 冒烟测试改为在 Windows、macOS 和 Linux 都执行。
- 主题可以写 `base = "auto"` 跟随系统浅色/深色。类上给出 `light` / `dark` 两个 `Theme` 或 `Tokens` 变体时，配色取当前方案那一份，本类显式写的 `style` 和 token 覆盖压在它上面；没写变体就把覆盖套到系统底色上。`App` 收到系统方案变化时不再只认 `"auto"` 字符串，`base = "auto"` 的主题对象同样重套。
- `App(..., remember_theme=True, theme_choices=[...])`：`set_theme` 把选择写进 `theme.json`，下次启动覆盖 `theme` 参数。配置只存名字，所以能记住的只有注册过的主题（内置主题、`theme_choices`、`theme` 与 `set_theme` 用过的 `Theme`）；`Tokens` 没有名字，不写配置。新增 `app.theme_name`、按主题名切换（`set_theme("obsidian")`）和 `psi6.theme.builtin_themes()`。`theme.json` 里的名字认不出来时记一行 warning 并用默认主题。
- `apply_theme` 用 `font_family` / `font_size` 调 `QApplication.setFont`。以前字体族只出现在 QSS 里，没被样式表覆盖的原生控件和字体量度仍用 Qt 默认字体。
- `Sparkline` 和 `LogConsole` 跟随主题切换：前者在 `PaletteChange` / `StyleChange` 重画；后者把记录留在控件里，切换后整片按新配色重画。以前终端日志的颜色写进文档就定死了，换主题后旧行还留着上一套配色。
- `psi6.theme` 导出全部内置主题（`ModernDark`、`CompactDark`、`Mono`、`Obsidian`、`Pine`、`Brass`、`Compact`）和 `builtin_themes()`，主题选择器不必再从私有模块路径取。
- `Tokens` 增加状态色：`color_pressed`、`color_selected`、`color_primary_hover`、`color_primary_pressed`、`color_danger_hover`、`color_danger_pressed`。留空时由基础色推导，主题只改主色也会得到配套状态色；写值即覆盖。普通按钮、幽灵按钮、导航项、图标/标题按钮和拖放区按下时改用 `color_pressed`，不再退回画布色。
- `contrast_notes` 从正文/背景一对扩到十四对语义文字、焦点框与底色：卡片、浮层、辅助文字、主/危险/成功/警告/信息按钮、侧栏、用户气泡和焦点环。支持 `#aarrggbb`（Qt 顺序）与 `rgba()`，半透明颜色先叠到底色再算对比度。正文提示文案不变。
- 新增 `python -m psi6 theme`：列出内置主题；`theme obsidian` 打印 token；`--json` 给机器读；`--check` 只报对比度诊断，退出码 0 无问题、1 有诊断、2 主题无法加载。自定义主题用 `模块:类名`，例如 `theme myapp.theme:Desk`。

## 0.5.0

- `on_failed` 声明第二个位置参数时同时收到原异常对象。数据错误可以直接读异常上的结构，不再把错误码和说明塞进一段文字。单参数回调行为不变，堆栈仍在 `TaskHandle.error_traceback`。
- 新增 `psi6.runtime.logs.task_log`：任务执行期间任意调用深度都能写一行日志，不必把 `on_log` 逐层传下去。日志仍批量节流送回界面；任务之外调用回退到标准库 `logging`。
- `runner.submit(..., on_busy=...)`：同名 `exclusive` 槽还在跑时，被挡下的提交会同步触发一次 `on_busy`。不给则保持原来的静默行为。按钮禁用仍由界面负责。

以上三条来自第一个真实应用（DBS）的集成反馈。它自绘页眉、路径行和按钮，验证了 0.4.0 删除 `BatchToolWindow` 后的组合模型。

以下五条来自 DBS 与 HK 的第二轮反馈：

- 日志与进度缓冲加锁：joblib 等工作线程并发调用注入的 `on_log` / `on_progress` 不再丢记录，应用不必在外面自己加锁。应用的收尾回调抛错也不再污染 Qt 事件循环，错误打印到 stderr。
- `on_failed` 声明第三个位置参数时再带堆栈文本，可直接交给 `fail(..., detail=...)`。
- `runner.submit(..., on_finished=...)`：成功、失败、取消任一收尾后都执行一次，即使收尾回调自己抛错。界面用它恢复按钮；被 `exclusive` 挡下的提交走 `on_busy`。
- `App.remember_path` / `App.recalled_path`：界面路径记进 `QSettings`；恢复时路径已不在就清掉该项。程序参数仍走 pydantic 配置。
- 新增 `LogConsole`（`QTextBrowser`）：按时间往下滚的终端式日志。时间戳用辅助色，级别名和正文用该级别的主题色。`LogConsoleHandler` 用标准库 `logger.addHandler(console.handler())` 接入，工作线程会排队回界面线程。表格型 `LogPanel` 仍然保留。

以下来自第三个应用的集成反馈：

- `TaskRunner` 把提交线程的 `ContextVar` 带进工作线程。任务内部再开的线程不会自动继承，用 `psi6.runtime.logs.capture_task_context().run(...)`。
- `FormView.set_model` / `restore` 回填时挡住全部子控件信号，即改即存不会把还没回填的字段写成空。
- `FileInput` / `FolderInput` 默认带清除按钮（`clearable=False` 可关）。`path_changed` 仍随按键发出；`path_edited` 在编辑结束、浏览、拖放或清除后发出，用来保存。多个路径仍用分号分隔。

## 0.4.1

- 默认浅色和深色调色板重调：中性色带轻微冷色倾向，边框更细，浅色主色改为更明确的蓝，深色主色更透亮。字体栈优先 `Segoe UI Variable Text`。
- 新增内置主题：`Mono`（黑白极简）、`Obsidian`（深黑 + 靛紫）、`Pine`（墨绿）、`ModernDark`、`CompactDark`。`python -m psi6 kit` 的主题页可以预览。
- 修复勾选框和单选框：未选时画出边框矩形，勾选时填充主色并显示勾选图。焦点、悬停、禁用和半选（indeterminate）也各有样式。QSS 里的勾选图改用逻辑尺寸的 SVG，由样式表引擎按当前分辨率绘制，高 DPI 缩放下不再裁切、涂出界或起毛边。

## 0.4.0

- 不再提供 `BatchToolWindow` 和 `TaskPanel`。表单、结果和日志由应用自己组合。
- `DesktopWindow` 默认使用 Qt 标题栏。`frameless=True` 才使用自绘标题栏。
- 进度没有指定位置时用 `StatusProgress`，放在状态栏右侧。开始和取消是分开的按钮。
- 浅色主题的 `color_bg` 改为纯白 `#ffffff`。
- 默认窗口的客户区和状态栏使用主题底色。只有 `frameless=True` 时主窗口才透明，背景画在圆角壳上。
- 项目模板包含主题、任务页和 `python app.py --check`。业务写在模板的 `job.py`。
- 关窗口、点取消、应用退出是三件事。文件索引页按这个区分：关窗口不取消任务，取消按钮只发请求，退出才 `shutdown`。
- `Theme.style` 取 `modern` 或 `compact`，只决定尺寸。`base` 仍只决定浅色或深色。未写尺寸的主题改为现代度量：控件高 36、圆角 6。`density` 已删除，旧主题改写 `style`。
- 文字只有标题、正文、辅助三档。表面是窗口、面板、输入、浮层四层。选中用同一套悬停底加正文色。主按钮实心，次按钮描边，危险按钮用危险色。
- `python -m psi6 kit` 按组件分组，并有状态矩阵和四种组合。文件索引组合页放在同一窗口里。macOS、Linux 和 150% 缩放尚未在本机验证。

## 0.3.0

- 根包只导出框架入口：`App`、`TaskRunner`、`TaskHandle`、`TaskStatus`、`JobOutcome`、`Theme`、`Tokens`、`contrast_notes`、`DesktopWindow`、`TitleBar`、`TrayIcon`。控件改从 `psi6.ui` 导入；`BatchToolWindow` 在 0.4.0 移除。对照见 [MIGRATION.md](MIGRATION.md)。
- `cancel()` 只发出取消请求，`TaskHandle.cancel_requested` 立即为真。`status` 等工作函数结束后才变成 `cancelled`。`shutdown` 超时返回 `False`，不强制结束线程。
- `App` 只能在主线程使用。`run` 不能嵌套。已有 `QApplication` 时复用。
- `LogPanel` 默认最多保留 2000 条。
- 安装后可运行 `python -m psi6.examples.minimal --check`，以及 `task_job`、`custom_theme`、`task_status`。项目骨架在 `skills/psi6-desktop/template/`，不属于运行时依赖。

## 0.2.0

- `App.run` 默认允许多开，也不再记住窗口位置。需要时显式传入 `single_instance=True` 或 `restore_geometry=True`。
- 主题改为 Python 类（`psi6.theme.Theme`）。不再读取 JSON、TOML、YAML 主题文件，安装也不再需要 PyYAML。
- 未知 token 名称会抛错。图标目录相对主题模块文件，不相对当前工作目录。
- 任务模型保持三条线：`TaskRunner` 执行，`JobOutcome` 只表示批处理表格结果，`BatchToolWindow` 是可选界面，并调用同一个 runner。
- 关闭窗口不取消任务。应用退出时才取消任务并等待线程池。回调碰到已销毁的控件时不再把这个错误当成任务失败。
- 对比度不足由 `contrast_notes` 报告，不阻止主题加载。配置或窗口几何损坏时退回默认值，不阻止启动。
- 单实例锁只在 `single_instance=True` 时创建和释放。
- 系统没有托盘时，`tray=True` 不把关闭改成隐藏，进程仍随最后一个窗口退出。
- 高 DPI 使用 `PassThrough`。窗口几何按逻辑像素恢复。图标按设备像素比栅格化，占位仍是逻辑尺寸。
- 稳定接口名单见 `psi6.api.STABLE`。`BatchToolWindow` 仍导出，但是可选界面。

## 版本

0.x 期间，上文「稳定接口」里的职责保持不变。新增参数使用默认值。破坏性变更写在本文件并升一个次版本。顶层导出的其余控件可用，但不单独承诺与核心接口同一稳定级别。内部模块以 `_` 开头。
