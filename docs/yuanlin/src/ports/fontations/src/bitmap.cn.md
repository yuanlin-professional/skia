# Fontations Bitmap 模块 - 位图字形处理

> 源文件: `src/ports/fontations/src/bitmap.rs`

## 概述

`bitmap.rs` 是 Skia Fontations 字体后端中负责处理位图字形的模块。该模块支持从两种 OpenType 位图表中提取字形数据：SBIX（Apple 的标准位图/图形表）和 CBDT/CBLC（Color Bitmap Data Table / Color Bitmap Location Table）。

位图字形常见于 emoji 字体和某些为特定像素尺寸优化的字体中。该模块负责选择最佳的位图 strike 尺寸、提取 PNG 格式的位图数据，并计算正确的放置度量信息。SBIX 和 CBDT/CBLC 两种格式在原点定义和度量计算上有显著差异，本模块针对各自的规范进行了正确处理。

## 架构位置

```
Skia C++ (SkScalerContext_Fontations)
    -> fontations_ffi (CXX bridge, ffi.rs)
        -> bitmap.rs (本模块)
            -> read_fonts::tables::bitmap (CBDT/CBLC 解析)
            -> read_fonts::tables::sbix (SBIX 解析)
```

该模块与 `colr.rs` 并列，共同处理字体中的彩色字形。`colr.rs` 处理矢量颜色字形（COLR 表），本模块处理位图颜色字形（SBIX 和 CBDT/CBLC 表）。

## 主要类与结构体

### `BitmapPixelData<'a>`
```rust
pub enum BitmapPixelData<'a> {
    PngData(&'a [u8]),
}
```
- 位图像素数据枚举，当前仅支持 PNG 格式
- 使用引用避免复制底层字体数据

### `BridgeBitmapGlyph<'a>`
```rust
#[derive(Default)]
pub struct BridgeBitmapGlyph<'a> {
    pub data: Option<BitmapPixelData<'a>>,
    pub metrics: FfiBitmapMetrics,
}
```
- 位图字形的桥接类型，包含像素数据和度量信息
- 使用 `Option` 表示可能不存在位图数据的情况
- 实现 `Default` 以支持错误时返回空对象

### `CblcGlyph<'a>`（内部）
```rust
struct CblcGlyph<'a> {
    bitmap_data: BitmapData<'a>,
    ppem_x: u8,
    ppem_y: u8,
}
```
- CBDT/CBLC 表中提取的字形数据
- 包含位图数据和水平/垂直 ppem（pixels per em）

### `SbixGlyph<'a>`（内部）
```rust
struct SbixGlyph<'a> {
    glyph_data: GlyphData<'a>,
    ppem: u16,
}
```
- SBIX 表中提取的字形数据
- 包含字形数据（含原点偏移和图像内容）和 ppem

### `StrikeSizeRetrievable` trait（内部）
```rust
trait StrikeSizeRetrievable {
    fn strike_size(&self) -> f32;
}
```
- 统一 SBIX Strike 和 CBLC BitmapSize 的尺寸获取接口
- 分别为 `&BitmapSize` 和 `Strike<'_>` 实现

## 公共 API 函数

### `has_bitmap_glyph(font_ref: &BridgeFontRef, glyph_id: u16) -> bool`
检查字体是否包含指定字形的位图数据。同时检查 SBIX 和 CBDT/CBLC 两种来源，不指定字号（即不进行 strike 选择）。

### `bitmap_glyph(font_ref, glyph_id, font_size) -> Box<BridgeBitmapGlyph>`
获取指定字形在给定字号下的位图数据和度量信息。优先检查 SBIX，其次检查 CBDT/CBLC。

**SBIX 处理逻辑:**
- 选择最佳 strike 尺寸
- 从 `glyf` 表获取字形边界框和左侧方位
- 设置 `placement_origin_bottom_left: true`（SBIX 使用左下角原点）
- `bearing_x` 设为 glyf 的左侧方位，`bearing_y` 设为 glyf 的 y_min
- `inner_bearing_x/y` 设为 SBIX 的 originOffsetX/Y（像素单位的偏移）
- `advance` 设为 `NAN`（SBIX 不提供独立的前进宽度）

**CBDT/CBLC 处理逻辑:**
- 选择最佳 strike 尺寸
- 支持 Small 和 Big 两种度量格式
- 仅处理 PNG 格式的位图数据
- 设置 `placement_origin_bottom_left: false`（CBDT 使用左上角原点）
- `bearing_x/y` 设为 0（CBDT 不使用外部方位）
- `inner_bearing_x/y` 从位图度量中获取

### `png_data(bitmap_glyph) -> &[u8]`
从 `BridgeBitmapGlyph` 中提取原始 PNG 数据。无数据时返回空切片。

### `bitmap_metrics(bitmap_glyph) -> &FfiBitmapMetrics`
获取位图字形的度量信息引用。

## 内部实现细节

### Strike 尺寸选择算法 (`best_strike_size`)
```rust
fn best_strike_size<T>(strikes: impl Iterator<Item = T>, font_size: f32) -> Option<T>
```
选择最佳 strike 的策略：
1. **优先选择大于请求尺寸的最小 strike** - 缩小比放大产生更好的视觉效果
2. **如果没有更大的 strike，选择最接近请求尺寸的较小 strike**
3. 使用 `reduce` 进行单遍扫描，复杂度 O(n)

选择逻辑的关键比较：
```rust
(entry_size >= font_size && entry_size < best.strike_size())  // 更近的大尺寸
|| (best.strike_size() < font_size && entry_size > best.strike_size())  // 更近的小尺寸
```

### SBIX 字形放置
根据 OpenType SBIX 规范：
- 如果存在 glyf 轮廓，图形设计空间原点放置在字形边界框的左下角 (xMin, yMin)
- `originOffsetX/Y` 在边界框内部应用
- 这与 CBDT/CBLC 的左上角原点定义不同，通过 `placement_origin_bottom_left` 标志区分

### CBDT/CBLC 度量处理
支持两种度量格式：
- `BitmapMetrics::Small`: 使用 `bearing_x()`, `bearing_y()`, `advance`
- `BitmapMetrics::Big`: 使用 `hori_bearing_x()`, `hori_bearing_y()`, `hori_advance`

仅处理 PNG 格式的位图数据（`BitmapDataFormat::Png`），其他格式被忽略。

### glyf 边界框获取 (`glyf_bounds`)
```rust
fn glyf_bounds(font_ref: &FontRef, glyph_id: GlyphId) -> Option<BoundingBox<i16>>
```
从 glyf 表获取字形的边界框，用于 SBIX 字形的放置计算。通过 loca 表定位字形数据。

## 依赖关系

- **read_fonts**:
  - `tables::bitmap::{BitmapContent, BitmapData, BitmapDataFormat, BitmapMetrics, BitmapSize}` - CBDT/CBLC 表类型
  - `tables::sbix::{GlyphData, Strike}` - SBIX 表类型
  - `FontRef`, `TableProvider`
- **font_types**: `BoundingBox`, `GlyphId`
- **skrifa**: `instance::{LocationRef, Size}`, `metrics::GlyphMetrics`
- **内部模块**: `crate::ffi::BitmapMetrics` (as `FfiBitmapMetrics`), `crate::BridgeFontRef`

## 设计模式与设计决策

1. **策略模式（via trait）**: `StrikeSizeRetrievable` trait 统一了 SBIX 和 CBLC 两种格式的 strike 尺寸获取接口，使 `best_strike_size` 函数可以泛型化处理
2. **优先级链**: `bitmap_glyph` 函数先尝试 SBIX 再尝试 CBLC，建立了明确的格式优先级
3. **内外方位分离**: `BitmapMetrics` 区分 `bearing_x/y`（外部，字体单位）和 `inner_bearing_x/y`（内部，像素单位），以适配两种不同的放置模型
4. **Option 传播**: 大量使用 `Option` 和 `?` 运算符进行错误传播，任何步骤失败都安全地返回 `None`

## 性能考量

- `best_strike_size` 使用单次遍历（`reduce`），对 strike 列表仅扫描一次
- 位图数据通过引用传递（`&'a [u8]`），避免复制底层字体数据中的 PNG 内容
- `has_bitmap_glyph` 不指定字号，仅检查任意 strike 中是否存在字形，快速判断
- `BridgeBitmapGlyph` 实现 `Default`，允许在错误情况下快速返回空对象而无需额外分配

## 相关文件

- `src/ports/fontations/src/ffi.rs` - 定义 `BitmapMetrics` 共享类型和位图相关的 FFI 函数声明
- `src/ports/fontations/src/base.rs` - 提供 `BridgeFontRef` 基础类型
- `src/ports/fontations/src/colr.rs` - COLR 矢量颜色字形模块（与本模块互补）
- `src/ports/SkScalerContext_fontations.cpp` - C++ 侧调用位图字形 FFI 的实现
