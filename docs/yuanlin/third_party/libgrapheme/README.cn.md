# third_party/libgrapheme - Unicode 字位分割库

## 概述

`third_party/libgrapheme/` 包含 libgrapheme 库的 Skia 构建配置。libgrapheme
提供 Unicode 字位簇（grapheme cluster）分割功能，用于确定文本中可见字符的
边界。它是 ICU 的轻量级替代方案之一。

## 目录结构

```
libgrapheme/
├── BUILD.gn                 # GN 构建配置
├── LICENSE                  # 许可证
└── generate_headers.py      # 头文件生成脚本
```

## 关键文件

- **BUILD.gn**: 配置 libgrapheme 的编译选项
- **generate_headers.py**: 从 Unicode 数据生成所需头文件的脚本

## 依赖关系

- libgrapheme 源码（通过 DEPS 拉取）

## 相关文档与参考

- libgrapheme: https://libs.suckless.org/libgrapheme/
- Unicode 字位簇: https://unicode.org/reports/tr29/
- Skia Unicode 模块: `modules/skunicode/`
