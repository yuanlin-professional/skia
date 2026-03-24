# SkTypeface_fontations_priv

> 源文件: [src/ports/SkTypeface_fontations_priv.h](../../../../src/ports/SkTypeface_fontations_priv.h)

## 概述

本头文件是 Fontations (Rust) 字体后端的核心私有头文件（261行），定义了三个主要组件：(1) `sk_fontations` 命名空间中的 FFI 辅助类 (`AxisWrapper`, `ColorPainter`, `BoundsPainter`)，用于实现 Rust 到 C++ 的回调接口；(2) `SkTypeface_Fontations` 类，即基于 Fontations 的 `SkTypeface` 实现，管理字体数据和 Rust 桥接对象的生命周期。

## 架构位置

```
SkTypeface (字体面抽象基类)
  ├── SkTypeface_FreeType  (FreeType 后端)
  └── SkTypeface_Fontations (本文件: Fontations/Rust 后端)
        ├── fontations_ffi::BridgeFontRef (Rust 字体引用)
        ├── fontations_ffi::BridgeNormalizedCoords (归一化坐标)
        ├── fontations_ffi::BridgeOutlineCollection (轮廓集合)
        └── sk_fontations:: (C++ 回调实现)
              ├── AxisWrapper (变轴信息填充)
              ├── ColorPainter (COLR 彩色字形绘制)
              └── BoundsPainter (边界计算)
```

## 主要类与结构体

### sk_fontations::AxisWrapper

实现 `fontations_ffi::AxisWrapper` FFI 接口，允许 Rust 代码回调 C++ 以填充变轴信息。

| 方法 | 说明 |
|------|------|
| `AxisWrapper(Axis[], size_t)` | 构造时接收轴数组和大小 |
| `bool populate_axis(i, tag, min, def, max, hidden)` | 由 Rust 调用，填充单个轴的定义 |
| `size_t size() const` | 返回轴数组大小 |

### sk_fontations::ColorPainter

实现 `fontations_ffi::ColorPainterWrapper` 接口，用于将 COLR 表的彩色字形绘制到 SkCanvas:

**状态管理方法:**
| 方法 | 说明 |
|------|------|
| `push_transform()` / `pop_transform()` | 变换矩阵栈 |
| `push_clip_glyph()` / `push_clip_rectangle()` / `pop_clip()` | 裁剪栈 |
| `push_layer()` / `pop_layer()` | 合成图层栈 |

**填充方法:**
| 方法 | 说明 |
|------|------|
| `fill_solid()` | 纯色填充 |
| `fill_radial()` / `fill_linear()` / `fill_sweep()` | 渐变填充 |
| `fill_glyph_solid()` | 优化的字形+纯色填充 (直接 drawPath) |
| `fill_glyph_radial()` / `fill_glyph_linear()` / `fill_glyph_sweep()` | 优化的字形+渐变填充 |

**私有辅助:**
| 方法 | 说明 |
|------|------|
| `configure_solid_paint()` | 配置纯色 SkPaint |
| `configure_linear_paint()` / `configure_radial_paint()` / `configure_sweep_paint()` | 配置渐变 SkPaint |

**构造参数:**
- `SkFontationsScalerContext&` — 缩放上下文（用于获取字形路径）
- `SkCanvas&` — 绘制目标画布
- `SkSpan<const SkColor>` — 调色板
- `SkColor foregroundColor` — 前景色
- `bool antialias` — 抗锯齿开关
- `uint16_t upem` — 单位/em 值

### sk_fontations::BoundsPainter

实现 `ColorPainterWrapper` 的边界计算变体。不实际绘制像素，仅追踪变换和裁剪以计算字形的包围盒。

| 方法 | 说明 |
|------|------|
| `is_bounds_mode()` | 返回 `true`，标识边界模式 |
| `getBoundingBox()` | 获取计算出的包围盒 |
| `push_transform()` / `pop_transform()` | 追踪变换矩阵 |
| `push_clip_glyph()` / `push_clip_rectangle()` | 累积裁剪区域到边界 |
| `fill_glyph_*()` | 转发到 `push_clip_glyph()` 获取字形边界 |
| 其他 fill/layer 方法 | 空实现 (不需要绘制) |

**私有成员:**
| 成员 | 说明 |
|------|------|
| `fScalerContext` | 缩放上下文引用 |
| `fMatrixStack` | 变换矩阵栈 (STArray<4, SkMatrix>) |
| `fUpem` | 单位/em |
| `fBounds` | 累积的包围盒 |

### SkTypeface_Fontations

基于 Fontations 的 SkTypeface 实现。

**公共接口:**

| 方法/成员 | 说明 |
|----------|------|
| `getBridgeFontRef()` | 获取 Rust 字体引用 |
| `getBridgeNormalizedCoords()` | 获取归一化坐标 |
| `getOutlines()` | 获取轮廓集合 |
| `getGlyphStyles()` | 获取字形样式信息 |
| `getMappingIndex()` | 获取字符映射索引 |
| `getPalette()` | 获取调色板 |
| `FactoryId` | 工厂标识 `'fnta'` |
| `MakeFromData()` | 从数据创建 typeface |
| `MakeFromStream()` | 从流创建 typeface |

**重写的 SkTypeface 虚方法 (protected):**

| 方法 | 功能 |
|------|------|
| `onOpenStream()` | 打开字体数据流 |
| `onMakeClone()` | 克隆并应用新参数 |
| `onCreateScalerContext()` | 创建缩放上下文 |
| `onCreateScalerContextAsProxyTypeface()` | 创建代理缩放上下文 |
| `onFilterRec()` | 过滤缩放参数 |
| `onGetAdvancedMetrics()` | 获取高级排版度量 |
| `onGetFontDescriptor()` | 获取字体描述符 |
| `onCharsToGlyphs()` | Unicode -> GlyphID |
| `onCountGlyphs()` | 字形数量 |
| `getGlyphToUnicodeMap()` | GlyphID -> Unicode |
| `onGetUPEM()` | units-per-em |
| `onGetFamilyName()` | 字体族名称 |
| `onGetPostScriptName()` | PostScript 名称 |
| `onCreateFamilyNameIterator()` | 本地化名称迭代 |
| `onGlyphMaskNeedsCurrentColor()` | 是否需要当前颜色 |
| `onGetVariationDesignPosition()` | 变体坐标 |
| `onGetVariationDesignParameters()` | 变体轴参数 |
| `onGetTableTags()` / `onGetTableData()` | SFNT 表访问 |

**私有成员:**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFontData` | `sk_sp<const SkData>` | 字体文件数据 |
| `fTtcIndex` | `uint32_t` | TTC 集合索引 |
| `fBridgeFontRef` | `rust::Box<BridgeFontRef>` | Rust 字体引用 |
| `fMappingIndex` | `rust::Box<BridgeMappingIndex>` | 字符映射索引 |
| `fBridgeNormalizedCoords` | `rust::Box<BridgeNormalizedCoords>` | 归一化坐标 |
| `fOutlines` | `rust::Box<BridgeOutlineCollection>` | 轮廓数据 |
| `fGlyphStyles` | `rust::Box<BridgeGlyphStyles>` | 字形样式 |
| `fPalette` | `rust::Vec<uint32_t>` | 调色板数据 |
| `fGlyphMasksMayNeedCurrentColorOnce` | `SkOnce` | 延迟初始化守卫 |
| `fGlyphMasksMayNeedCurrentColor` | `bool` | 是否需要前景色 |

## 公共 API 函数

见上方各类的方法列表。主要入口点:
- `SkTypeface_Fontations::MakeFromData()` / `MakeFromStream()` — 创建字体面
- `ColorPainter` — 彩色字形绘制
- `BoundsPainter` — 边界计算

## 内部实现细节

### Rust 所有权管理

所有 `rust::Box<>` 成员拥有 Rust 堆上对象的所有权，析构时自动调用 Rust 的 `drop`:
- `fBridgeFontRef` 引用 `fFontData` 中的数据，`fFontData` 必须存活更久
- `fBridgeNormalizedCoords` 依赖 `fBridgeFontRef`

### ColorPainter vs BoundsPainter

两者实现相同的 `ColorPainterWrapper` 接口:
- `ColorPainter`: `is_bounds_mode() = false`，实际绘制到 SkCanvas
- `BoundsPainter`: `is_bounds_mode() = true`，仅计算包围盒

Rust 代码通过 `is_bounds_mode()` 判断当前模式，可能选择不同的遍历路径。

### 优化的 fill_glyph_* 方法

`fill_glyph_solid/radial/linear/sweep` 方法是 `push_clip_glyph + fill_* + pop_clip` 的优化合并版本，允许直接使用 `SkCanvas::drawPath()` 进行绘制，避免额外的裁剪操作。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/core/SkTypeface.h` | 基类 |
| `src/core/SkScalerContext.h` | 缩放上下文 |
| `src/core/SkAdvancedTypefaceMetrics.h` | 高级度量 |
| `src/ports/fontations/src/ffi.rs.h` | Fontations FFI 自动生成头文件 |
| `src/ports/SkTypeface_fontations_factory.h` | 工厂标识 |
| `include/private/base/SkOnce.h` | 延迟初始化 |
| `include/private/base/SkTArray.h` | STArray |

## 设计模式与设计决策

1. **CXX FFI 桥接**: 使用 `rust::Box<>` 和 `rust::Vec<>` 管理 Rust 对象生命周期
2. **回调接口模式**: C++ 类实现 Rust 定义的回调接口，Rust 通过虚方法调用 C++
3. **策略模式**: ColorPainter/BoundsPainter 实现相同接口但行为不同
4. **合并优化**: `fill_glyph_*` 方法将多步操作合并为一步
5. **数据引用安全**: 注释明确标注了 Rust 引用对 `fFontData` 的生命周期依赖

## 性能考量

- `rust::Box<>` 的析构涉及 FFI 调用，有固定开销
- `BoundsPainter` 的空方法实现避免了不必要的绘制计算
- `fGlyphMasksMayNeedCurrentColorOnce` 使用 `SkOnce` 延迟到首次查询
- `STArray<4, SkMatrix>` 在 BoundsPainter 中使用栈内联存储，减少堆分配
- 优化的 `fill_glyph_*` 方法减少 Canvas 状态保存/恢复次数

## 相关文件

- `src/ports/SkFontScanner_fontations.cpp` — 使用本文件中的类型
- `src/ports/fontations/src/ffi.rs.h` — Rust FFI 生成的接口定义
- `src/ports/SkTypeface_fontations_factory.h` — 工厂标识定义
- `src/ports/SkTypeface_FreeType.h` — FreeType 对应实现
- `include/core/SkTypeface.h` — 基类接口
