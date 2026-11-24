# 0.7.0 阶段四验收

状态：材料已补。对照里的布局问题仍在。版本已按发布要求改为 `0.7.0`。

这次用真实窗口重拍了阶段一的同一批页面，并对照了改前截图。色板已经从蓝色换成石墨铜。页面结构里阶段一记下的几项仍然在。这些页面没有改到占满、不裁字和同一表面，记录留在下面。版本号随后改为 0.7.0 并发布。

## 环境

| 项 | 值 |
| --- | --- |
| 系统 | Windows 11（10.0.26200），可用区域 2560×1392 |
| 系统缩放 | 100%（`devicePixelRatio` 1.0，逻辑 DPI 96） |
| Python | 3.13.9 |
| 窗口 | `App.run` 打开的真实窗口 |
| 125% / 150% | 单独进程的 `QT_SCALE_FACTOR`。这是逻辑缩放，不是 Windows 显示缩放 |

系统显示缩放 125%、150%、175%、200%，以及 macOS、Linux，这次没有跑。不能写成已验证。

重拍命令：

```powershell
uv run python scripts/visual_audit_070.py --dest after --scales 1.25,1.5
```

结果：100% 107 张，125% 44 张，150% 44 张，脚本报告的错误数都是 0。清单在 `after/manifest.json`、`after/manifest-dpi125.json`、`after/manifest-dpi.json`。

抓图和阶段一相同：带系统标题栏的场景用 `QScreen.grabWindow`（清单里 `source` 为 `screen`）。组件目录是自绘标题栏，屏幕抓图接近全黑，改用已经显示出来的窗口的 `widget.grab()`（`source` 为 `widget`）。组件目录的图不能单独当成「系统合成已经正确」的证据。

## 对照

| 问题 | 结论 | 依据 |
| --- | --- | --- |
| 默认色从蓝变成石墨铜 | 已看到 | `after/scenes/light/task.png` 的「开始」是铜，`before/scenes/light/task.png` 是蓝。深色紧凑同一页是浅铜字，见 `after/scenes/compact-dark/task.png` |
| V-01 任务页只有两个按钮，其余是空白 | 仍在 | `comparison/task.md` |
| V-01 设置页组与组之间空得很大 | 仍在 | `comparison/settings.md` |
| V-05 文件索引的开始和取消分开，浏览与导出被省略号吃掉 | 仍在 | `comparison/components.md` |
| V-03 状态矩阵列被拉开，覆盖的控件不够 | 仍在 | `comparison/components.md` |
| V-04 窄窗口裁字 | 仍在 | `comparison/workbench.md` |
| V-08 三栏不是同一种表面 | 仍在 | `comparison/workbench.md` |
| V-09 侧栏底部空项 | 仍在 | `comparison/workbench.md` |
| 100% / 逻辑 125% / 逻辑 150% 结构没有整页散掉 | 这三项逻辑缩放下没有新的整页错位 | 设置页 `after/dpi150/scenes/light/settings.png` 与 100% 是同一套留白。Windows 显示缩放未测 |
| 浅色、深色、现代、紧凑的色板角色 | 铜和暖炭在抽查的四套组合里一致 | 任务页浅色与 `compact-dark`。布局问题也四套都在，不是某一套独有 |

## 版本

上面仍在的 V-01、V-03、V-04、V-05、V-08 分别落在参考页、状态矩阵和窄窗口上。这些页面还没有达到规范里的占满、不裁字和同一表面。

版本号已改为 `0.7.0`：`pyproject.toml`、README 状态行和 CHANGELOG 的 0.7.0 条目一起发布。布局问题不改名叫已通过。下一轮若只改这些页面的布局，仍然先对照 `docs/design/0.7.0/`，改完用同一条命令重拍 `after/`，再改这份验收的结论。
