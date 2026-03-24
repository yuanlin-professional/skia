# third_party/icu_bidi - ICU 双向文本支持

## 概述

`third_party/icu_bidi/` 包含 ICU 双向文本（BiDi）算法的独立构建配置。
双向文本算法用于处理同时包含从左到右（如英文）和从右到左（如阿拉伯文、
希伯来文）文字的文本排版。

## 目录结构

```
icu_bidi/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 ICU BiDi 组件的编译选项

## 依赖关系

- ICU 源码（通过 DEPS 拉取）

## 相关文档与参考

- Unicode 双向算法: https://unicode.org/reports/tr9/
- ICU: `third_party/icu/`
- Skia 文本模块: `src/text/`
