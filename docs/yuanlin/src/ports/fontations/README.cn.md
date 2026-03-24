# src/ports/fontations - Fontations 字体后端 (Rust FFI 桥接层)

## 概述

`src/ports/fontations` 目录是 Skia 与 Google Fontations 项目之间的 **Rust FFI（外部函数接口）
桥接层**。Fontations 是 Google 主导开发的一套完全用 Rust 编写的 OpenType 字体解析和渲染库，
旨在提供安全、高性能且功能完整的字体处理方案。该目录通过 CXX 框架（C++/Rust 互操作工具）实现了
Skia C++ 代码与 Fontations Rust 库之间的双向通信。

Fontations 后端代表了 Skia 字体系统的**新一代架构方向**，相比传统的 FreeType 后端，它具备以下
优势：内存安全（Rust 语言保障）、更现代的 OpenType 规范支持、原生的可变字体（Variable Font）
处理能力，以及完整的 COLRv0/v1 彩色字体渲染支持。从 2023 年开始引入 Skia，Fontations 后端
已经逐步成熟，在 Chrome 等产品中投入使用。

该子目录的核心职责是定义 CXX 桥接接口，将 Fontations 生态中的 `read-fonts`（底层字体表读取）、
`font-types`（字体类型定义）和 `skrifa`（高层字体操作 API）三个 Rust crate 的功能暴露给
Skia 的 C++ 代码。桥接层的设计理念是**最小化跨语言边界的数据拷贝**，通过共享的内存切片
（`rust::Slice`）和不透明类型（`rust::Box<T>`）实现高效的数据传递。

从模块组织角度看，Rust 侧代码按功能域划分为多个模块：`base.rs` 处理基础字体操作和度量信息、
`colr.rs` 负责 COLR 彩色字体表的遍历与绘制回调、`bitmap.rs` 处理 CBDT/sbix 位图字体、
`hinting.rs` 管理字体微调实例、`names.rs` 处理字体名称表、`verbs_points_pen.rs` 负责
字形轮廓到 SkPath 的转换。每个模块都通过 `ffi.rs` 中定义的 `#[cxx::bridge]` 宏暴露给
C++ 侧使用。

## 架构图

```
+-------------------------------------------------------------------+
|                    Skia C++ 侧                                     |
|                                                                   |
|  SkTypeface_Fontations        SkFontationsScalerContext            |
|  (SkTypeface_fontations.cpp)  (SkTypeface_fontations.cpp)         |
|       |                            |                              |
|       |  sk_fontations::           |  sk_fontations::             |
|       |  ColorPainter              |  BoundsPainter               |
|       |       |                    |       |                      |
|       +-------+--------------------+-------+                      |
|               |                                                   |
|               v                                                   |
|  +----------------------------------------------------------+    |
|  |  skpath_bridge.h (C++ 纯虚接口)                           |    |
|  |  - AxisWrapper                                            |    |
|  |  - ColorPainterWrapper                                    |    |
|  +----------------------------------------------------------+    |
+-------------------------------------------------------------------+
                |  CXX 桥接边界  |
                v (ffi.rs.h 生成) v
+-------------------------------------------------------------------+
|                    Rust FFI 侧                                     |
|                                                                   |
|  +----------------------------------------------------------+    |
|  |  ffi.rs - CXX 桥接定义 (#[cxx::bridge])                   |    |
|  |  - 共享数据结构: Metrics, FfiPoint, ColorStop, ...        |    |
|  |  - extern "Rust" 块: 暴露 Rust 函数给 C++                 |    |
|  |  - extern "C++" 块: 声明 C++ 接口供 Rust 调用             |    |
|  +----------------------------------------------------------+    |
|       |           |          |          |          |              |
|       v           v          v          v          v              |
|  +--------+  +--------+  +-------+  +--------+  +--------+      |
|  |base.rs |  |colr.rs |  |bitmap |  |hinting |  |names.rs|      |
|  |        |  |        |  |.rs    |  |.rs     |  |        |      |
|  |字体引用|  |彩色字体|  |位图   |  |字体    |  |名称表  |      |
|  |度量信息|  |COLR表  |  |CBDT   |  |微调    |  |family  |      |
|  |字符映射|  |调色板  |  |sbix   |  |hinting |  |postscri|      |
|  |变量轴  |  |渐变填充|  |       |  |autohint|  |pt name |      |
|  +--------+  +--------+  +-------+  +--------+  +--------+      |
|       |           |          |          |          |              |
|  +--------+                                                      |
|  |verbs_  |                                                      |
|  |points_ |                                                      |
|  |pen.rs  |                                                      |
|  |路径提取|                                                      |
|  |OutlinePen                                                     |
|  +--------+                                                      |
|       |                                                          |
|       v                                                          |
|  +----------------------------------------------------------+    |
|  |  Fontations Rust 生态                                      |    |
|  |  skrifa 0.36    | read-fonts 0.34  | font-types 0.9      |    |
|  |  (高层 API)      | (底层表读取)      | (类型定义)           |    |
|  +----------------------------------------------------------+    |
+-------------------------------------------------------------------+
```

## 目录结构

```
src/ports/fontations/
|
|-- BUILD.bazel        # Bazel 构建规则
|                      #   - rust_static_library: bridge_rust_side
|                      #   - rust_cxx_bridge: fontations_ffi
|                      #   - skia_cc_library: deps, path_bridge_include
|                      #   - rust_test: test_ffi
|
|-- Cargo.toml         # Rust 项目配置（依赖声明）
|                      #   - read-fonts 0.34
|                      #   - font-types 0.9
|                      #   - skrifa 0.36
|                      #   - bytemuck 1.16
|                      #   - cxx 1.0
|
|-- src/
    |-- ffi.rs                # CXX 桥接入口（crate root）
    |                         # 定义所有跨语言共享结构体和函数签名
    |
    |-- base.rs               # 基础字体操作模块
    |                         # BridgeFontRef, BridgeNormalizedCoords,
    |                         # BridgeOutlineCollection, BridgeMappingIndex
    |
    |-- colr.rs               # COLR 彩色字体表模块
    |                         # BridgeColorStops, ColorPainterImpl,
    |                         # draw_colr_glyph(), resolve_palette()
    |
    |-- bitmap.rs             # 位图字体模块
    |                         # BridgeBitmapGlyph, CBDT/sbix 支持
    |
    |-- hinting.rs            # 字体微调模块
    |                         # BridgeHintingInstance, BridgeGlyphStyles,
    |                         # make_hinting_instance(), SmoothMode 配置
    |
    |-- names.rs              # 字体名称模块
    |                         # BridgeLocalizedStrings, family_name(),
    |                         # postscript_name()
    |
    |-- verbs_points_pen.rs   # 路径提取模块
    |                         # VerbsPointsPen (OutlinePen trait 实现)
    |                         # get_path_verbs_points()
    |
    |-- skpath_bridge.h       # C++ 纯虚接口头文件
                              # AxisWrapper, ColorPainterWrapper
```

## 关键类与函数

### 1. CXX 桥接共享数据结构 (ffi.rs)

这些结构体在 C++ 和 Rust 两侧共享，保持完全一致的内存布局：

```rust
// 字体度量信息（对应 SkFontMetrics 的子集）
pub struct Metrics {
    top: f32, ascent: f32, descent: f32, bottom: f32,
    leading: f32, avg_char_width: f32, max_char_width: f32,
    x_min: f32, x_max: f32, x_height: f32, cap_height: f32,
    underline_position: f32, underline_thickness: f32,
    strikeout_position: f32, strikeout_thickness: f32,
}

// 路径点坐标
struct FfiPoint { x: f32, y: f32 }

// 颜色停止点（渐变用）
pub struct ColorStop { stop: f32, palette_index: u16, alpha: f32 }

// 变量轴设计坐标（对应 SkFontArguments::VariationPosition::Coordinate）
struct SkiaDesignCoordinate { axis: u32, value: f32 }

// 字形缩放器度量
struct BridgeScalerMetrics {
    has_overlaps: bool,
    has_adjusted_advance: bool,
    adjusted_advance: f32,
}

// 位图字形度量
struct BitmapMetrics {
    bearing_x: f32, bearing_y: f32,
    ppem_x: f32, ppem_y: f32,
    placement_origin_bottom_left: bool,
    inner_bearing_x: f32, inner_bearing_y: f32,
    advance: f32,
}

// 仿射变换矩阵
struct Transform { xx: f32, xy: f32, yx: f32, yy: f32, dx: f32, dy: f32 }

// 字体样式信息
pub struct BridgeFontStyle { pub weight: i32, pub slant: i32, pub width: i32 }

// 渐变参数
struct FillLinearParams { x0: f32, y0: f32, x1: f32, y1: f32 }
struct FillRadialParams { x0: f32, y0: f32, r0: f32, x1: f32, y1: f32, r1: f32 }
struct FillSweepParams { x0: f32, y0: f32, start_angle: f32, end_angle: f32 }

// 调色板覆盖
pub struct PaletteOverride { index: u16, color_8888: u32 }

// 裁剪框
struct ClipBox { x_min: f32, y_min: f32, x_max: f32, y_max: f32 }

// 自动微调控制枚举
pub enum AutoHintingControl { ForceForGlyf, ForceForGlyfAndCff, ForceOff, Fallback }

// 轮廓格式枚举
pub enum OutlineFormat { NoOutlines, Glyf, Cff, Cff2 }
```

### 2. base.rs - 基础字体操作

**不透明桥接类型：**

```rust
// 字体引用包装器，持有 skrifa::FontRef 的可选值
pub struct BridgeFontRef<'a> {
    font: Option<FontRef<'a>>,
    has_any_color: bool,           // 快速判断是否包含彩色表
}

// 轮廓集合包装器
pub struct BridgeOutlineCollection<'a>(pub Option<OutlineGlyphCollection<'a>>);

// 归一化坐标（变量字体用）
pub struct BridgeNormalizedCoords {
    pub normalized_coords: Location,
    filtered_user_coords: Vec<VariationSetting>,
}

// 字符映射索引（优化批量字符查找性能）
pub struct BridgeMappingIndex(MappingIndex);
```

**核心函数：**

| 函数名 | 说明 |
|--------|------|
| `make_font_ref(font_data, index)` | 从字节切片创建字体引用 |
| `font_ref_is_valid(ref)` | 验证字体引用有效性 |
| `font_or_collection(data, num_fonts)` | 判断单字体或 TTC 集合 |
| `make_mapping_index(font_ref)` | 构建字符映射索引 |
| `lookup_glyph_or_zero(ref, map, codepoints, glyphs)` | 批量字符到字形 ID 映射 |
| `num_glyphs(font_ref)` | 获取字形数量 |
| `fill_glyph_to_unicode_map(ref, map)` | 构建字形到 Unicode 反向映射 |
| `unhinted_advance_width_or_zero(ref, size, coords, glyph_id)` | 获取无微调前进宽度 |
| `units_per_em_or_zero(font_ref)` | 获取 UPM（每 em 单位数） |
| `get_skia_metrics(ref, size, coords)` | 获取缩放后的字体度量 |
| `get_unscaled_metrics(ref, coords)` | 获取未缩放的字体度量 |
| `resolve_into_normalized_coords(ref, design_coords)` | 将设计坐标归一化 |
| `get_outline_collection(font_ref)` | 获取轮廓集合 |
| `get_font_style(ref, coords, style)` | 获取字体样式（weight/width/slant） |
| `table_data(ref, tag, offset, data)` | 读取原始字体表数据 |
| `table_tags(ref, tags)` | 枚举字体表标签 |
| `populate_axes(ref, axis_wrapper)` | 填充变量轴参数 |
| `variation_position(coords, coordinates)` | 获取当前变量位置 |
| `is_embeddable/is_subsettable/is_fixed_pitch(ref)` | 字体属性查询 |
| `is_serif_style/is_script_style(ref)` | 字体风格分类查询 |
| `italic_angle(ref)` | 获取斜体角度 |

### 3. colr.rs - 彩色字体模块

```rust
// 颜色停止点迭代器桥接
pub struct BridgeColorStops<'a> {
    pub stops_iterator: Box<dyn Iterator<Item = &'a skrifa::color::ColorStop> + 'a>,
    pub num_stops: usize,
}

// 内部 ColorPainter 实现，适配 skrifa::color::ColorPainter trait
struct ColorPainterImpl<'a> {
    color_painter_wrapper: Pin<&'a mut ColorPainterWrapper>,
    clip_level: usize,   // 用于 BoundsPainter 模式下的裁剪优化
}
```

**关键函数：**

| 函数名 | 说明 |
|--------|------|
| `draw_colr_glyph(ref, coords, glyph_id, painter)` | 绘制 COLR 彩色字形 |
| `has_colrv1_glyph(ref, glyph_id)` | 检查是否有 COLRv1 字形 |
| `has_colrv0_glyph(ref, glyph_id)` | 检查是否有 COLRv0 字形 |
| `get_colrv1_clip_box(ref, coords, glyph_id, size, clip_box)` | 获取 COLRv1 裁剪框 |
| `resolve_palette(ref, base_palette, overrides)` | 解析 CPAL 调色板 |
| `next_color_stop(stops, stop)` | 迭代下一个颜色停止点 |
| `num_color_stops(stops)` | 获取颜色停止点数量 |

`ColorPainterImpl` 实现了 skrifa 的 `ColorPainter` trait，将 COLR 绘制操作转发到
C++ 侧的 `ColorPainterWrapper`。它支持以下操作：
- `push_transform` / `pop_transform` - 变换矩阵栈
- `push_clip_glyph` / `push_clip_box` / `pop_clip` - 裁剪操作
- `fill_solid` / `fill_linear_gradient` / `fill_radial_gradient` / `fill_sweep_gradient` - 填充
- `push_layer` / `pop_layer` - 合成图层
- 优化路径：`fill_glyph_solid/linear/radial/sweep` - 合并字形裁剪和填充为单次 drawPath 调用

### 4. bitmap.rs - 位图字体模块

```rust
// 位图像素数据枚举
pub enum BitmapPixelData<'a> {
    PngData(&'a [u8]),       // PNG 格式的位图数据
}

// 位图字形桥接类型
pub struct BridgeBitmapGlyph<'a> {
    pub data: Option<BitmapPixelData<'a>>,
    pub metrics: FfiBitmapMetrics,
}
```

支持两种位图字体格式：
- **CBDT/CBLC** (Color Bitmap Data Table) - 由 `CblcGlyph` 内部类型处理
- **sbix** (Standard Bitmap Graphics Table) - 由 `SbixGlyph` 内部类型处理

`best_strike_size()` 函数实现了最佳 strike 尺寸选择算法：优先选择不小于请求尺寸的最近 strike，
如果没有更大的 strike，则选择最接近的较小 strike。

| 函数名 | 说明 |
|--------|------|
| `has_bitmap_glyph(ref, glyph_id)` | 检查是否有位图字形 |
| `bitmap_glyph(ref, glyph_id, font_size)` | 获取位图字形数据和度量 |
| `png_data(bitmap_glyph)` | 提取 PNG 数据切片 |
| `bitmap_metrics(bitmap_glyph)` | 获取位图度量信息 |

### 5. hinting.rs - 字体微调模块

```rust
// 延迟计算的字形样式（用于自动微调优化）
pub struct BridgeGlyphStyles {
    glyph_styles: OnceLock<GlyphStyles>,   // 线程安全的懒初始化
}

// 微调实例包装器
pub struct BridgeHintingInstance(pub Option<HintingInstance>);
```

**微调模式映射：**

| Skia 请求 | Rust SmoothMode | 说明 |
|-----------|-----------------|------|
| `do_light_hinting = true` | `SmoothMode::Light` | 轻量微调 |
| `do_lcd_antialiasing = true, vertical = false` | `SmoothMode::Lcd` | LCD 水平子像素 |
| `do_lcd_antialiasing = true, vertical = true` | `SmoothMode::VerticalLcd` | LCD 垂直子像素 |
| 其他 | `SmoothMode::Normal` | 标准微调 |

**自动微调引擎选择：**

| AutoHintingControl | Engine | 说明 |
|-------------------|--------|------|
| `ForceForGlyf` | `Engine::Auto` | 仅对 glyf 格式强制自动微调 |
| `ForceForGlyfAndCff` | `Engine::Auto` | 对 glyf 和 CFF 都强制自动微调 |
| `ForceOff` | `Engine::Interpreter` | 强制关闭自动微调（Android Framework） |
| `Fallback` | `Engine::AutoFallback` | 自动回退（默认，匹配 FreeType 行为） |

| 函数名 | 说明 |
|--------|------|
| `hinting_reliant(outlines)` | 检测字体是否依赖微调指令 |
| `no_hinting_instance()` | 创建无微调实例 |
| `make_hinting_instance(...)` | 创建平滑微调实例 |
| `make_mono_hinting_instance(...)` | 创建单色（BW）微调实例 |
| `get_bridge_glyph_styles()` | 创建延迟计算的字形样式容器 |

### 6. names.rs - 字体名称模块

```rust
pub struct BridgeLocalizedStrings<'a> {
    localized_strings: LocalizedStrings<'a>,
}
```

家族名称解析遵循 OpenType 规范优先级：
1. 检查 `OS/2` 表的 `fsSelection` 位 8（WWS 标志）
2. 如果不是 WWS-only：先查 `WWS_FAMILY_NAME` (StringId 21)
3. 回退到 `TYPOGRAPHIC_FAMILY_NAME` (StringId 16)
4. 最终回退到 `FAMILY_NAME` (StringId 1)

| 函数名 | 说明 |
|--------|------|
| `family_name(font_ref)` | 获取字体家族名称 |
| `postscript_name(font_ref, out)` | 获取 PostScript 名称 |
| `get_localized_strings(font_ref)` | 创建本地化名称迭代器 |
| `localized_name_next(strings, name)` | 获取下一个本地化名称 |

### 7. verbs_points_pen.rs - 路径提取模块

```rust
// 路径提取笔实现，将 skrifa 轮廓输出为 SkPath 格式的 verbs + points
pub struct VerbsPointsPen<'a> {
    verbs: &'a mut Vec<u8>,         // 路径动词（MoveTo/LineTo/QuadTo/CubicTo/Close）
    points: &'a mut Vec<FfiPoint>,  // 路径控制点
    started: bool,                   // 子路径是否已开始
    current: FfiPoint,              // 当前点位置
}

// 路径动词对应 SkPathVerb 枚举值
enum PathVerb {
    MoveTo = 0, LineTo = 1, QuadTo = 2, CubicTo = 4, Close = 5
}
```

`VerbsPointsPen` 实现了 skrifa 的 `OutlinePen` trait：
- `move_to(x, y)` - 移动到新位置（Y 轴取反以适配 Skia 坐标系）
- `line_to(x, y)` - 画直线
- `quad_to(cx, cy, x, y)` - 二次贝塞尔曲线
- `curve_to(cx0, cy0, cx1, cy1, x, y)` - 三次贝塞尔曲线
- `close()` - 关闭子路径

**注意：** 该 Pen 会自动对所有 Y 坐标取反（`-y`），因为 OpenType 字体使用向上为正的坐标系，
而 Skia 使用向下为正的屏幕坐标系。

预分配常量 `PATH_EXTRACTION_RESERVE = 150`，用于减少路径提取时的内存分配次数。
C++ 侧在每次路径提取后调用 `shrink_verbs_points_if_needed()` 将缓冲区收缩回预分配大小。

### 8. skpath_bridge.h - C++ 纯虚接口

该头文件定义了两个 C++ 纯虚接口，供 Rust 侧通过 CXX 回调：

```cpp
namespace fontations_ffi {

// 变量轴参数填充接口
class AxisWrapper {
    virtual bool populate_axis(size_t i, uint32_t axisTag,
                               float min, float def, float max, bool hidden) = 0;
    virtual size_t size() const = 0;
};

// COLR 彩色字体绘制回调接口
class ColorPainterWrapper {
    virtual bool is_bounds_mode() = 0;
    virtual void push_transform(const Transform&) = 0;
    virtual void pop_transform() = 0;
    virtual void push_clip_glyph(uint16_t glyph_id) = 0;
    virtual void push_clip_rectangle(float x_min, float y_min, float x_max, float y_max) = 0;
    virtual void pop_clip() = 0;
    virtual void fill_solid(uint16_t palette_index, float alpha) = 0;
    virtual void fill_linear(const FillLinearParams&, BridgeColorStops&, uint8_t extend_mode) = 0;
    virtual void fill_radial(const FillRadialParams&, BridgeColorStops&, uint8_t extend_mode) = 0;
    virtual void fill_sweep(const FillSweepParams&, BridgeColorStops&, uint8_t extend_mode) = 0;
    // 优化调用：合并字形裁剪与填充
    virtual void fill_glyph_solid(uint16_t glyph_id, uint16_t palette_index, float alpha) = 0;
    virtual void fill_glyph_radial(...) = 0;
    virtual void fill_glyph_linear(...) = 0;
    virtual void fill_glyph_sweep(...) = 0;
    virtual void push_layer(uint8_t colrV1CompositeMode) = 0;
    virtual void pop_layer() = 0;
};

}  // namespace fontations_ffi
```

## 依赖关系

### Rust Crate 依赖

| Crate | 版本 | 用途 |
|-------|------|------|
| `skrifa` | 0.36 | 高层字体操作 API（度量、轮廓、COLR、hinting） |
| `read-fonts` | 0.34 | 底层 OpenType 表读取与解析 |
| `font-types` | 0.9 | 基础字体类型定义（GlyphId、Tag 等） |
| `bytemuck` | 1.16 | 安全的字节级类型转换 |
| `cxx` | 1.0 | C++/Rust 互操作框架 |

**Skrifa 使用的关键 API：**
- `skrifa::MetadataProvider` - 字体元数据访问
- `skrifa::OutlineGlyphCollection` - 字形轮廓集合
- `skrifa::charmap::MappingIndex` - 高效字符映射
- `skrifa::metrics::Metrics` / `GlyphMetrics` - 度量信息
- `skrifa::color::ColorPainter` - COLR 绘制回调 trait
- `skrifa::outline::HintingInstance` - 微调配置
- `skrifa::outline::OutlinePen` - 轮廓输出 trait
- `skrifa::outline::GlyphStyles` - 自动微调字形分类

### Bazel 构建目标

```
:deps (skia_cc_library)
  |-- :bridge_rust_side     (rust_static_library - 编译后的 Rust 静态库)
  |-- :fontations_ffi       (rust_cxx_bridge - CXX 生成的 C++ 绑定代码)
  |-- :path_bridge_include  (skia_cc_library - skpath_bridge.h 头文件)
```

### 上游依赖方

```
//src/ports:fontations_support    <-- 依赖 :deps
//src/ports:fontmgr_fontations_empty  <-- 依赖 :deps
```

## 设计模式分析

### 1. 桥接模式 (Bridge Pattern)

整个 fontations 子目录本身就是桥接模式的典型应用。CXX 框架在编译时生成 `ffi.rs.h` 头文件，
包含了 Rust 类型的 C++ 前向声明和函数签名，使得两种语言的代码可以在运行时通过二进制接口互调。
不透明类型（`rust::Box<BridgeFontRef>` 等）确保了跨语言边界的类型安全。

### 2. 适配器模式 (Adapter Pattern)

`ColorPainterImpl`（colr.rs）是适配器模式的精确实现：它将 skrifa 的 `ColorPainter` trait
接口适配为 Skia 的 `ColorPainterWrapper` C++ 虚接口。Skrifa 使用 Rust 风格的
`Transform`、`BoundingBox<f32>` 等类型，而 Skia 使用 `fontations_ffi::Transform`、
`ClipBox` 等 FFI 兼容类型。`ColorPainterImpl` 负责在两者之间进行转换。

### 3. 策略模式 (Strategy Pattern)

`BridgeHintingInstance` 封装了不同的微调策略。根据请求的 hinting 级别和平台配置，可以创建
不同的微调实例（无微调、轻量微调、标准微调、LCD 微调、单色微调），每种实例内部使用不同的
skrifa `HintingOptions` 配置。

### 4. 迭代器模式 (Iterator Pattern)

`BridgeColorStops` 和 `BridgeLocalizedStrings` 都是跨语言迭代器的实现。由于 CXX 不支持
直接暴露 Rust 迭代器，这些类型将 Rust 迭代器包装为具有 `next()` 语义的函数对，C++ 侧通过
循环调用 `next_color_stop()` 或 `localized_name_next()` 来消费元素。

### 5. 延迟初始化模式 (Lazy Initialization)

`BridgeGlyphStyles` 使用 `OnceLock<GlyphStyles>` 实现线程安全的延迟初始化。`GlyphStyles`
的计算开销较大（需要分析所有字形的 hinting 特征），通过延迟到首次需要时才计算，避免了不使用
自动微调时的性能浪费。

## 数据流

### CXX 桥接数据流

```
C++ 调用 Rust:
  sk_sp<SkData> fontData  -->  rust::Slice<const uint8_t>  -->  FontRef<'a>
  (零拷贝，Rust 直接读取 C++ 管理的内存)

Rust 返回到 C++:
  rust::Box<BridgeFontRef>  -->  C++ 持有 opaque pointer
  (C++ 不能直接访问内部字段，只能通过 FFI 函数操作)

路径数据返回:
  Rust Vec<u8> (verbs) + Vec<FfiPoint> (points)
    --> C++ 侧直接通过 rust::Vec 访问数据
    --> 构建 SkPath::Make(points, verbs, ...)
```

### COLR 彩色字形渲染数据流

```
C++ 侧:
  SkFontationsScalerContext::drawCOLRGlyph()
    |-- 创建 sk_fontations::ColorPainter (实现 ColorPainterWrapper)
    |-- 调用 fontations_ffi::draw_colr_glyph(ref, coords, glyph_id, painter)
         |
         v
Rust 侧 (colr.rs):
  draw_colr_glyph()
    |-- 创建 ColorPainterImpl { color_painter_wrapper: &mut painter }
    |-- 调用 skrifa color_glyph.paint(normalizedCoords, &mut colorPainterImpl)
         |
         |  skrifa 遍历 COLR 表，对每个绘制操作回调:
         |
         |-- ColorPainterImpl::push_transform(transform)
         |     --> Pin<&mut ColorPainterWrapper>::push_transform()
         |           --> [跨 FFI 边界] --> ColorPainter::push_transform()
         |                 --> SkCanvas::concat()
         |
         |-- ColorPainterImpl::fill_solid(palette_index, alpha)
         |     --> Pin<&mut ColorPainterWrapper>::fill_glyph_solid()
         |           --> [跨 FFI 边界] --> ColorPainter::fill_glyph_solid()
         |                 --> SkCanvas::drawPath(path, paint)
         |
         |-- ... (线性/径向/扫描渐变、图层合成等)
```

### 变量字体坐标归一化流

```
C++ 侧:
  SkFontArguments::VariationPosition (用户设计坐标)
    |-- SkiaDesignCoordinate[] { axis: u32, value: f32 }
    |
    v (static_assert 确保内存布局一致，reinterpret_cast 零拷贝)
    |
Rust 侧 (base.rs):
  resolve_into_normalized_coords(font_ref, design_coords)
    |-- skrifa Location::new(...) 将设计坐标归一化到 [-1.0, 1.0]
    |-- 返回 Box<BridgeNormalizedCoords>
    |
C++ 侧:
    持有 rust::Box<BridgeNormalizedCoords>，后续所有操作使用归一化坐标
```

## 平台特定说明

### Android Framework 特殊处理

在 `SkFontationsScalerContext` 构造函数中，Android Framework 构建会强制关闭自动微调，
以匹配 FreeType 后端的行为：

```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    if (!forceAutoHinting)
        autoHintingControl = AutoHinting::ForceOff;
#endif
```

对应 Rust 侧，`AutoHintingControl::ForceOff` 会使用 `Engine::Interpreter`，仅使用
字体内置的 TrueType/CFF 指令，完全不使用 skrifa 的自动微调引擎。

### FreeType 行为兼容性

Fontations 后端在多处刻意匹配 FreeType 的行为：

1. **Named Instance 索引编码** - 使用 FreeType 的"shifted index"编码方式，将命名实例
   索引左移 16 位并加 1 存储在 TTC 集合索引的高位中。

2. **Hinting 降级** - 与 FreeType 一致，非 LCD 渲染时将 Full hinting 降级为 Normal：
   ```cpp
   if (SkFontHinting::kFull == h && !isLCD(*rec)) {
       h = SkFontHinting::kNormal;
   }
   ```

3. **抗锯齿标志处理** - 忽略 `kGenA8FromLCD_Flag` 以避免与 FreeType 后端的视觉差异。

4. **Advance 舍入** - Hinting 模式下将前进宽度舍入到整数像素，匹配 FreeType 的
   `FT_Load_Glyph` + `FT_LOAD_DEFAULT` 行为。

### 线程安全考虑

- `BridgeGlyphStyles` 使用 `OnceLock` 实现线程安全的延迟初始化。
- `SkFontationsScalerContext` 中的路径提取缓冲区（`fPathVerbs`、`fPathPoints`）通过
  `SkMutex fPathMutex` 保护，因为 COLRv1 绘制可能从 `SkDrawable` 中递归调用路径提取。
- Rust 侧的不可变引用（`&BridgeFontRef`）可以安全地在多线程间共享。

## 相关文档与参考

### Skia 内部相关文件

| 路径 | 说明 |
|------|------|
| `src/ports/SkTypeface_fontations.cpp` | C++ 侧 Typeface 完整实现 |
| `src/ports/SkTypeface_fontations_priv.h` | C++ 侧类定义 |
| `src/ports/SkTypeface_fontations_factory.h` | FactoryId 注册 |
| `src/ports/SkFontScanner_fontations.cpp` | 字体扫描器实现 |
| `src/ports/SkFontMgr_fontations_empty.cpp` | 空字体管理器 |
| `include/ports/SkTypeface_fontations.h` | 公开 API 头文件 |
| `include/ports/SkFontMgr_Fontations.h` | FontMgr 公开 API |
| `include/ports/SkFontScanner_Fontations.h` | FontScanner 公开 API |

### 外部参考

- [Google Fontations 项目](https://github.com/googlefonts/fontations) - Rust 字体库源码
- [Skrifa API 文档](https://docs.rs/skrifa/) - 高层字体操作 Rust 文档
- [read-fonts API 文档](https://docs.rs/read-fonts/) - 底层字体表读取文档
- [CXX 框架文档](https://cxx.rs/) - C++/Rust 互操作框架
- [OpenType 规范](https://learn.microsoft.com/en-us/typography/opentype/spec/) - 字体格式标准
- [OpenType COLR 表](https://learn.microsoft.com/en-us/typography/opentype/spec/colr) - 彩色字体规范
- [OpenType CPAL 表](https://learn.microsoft.com/en-us/typography/opentype/spec/cpal) - 调色板规范
- [OpenType CBDT/CBLC](https://learn.microsoft.com/en-us/typography/opentype/spec/cbdt) - 位图字体规范
- [Apple sbix 表](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6sbix.html) - Apple 位图字体规范
