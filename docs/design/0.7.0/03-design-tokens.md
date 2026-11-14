# 03 设计 token

状态：默认浅色和深色以纯白或炭黑为底，中性灰做层次，蕨绿只做强调。不新增公开字段，不改 `Tokens` 的名字。可选主题（黑曜石、松绿、黄铜、极简）保持各自的主色。

映射原则：浅色画布是纯白。侧栏、悬停、输入槽用中性灰，不把绿色铺进面板。主操作、焦点、链接和用户气泡用蕨绿。成功用橄榄，信息用暖褐，警告用琥珀，危险用红。紧凑不改变任何颜色。

推导保持 `Tokens.resolve_states`：空的按下、选中、主色悬停、危险悬停、控件边，按现有公式补齐。自定义主题写了值就用写的值。

## 颜色

浅色是 `Tokens.light()`，深色是 `Tokens.dark()`。紧凑不改变任何颜色。

| 语义 | 字段 | 浅色现值 | 深色现值 | 用途 |
| --- | --- | --- | --- | --- |
| Window | `color_bg` | `#ffffff` | `#161716` | 页面画布 |
| Surface | `color_surface` | `#ffffff` | `#1c1d1c` | 面板、表格底 |
| Surface Elevated | `color_elevated` | `#ffffff` | `#232423` | 对话框、次按钮、菜单 |
| Surface Sunken | `color_sunken` | `#f3f4f4` | `#101110` | 输入、日志、对话记录 |
| Surface Selected | `color_selected` | 推导 `#dfece6` | 推导 `#253029` | 选中行和选中导航的填充 |
| Border | `color_border_subtle` | `#eeefef` | `#262726` | 分隔线 |
| Border | `color_border` | `#e4e6e5` | `#333533` | 面板和表格的边 |
| Border Strong | `color_control_border` | 空，等于 `color_border` | 同左 | 可交互控件的边 |
| Text Primary | `color_text` | `#1c1f1e` | `#f2f3f2` | 标题、正文、次按钮文字 |
| Text Secondary | `color_muted` | `#5f6863` | `#a0a6a2` | 说明、表头、未强调的计数 |
| Text Muted | `color_disabled` | `#aeb4b0` | `#6e746f` | 只用于禁用控件的文字 |
| Accent | `color_primary` | `#1f7a4d` | `#86d0a4` | 主按钮、选中标记、链接 |
| Accent 上的字 | `color_on_primary` | `#f7fcf9` | `#102016` | 主按钮和危险按钮的字 |
| Focus | `color_focus` | `#0e5c38` | `#d4f3e2` | 外侧焦点环 |
| Success | `color_success` | `#5c7010` | `#d2d56a` | 成功标签、成功日志 |
| Warning | `color_warning` | `#9a6408` | `#e4b45e` | 警告标签、警告横幅 |
| Error | `color_danger` | `#c93b32` | `#e99088` | 错误边、错误句、危险按钮 |
| Info | `color_info` | `#6a6156` | `#c9c1b6` | 信息标签 |
| Hover | `color_hover` | `#f0f1f1` | `#2a2b2a` | 次按钮和行的悬停填充 |
| Pressed | `color_pressed` | 推导 `#d6d7d7` | 推导 `#424342` | 按下填充 |
| Sidebar | `color_sidebar` | `#f7f7f7` | `#121312` | 侧栏底 |
| Sidebar text | `color_sidebar_text` | `#3c4440` | `#c6ccc8` | 未选中导航 |
| Overlay | `color_overlay` | `rgba(244,245,245,210)` | `rgba(14,15,14,210)` | 模态遮罩 |
| 用户消息 | `color_user_bubble` / `color_user_on_bubble` | `#1f7a4d` / `#f7fcf9` | `#173828` / `#e7f6ee` | 对话里用户的气泡 |

不拆「Text Secondary」和「Text Muted」成两个新的正文灰。次要说明用 `color_muted`（浅色对白底 5.76，深色对窗口底 7.25，都高于 4.5）。`color_disabled` 只出现在禁用控件上（浅色对白底 2.11）。次按钮的字用 `color_text`，因此不会和禁用共用这个灰。

选中填充对侧栏底的对比度只有约 1.1。它负责色相差别，不负责单独表达选中。选中导航还要有 2px `color_primary` 竖条和图标变色。见 [01](01-visual-language.md)。

### 已经量过、决定维持的对比

用 `psi6.theme.colors.contrast_ratio` 对现值计算。文字阈值 4.5，焦点作为非文字阈值 3.0，与 `contrast_notes` 一致。

| 一对 | 浅色 | 深色 | 决定 |
| --- | --- | --- | --- |
| 正文 / 窗口 | 16.61 | 16.16 | 维持这套中性字色 |
| 辅助 / 窗口 | 5.76 | 7.25 | 维持。说明文字用这一对 |
| 主按钮字 / 主色 | 5.13 | 9.33 | 维持。浅色白字压在蕨绿上，深色深字压在浅蕨绿上 |
| 主按钮字 / 危险色 | 4.87 | 7.10 | 维持。危险按钮继续用 `color_on_primary` |
| 侧栏字 / 侧栏底 | 9.37 | 11.42 | 维持 |
| 焦点色 / 窗口底 | 8.06 | 15.17 | 维持，并且环必须画在窗口或面板底上 |
| 焦点色 / 主色填充 | 1.52 | 1.53 | 同色相，禁止把环画成主按钮的边 |
| 错误色 / 窗口底 | 5.05 | 7.54 | 维持 |
| 禁用字 / 窗口底 | 2.11 | 3.76 | 维持，且只用于禁用 |

`contrast_notes` 今天还没检查「错误字 / 窗口」和「焦点色 / 主色」。实现阶段可以把这两对加进诊断。加诊断不是新的颜色字段。

主色悬停、按下、危险悬停、按下继续用 `resolve_states` 的 `mix_hex`，不手写新色。

## 字体 token

没有新的字号字段。见 [01](01-visual-language.md) 的字号表。

| 语义 | 实现 |
| --- | --- |
| Display | 不设。页面标题即最大 |
| Heading | `font_size_title` + `font_weight_title` |
| Title | 节标题：`font_size` + `font_weight_title` |
| Body | `font_size` + `font_weight_body` |
| Label | `font_size` + `font_weight_title` |
| Caption | `font_size_sm` + `font_weight_body` + `color_muted` |
| Monospace | `font_mono` + `font_size` |

行高是排版规则，不是字段：标题 1.25，正文 1.40，辅助 1.35。单行控件在 `control_height` 内垂直居中。

## 间距

不新增 4px 基准字段。三档已经存在，紧凑的 `space_sm` 就是 4。

| 语义 | 现代 | 紧凑 | 字段 |
| --- | --- | --- | --- |
| 控件内部、图标与文字 | 8 | 4 | `space_sm` |
| 可聚焦控件之间、相关块 | 12 | 8 | 现代可用 `space_sm`（8）或 `space_md`；紧凑控件间距必须用 `space_md` |
| 页面内边距、节间距 | 16 | 10 | `space_lg` |

页面内边距 = `space_lg`。节间距 = `space_lg`。控件内左右文字 = `space_md`。

阅读列最大 720，短控件最大 320，路径控件最大 480。这三个是布局常数，不是颜色 token，实现时写成命名常数，不要散落在各个页面里。

## 度量

| 语义 | 字段 | 现代 | 紧凑 |
| --- | --- | --- | --- |
| 按钮高、输入高、导航项高 | `control_height` | 36 | 30 |
| 图标按钮、页签、紧凑行内控件 | `control_height_sm` | 28 | 24 |
| 图标 | `icon_size` | 16 | 14 |
| 导航宽 | `sidebar_width` | 212 | 188 |
| 导航收起 | `sidebar_compact_width` | 56 | 52 |
| 表行 | `row_height` | 32 | 28 |
| 工具栏内容高 | `control_height` | 36 | 30 |
| 底栏总高 | `control_height + space_sm * 2` | 52 | 38 |
| 标题栏（仅自绘时） | `title_bar_height` | 36 | 32 |
| 开关 | `switch_width` × `switch_height` | 44×24 | 38×20 |

工具栏不另设高度字段。底栏高度由控件高和垂直内边距相加，写在布局里。

## 形状

| 语义 | 字段 | 现代 | 紧凑 |
| --- | --- | --- | --- |
| 控件圆角 | `radius` / `button_radius` | 6 | 4 |
| 容器圆角 | `radius` | 6 | 4 |
| 浮层圆角 | `radius` | 6 | 4 |
| 窗口圆角 | `window_radius` | 10 | 10（度量表未覆盖，保持字段默认） |
| 焦点环圆角 | 控件圆角 + 4 | 10 | 8 |

焦点环圆角是几何推导，不新增字段。样式表里不再出现与上表无关的半径字面量。

## 效果

| 语义 | 规则 |
| --- | --- |
| 边框 | 1 逻辑像素，角色见颜色表 |
| 阴影 | 无字段。页内不用投影。`Card(elevated=True)` 用固定的轻投影，不进 token。模态只用 `color_overlay` |
| Focus Ring | 宽 `focus_ring_width`，色 `color_focus`，与控件之间留 2px 父级表面。1px 缝会被抗锯齿吃掉 |
| 动效时长 | `motion_fast_ms` 160，`motion_ms` 220，`reduced_motion` 时为 0 |
| 缓动 | 颜色过渡用平滑的减速（Qt 的 `OutCubic` 一类）。不要求弹性。本阶段不把曲线做成 token |

## 四种组合

| 组合 | 颜色来自 | 尺寸来自 |
| --- | --- | --- |
| 浅色现代 | `Tokens.light()` | `_MODERN_METRICS` |
| 深色现代 | `Tokens.dark()` | `_MODERN_METRICS` |
| 浅色紧凑 | `Tokens.light()` | `_COMPACT_METRICS` |
| 深色紧凑 | `Tokens.dark()` | `_COMPACT_METRICS` |

`Theme.base = "auto"` 在系统为深色时取深色现值，否则取浅色现值。`App.density = "auto"` 只可能把尺寸换成紧凑预设，不改上表的颜色。

既有皮肤继续用它们自己的类属性。它们要能通过现有 `contrast_notes`。本规范的参考页不重绘它们。

## 实现时仍然不要做的别名

0.4 草案里的 `window_bg`、`text_primary`、`accent` 只出现在说明文字里。Python 字段保持 `color_bg`、`color_text`、`color_primary`。

`set_style` 仍可接受字面色或 token 名。字面色在换主题时不跟随。默认检查不因此失败。参考页不使用字面色，控件颜色都走上表的字段。
