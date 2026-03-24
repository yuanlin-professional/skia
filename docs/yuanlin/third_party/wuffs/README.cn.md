# third_party/wuffs - Wuffs 安全编解码库

## 概述

`third_party/wuffs/` 包含 Wuffs（Wrangling Untrusted File Formats Safely）
库的 Skia 构建配置。Wuffs 是一个内存安全的编解码库，专门设计用于安全地处理
不可信的文件格式。Skia 使用 Wuffs 来解码 GIF、PNG（作为解码加速器）等格式。

## 目录结构

```
wuffs/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 Wuffs 的编译选项

## 依赖关系

- Wuffs 源码（通过 DEPS 拉取）

## 相关文档与参考

- Wuffs: https://github.com/nicknash/wuffs
- Skia Wuffs 编解码: `src/codec/SkWuffsCodec.cpp`
