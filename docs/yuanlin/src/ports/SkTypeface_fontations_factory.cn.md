# SkTypeface_fontations_factory

> 源文件: [src/ports/SkTypeface_fontations_factory.h](../../../../src/ports/SkTypeface_fontations_factory.h)

## 概述

本头文件定义了 Fontations 字体后端的工厂标识符 (FactoryId)。`FactoryId` 是一个 4 字节标签 (`'f','n','t','a'`)，用于在 Skia 字体序列化/反序列化流程中唯一标识由 Fontations 引擎创建的字体面。当字体描述符被序列化时，此标识符记录了创建该字体所需的工厂类型。

## 架构位置

本文件是 Fontations 字体后端的标识注册组件，位于工厂模式的最底层。

```
SkTypeface (基类)
  └── FactoryId (工厂标识系统)
        ├── SkTypefaces::Fontations::FactoryId = 'fnta' (本文件)
        └── SkTypeface_FreeType::FactoryId = 'free'
```

## 主要类与结构体

### 命名空间 `SkTypefaces::Fontations`

| 成员 | 类型 | 值 | 说明 |
|------|------|---|------|
| `FactoryId` | `constexpr SkTypeface::FactoryId` | `SkSetFourByteTag('f','n','t','a')` | Fontations 工厂的唯一标识 |

## 公共 API 函数

本文件不定义函数，仅定义常量。

## 内部实现细节

- 使用 `SkSetFourByteTag` 宏将 4 个字符编码为一个 32 位整数
- 标签 `'fnta'` 是 "fontations" 的缩写
- `static constexpr` 确保编译时求值，零运行时开销
- 嵌套命名空间 `SkTypefaces::Fontations` 提供清晰的作用域隔离

## 依赖关系

- **`include/core/SkFourByteTag.h`** — `SkSetFourByteTag` 和 `SkFourByteTag` 类型
- **`include/core/SkTypeface.h`** — `SkTypeface::FactoryId` 类型定义

## 设计模式与设计决策

1. **四字节标签 (FourCC)**: 遵循 OpenType 和多媒体领域的 FourCC 惯例，使用 4 字节标签作为类型标识符
2. **命名空间隔离**: `SkTypefaces::Fontations` 命名空间清晰地将此标识与其他后端（如 FreeType）区分
3. **编译时常量**: `constexpr` 保证零运行时开销
4. **独立头文件**: 将工厂标识单独放在一个小文件中，减少包含依赖，便于多处引用

## 性能考量

- 纯编译时常量，不产生运行时开销
- 作为独立头文件，最小化了 include 链
- 四字节标签的比较操作是单条整数比较指令，效率最优
- `constexpr` 在 header-only 模式下不产生任何存储，编译器直接内联常量值

## 使用场景

FactoryId 在以下场景中使用:
- **序列化**: 当 `SkFontDescriptor` 被序列化到 SkPicture 或其他格式时，FactoryId 标识创建字体所用的后端
- **反序列化**: 读取已序列化的字体描述符时，根据 FactoryId 选择正确的工厂恢复字体
- **字体扫描器注册**: `SkFontScanner_Fontations::getFactoryId()` 返回此常量
- **字体面标识**: `SkTypeface_Fontations::FactoryId` 引用此处定义的常量

## 四字节标签约定

Skia 使用四字节标签 (FourCC) 标识各类工厂和资源，遵循 OpenType 表标签的惯例:

| 标签 | 后端 | 说明 |
|------|------|------|
| `'fnta'` | Fontations | 本文件定义 |
| `'free'` | FreeType | 定义于 SkTypeface_FreeType.h |

标签编码使用 `SkSetFourByteTag` 宏，将 4 个 `char` 值组合为一个 `uint32_t`，字节顺序为大端序。

## 相关文件

- `src/ports/SkTypeface_fontations_priv.h` — Fontations 字体面实现，引用此 FactoryId
- `src/ports/SkFontScanner_fontations.cpp` — Fontations 扫描器，使用此 FactoryId
- `src/ports/SkTypeface_FreeType.h` — FreeType 字体面，定义对应的 `FactoryId = 'free'`
- `include/core/SkTypeface.h` — `FactoryId` 类型定义
