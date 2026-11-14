# 参考稿

这些 PNG 是阶段二的设计原型，用现有 token 的现值离屏绘制。它们不是 `apply.py` 画出来的控件，也不能代替阶段四的真实窗口验收。

重新生成：

```powershell
uv run python scripts/design_reference_070.py
```

| 目录 | 内容 |
| --- | --- |
| `{页面}/{组合}/{wide,medium,narrow}.png` | 六页 × 四种组合 × 三档宽度，共 72 张 |
| `states/{页面}-{empty,loading,error}.png` | 浅色现代、中等宽度下的空、忙、错误，共 18 张 |
| `dialogs/confirm-{light,dark}-modern.png` | 带字段错误的对话框 |
| `manifest.json` | 上面全部文件的清单 |

页面目录名：`settings`、`file-index`、`task`、`workbench`、`components`、`chat`。

组合目录名：`light-modern`、`dark-modern`、`light-compact`、`dark-compact`。

宽度：宽 1180×760，中 960×680，窄 640×520。窄档是参考应用的最小窗口。

画面顶部的标题条只用来标出客户区。实现仍使用系统标题栏。
