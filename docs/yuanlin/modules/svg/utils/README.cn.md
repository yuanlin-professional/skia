# svg/utils - SVG 工具程序

## 概述

`modules/svg/utils/` 目录包含基于 SVG 模块构建的实用工具程序。目前主要包含 `SvgTool.cpp`,这是一个命令行工具,用于加载和渲染 SVG 文件。

该工具可用于 SVG 渲染效果的快速验证和调试,直接调用 `SkSVGDOM` 的 API 来解析和渲染 SVG 文档。

## 目录结构

```
utils/
+-- BUILD.bazel      # Bazel 构建配置
+-- SvgTool.cpp      # SVG 命令行渲染工具
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `SvgTool.cpp` | 命令行 SVG 渲染工具,加载 SVG 文件并通过 SkSVGDOM 渲染 |

## 相关文档与参考

- SVG DOM API: `modules/svg/include/SkSVGDOM.h`
- SVG 模块概述: `modules/svg/README.md`
