# 0.7.0 桌面设计规范

阶段二之后，默认浅色和深色已改为石色与蕨绿。色值见 [03-design-tokens.md](03-design-tokens.md)。不新增公开 token 字段。

另一位实现者从这里读起，然后按编号往下。冲突时以 [08-design-decisions.md](08-design-decisions.md) 为准。

| 文档 | 内容 |
| --- | --- |
| [01-visual-language.md](01-visual-language.md) | 气质、原则、两个轴、字体、圆角、边框、表面、焦点、动效、留白 |
| [02-page-layouts.md](02-page-layouts.md) | 十三种布局的结构、宽度、间距、溢出和窄窗口 |
| [03-design-tokens.md](03-design-tokens.md) | 语义角色到现有字段的映射，以及已经量过的对比度 |
| [04-component-visual-spec.md](04-component-visual-spec.md) | 现有控件的变体和状态通道 |
| [05-responsive-accessibility.md](05-responsive-accessibility.md) | 宽度等级、折叠、滚动、键盘、对比度、高 DPI |
| [06-reference-screens.md](06-reference-screens.md) | 六页参考稿的结构、状态和文件路径 |
| [07-visual-audit-resolution.md](07-visual-audit-resolution.md) | V-01 到 V-10 的原因、决策和验收 |
| [08-design-decisions.md](08-design-decisions.md) | 决策编号和未决问题 |

可视化原型在 [reference/](reference/README.md)。重新生成：

```powershell
uv run python scripts/design_reference_070.py
```

阶段一的改前窗口在 [../plans/audit-0.7.0/findings.md](../plans/audit-0.7.0/findings.md)。
