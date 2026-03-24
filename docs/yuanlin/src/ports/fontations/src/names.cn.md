# Fontations Names 模块 - 字体名称查询

> 源文件: `src/ports/fontations/src/names.rs`

## 概述

`names.rs` 是 Skia Fontations 字体后端中负责字体名称查询的模块。该模块提供了从 OpenType `name` 表中提取字体家族名称、PostScript 名称以及本地化名称字符串的功能。

字体名称在 Skia 中用于字体匹配（font matching）、字体枚举和用户界面展示。该模块实现了 OpenType 规范中定义的名称优先级逻辑，特别是在处理 WWS（Weight/Width/Slope）家族名称、排版家族名称和标准家族名称的回退链。

## 架构位置

```
Skia C++ (SkTypeface_Fontations)
    -> fontations_ffi (CXX bridge, ffi.rs)
        -> names.rs (本模块)
            -> skrifa::string::LocalizedStrings
            -> read_fonts::tables::os2 (fsSelection 标志)
```

该模块在 Fontations 桥接层中相对独立，主要为 `SkTypeface` 的名称相关方法提供后端实现。

## 主要类与结构体

### `BridgeLocalizedStrings<'a>`
```rust
pub struct BridgeLocalizedStrings<'a> {
    localized_strings: LocalizedStrings<'a>,
}
```
- 本地化字符串迭代器的桥接类型
- 封装 skrifa 的 `LocalizedStrings` 迭代器
- 当前固定查询 `StringId::FAMILY_NAME`（名称 ID 1）
- `#[allow(dead_code)]` 标注表明该字段虽然看似未直接读取，但通过可变引用在 `localized_name_next` 中被迭代消费

## 公共 API 函数

### `get_localized_strings(font_ref) -> Box<BridgeLocalizedStrings>`
创建字体家族名称的本地化字符串迭代器。使用 `StringId::FAMILY_NAME`（名称 ID 1）查询所有语言版本的家族名称。

### `localized_name_next(bridge_localized_strings, out_localized_name) -> bool`
从迭代器中获取下一个本地化名称：
- 成功时将名称字符串和语言标识写入 `out_localized_name`，返回 `true`
- 迭代完毕返回 `false`
- 语言标识不可用时设为空字符串

### `family_name(font_ref: &BridgeFontRef) -> String`
获取字体的家族名称，遵循以下优先级链：
1. **WWS 家族名称**（`StringId::WWS_FAMILY_NAME`，名称 ID 21）- 仅在 `fsSelection` 的 bit 8（WWS 标志）未设置时使用
2. **排版家族名称**（`StringId::TYPOGRAPHIC_FAMILY_NAME`，名称 ID 16）
3. **标准家族名称**（`StringId::FAMILY_NAME`，名称 ID 1）

关于 WWS 标志的语义：当 `OS/2` 表的 `fsSelection` 中 bit 8 被设置时，表示该字体是 WWS-only 字体面（font face），此时 **不应** 使用 WWS 名称字符串。

### `postscript_name(font_ref, out_string) -> bool`
获取字体的 PostScript 名称（`StringId::POSTSCRIPT_NAME`，名称 ID 6）：
- 成功时写入 `out_string` 并返回 `true`
- 名称不存在时返回 `false`

### `english_or_first_font_name(font_ref, name_id) -> Option<String>`（内部辅助函数）
按指定的名称 ID 获取字体名称，优先返回英文版本，如果没有英文版本则返回第一个可用的版本。这是 `family_name` 和 `postscript_name` 的底层实现。

## 内部实现细节

### WWS 名称逻辑
```rust
let use_wws = !f.os2()
    .map(|t| t.fs_selection().contains(SelectionFlags::WWS))
    .unwrap_or_default();
```
OpenType 规范的 `fsSelection` bit 8 的含义比较反直觉：
- bit 8 **设置** = WWS-only 字体 = **不** 使用 WWS 名称
- bit 8 **未设置** = 可以使用 WWS 名称

这是因为 bit 8 表示"字体面的基本属性仅包含 Weight/Width/Slope"，此时标准家族名称已经足够，WWS 名称是冗余的。

### 名称优先级的设计意图
- WWS 家族名称（ID 21）：专为区分 Weight/Width/Slope 之外有额外属性区分的字体家族设计
- 排版家族名称（ID 16）：将同一设计的所有变体归为一个家族
- 标准家族名称（ID 1）：最基础的家族名称，几乎所有字体都包含

使用 `then(|| ...)` + `flatten()` + `or_else(|| ...)` 链实现惰性求值的优先级回退。

### 迭代器模式
`BridgeLocalizedStrings` 通过 `localized_name_next` 函数以 C 风格的迭代模式（返回 `bool` 表示是否有更多元素）暴露给 C++ 侧，适配 CXX bridge 的约束。

## 依赖关系

- **read_fonts**: `tables::os2::SelectionFlags`, `TableProvider` - OS/2 表的 fsSelection 标志
- **skrifa**:
  - `string::{LocalizedStrings, StringId}` - 本地化字符串迭代器和名称 ID 常量
  - `MetadataProvider` - 元数据访问 trait
- **内部模块**: `crate::base::BridgeFontRef`, `crate::ffi::BridgeLocalizedName`

## 设计模式与设计决策

1. **优先级回退链**: `family_name` 使用 `Option` 链实现 WWS -> Typographic -> Family 的名称回退，每一级仅在上一级返回 `None` 时才执行
2. **英文优先策略**: `english_or_first_font_name` 优先返回英文版本的名称，确保跨平台一致性
3. **C 风格迭代器**: `localized_name_next` 使用返回 `bool` + 输出参数的模式，适配 CXX bridge 不支持 Rust 原生迭代器跨 FFI 边界的限制
4. **规范驱动实现**: WWS 标志的处理严格遵循 OpenType 规范的 `fsSelection` 定义

## 性能考量

- `english_or_first_font_name` 使用 skrifa 的 `english_or_first()` 方法，避免遍历所有本地化版本
- 名称优先级链使用惰性求值（`or_else`），仅在需要时才查询低优先级的名称
- `BridgeLocalizedStrings` 通过迭代器逐个产出名称，避免一次性加载所有本地化字符串

## 相关文件

- `src/ports/fontations/src/ffi.rs` - 定义 `BridgeLocalizedName` 共享类型和名称相关的 FFI 函数声明
- `src/ports/fontations/src/base.rs` - 提供 `BridgeFontRef` 基础类型
- `src/ports/SkTypeface_fontations.cpp` - C++ 侧调用名称 FFI 的 Typeface 实现
- OpenType 规范: `name` 表 (https://learn.microsoft.com/en-us/typography/opentype/spec/name)
- OpenType 规范: `OS/2` 表 fsSelection (https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fsselection)
