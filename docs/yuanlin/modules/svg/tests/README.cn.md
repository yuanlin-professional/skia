# svg/tests - SVG 模块测试

## 概述

`modules/svg/tests/` 目录包含 SVG 模块的单元测试代码。目前主要覆盖两个方面:文本渲染测试和滤镜效果测试。这些测试验证 SVG 解析和渲染的正确性。

测试文件使用 Skia 的标准测试框架,通过构建 SVG DOM 实例并渲染到测试画布上来验证功能正确性。

## 目录结构

```
tests/
+-- BUILD.bazel      # Bazel 构建配置
+-- Text.cpp         # <text> 元素解析与渲染测试
+-- Filters.cpp      # SVG 滤镜效果测试
```

## 关键测试

| 文件 | 测试范围 |
|------|---------|
| `Text.cpp` | 文本元素的属性解析、文本整形、多行文本、tspan 等 |
| `Filters.cpp` | 各滤镜原语的参数解析与 ImageFilter 生成 |

## 相关文档与参考

- SVG 模块实现: `modules/svg/src/`
- Skia 测试框架: `tests/`
