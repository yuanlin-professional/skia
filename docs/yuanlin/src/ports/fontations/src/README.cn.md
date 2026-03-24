# src/ports/fontations/src - Fontations Rust 源代码目录

## 概述

`src/ports/fontations/src` 目录包含了 Skia Fontations 字体后端的全部 **Rust 源代码**。
这些代码通过 CXX 框架（C++/Rust 互操作工具）编译为静态库，与 Skia 的 C++ 代码链接在一起。
该目录是 Skia 代码库中唯一使用 Rust 语言编写的产品代码（非测试），代表了在大型 C++ 项目中
逐步引入 Rust 的工程实践。

整个 Rust 代码库围绕一个核心目标设计：**将 Fontations 生态（skrifa、read-fonts、font-types）
的字体解析能力通过类型安全的 FFI 接口暴露给 Skia C++**。代码组织遵循了清晰的关注点分离原则，
每个 `.rs` 文件负责一个特定的字体功能域。`ffi.rs` 作为 crate root 和桥接入口，既定义了
共享数据结构，也声明了双向的函数签名；其他模块则提供实际的函数实现。

从 Rust 生态的角度看，本目录的代码是对 `skrifa` crate 的**薄封装层（thin wrapper）**。
大部分函数的实现逻辑都很直接：接收 CXX 桥接类型，解包为 skrifa 原生类型，调用 skrifa API，
然后将结果转换回 CXX 桥接类型返回。这种设计保证了性能（避免不必要的数据转换和拷贝），同时也
使得 Fontations 上游的版本升级对 Skia 侧的影响最小化。

该目录中最复杂的模块是 `colr.rs`（COLR 彩色字体渲染）和 `hinting.rs`（字体微调），它们
不仅需要桥接数据类型，还需要实现 skrifa 定义的 trait 接口（`ColorPainter`、`OutlinePen`）
以提供渲染回调机制。`colr.rs` 中的 `ColorPainterImpl` 尤为精巧，它将 skrifa 的
`ColorPainter` trait 回调转发为 CXX Pin 引用上的 C++ 虚函数调用，实现了从 Rust trait
到 C++ 虚表的无缝桥接。

值得注意的是，本目录中的 Rust 代码大量使用了 `unsafe` 块。这是因为 CXX 生成的 FFI 函数
天然涉及跨语言内存操作，而且许多函数需要保证引用的生命周期（`'a` 参数）在 C++ 侧被正确管理。
这些 `unsafe` 的安全性由上层 C++ 代码（`SkTypeface_fontations.cpp`）中的资源管理逻辑
来保证——例如 `SkTypeface_Fontations` 持有 `fFontData`（`sk_sp<const SkData>`），
确保 `BridgeFontRef` 引用的字节切片在整个 Typeface 生命周期内有效。

## 架构图

```
+-------------------------------------------------------------------+
|  ffi.rs (crate root, CXX 桥接入口)                                 |
|                                                                   |
|  #[cxx::bridge(namespace = "fontations_ffi")]                     |
|  pub mod ffi {                                                    |
|    +-----------------------------------------------------+       |
|    | 共享类型区域 (C++ 和 Rust 都可直接使用)               |       |
|    | Metrics, FfiPoint, ColorStop, SkiaDesignCoordinate,  |       |
|    | BridgeScalerMetrics, Transform, Fill*Params,         |       |
|    | BitmapMetrics, PaletteOverride, ClipBox,             |       |
|    | BridgeFontStyle, AutoHintingControl, OutlineFormat   |       |
|    +-----------------------------------------------------+       |
|    | extern "Rust" { ... }  (Rust 函数暴露给 C++)          |       |
|    |   make_font_ref, font_ref_is_valid, num_glyphs, ... |       |
|    +-----------------------------------------------------+       |
|    | extern "C++" { ... }  (C++ 接口供 Rust 调用)          |       |
|    |   AxisWrapper, ColorPainterWrapper                   |       |
|    +-----------------------------------------------------+       |
|  }                                                                |
|                                                                   |
|  mod base;     --+                                                |
|  mod bitmap;     |  use crate::{base::..., colr::..., ...};       |
|  mod colr;       |  (模块间引用)                                   |
|  mod hinting;    |                                                |
|  mod names;    --+                                                |
|  mod verbs_points_pen;                                            |
+-------------------------------------------------------------------+
         |              |             |             |
         v              v             v             v
+-------------+  +-------------+  +---------+  +----------+
|   skrifa    |  | read-fonts  |  | font-   |  |   cxx    |
|   0.36      |  |   0.34      |  | types   |  |   1.0    |
|             |  |             |  | 0.9     |  |          |
| MetadataPr  |  | FontRef     |  | GlyphId |  | Bridge   |
| ovider      |  | TableProvid |  | Tag     |  | 代码生成 |
| ColorPainte |  | er          |  |         |  |          |
| r, Outline  |  |             |  |         |  |          |
| Pen         |  |             |  |         |  |          |
+-------------+  +-------------+  +---------+  +----------+
```

## 目录结构

```
src/ports/fontations/src/
|
|-- ffi.rs                  # CXX 桥接定义（crate root）
|                           #   - 40+ 共享数据结构
|                           #   - 50+ extern "Rust" 函数声明
|                           #   - 2 个 extern "C++" 接口类
|                           #   - 模块导入和 use 声明
|
|-- base.rs                 # 基础字体操作（约 500 行）
|                           #   - BridgeFontRef: 核心字体引用封装
|                           #   - BridgeNormalizedCoords: 变量字体坐标
|                           #   - BridgeOutlineCollection: 轮廓集合
|                           #   - BridgeMappingIndex: 字符映射索引
|                           #   - 字形映射、度量、表访问、轴信息等
|
|-- colr.rs                 # COLR 彩色字体表处理（约 300 行）
|                           #   - BridgeColorStops: 颜色停止点迭代
|                           #   - ColorPainterImpl: skrifa ColorPainter 适配
|                           #   - COLR 绘制、调色板解析、裁剪框
|
|-- bitmap.rs               # 位图字体处理（约 200 行）
|                           #   - BridgeBitmapGlyph: 位图字形数据
|                           #   - CBDT/CBLC 和 sbix 两种格式支持
|                           #   - best_strike_size(): 最佳 strike 选择
|
|-- hinting.rs              # 字体微调处理（约 150 行）
|                           #   - BridgeGlyphStyles: 延迟初始化字形样式
|                           #   - BridgeHintingInstance: 微调实例封装
|                           #   - SmoothMode / Engine 映射逻辑
|
|-- names.rs                # 字体名称表处理（约 80 行）
|                           #   - BridgeLocalizedStrings: 本地化名称迭代
|                           #   - 家族名称优先级解析
|                           #   - PostScript 名称提取
|
|-- verbs_points_pen.rs     # 字形轮廓路径提取（约 120 行）
|                           #   - VerbsPointsPen: OutlinePen trait 实现
|                           #   - PathVerb 枚举（匹配 SkPathVerb）
|                           #   - 坐标系翻转（Y轴取反）
|
|-- skpath_bridge.h         # C++ 纯虚接口定义（约 80 行）
|                           #   - AxisWrapper: 变量轴参数回写接口
|                           #   - ColorPainterWrapper: COLR 绘制回调接口
```

## 关键类与函数

### ffi.rs - 桥接定义入口

`ffi.rs` 是整个 Rust crate 的根文件（`lib.rs` 的等价物，通过 Cargo.toml 中
`path = "src/ffi.rs"` 指定）。它使用 `#[cxx::bridge(namespace = "fontations_ffi")]`
宏定义了 C++ 和 Rust 之间的完整接口。

**模块导入结构：**

```rust
mod base;
mod bitmap;
mod colr;
mod hinting;
mod names;
mod verbs_points_pen;

use crate::{
    base::{make_font_ref, font_ref_is_valid, ..., BridgeFontRef, ...},
    bitmap::{bitmap_glyph, ..., BridgeBitmapGlyph},
    colr::{draw_colr_glyph, ..., BridgeColorStops},
    hinting::{make_hinting_instance, ..., BridgeHintingInstance},
    names::{family_name, ..., BridgeLocalizedStrings},
    verbs_points_pen::{get_path_verbs_points, shrink_verbs_points_if_needed},
};
```

**extern "Rust" 块中的关键函数签名分类：**

| 功能域 | 函数 | 说明 |
|--------|------|------|
| 字体引用 | `make_font_ref`, `font_ref_is_valid` | 创建和验证字体引用 |
| 集合判断 | `font_or_collection`, `num_named_instances` | TTC 集合检测 |
| 字符映射 | `make_mapping_index`, `lookup_glyph_or_zero` | cmap 表操作 |
| 轮廓提取 | `get_path_verbs_points`, `shrink_verbs_points_if_needed` | glyf/CFF 轮廓 |
| 度量信息 | `get_skia_metrics`, `get_unscaled_metrics`, `unhinted_advance_width_or_zero` | 字体度量 |
| 基本信息 | `num_glyphs`, `units_per_em_or_zero`, `family_name`, `postscript_name` | 元数据 |
| 变量字体 | `resolve_into_normalized_coords`, `variation_position`, `populate_axes` | 变量轴 |
| 彩色字体 | `draw_colr_glyph`, `has_colrv1_glyph`, `has_colrv0_glyph`, `resolve_palette` | COLR/CPAL |
| 位图字体 | `bitmap_glyph`, `png_data`, `bitmap_metrics`, `has_bitmap_glyph` | CBDT/sbix |
| 微调 | `make_hinting_instance`, `no_hinting_instance`, `hinting_reliant` | hinting |
| 表访问 | `table_data`, `table_tags` | 原始表读取 |
| 属性查询 | `is_embeddable`, `is_subsettable`, `is_fixed_pitch`, `italic_angle` | 字体属性 |
| 样式信息 | `get_font_style`, `is_serif_style`, `is_script_style` | 字体分类 |
| 名称遍历 | `get_localized_strings`, `localized_name_next` | 名称国际化 |

**extern "C++" 块中声明的 C++ 接口：**

```rust
unsafe extern "C++" {
    include!("src/ports/fontations/src/skpath_bridge.h");

    type AxisWrapper;
    fn populate_axis(self: Pin<&mut AxisWrapper>, ...) -> bool;
    fn size(self: Pin<&AxisWrapper>) -> usize;

    type ColorPainterWrapper;
    fn is_bounds_mode(self: Pin<&mut ColorPainterWrapper>) -> bool;
    fn push_transform(self: Pin<&mut ColorPainterWrapper>, ...);
    fn pop_transform(self: Pin<&mut ColorPainterWrapper>);
    fn push_clip_glyph(self: Pin<&mut ColorPainterWrapper>, glyph_id: u16);
    fn fill_solid(self: Pin<&mut ColorPainterWrapper>, palette_index: u16, alpha: f32);
    fn fill_linear(self: Pin<&mut ColorPainterWrapper>, ...);
    fn fill_radial(self: Pin<&mut ColorPainterWrapper>, ...);
    fn fill_sweep(self: Pin<&mut ColorPainterWrapper>, ...);
    fn fill_glyph_solid(self: Pin<&mut ColorPainterWrapper>, ...);
    fn fill_glyph_linear(self: Pin<&mut ColorPainterWrapper>, ...);
    fn fill_glyph_radial(self: Pin<&mut ColorPainterWrapper>, ...);
    fn fill_glyph_sweep(self: Pin<&mut ColorPainterWrapper>, ...);
    fn push_layer(self: Pin<&mut ColorPainterWrapper>, compositeMode: u8);
    fn pop_layer(self: Pin<&mut ColorPainterWrapper>);
}
```

### base.rs - 详细实现

**BridgeFontRef - 核心字体引用：**

```rust
pub struct BridgeFontRef<'a> {
    font: Option<FontRef<'a>>,   // skrifa 的字体引用，None 表示无效
    has_any_color: bool,          // 缓存结果：是否包含任何彩色表
}

impl<'a> BridgeFontRef<'a> {
    // 安全的字体引用访问模式：如果 font 为 None 则返回 None
    pub fn with_font<T>(&'a self, f: impl FnOnce(&'a FontRef) -> Option<T>) -> Option<T> {
        f(self.font.as_ref()?)
    }
}
```

`with_font()` 方法是一个关键的设计选择——它将字体引用的可选性（`Option<FontRef>`）封装在
一个高阶函数中，使得所有使用字体引用的代码不需要显式处理 `None` 情况。返回 `None` 表示操作
失败，C++ 侧通常将其映射为零值或空结果。

**度量信息获取实现模式：**

```rust
pub fn get_skia_metrics(
    font_ref: &BridgeFontRef,
    size: f32,
    coords: &BridgeNormalizedCoords,
) -> Metrics {
    font_ref
        .with_font(|f| {
            let skrifa_metrics = SkrifaMetrics::new(f, Size::new(size), coords.normalized_coords.coords());
            Some(Metrics {
                top: skrifa_metrics.bounds.map(|b| b.y_min).unwrap_or_default(),
                ascent: skrifa_metrics.ascent,
                // ... 其他字段映射
            })
        })
        .unwrap_or_default()   // 如果字体无效，返回全零的 Metrics
}
```

### colr.rs - COLR 彩色字体详细实现

**ColorPainterImpl 的 Brush 处理：**

`ColorPainterImpl` 实现 skrifa `ColorPainter` trait 时，最复杂的部分是 `fill` 方法中
对不同 `Brush` 类型的分派：

```rust
impl<'a> ColorPainter for ColorPainterImpl<'a> {
    fn fill(&mut self, brush: Brush<'_>) {
        match brush {
            Brush::Solid { palette_index, alpha } => {
                self.color_painter_wrapper.as_mut()
                    .fill_solid(palette_index, alpha);
            }
            Brush::LinearGradient { p0, p1, color_stops, extend } => {
                // 构建 BridgeColorStops 并调用 fill_linear
            }
            Brush::RadialGradient { c0, r0, c1, r1, color_stops, extend } => {
                // 构建 BridgeColorStops 并调用 fill_radial
            }
            Brush::SweepGradient { center, start_angle, end_angle, color_stops, extend } => {
                // 构建 BridgeColorStops 并调用 fill_sweep
            }
        }
    }
}
```

**优化调用（fill_glyph_* 系列）：**

colr.rs 中实现了一个关键优化——当 COLR 操作序列为"裁剪到字形轮廓 + 填充"的常见模式时，
Rust 侧可以直接调用 `fill_glyph_solid/linear/radial/sweep`，C++ 侧可以将其合并为
单次 `SkCanvas::drawPath(path, paint)` 调用，避免了创建临时裁剪路径的开销。

**BoundsPainter 模式优化：**

colr.rs 中的 `clip_level` 字段用于 `BoundsPainter` 模式的优化。当
`is_bounds_mode()` 返回 true 时，只有第一层裁剪操作会被执行（用于获取边界框），
嵌套的裁剪和绘制操作会被跳过以提升性能。

### verbs_points_pen.rs - 路径提取详细实现

**坐标系转换：**

OpenType 字体的坐标系为 Y 轴向上（数学坐标系），而 Skia 使用 Y 轴向下（屏幕坐标系）。
`VerbsPointsPen` 在所有输出点的 Y 坐标上执行取反操作：

```rust
impl<'a> OutlinePen for VerbsPointsPen<'a> {
    fn move_to(&mut self, x: f32, y: f32) {
        let pt0 = FfiPoint::new(x, -y);  // 注意 -y
        // ...
    }
    fn line_to(&mut self, x: f32, y: f32) {
        let pt1 = FfiPoint::new(x, -y);  // 注意 -y
        // ...
    }
    // quad_to, curve_to 同理
}
```

**隐式 MoveTo 处理：**

`VerbsPointsPen` 通过 `started` 标志和 `going_to()` 辅助方法实现了隐式 MoveTo 逻辑。
当收到第一个 `line_to` 或 `quad_to` 调用时，如果子路径尚未开始，会自动插入一个 MoveTo
指令。这匹配了 OpenType 字形轮廓的语义，其中第一个点隐含了 MoveTo。

**冗余 Close 消除：**

```rust
fn close(&mut self) {
    if self.started {
        if self.current_is_not(&self.points[self.points.len() - /* start point */]) {
            // 只有当终点不等于起点时才需要 close
        }
        self.verbs.push(PathVerb::Close as u8);
        self.started = false;
    }
}
```

### hinting.rs - 微调配置详细实现

**Engine 选择逻辑：**

```rust
let engine = match autohinting_control {
    AutoHintingControl::ForceForGlyf => {
        match outlines.format() {
            Some(OutlineGlyphFormat::Glyf) => Engine::Auto,
            _ => Engine::AutoFallback,
        }
    }
    AutoHintingControl::ForceForGlyfAndCff => Engine::Auto,
    AutoHintingControl::ForceOff => Engine::Interpreter,
    AutoHintingControl::Fallback => Engine::AutoFallback,
};
```

`Engine::AutoFallback` 是默认行为，其语义为：
- CFF/CFF2 字体始终使用内置的 PostScript 解释器（不自动微调）
- TrueType (glyf) 字体：如果 `fpgm` 或 `prep` 表非空则使用 TrueType 解释器，
  否则回退到自动微调器

这与 FreeType 的默认行为完全一致。

### bitmap.rs - 位图字体详细实现

**Strike 选择算法：**

```rust
fn best_strike_size<T>(strikes: impl Iterator<Item = T>, font_size: f32) -> Option<T>
where T: StrikeSizeRetrievable
{
    strikes.reduce(|best, entry| {
        let entry_size = entry.strike_size();
        if (entry_size >= font_size && entry_size < best.strike_size())
            || (best.strike_size() < font_size && entry_size > best.strike_size())
        {
            entry
        } else {
            best
        }
    })
}
```

该算法的策略是：
1. 优先选择大于等于请求尺寸的最小 strike（向上取最近）
2. 如果没有足够大的 strike，选择小于请求尺寸的最大 strike（向下取最近）

这确保了位图字体在缩放时尽量使用最合适的预渲染尺寸。

## 依赖关系

### 模块间依赖关系

```
ffi.rs (crate root)
  |-- use base::*            (所有基础函数和类型)
  |-- use bitmap::*          (位图相关函数和类型)
  |-- use colr::*            (彩色字体函数和类型)
  |-- use hinting::*         (微调函数和类型)
  |-- use names::*           (名称函数和类型)
  |-- use verbs_points_pen::*(路径提取函数)

base.rs
  |-- skrifa::{MetadataProvider, OutlineGlyphCollection, ...}
  |-- read_fonts::{FileRef, FontRef, TableProvider}
  |-- font_types::GlyphId
  |-- crate::ffi::{AxisWrapper, BridgeFontStyle, Metrics, ...}

colr.rs
  |-- crate::base::{BridgeFontRef, BridgeNormalizedCoords}
  |-- crate::ffi::{ClipBox, ColorPainterWrapper, ...}
  |-- skrifa::color::{ColorPainter, Transform, Brush}
  |-- read_fonts::tables::{colr, cpal}

bitmap.rs
  |-- crate::base::BridgeFontRef
  |-- crate::ffi::BitmapMetrics
  |-- read_fonts::tables::{bitmap, sbix}
  |-- skrifa::metrics::GlyphMetrics

hinting.rs
  |-- crate::ffi::AutoHintingControl
  |-- crate::{BridgeNormalizedCoords, BridgeOutlineCollection}
  |-- skrifa::outline::{GlyphStyles, HintingInstance, ...}

names.rs
  |-- crate::base::BridgeFontRef
  |-- crate::ffi::BridgeLocalizedName
  |-- skrifa::string::{LocalizedStrings, StringId}
  |-- read_fonts::tables::os2::SelectionFlags

verbs_points_pen.rs
  |-- crate::ffi::{BridgeScalerMetrics, FfiPoint}
  |-- crate::hinting::BridgeHintingInstance
  |-- crate::{BridgeNormalizedCoords, BridgeOutlineCollection}
  |-- skrifa::outline::{DrawSettings, OutlinePen}
```

### 外部 Crate 使用分布

| 模块 | skrifa | read-fonts | font-types | cxx |
|------|--------|------------|------------|-----|
| ffi.rs | - | - | - | #[cxx::bridge] |
| base.rs | MetadataProvider, Metrics, OutlineGlyphCollection, MappingIndex, Location | FontRef, FileRef, TableProvider | GlyphId | - |
| colr.rs | ColorPainter, ColorGlyphFormat, MetadataProvider | colr::CompositeMode, cpal::Cpal | GlyphId, BoundingBox | Pin |
| bitmap.rs | GlyphMetrics | bitmap::*, sbix::* | GlyphId, BoundingBox | - |
| hinting.rs | GlyphStyles, HintingInstance, HintingOptions, Engine, SmoothMode, Target | - | - | - |
| names.rs | LocalizedStrings, StringId, MetadataProvider | os2::SelectionFlags | - | - |
| verbs_points_pen.rs | OutlinePen, DrawSettings, GlyphId | - | - | - |

## 设计模式分析

### 1. Newtype 模式 (Newtype Pattern)

Rust 代码广泛使用 Newtype 模式包装 skrifa 类型：

```rust
pub struct BridgeFontRef<'a> { font: Option<FontRef<'a>>, ... }
pub struct BridgeOutlineCollection<'a>(pub Option<OutlineGlyphCollection<'a>>);
pub struct BridgeMappingIndex(MappingIndex);
pub struct BridgeHintingInstance(pub Option<HintingInstance>);
pub struct BridgeNormalizedCoords { pub normalized_coords: Location, ... }
```

每个包装类型都是 CXX 桥接的不透明类型，C++ 侧无法直接访问内部字段。这提供了：
- **类型安全**：防止 C++ 代码意外访问 Rust 内部状态
- **API 稳定性**：内部实现可以自由变更而不影响 FFI 接口
- **生命周期管理**：`'a` 生命周期参数确保引用有效性

### 2. Option 类型安全模式

几乎所有 Bridge 类型内部都使用 `Option<T>` 来表示可能无效的状态：

```rust
// BridgeFontRef::with_font 统一处理 None 情况
pub fn with_font<T>(&self, f: impl FnOnce(&FontRef) -> Option<T>) -> Option<T> {
    f(self.font.as_ref()?)  // ? 运算符自动传播 None
}

// 调用方模式
pub fn num_glyphs(font_ref: &BridgeFontRef) -> u16 {
    font_ref
        .with_font(|f| Some(f.maxp().ok()?.num_glyphs()))
        .unwrap_or_default()  // 字体无效时返回 0
}
```

这种模式确保了即使字体数据损坏或不完整，也不会导致 panic 或未定义行为。

### 3. Trait 适配器模式

`colr.rs` 中的 `ColorPainterImpl` 和 `verbs_points_pen.rs` 中的 `VerbsPointsPen`
都是 trait 适配器，它们实现 skrifa 的 trait 接口，将回调转发到 CXX 边界的另一侧：

```
skrifa trait            Rust 适配器           CXX 边界         C++ 实现
ColorPainter  <--实现-- ColorPainterImpl  -->Pin<&mut>--> ColorPainterWrapper
OutlinePen    <--实现-- VerbsPointsPen    -->(&mut Vec) --> rust::Vec<u8/FfiPoint>
```

### 4. 零拷贝数据传递

基础数据在 C++ 和 Rust 之间以零拷贝方式传递：

```rust
// C++ 传入字体数据切片，Rust 直接引用（不拷贝）
fn make_font_ref<'a>(font_data: &'a [u8], index: u32) -> Box<BridgeFontRef<'a>>;

// Rust 输出路径数据到 C++ 管理的向量（直接写入）
fn get_path_verbs_points(
    ...,
    verbs: &mut Vec<u8>,        // C++ 的 rust::Vec<uint8_t>
    points: &mut Vec<FfiPoint>, // C++ 的 rust::Vec<fontations_ffi::FfiPoint>
    ...
) -> bool;
```

## 数据流

### 字体引用创建数据流

```
C++ SkData 字节  -->  rust::Slice<const uint8_t>
                        |
                        v  (ffi.rs extern "Rust")
                  make_font_ref(font_data: &[u8], index: u32)
                        |
                        v  (base.rs)
                  FontRef::from_index(data, index)   [skrifa API]
                        |
                  +-----+------+
                  |            |
                  v            v
              Ok(font)    Err(...)
                  |            |
                  v            v
        BridgeFontRef {    BridgeFontRef {
          font: Some(f),     font: None,
          has_any_color:     has_any_color:
            check_tables()     false
        }                  }
                  |
                  v
            Box<BridgeFontRef>  -->  C++ rust::Box<BridgeFontRef>
```

### 路径提取数据流

```
C++ 调用:
  fontations_ffi::get_path_verbs_points(
    outlines, glyph_id, size, coords,
    hintingInstance, verbs, points, scalerMetrics)
        |
        v  (verbs_points_pen.rs)
  get_path_verbs_points():
    1. 创建 VerbsPointsPen { verbs, points }
    2. 根据 hintingInstance 选择 DrawSettings:
       - None: DrawSettings::unhinted(Size::new(size), coords)
       - Some(h): DrawSettings::hinted(&h.0, false)
    3. outlines.get(glyph_id)?.draw(settings, &mut pen)
       |
       |  [skrifa 遍历字形轮廓，回调 OutlinePen trait]
       |
       |-- pen.move_to(x, y) --> verbs.push(0), points.push(x, -y)
       |-- pen.line_to(x, y) --> verbs.push(1), points.push(x, -y)
       |-- pen.quad_to(...)  --> verbs.push(2), points.push(...)
       |-- pen.curve_to(...) --> verbs.push(4), points.push(...)
       |-- pen.close()       --> verbs.push(5)
    4. 填充 scalerMetrics (has_overlaps, adjusted_advance)
        |
        v
  C++ 侧通过 rust::Vec 直接访问 verbs 和 points 数据
  构建 SkPath::Make(points, verbs, {}, SkPathFillType::kWinding)
```

## 平台特定说明

### 编译配置

本目录的 Rust 代码通过 Bazel 的 `rust_static_library` 规则编译为静态库。CXX 桥接代码
通过 `rust_cxx_bridge` 规则生成 C++ 头文件 `ffi.rs.h` 和对应的 C++ 源文件。

```
BUILD.bazel 构建目标:
  :bridge_rust_side    -- Rust 静态库 (libfontations_ffi.a)
  :fontations_ffi      -- CXX 生成的 C++ 绑定
  :path_bridge_include -- skpath_bridge.h 头文件
  :deps                -- 上述三者的聚合目标
```

Cargo.toml 中声明的 `lib.name = "fontations_ffi"` 和 `path = "src/ffi.rs"` 确保
crate 名称和入口点与 Bazel 构建一致。

### 测试

Bazel 构建中包含 `rust_test` 目标 `test_ffi`，它编译并运行 Rust 代码中的 `#[test]`
函数，使用 `//resources` 目录下的测试字体文件。

### unsafe 使用约定

本代码库中 `unsafe` 的使用遵循以下约定：
- FFI 函数签名中的 `unsafe fn` 表示 C++ 调用方必须保证生命周期约束
- `BridgeFontRef<'a>` 中的 `'a` 绑定到传入的字节切片生命周期
- C++ 侧通过 `sk_sp<const SkData>` 的引用计数确保字节切片的生命周期

## 相关文档与参考

### Skia 内部文件

| 路径 | 说明 |
|------|------|
| `src/ports/SkTypeface_fontations.cpp` | C++ 侧完整实现（消费 FFI 函数） |
| `src/ports/SkTypeface_fontations_priv.h` | C++ 侧类型定义 |
| `src/ports/SkFontScanner_fontations.cpp` | 字体扫描器（也使用 FFI） |
| `src/ports/fontations/BUILD.bazel` | Bazel 构建规则 |
| `src/ports/fontations/Cargo.toml` | Rust 依赖配置 |
| `bazel/rust_cxx_bridge.bzl` | CXX 桥接 Bazel 规则定义 |

### 外部参考

- [skrifa crate 文档](https://docs.rs/skrifa/0.36/) - 高层字体 API
- [read-fonts crate 文档](https://docs.rs/read-fonts/0.34/) - 底层表读取
- [font-types crate 文档](https://docs.rs/font-types/0.9/) - 基础类型
- [CXX 用户指南](https://cxx.rs/) - C++/Rust 互操作框架
- [CXX #[cxx::bridge] 参考](https://cxx.rs/binding/bridge.html) - 桥接宏详细说明
- [Google Fontations GitHub](https://github.com/googlefonts/fontations) - 上游项目
- [OpenType 规范 - glyf 表](https://learn.microsoft.com/en-us/typography/opentype/spec/glyf) - TrueType 轮廓
- [OpenType 规范 - CFF 表](https://learn.microsoft.com/en-us/typography/opentype/spec/cff) - PostScript 轮廓
- [OpenType 规范 - COLR 表](https://learn.microsoft.com/en-us/typography/opentype/spec/colr) - 彩色字体
- [OpenType 规范 - cmap 表](https://learn.microsoft.com/en-us/typography/opentype/spec/cmap) - 字符映射
