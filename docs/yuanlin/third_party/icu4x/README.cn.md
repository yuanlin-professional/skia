# third_party/icu4x - ICU4X Rust 国际化库

## 概述

`third_party/icu4x/` 包含 ICU4X 库的 Skia 构建配置。ICU4X 是用 Rust 编写的
Unicode 和国际化库，作为传统 ICU C/C++ 库的现代替代方案。Skia 可以选择使用
ICU4X 来提供 Unicode 文本处理支持。

## 目录结构

```
icu4x/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 ICU4X 的编译选项，通过 `skia_use_icu4x` 开关控制

## 依赖关系

- ICU4X 源码（通过 DEPS 拉取）
- Rust 工具链

## 相关文档与参考

- ICU4X: https://github.com/unicode-org/icu4x
- 传统 ICU: `third_party/icu/`
- Skia Unicode 模块: `modules/skunicode/`
