# 04 组件视觉规范

状态：阶段二设计稿。状态用 token 角色描述，不在这里写 QSS。控件名单以 `psi6.ui.__all__` 为准。没有出现在名单里的控件不在 0.7 补画。

四种组合的差异只有 [03](03-design-tokens.md) 的颜色和尺寸。下面说「现代 / 紧凑」时，只替换高度、字号、间距和圆角。

非视觉导出跟随它们画出来的控件：`Style`、`set_style`、`ColumnState`、`Command`、`MenuAction`、`PathState`、`Tone`、`TreeNode`、`TableColumn`、`TreeColumn`、`EditHistory`、`ShortcutBook`、`DebugEventFilter`、`PressScaleFilter`、`FlowLayout`。

## 共享状态

独立控件的盒模型在所有状态下外沿不变。

| 状态 | 填充 | 边 | 文字 | 附加 |
| --- | --- | --- | --- | --- |
| 默认 | 该变体的填充 | 该变体的 1px 边 | 该变体的文字色 | 无 |
| 悬停 | 见变体。禁止改成焦点色的边 | 次按钮和输入保持原边 | 保持 | 时长 `motion_fast_ms` |
| 按下 | 在悬停填充上改用 `color_pressed` 或主色/危险色的按下推导 | 保持 | 保持 | 无位移 |
| 焦点 | 不改变填充和边 | 不替换原边 | 保持 | 独立控件用外侧环；连排行用内收环。见 [01](01-visual-language.md) |
| 禁用 | `color_bg` | `color_border_subtle` | `color_disabled` | 无悬停，无焦点环 |
| 选中 | `color_selected` | 区域边保持 | `color_text` | 导航加 2px 主色竖条；表格行不加竖条 |
| 忙 | 控件仍在 | 保持 | 保持 | 区域上用 `BusyOverlay` 或底栏进度，不另做一种按钮皮肤 |
| 错误 | 输入类保持 `color_sunken` | `color_danger` | 控件内文字仍是 `color_text` | 控件下辅助档句子，颜色 `color_danger` |

错误、焦点、禁用在输入框、表单、对话框、表格里用这一张表。对话框里的字段错误不改成横幅；页面级失败才用 `Banner`。瞬时成功用 Toast，不用字段错误的句子。

对比度：正文和按钮字遵守 4.5，焦点环对它所在的表面遵守 3.0。环不画在主色填充上。

键盘：Tab 按壳、页头、工具栏、内容、底栏的顺序。方向键在表格、页签、侧栏、分段控件内移动。Enter 激活焦点所在的按钮。Esc 关闭对话框和菜单，不取消任务。

## 基础

### Icon

变体：命名字形，尺寸 `icon_size`，空状态用两倍。颜色跟随宿主文字，或语义色。无悬停。焦点落在包住它的按钮上。禁用时用 `color_disabled`。

### DesktopWindow / TitleBar

默认系统标题栏，客户区直角。`frameless=True` 才用 `TitleBar`，高度 `title_bar_height`，圆角只用 `window_radius`。标题栏按钮是图标按钮。参考稿里的标题条只标明客户区起点，实现不要为了参考稿改成自绘。

### TrayIcon / FloatBall

保持现有可选能力。不进入默认壳，不在参考页出现。悬浮球不是页面的一种卡片。

### Panel / Card / Section / Collapsible

`Panel`：平面分区。表面 `color_surface`，边 `color_border`，圆角 `radius`，内边距 `space_md`。无阴影。

`Card`：分组容器，以样例工作台的卡片为准。表面 `color_surface`，边用更弱的 `color_border_subtle`，圆角仍是 `radius`（不另加一档），内边距 `space_lg`。默认无阴影。`elevated=True` 时允许唯一的页内投影：模糊 16、向下 2px、低透明度，只服务这张浮起的卡片。文件索引、设置、任务页仍然不用卡片网格。

`Section`：节标题加一条 `color_border_subtle`。节本身没有填充和圆角。设置页用节，不用面板套每一组。

`Collapsible`：标题行高 `control_height`，悬停 `color_hover`，展开不动画高度以外的属性。焦点为独立控件的外侧环。

## 按钮

共同：高 `control_height`，圆角 `button_radius`，左右内边距 `space_md`，图标 `icon_size`，图标与文字 `space_sm`。文字不省略。最小宽度能放下两个汉字加内边距。

| 变体 | 工厂 | 默认填充 | 默认字 | 悬停填充 | 按下 |
| --- | --- | --- | --- | --- | --- |
| 主 | `primary_button` | `color_primary` | `color_on_primary` | `color_primary_hover` | `color_primary_pressed` |
| 危险 | `danger_button` | `color_danger` | `color_on_primary` | `color_danger_hover` | `color_danger_pressed` |
| 次 | `ghost_button` | `color_elevated` | `color_text` | `color_hover` | `color_pressed` |
| 文字 | `text_button` | 透明 | `color_text` | `color_hover` | `color_pressed` |
| 链接 | `link_button` | 透明 | `color_primary` | 透明，字色 `color_text` | 同悬停 |

主按钮和危险按钮的边与填充同色。次按钮的边是 `color_border`。文字按钮和链接没有边。

禁用四者相同：`color_bg` / `color_border_subtle` / `color_disabled`。禁用的主按钮不再保持蓝色，这样次按钮的白底灰边不会和它混淆。

`IconButton`：点击区域至少 `control_height_sm`，图标居中，默认透明，悬停 `color_hover`，有边仅在它承担「关闭」以外的工具命令时使用次按钮的边。横幅关闭、对话框关闭使用无边的图标按钮，图标 `color_muted`，不用主色填充。

焦点都是外侧环。加载中的按钮保持当前变体的填充和文字，左侧画一条旋转圆弧，点击、空格和回车不再触发；外框尺寸不跳。`reduced_motion` 时圆弧停住，不转。调用 `set_loading(button, True)`。进度句子仍放底栏，不把百分比写进按钮。

## 输入

共同：高 `control_height`，填充 `color_sunken`，边 `color_control_border`，圆角 `radius`，文字 `color_text`，占位 `color_muted`。

悬停：填充改为 `color_bg`，边不变。焦点：边不变，外侧环。错误：边改为 `color_danger`，下方 `FormError`。禁用：共享禁用表，但仍能读出文字时用 `color_disabled`。

| 组件 | 规则 |
| --- | --- |
| 单行文本 | 短字段最大宽 320 |
| `SearchField` | 左侧 `search` 图标，最大宽 280，清除按钮是图标按钮 |
| 数字框 | 与单行文本同一边和同一环，步进按钮无单独底色 |
| `FileInput` / `FolderInput` | 路径框最大宽 480，等宽字体，浏览是次按钮，紧挨框的右侧。清除按钮保持默认开启。保存路径接 `path_edited` |
| `DropZone` | 边为 1px 虚线 `color_border`，焦点改为外侧实线环，不用 2px 的另一套边。拖入时填充 `color_hover` |
| 多行文本 | 最小高度 3 行，边和错误规则与单行相同 |

`IconPreview` 只展示字形，无交互状态。

## 选择

| 组件 | 默认 | 悬停 | 选中 | 焦点 | 禁用 |
| --- | --- | --- | --- | --- | --- |
| 复选框 | 指示器 `color_sunken`，边 `color_control_border`，圆角 `max(2, radius-2)`，边宽始终 1px | 边 `color_primary` | 填充 `color_primary`，勾为 `color_on_primary` | 外侧环包住指示器加标签的整行。环不画成指示器的加粗边：加粗会缩小勾选图的内容盒，勾被裁掉，失焦后旧边还会留在原处 | 共享禁用 |
| 单选 | 圆形指示器，边宽始终 1px，底为 `color_surface` | 边 `color_primary` | 外环与圆心都是 `color_primary`，中间留白。禁用时环和点都是 `color_muted` | 同复选，环在整行外侧 | 共享禁用 |
| `Switch` | 轨 `color_border`，拇指 `color_elevated` | 轨略用 `color_hover` | 轨 `color_primary` | 外侧环 | 共享禁用 |
| `SegmentedControl` | 槽 `color_sunken` | 项 `color_hover` | 项 `color_elevated` 加 1px `color_border` | 内收环在选中项内 | 整组禁用 |
| 下拉 | 与单行输入相同 | 与输入相同 | 菜单项用 `color_selected` | 外侧环在框上；菜单打开时当前项内收环 | 共享禁用 |
| `CheckList` / `CheckItem` | 行高 `row_height` | 行 `color_hover` | 勾选不改变行填充，只用指示器 | 内收环 | 行文字 `color_disabled` |

主题切换用分段或下拉，选项是「浅色现代、深色现代、浅色紧凑、深色紧凑、跟随系统」。不要用「紧凑」代替深色紧凑。

## 导航

| 组件 | 规则 |
| --- | --- |
| `AppShell` / `NavDestination` | 见 [02](02-page-layouts.md) 侧栏。空标题不生成项 |
| `Breadcrumb` | 当前节 `color_text` 字重 600，祖先 `color_muted`，分隔用 `chevron-right`。不换行，超出省略祖先 |
| `UnderlineTabs` | 页内分段。文字页签，底有一条 2px `color_primary` 指示器，切换时在 `motion_ms` 内滑到新页签。`reduced_motion` 时直接到位。焦点内收在当前页签 |
| `TabView` | 文档页签。条高 `control_height_sm`。选中项底部同样有一条滑动的 2px `color_primary`，不推动页签宽度。未选中字 `color_muted`。焦点内收。可关闭、可拖动；拖动时指示器直接跟到新位置。全部关掉显示空态 |
| `CommandPalette` | 浮层：`color_elevated`，1px 边，宽 560，顶距 80。输入用输入规则。结果行高 `row_height`，选中 `color_selected`。无阴影 |
| `KbdHint` | 辅助档，填充 `color_sunken`，边 `color_border_subtle`，等宽 |

`ShortcutBook` 不单独画外观，快捷键在命令和 `KbdHint` 上可见。

## 展示

| 组件 | 规则 |
| --- | --- |
| `PageHeader` | 标题档加可选辅助说明。右侧最多两个次按钮。无底边，间距见布局 |
| `StatCard` | 只用在启动器或看板的少数指标上。填充 `color_surface`，1px `color_border`，无阴影。文件索引和设置不用它做统计墙 |
| `Tag` / `TagRow` / `StatusBadge` | 高 `control_height_sm`，圆角 `radius`，字 `font_size_sm`。成功、警告、错误、信息用对应颜色作字色，填充为该色与 `color_bg` 的弱混合（实现时用 `mix_hex(语义色, color_bg, 0.88)`，不新增字段）。表格状态用标签，不用灰色正文 |
| `PropertyList` | 名 `color_muted`，值 `color_text`。行间 `color_border_subtle`。工作台右栏用它 |
| `Sparkline` | 线色 `color_primary`，无坐标轴装饰。只放在已经使用 `StatCard` 的看板 |
| `ImageWell` | 表面 `color_sunken`，边 `color_border`，空时在井内放空状态 |
| `DiffView` | 等宽。新增行用成功色文字，删除行用错误色文字，底仍是 `color_sunken`。焦点内收在视图上 |
| `ChangeList` / `ChangeRow` | 行高 `row_height`，状态用标签 |

语义标签的弱混合是推导，阶段四若看不清，改混合比例，不改语义色本身。

## 数据

### DataTable

外框 1px `color_border`，底 `color_surface`，圆角 `radius`。表头高 `row_height`，字辅助档、`color_muted`，底边 `color_border_subtle`。单元格左右 `space_md`。

行悬停 `color_hover`。行选中 `color_selected`，字仍是 `color_text`。焦点内收在选中行，不另画单元格蓝框。状态列用 `Tag`。空状态在视口中央。加载用表体上的 `BusyOverlay`，表头保留。列不够宽时在表内横向滚动。

`ColumnPicker` 是菜单，规则同命令面板的结果行。

### TreeView

与表格共用行高、悬停、选中和焦点。展开图标 `chevron-right` / `chevron-down`，颜色 `color_muted`。多选和拖拽不在 0.7 扩展；现有单击选中遵守上一行。

### LogPanel / LogConsole

填充 `color_sunken`，边 `color_border`，等宽，行高 `row_height`。级别颜色：错误 `color_danger`，警告 `color_warning`，信息 `color_info`，其余 `color_text`。空状态在面板内部。面板外部已有日志时不再放第二个空状态。

## 反馈

| 组件 | 规则 |
| --- | --- |
| `Banner` | 页面内容顶部，全宽于内容列。填充为语义色与 `color_bg` 的 `mix_hex(..., 0.90)`，边 1px 语义色，图标用语义色，文字 `color_text`。关闭是无边图标按钮。警告横幅的关闭按钮不得使用主色填充 |
| `Toast` / `ToastHost` / `ToastCard` | 浮起表面，1px 边，圆角 `radius`，无阴影。出现在窗口下角，不推动页面布局。成功、失败用语义色图标 |
| `EmptyState` | 只放在宿主内。图标、标题、一句说明、至多一个主按钮 |
| `BusyOverlay` | 盖住声明的区域，遮罩用 `color_overlay`，指示器 `color_primary`。页头和底栏留在外面 |
| `StatusProgress` | 放在窗口状态栏或任务底栏的右端。轨道 `color_sunken`，进度 `color_primary`，高 4px |

`inform` / `warn` / `fail` / `confirm` 打开的是对话框或 Toast，外观遵守对应组件，不另做一套颜色。

## 表单

| 组件 | 规则 |
| --- | --- |
| `FormView` | 使用 [02](02-page-layouts.md) 的表单布局。错误只走共享错误行 |
| `FormError` | 辅助档，`color_danger`，在控件下 `space_sm`。没有错误时不占高度 |
| `SettingsPage` | 阅读列 720，分组用 `Section`，底栏用 `ActionBar` |
| `SettingRow` | 左标题加可选说明，右 `Switch`。行悬停 `color_hover`。不把开关行画成输入框 |
| `Stepper` | 当前步字重 600、`color_text`，未到的步 `color_muted`，完成的步 `color_success`。连接线 `color_border_subtle` |

## 容器

| 组件 | 规则 |
| --- | --- |
| `Workspace` | 三栏规则见布局文档。每栏 `color_surface` 与 `color_border` |
| `ToolBar` | 无自己的填充。底边可以没有，由与内容的 `space_md` 分开。按钮组遵守按钮节 |
| `ActionBar` | 顶边 `color_border_subtle`，背景 `color_bg`。任务页按钮在左，设置页按钮在右 |
| `ContentDialog` | 见布局文档对话框。内部字段与表单同一错误语言 |
| `ToolTile` | 仅启动器。表面 `color_surface`，1px 边，悬停 `color_hover`，选中外侧环。工具页不把 `ToolTile` 铺满 |

## 消息与播放

| 组件 | 规则 |
| --- | --- |
| `MessageList` | 宿主是下沉表面，占满页头和输入条之间。消息上对齐。用户气泡 `color_user_bubble`，字 `color_user_on_bubble`，最大宽 640。对方气泡 `color_surface`，1px `color_border`，字 `color_text`。空状态在列表内部 |
| `Composer` | 贴底。输入遵守输入规则，发送是主按钮 `send`。错误句子在输入上方，不把气泡改成另一种红 |
| `Playlist` / `TransportBar` | 行和按钮遵守数据和按钮节。播放主命令是主按钮或图标按钮，暂停与它成组。不在 0.7 重新设计播放器皮肤 |

## 组件级验收清单

04 的状态表说「长什么样」，本节说「怎么算做到了」。每个控件按同一组固定项检查，
缺一项就写进工作台的例外说明，不靠口头约定。

七项基线，适用于全部控件：

1. **颜色与度量来自 token**。样式表里不出现字面量圆角、字面量字号，也不出现
   `font_size + 4` 这类偏移。`tests/test_theme.py` 扫源码守这条。
2. **状态覆盖共享状态表**中适用的行，缺的行在下方清单里注明「不适用」。
3. **焦点可达且可见**。Tab 能到，环画在父级表面上，聚焦前后外框尺寸不变。
4. **`reduced_motion` 下功能等价**。动画直达终值，不出现「关掉动效后状态没变」。
5. **离屏 `grab()` 无异常**，`paintEvent` 用 `paint.create_painter` 收尾。
6. **换浅色 / 深色不改变布局**，只改配色。
7. **切 `modern` / `compact` 不改变结构**，只改高度、字号、间距、圆角。

逐控件清单：

| 控件 | 额外验收 |
| --- | --- |
| `primary_button` / `danger_button` / `ghost_button` / `text_button` / `link_button` | 禁用态是 `color_bg` + `color_border_subtle` + `color_disabled`，不复用主色；文字不省略 |
| `IconButton` | 点击区域 ≥ `control_height_sm`，图标仍是 `icon_size`；关闭用无边框图标按钮 |
| `Tag` / `TagRow` / `StatusBadge` | 五种 `tone` 在样式表里各有规则；填充是语义色与 `color_bg` 的弱混合；表格状态列用它而不是灰字 |
| `Switch` | 滑块与轨道同步；悬停不改轨道色；Space / Enter 可切换 |
| `SearchField` | 有内容才显示清除；ESC 清空；最大宽 280 |
| `FileInput` / `FolderInput` | 路径框最大 480、等宽；清除按钮默认开；保存接 `path_edited` |
| `DropZone` | 虚线边；拖入改填充；焦点是外侧实线环而不是第二种边 |
| `DataTable` | 行悬停 / 选中 / 表头排序 / 空 / 忙 五态；排序筛选保留选中行与滚动位置 |
| `TreeView` | 展开折叠箭头是主题图形，不是原生三角；行状态与表格一致 |
| `UnderlineTabs` | 指示器滑到当前页签；`reduced_motion` 时直接到位 |
| `TabView` | 选中底边 2px `color_primary`，切换时滑动；关闭按钮是主题图形；全部关掉显示空态 |
| `AppShell` 导航项 | 每个目的地不同图标；选中是 `color_selected` + 左侧 2px `color_primary` 竖条 + 主色图标；聚焦时竖条仍在。`set_nav_accent(False)` 关掉竖条，只留选中填充，文字不位移。颜色跟主题的 `color_primary`，不另开字段 |
| `Toast` | 出现在窗口下角；悬停暂停、移开按剩余时长继续；`reduced_motion` 下无动画 |
| `Banner` | 关闭是无边框图标按钮，不用主色填充 |
| `EmptyState` | 只在宿主内部居中；有数据时不渲染 |
| `Stepper` | 完成态、当前态、未达态可分辨；圆点在任何密度下都是正圆 |
| `Menu` / `ContextMenu` | 勾选与单选标记是主题图形；菜单项左侧留位，勾选出现时文字不跳 |
| `QCalendarWidget`（`QDateEdit` 弹出面板） | 导航栏、日期格、选中态接管，不露 Fusion 默认外观 |
| `Slider` | 已选段是主色；横竖两个方向都有；禁用态降对比 |

不在本版补画的控件（`Pagination`、`Drawer`、`Skeleton`、`Spinner`）按 2.2 节留到后续版本，
不要为了让清单整齐而临时加一个只有默认态的控件。

## 主题预览里必须能指认的状态

组件设计工作台（参考页「组件」）把下列族以固定列宽排开，列不拉伸：

- 按钮：主、次、危险、文字 × 默认、悬停、按下、焦点、禁用
- 输入：默认、悬停、焦点、错误、禁用
- 选择：复选、开关、分段的默认与选中
- 导航：页签的未选中与选中
- 数据：表格的普通行、选中行、成功标签、失败标签
- 反馈：警告横幅及其安静的关闭按钮，四种语义标签

这一页是目录，不是卡片墙。见 `reference/components/`。
