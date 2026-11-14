# 06 参考页面

状态：阶段二设计稿。画面是设计原型，不是已实现的控件截图。生成方式见 [`reference/README.md`](reference/README.md)。

六页共用一个壳：系统标题栏的位置、左侧导航、内容列。导航目的地是文件、任务、工作台、组件、对话、设置，图标分别是 `folder`、`play`、`sidebar`、`table`、`message`、`settings`。

每页都有四种组合和三档宽度：

| 档 | 文件尺寸 |
| --- | --- |
| 宽 | 1180×760，`wide.png` |
| 中 | 960×680，`medium.png` |
| 窄 | 640×520，`narrow.png` |

窄档取参考应用的最小窗口，而不是 700。700 已经低于 760，侧栏会收成图标轨，但内容内宽仍可能大于 560，表单不会上下堆叠，工作台左栏也还放得下。640 能把这些规则同时画出来。实现验收时 700 也必须不裁字。

组合目录名：`light-modern`、`dark-modern`、`light-compact`、`dark-compact`。

空、忙、错误单独放在 `reference/states/`，使用浅色现代、中等宽度。对话框在 `reference/dialogs/`。这些状态的布局和颜色通道在四种组合下相同，只有度量和配色跟随 token。

标题栏画进原型，是为了标出客户区。实现仍使用 `DesktopWindow` 的系统标题栏。

## 1. 设置中心

路径：`reference/settings/{组合}/{档}.png`

结构：页头「设置」。阅读列最大 720，左对齐，分组为外观、工作区、运行，组之间是分隔线。短下拉最大约 320，路径框约 480，浏览紧挨路径。底栏横跨内容列：左侧状态，右侧取消和保存。

信息层级：页标题，节标题，行标题，辅助说明。

状态：

- 默认：`wide.png` 等九宫格里的常规稿。
- 空：`states/settings-empty.png`，阅读列内的空状态，底栏仍在。
- 忙：`states/settings-loading.png`，阅读列上的遮罩，页头和底栏可见。
- 错误：`states/settings-error.png`，路径框红边，下方红字，保存仍在底栏。

宽度：宽和中保持标签在左。窄档内容内宽低于 560，标签改到控件上方，侧栏为图标轨。紧凑组合只缩小行高和字号，列宽规则不变。

控件：`AppShell`、`PageHeader`、`Section`、`SettingRow`、`FileInput`、`ActionBar`、`EmptyState`、`BusyOverlay`、`FormError`。

## 2. 文件索引

路径：`reference/file-index/{组合}/{档}.png`

结构：页头，工具栏左组是开始和取消，右组是刷新。筛选行是搜索、后缀、递归开关，右端是计数和失败标签。表格占满剩余高度。状态列是语义标签。

信息层级：命令组先于筛选，筛选先于表，表是主体。

状态：

- 默认：表中有行。
- 空：`states/file-index-empty.png`，空状态在表框内部，工具栏和筛选仍在。
- 忙：`states/file-index-loading.png`，表体遮罩，底边进度在状态行。
- 错误：`states/file-index-error.png`，内容顶部一条错误横幅，已有的行保留。

宽度：宽和中显示路径列。窄窗口隐藏路径列，刷新进入溢出，侧栏为图标轨。筛选不压在任何分割线上。

控件：`ToolBar`、`SearchField`、`DataTable`、`Tag`、`Banner`、`EmptyState`、`BusyOverlay`。

## 3. 任务工作区

路径：`reference/task/{组合}/{档}.png`

结构：页头是任务名。内容宽够时，左侧参数表单，右侧下沉日志。底栏左组是取消和开始，右端是进度文字。

信息层级：任务名，参数，日志，最后是执行命令。开始不是页面中央的唯一对象。

状态：

- 默认：日志已有级别色的行，开始可用。
- 空：`states/task-empty.png`，日志内部空状态，表单可编辑。
- 忙：`states/task-loading.png`，开始禁用，取消可用，底栏有进度。
- 错误：`states/task-error.png`，日志中的错误行用 `color_danger`，参数区没有第二套红框，除非某个字段自己无效。

宽度：宽档左右分栏。中档和窄档的内容内宽不足 720，改为上表单、下日志，日志仍占剩余高度。窄档侧栏为图标轨。

控件：`FormView`、`FolderInput`、`LogPanel`、`ActionBar`、`StatusProgress`、`EmptyState`。

## 4. 多视图工作台

路径：`reference/workbench/{组合}/{档}.png`

结构：面包屑和工具栏。三栏都有表面和边：文档列表、页签加正文、属性列表。

信息层级：列表用于切换，中栏是当前文档，属性是附属。

状态：

- 默认：三栏都有内容。
- 空：`states/workbench-empty.png`，空状态在中栏，左右栏仍在。
- 忙：`states/workbench-loading.png`，遮罩只盖中栏。
- 错误：`states/workbench-error.png`，中栏顶部错误横幅，文档正文仍在横幅下面。

宽度：宽档三栏都在。中档收起右栏，工具栏出现属性按钮，左栏和中栏保留。窄档中栏若再放下左栏就会低于 360，于是左栏收成文档切换，只留中栏，侧栏变为图标轨。

控件：`Workspace`、`Breadcrumb`、`TabView`、`PropertyList`、`EmptyState`、`Banner`、`BusyOverlay`。

## 5. 组件设计工作台

路径：`reference/components/{组合}/{档}.png`

结构：这是给设计和实现验收用的目录，不是用户工具的首页。内容区按族排列按钮、输入、选择、页签、表格和横幅。列宽跟随控件，不把最后一列推到窗口右边。焦点列能看见外侧环。错误输入同时有红边和红字。横幅关闭是安静的图标按钮。

信息层级：族标题，然后状态行。真实侧栏负责导航选中态，矩阵里不再单放一列被拉伸的侧栏。

状态：

- 默认稿已经包含焦点、禁用、错误、选中行和横幅。
- 空：`states/components-empty.png`，在目录底部的反馈区单独演示空状态组件。
- 忙：`states/components-loading.png`，演示区域遮罩，不替换按钮皮肤。
- 错误：`states/components-error.png`，与默认稿同一错误语言，方便和设置页对照。

宽度：宽为多列族。中和窄减少并列的族，改为向下排，并出现滚动。四种组合的结构和状态种类相同。

控件：按钮工厂、输入、`Switch`、`SegmentedControl`、`TabView`、`DataTable`、`Tag`、`Banner`、`IconButton`、`EmptyState`。

## 6. 对话

路径：`reference/chat/{组合}/{档}.png`

结构：页头。中间是下沉记录区，消息从上向下，用户气泡靠右，对方气泡靠左并有边。输入条贴底，发送是主按钮。

信息层级：对方的说明是正文，用户的话是主色气泡，输入是下一步动作。记录区的空白是下沉表面，不是没排完的画布。

状态：

- 默认：两条以上消息，输入为空。
- 空：`states/chat-empty.png`，空状态在记录区，输入条仍贴底。
- 忙：`states/chat-loading.png`，对方气泡位置是「正在回复」，发送禁用。
- 错误：`states/chat-error.png`，输入条上方一行错误句，已发送的气泡保持原样。

宽度：气泡最大 640。窄窗口气泡变为内容宽减内边距，输入和发送仍在一行；放不下时发送掉到输入下一行，仍右对齐。

控件：`MessageList`、`Composer`、`primary_button`、`EmptyState`、`FormError`。

## 对话框

`reference/dialogs/confirm-light-modern.png` 和 `confirm-dark-modern.png`。遮罩用 `color_overlay`，对话框浮起填充，1px 边，无阴影。内部是一条路径字段的错误，底栏是取消和保存。用来确认对话框与设置页是同一种错误。

## 阅读顺序

实现某一页时，先看本文件的结构和控件名单，再看 [02](02-page-layouts.md) 的数字，再看 [04](04-component-visual-spec.md) 的状态，最后用对应 PNG 核对对齐、区域和焦点落点。PNG 与文档冲突时，以 [08](08-design-decisions.md) 为准，并改文档，不在控件里另做一版。
