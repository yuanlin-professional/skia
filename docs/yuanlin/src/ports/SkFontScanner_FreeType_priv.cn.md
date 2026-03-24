# SkFontScanner_FreeType_priv

> 源文件: [src/ports/SkFontScanner_FreeType_priv.h](../../../../src/ports/SkFontScanner_FreeType_priv.h)

## 概述

本头文件声明了 `SkFontScanner_FreeType` 类，它是 `SkFontScanner` 接口的 FreeType 后端实现。该类封装了一个独立的 FreeType 库实例和互斥锁，提供线程安全的字体文件扫描、字体面枚举、实例元数据提取以及变体轴值计算功能。

## 架构位置

```
SkFontScanner (纯虚接口)
  ├── SkFontScanner_FreeType (本文件: FreeType 后端)
  │     ├── 拥有独立的 FT_Library (非全局共享)
  │     └── 使用 SkMutex 保护并发访问
  └── SkFontScanner_Fontations (Fontations/Rust 后端)
```

## 主要类与结构体

### SkFontScanner_FreeType

继承自 `SkFontScanner`，持有独立的 FreeType 库实例。

**公共成员:**

| 成员 | 说明 |
|------|------|
| 构造/析构函数 | 初始化/释放 FreeType 库 |
| `scanFile()` | 扫描字体文件获取面数量 |
| `scanFace()` | 扫描字体面获取实例数量 |
| `scanInstance()` | 扫描实例获取完整元数据 |
| `MakeFromStream()` | 从流创建字体面 |
| `getFactoryId()` | 获取工厂标识 |

**静态方法:**

| 方法 | 说明 |
|------|------|
| `computeAxisValues(...)` | 合并默认/当前/请求的变体轴值并推导字体样式 |

**私有成员:**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fLibrary` | `FT_Library` | 独立的 FreeType 库实例 |
| `fLibraryMutex` | `mutable SkMutex` | 保护库访问的互斥锁 |

**私有方法:**

| 方法 | 说明 |
|------|------|
| `openFace(stream, ttcIndex, ftStream)` | 打开字体面（支持内存和流两种方式） |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `bool scanFile(SkStreamAsset*, int* numFaces) const` | 扫描字体文件，获取面数量 |
| `bool scanFace(SkStreamAsset*, int faceIndex, int* numInstances) const` | 扫描字体面，获取命名实例数 |
| `bool scanInstance(SkStreamAsset*, int faceIndex, int instanceIndex, SkString*, SkFontStyle*, bool*, AxisDefinitions*, VariationPosition*) const` | 扫描实例获取全部元数据 |
| `sk_sp<SkTypeface> MakeFromStream(unique_ptr<SkStreamAsset>, const SkFontArguments&) const` | 从流创建字体面 |
| `SkTypeface::FactoryId getFactoryId() const` | 返回 FreeType 工厂标识 |
| `static void computeAxisValues(const AxisDefinitions&, VariationPosition current, VariationPosition requested, SkFixed*, const SkString&, SkFontStyle*)` | 计算变体轴值 |

## 内部实现细节

- **独立库实例**: 与全局 `gFTLibrary` 不同，扫描器拥有自己的 `FT_Library`，避免与渲染管线竞争
- **mutable 互斥锁**: `fLibraryMutex` 声明为 `mutable`，允许在 `const` 方法中加锁
- **computeAxisValues 为静态方法**: 不依赖实例状态，可被 `SkTypeface_FreeType` 的其他代码复用

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkFontScanner.h` | 基类接口 |
| `include/core/SkTypeface.h` | 字体面抽象 |
| `include/core/SkTypes.h` | 基础类型 |
| `src/ports/SkTypeface_FreeType.h` | FreeType typeface (含 FT_Face 前向声明) |

## 设计模式与设计决策

1. **独立库实例**: 扫描器拥有专用的 `FT_Library`，与渲染使用的全局库分离，减少锁竞争
2. **接口-实现分离**: `_priv.h` 后缀表明这是内部头文件，仅供 ports 层使用
3. **静态 computeAxisValues**: 将变体轴值计算抽取为静态方法，支持跨上下文复用
4. **const 正确性**: 扫描方法均为 `const`，互斥锁声明为 `mutable` 以满足此要求

## 性能考量

- 独立 `FT_Library` 避免与全局渲染锁竞争，扫描和渲染可并行
- `fLibraryMutex` 仍会序列化同一扫描器的并发扫描操作
- `openFace` 优先使用 `FT_OPEN_MEMORY` 直接访问内存，避免 I/O 回调

## 相关文件

- `src/ports/SkFontHost_FreeType.cpp` — 完整实现
- `src/ports/SkTypeface_FreeType.h` — FreeType typeface 声明
- `include/core/SkFontScanner.h` — 扫描器接口
- `src/ports/SkFontScanner_fontations_priv.h` — Fontations 对应声明
