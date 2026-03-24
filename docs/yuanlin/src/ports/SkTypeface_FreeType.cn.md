# SkTypeface_FreeType

> 源文件: [src/ports/SkTypeface_FreeType.h](../../../../src/ports/SkTypeface_FreeType.h)

## 概述

本头文件定义了 `SkTypeface_FreeType` 及其子类 `SkTypeface_FreeTypeStream`，构成 Skia 中基于 FreeType 库的字体面实现的核心接口。`SkTypeface_FreeType` 是一个抽象基类，封装了 FreeType 字体面的通用功能（字形映射、度量查询、表数据访问、变体支持等），而 `SkTypeface_FreeTypeStream` 是基于内存流的具体实现。

## 架构位置

```
SkTypeface (Skia 字体面抽象基类)
  └── SkTypeface_FreeType (本文件: FreeType 抽象中间层)
        ├── SkTypeface_FreeTypeStream (本文件: 流式字体实现)
        ├── SkTypeface_FCI (FontConfig 集成)
        └── 其他平台特定子类
```

## 主要类与结构体

### SkTypeface_FreeType

继承 `SkTypeface`，抽象基类。

**公共静态方法:**

| 方法 | 说明 |
|------|------|
| `GetUnitsPerEm(FT_Face)` | 从字体面获取 units-per-em（处理位图字体的特殊情况） |
| `MakeFromStream(stream, args)` | 从流和参数创建字体面 |

**公共实例方法:**

| 方法 | 说明 |
|------|------|
| `makeFontData()` | 获取字体数据 |
| `getFaceRec()` | 获取 FaceRec（需持有 f_t_mutex） |

**常量:**
- `FactoryId = SkSetFourByteTag('f','r','e','e')` — FreeType 工厂标识

**Protected 方法（SkTypeface 虚方法重写）:**

| 方法 | 功能 |
|------|------|
| `onCreateScalerContext()` | 创建缩放上下文 |
| `onCreateScalerContextAsProxyTypeface()` | 创建代理缩放上下文 |
| `onFilterRec()` | 过滤缩放参数 |
| `getGlyphToUnicodeMap()` | GlyphID -> Unicode 映射 |
| `onGetAdvancedMetrics()` | 高级排版度量 |
| `getPostScriptGlyphNames()` | PostScript 字形名称 |
| `onGetPostScriptName()` | PostScript 字体名 |
| `onGetUPEM()` | units-per-em |
| `onGetKerningPairAdjustments()` | 字距调整 |
| `onCharsToGlyphs()` | Unicode -> GlyphID |
| `onCountGlyphs()` | 字形数量 |
| `onCreateFamilyNameIterator()` | 本地化名称迭代 |
| `onGlyphMaskNeedsCurrentColor()` | 是否需要前景色（COLR/SVG） |
| `onGetVariationDesignPosition()` | 变体坐标 |
| `onGetVariationDesignParameters()` | 变体轴参数 |
| `onGetTableTags()` / `onGetTableData()` / `onCopyTableData()` | SFNT 表访问 |
| `cloneFontData(args, style)` | 克隆字体数据并应用变体参数 |

**纯虚方法:**
- `onMakeFontData()` — 子类必须实现，提供字体数据

**静态辅助:**
- `FontDataPaletteToDescriptorPalette()` — 从 SkFontData 填充 SkFontDescriptor 的调色板信息

**私有成员:**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFTFaceOnce` | `SkOnce` | FaceRec 延迟初始化 |
| `fFaceRec` | `unique_ptr<FaceRec>` | FreeType 字体面记录 |
| `fC2GCacheMutex` | `SkSharedMutex` | 字符到字形缓存的读写锁 |
| `fC2GCache` | `SkCharToGlyphCache` | 字符到字形映射缓存 |
| `fGlyphMasksMayNeedCurrentColorOnce` | `SkOnce` | 颜色需求延迟检查 |
| `fGlyphMasksMayNeedCurrentColor` | `bool` | 是否需要前景色 |

### SkTypeface_FreeTypeStream

`SkTypeface_FreeType` 的具体子类，持有字体数据流的副本。

**构造参数:**
- `unique_ptr<SkFontData>` — 字体数据（含流、TTC 索引、变轴值、调色板等）
- `SkString familyName` — 字体族名称
- `SkFontStyle` — 字体样式
- `bool isFixedPitch` — 是否等宽

**Protected 方法:**

| 方法 | 说明 |
|------|------|
| `onGetFamilyName()` | 返回存储的族名 |
| `onGetFontDescriptor()` | 填充描述符并标记需要序列化 |
| `onOpenStream()` | 复制数据流 |
| `onMakeFontData()` | 复制 SkFontData |
| `onMakeClone()` | 克隆并应用新参数 |

**私有成员:**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFamilyName` | `const SkString` | 字体族名称 |
| `fData` | `const unique_ptr<const SkFontData>` | 不可变的字体数据 |

## 公共 API 函数

见上方类方法列表。

## 内部实现细节

### FreeType 前向声明

文件中前向声明了 FreeType 的核心类型，避免在头文件中包含 FreeType 头文件:
```cpp
typedef struct FT_LibraryRec_* FT_Library;
typedef struct FT_FaceRec_* FT_Face;
typedef struct FT_StreamRec_* FT_Stream;
typedef signed long FT_Pos;
typedef struct FT_BBox_ FT_BBox;
```

### 读写锁优化

`fC2GCacheMutex` 使用 `SkSharedMutex` (读写锁):
- 字符到字形的查找操作使用共享锁（允许并发读）
- 添加新映射时升级为独占锁
- 这在多线程文本布局场景下显著减少锁竞争

### 延迟初始化

- `fFTFaceOnce` — FT_Face 在首次使用时才创建
- `fGlyphMasksMayNeedCurrentColorOnce` — COLR/SVG 表检查延迟到首次查询

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkFontScanner.h` | 字体扫描器接口 |
| `include/core/SkSpan.h` | 安全数组切片 |
| `include/core/SkTypeface.h` | 基类 |
| `include/private/base/SkFixed.h` | 定点数类型 |
| `include/private/base/SkMutex.h` | 互斥锁 |
| `include/private/base/SkNoncopyable.h` | 不可拷贝基类 |
| `include/private/base/SkTArray.h` | 动态数组 |
| `src/base/SkSharedMutex.h` | 读写锁 |
| `src/utils/SkCharToGlyphCache.h` | 字符->字形缓存 |

## 设计模式与设计决策

1. **模板方法模式**: `SkTypeface_FreeType` 定义骨架算法，`onMakeFontData()` 由子类实现
2. **延迟初始化 (SkOnce)**: FaceRec 和颜色检查延迟到首次使用，减少不必要的 FreeType 调用
3. **读写锁分离**: C2G 缓存使用读写锁优化高并发读场景
4. **pimpl 风格隐藏**: FreeType 类型通过前向声明暴露在头文件中，避免依赖传播
5. **不可变数据**: `SkTypeface_FreeTypeStream` 的 `fData` 为 `const`，保证线程安全

## 性能考量

- `SkCharToGlyphCache` + 读写锁避免频繁的 FreeType 互斥锁竞争
- `SkOnce` 延迟初始化减少创建 typeface 时的开销
- `FaceRec` 缓存避免重复创建 FT_Face
- `onCopyTableData()` 提供零拷贝的表数据访问

## 相关文件

- `src/ports/SkFontHost_FreeType.cpp` — 完整实现
- `src/ports/SkFontScanner_FreeType_priv.h` — FreeType 扫描器
- `src/ports/SkFontHost_FreeType_common.h` — FreeType 通用工具
- `src/ports/SkFontConfigTypeface.h` — FontConfig 集成的子类
- `src/utils/SkCharToGlyphCache.h` — 字符到字形缓存
