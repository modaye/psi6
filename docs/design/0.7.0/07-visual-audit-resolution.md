# 07 阶段一问题的设计处理

状态：阶段二设计稿。每条都回到 [`findings.md`](../../plans/audit-0.7.0/findings.md) 的截图。处理方式是布局和状态规则，不是单独改一个间距。

## V-01 页面空间组织不合理

根因：页面没有声明哪个区域吃掉剩余空间。控件按默认从上往下排，短内容下面就是窗口底色。设置把输入拉满整行，组距又大，所以既空又散。任务页把两个按钮放在客户区中央。对话的记录区和输入条之间没有一块属于消息的表面。

决策：D8。短页面用区域钉住窗口，而不是把控件垂直居中或加大页边距。

方案：

- 设置：720 阅读列从上排起，动作条贴住内容列下缘。剩余高度在阅读列和动作条之间，是同一块窗口底，不是一组卡片。
- 文件索引：表格吃掉筛选行以下的全部高度。
- 任务：日志吃掉参数列旁边或下面的全部高度，开始和取消在底栏左组。
- 对话：下沉的记录区吃掉页头和输入条之间的高度，消息从上对齐。
- 组件目录：状态矩阵按族铺在内容区里，列宽固定。

影响：`SettingsPage`、`PageHeader`、`ToolBar`、`ActionBar`、`DataTable`、`LogPanel`、`MessageList`、`Composer`、`Workspace`。

验收：在 1180×760 的真实窗口里，设置的保存按钮贴底；任务页能同时看见参数和日志；对话的空白处是记录区的下沉底色；文件表伸到内容区底部。对照 `reference/settings`、`reference/task`、`reference/chat`、`reference/file-index`。

## V-02 焦点环不明显

根因：默认 `focus_ring=False`，关闭时样式只剩 `outline: none`。打开之后，环画成控件的 `border` 且使用 `color_focus`。主按钮填充是 `color_primary`，两者浅色对比 1.20、深色 1.24。输入框则用同一条边的加粗替换，和按钮不是一种焦点。

决策：D4、D5、D6。色值不改，位置改到父级表面上。默认值的代码变更留到实现阶段。

方案：独立控件外侧 2px 父级表面缝，再加 2px `color_focus`。1px 缝在抗锯齿后会贴进主按钮填充。错误边保留。连排行内收 2px。边框盒尺寸不随焦点变化。控件间距至少 8，给环留位置。

影响：`apply.py` 的焦点规则、按钮、输入、页签、图标按钮、复选框。`App` 默认值与 `MIGRATION.md`。

验收：浅色和深色下，主按钮焦点与未焦点的像素差集中在按钮外侧的表面上，缝里能看见 `color_bg` 或 `color_surface`。次按钮同时看见灰边和焦点环。聚焦前后按钮的边框盒宽高不变。对照 `reference/components/light-modern/wide.png` 的焦点列，以及 `reference/components/dark-modern/wide.png`。

## V-03 状态矩阵覆盖不足

根因：状态页是四列拉伸网格。输入列把多余宽度吃掉，侧栏列被推到右缘。列里没有危险按钮、表格、树、页签、横幅。表格自己的状态又改用灰色字。

决策：D12。矩阵是目录，不是自适应四列。

方案：族分块，列宽按控件 `sizeHint`，块与块用节标题分隔。必须包含按钮四态、输入错误、页签、表格选中行和语义标签、警告横幅。表格状态与标签用同一套语义色。侧栏选中态放在真实侧栏里看，不作为矩阵里被拉伸的第四列。

影响：组件目录的状态页。`Tag`、`DataTable` 的状态列、`Banner`、`TabView`。

验收：1180 宽的组件页上，每一列紧挨上一列，右侧可以留下窗口底，而不是把最后一列推到边上。能指认危险按钮、错误输入、选中表行、页签和横幅。对照 `reference/components/`。

## V-04 窄窗口裁切和滚动

根因：组件目录的最小尺寸使窗口停在约 921–977，文档中的 760 在拖动中不会发生。强制缩到 700 后，侧栏标题、工作台句子和工具栏被裁切，数据页高于视口且没有滚动。

决策：D9。

方案：参考应用最小 640×420。宽度 < 760 时侧栏改为图标轨，工具栏右组进入溢出，长句子在区域内换行或区域滚动。页头和底栏固定，中间滚动。表格在表内滚动。工作台按最小栏宽收起，不把文字画到栏外。

影响：`AppShell`、`Workspace`、`ToolBar`、示例窗口的最小尺寸、数据页和表单页的滚动宿主。

验收：从宽拖到 700×520 的过程中，窗口真的会经过 760。到达 700 时「psi6」不重叠，工作台句子不画出栏外，数据页底部的行可以滚到。对照 `reference/workbench/light-modern/narrow.png`、`reference/kit` 对应的 `reference/components/light-modern/narrow.png`、`reference/file-index/light-modern/narrow.png`。

## V-05 次要控件辨识度和文字省略

根因：次按钮填充接近窗口底，边又弱，和禁用的灰字靠在一起。按钮宽度不够时直接省略。文件索引把筛选压在分割线上，开始和取消分居两角。

决策：D6、D7。

方案：次按钮使用浮起填充、`color_border` 和 `color_text`。禁用使用 `color_disabled` 且不用主色。浏览、校验、取消都是次按钮，和相关的主按钮相邻。路径按钮的文字按 `sizeHint` 排，放不下整组进入溢出。筛选在表格上方单独一行。

影响：`ghost_button`、`FileInput`、`FolderInput`、`ToolBar`、文件索引示例、`ActionBar`。

验收：不读提示也能分开「取消」和禁用按钮。100% 和 1.5 倍逻辑缩放下，「浏览」「导出日志」要么完整，要么整颗按钮在溢出菜单里完整出现。开始和取消在同一组。对照 `reference/file-index/light-modern/wide.png` 与 `reference/settings/light-modern/wide.png`。

## V-06 错误态不一致

根因：状态页用边框通道表示错误，表单只在下面放了一行 `color_danger` 文字，输入边仍是 `color_control_border`。深色里这行字缺少边框的上下文，所以更像淡粉注释。

决策：D6。色值先维持，结构先统一。

方案：凡是字段错误，边为 `color_danger`，下方有句子，句子颜色 `color_danger`，句子说明如何改。对话框里的字段同样。页面级失败用 `Banner`，横幅文字是 `color_text`，边和图标用 `color_danger`。焦点环不取代错误边。

影响：`FormError`、输入样式、`ContentDialog`、`Banner`、设置页。

验收：同一份「数值过小」在组件矩阵、设置页和对话框里都是红边加红字。深色截图里红边清楚可见。对照 `reference/states/settings-error.png`、`reference/components/dark-modern/wide.png`、`reference/dialogs/confirm-dark-modern.png`。

## V-07 空状态区域归属

根因：`EmptyState` 被放在页面流里，前后都是已有数据的表格或已有行的日志，读起来像整页没内容。横幅关闭按钮用了主色填充，比警告本身更响。

决策：D8、D12。

方案：空状态只作为宿主的子内容居中。文件表、日志、对话、工作台中栏各自拥有自己的空状态。有数据时不渲染它。横幅关闭改为 `color_muted` 的图标按钮，悬停才用 `color_hover`。

影响：`EmptyState`、`DataTable`、`LogPanel`、`MessageList`、`Banner`、`IconButton`。组件目录的组合方式。

验收：数据页不再出现夹在两张有数据的表中间的「暂无数据」。空的文件索引只在表体内居中空状态，工具栏仍在。警告横幅上没有实心蓝块。对照 `reference/states/file-index-empty.png`、`reference/components/light-modern/wide.png`。

## V-08 多视图表面层级

根因：中栏有边和表面，左右栏把字直接画在 `color_bg` 上，三块不是同一种区域。窄时继续挤压，文字画出边界。

决策：D8、D9。

方案：三栏都是 `color_surface` 加 `color_border`。缝露出 `color_bg`。右栏用 `PropertyList`。宽度不够时按 200 / 360 / 220 收起，栏内文字换行或滚动。

影响：`Workspace`、`Panel`、`PropertyList`、组件目录的多视图页。

验收：宽窗口三栏边界都能指认。中窗口没有右栏，有「属性」按钮。窄窗口没有文字溢出栏矩形。对照 `reference/workbench/` 的 wide、medium、narrow。

## V-09 导航图标和结构

根因：目的地共用一个文档图标，选中只靠很浅的 `color_selected`（对侧栏底对比约 1.1）。列表末尾还有一个没有文字的项。

决策：D11。

方案：文件、任务、工作台、组件、对话、设置使用 `folder`、`play`、`sidebar`、`table`、`message`、`settings`。选中加 2px 主色竖条，图标改 `color_primary`。不创建空标题的 `NavDestination`。

影响：`AppShell`、示例和组件目录的导航数据。

验收：四种旗舰组合的侧栏里，各项图标不同，底部没有无名图标。只看图标能区分当前页。对照任意一张 `reference/*/light-modern/wide.png`。

## V-10 画廊和工具页版式不一致

根因：画廊首页是完整的卡片网格，主题切换却把「紧凑」做成和浅色、深色并列的第三项，深色紧凑进不去。工具页则是 V-01 的空画布。两套版式没有分工。

决策：D2、D8、D11。

方案：`ToolTile` 网格只保留给启动器首页。文件索引、设置、任务、工作台、对话、组件目录使用 02 的页面，不使用磁贴墙。主题切换提供四种旗舰组合和跟随系统。

影响：`gallery` 的主题控件和首页文案，示例页的组装方式。磁贴组件本身保留。

验收：启动器仍然可以是磁贴。从启动器进入文件索引或设置后，页面结构与 `reference/file-index`、`reference/settings` 一致，而不是缩小的磁贴。主题控件里能选到深色紧凑。对照 `reference/components/light-compact/wide.png` 与 `reference/components/dark-compact/wide.png`，两者尺寸不同、结构相同。
