# Fontations COLR 模块 - 颜色字形绘制

> 源文件: `src/ports/fontations/src/colr.rs`

## 概述

`colr.rs` 是 Skia Fontations 字体后端中负责处理 COLR（Color）表颜色字形的模块。COLR 表是 OpenType 规范中用于定义彩色字形的机制，广泛应用于 emoji 字体和彩色图标字体。

该模块支持两个版本的 COLR 表：
- **COLRv0**: 简单的分层颜色字形，每层使用单一颜色
- **COLRv1**: 功能丰富的颜色字形，支持渐变填充（线性、径向、扫描）、仿射变换、裁剪、图层合成等高级特性

模块的核心是 `ColorPainterImpl` 结构体，它实现了 skrifa 的 `ColorPainter` trait，将 skrifa 的颜色绘制回调转发给 C++ 侧的 `ColorPainterWrapper` 纯虚接口，最终由 Skia 的 Canvas API 完成实际渲染。

## 架构位置

```
skrifa::color::ColorGlyph::paint()
    -> ColorPainterImpl (实现 ColorPainter trait)
        -> ColorPainterWrapper (C++ 纯虚接口)
            -> Skia C++ 实现 (SkCanvas 操作)
```

该模块位于 Fontations 桥接层中，是从 Rust 字体解析到 C++ 图形渲染的中间适配器。它与 `bitmap.rs` 互补，分别处理矢量颜色字形和位图颜色字形。

## 主要类与结构体

### `BridgeColorStops<'a>`
```rust
pub struct BridgeColorStops<'a> {
    pub stops_iterator: Box<dyn Iterator<Item = &'a skrifa::color::ColorStop> + 'a>,
    pub num_stops: usize,
}
```
- 颜色停止点的桥接迭代器
- 使用动态分发的迭代器，因为不同渐变类型产生不同的迭代器类型
- `num_stops` 缓存了停止点总数，供 C++ 侧预分配缓冲区

### `ColorPainterImpl<'a>`（内部）
```rust
struct ColorPainterImpl<'a> {
    color_painter_wrapper: Pin<&'a mut ColorPainterWrapper>,
    clip_level: usize,
}
```
- 实现 skrifa `ColorPainter` trait 的核心结构
- `color_painter_wrapper`: 持有 C++ 侧 `ColorPainterWrapper` 的 Pin 引用
- `clip_level`: 裁剪层级计数器，用于在边界计算模式（bounds mode）下优化渲染

## 公共 API 函数

### `resolve_palette(font_ref, base_palette, palette_overrides) -> Vec<u32>`
解析字体调色板，将 CPAL 表中的颜色条目与用户覆盖合并：
1. 从 CPAL 表中读取指定基础调色板的所有颜色条目
2. 如果指定的调色板不存在，回退到调色板 0
3. 应用 `palette_overrides` 中的颜色覆盖（忽略越界的索引）
4. 返回 ARGB 8888 格式的颜色向量

### `has_colrv1_glyph(font_ref, glyph_id) -> bool`
检查指定字形是否有 COLRv1 颜色定义。

### `has_colrv0_glyph(font_ref, glyph_id) -> bool`
检查指定字形是否有 COLRv0 颜色定义。

### `get_colrv1_clip_box(font_ref, coords, glyph_id, size, clip_box) -> bool`
获取 COLRv1 字形的裁剪框（bounding box）：
- `size` 为 0 时直接返回 `false`
- 使用字形的可变字体坐标计算裁剪框
- 将结果写入 `clip_box` 并返回 `true`，无裁剪框时返回 `false`

### `draw_colr_glyph(font_ref, coords, glyph_id, color_painter) -> bool`
绘制 COLR 颜色字形（同时支持 v0 和 v1）：
- 创建 `ColorPainterImpl` 适配器
- 在边界计算模式下，第一个裁剪层以下的操作会被跳过
- 通过 skrifa 的 `paint()` 方法驱动绘制回调
- 成功返回 `true`

### `next_color_stop(color_stops, out_stop) -> bool`
从颜色停止点迭代器中获取下一个停止点：
- 将 skrifa 的 `ColorStop` 字段映射到 FFI 的 `ColorStop`（`offset` -> `stop`）
- 迭代完毕返回 `false`

### `num_color_stops(color_stops) -> usize`
返回颜色停止点的总数。

## 内部实现细节

### ColorPainter trait 实现

#### 边界计算模式优化
`clip_level` 用于在 `is_bounds_mode()` 为 `true` 时优化渲染：
- 当进入裁剪操作（`push_clip_glyph` 或 `push_clip_box`）时，`clip_level` 递增
- 当 `clip_level > 0` 时，所有变换、填充和图层操作被跳过
- 仅裁剪操作本身仍然传递给 C++ 侧（但仅在 `clip_level == 0` 时）
- 这是因为在边界计算模式下，裁剪后的区域不可能比裁剪框更大，所以内部操作无需追踪

#### 变换操作
```rust
fn push_transform(&mut self, transform: Transform) {
    if self.clip_level > 0 { return; }
    self.color_painter_wrapper.as_mut().push_transform(&crate::ffi::Transform { ... });
}
```
将 skrifa 的 `Transform` 转换为 FFI 定义的 `Transform`，通过 `ColorPainterWrapper` 传递给 C++。

#### fill 操作
处理四种画刷类型：
1. **Brush::Solid** - 纯色填充，传递调色板索引和 alpha
2. **Brush::LinearGradient** - 线性渐变，包含两个端点和颜色停止点
3. **Brush::RadialGradient** - 径向渐变，包含两个圆心、半径和颜色停止点
4. **Brush::SweepGradient** - 扫描渐变，包含中心点、起止角度和颜色停止点

所有渐变类型都创建 `BridgeColorStops` 来传递颜色停止点，`extend_mode` 以 `u8` 形式传递。

#### fill_glyph 优化操作
`fill_glyph` 方法处理两种情况：
1. **边界计算模式**: 仅执行 `push_clip_glyph` + `pop_clip`，快速估算边界
2. **正常模式**: 调用对应的 `fill_glyph_*` 优化方法，将裁剪和填充合并为单次操作

对于纯色填充使用 `fill_glyph_solid`，渐变填充则包含额外的 `brush_transform` 参数。

#### 图层操作
```rust
fn push_layer(&mut self, composite_mode: CompositeMode) { ... }
fn pop_layer(&mut self) { ... }
```
COLRv1 的合成模式通过 `push_layer` / `pop_layer` 实现，`CompositeMode` 以 `u8` 形式传递。边界计算模式下跳过。

### CPAL 调色板解析 (`resolve_palette`)
```rust
let cpal_to_vector = |cpal: &Cpal, palette_index| -> Option<Vec<u32>> { ... };
```
内部闭包将 CPAL 表中的颜色记录转换为 ARGB 8888 向量：
- 从 `color_record_indices` 获取指定调色板的起始索引
- 读取 `num_palette_entries` 个颜色记录
- 颜色记录存储为 `(alpha, red, green, blue)` 字节序列
- 转换为 `u32::from_be_bytes([alpha, red, green, blue])`
- 支持回退到默认调色板（索引 0）

调色板覆盖的应用逻辑：
```rust
for override_entry in palette_overrides {
    let index = override_entry.index as usize;
    if index < palette.len() {
        palette[index] = override_entry.color_8888;
    }
}
```
越界的覆盖索引被静默忽略，确保安全性。

### has_colr_glyph 辅助函数
```rust
pub fn has_colr_glyph(font_ref: &BridgeFontRef, format: ColorGlyphFormat, glyph_id: u16) -> bool
```
内部辅助函数，统一实现 `has_colrv0_glyph` 和 `has_colrv1_glyph` 的逻辑。使用 skrifa 的 `get_with_format` 方法按指定格式查询颜色字形。

### 大字形 ID 限制
多处标有 `TODO(drott)` 的注释表明当前将 `GlyphId`（u32）截断为 `u16`，待 Skia 支持大字形 ID 后需要更新。

## 依赖关系

- **font_types**: `BoundingBox`, `GlyphId`
- **read_fonts**:
  - `tables::colr::CompositeMode` - COLR 合成模式枚举
  - `tables::cpal::Cpal` - CPAL 调色板表
  - `TableProvider`
- **skrifa**:
  - `color::{Brush, ColorGlyphFormat, ColorPainter, Transform}` - 颜色绘制相关类型
  - `prelude::Size`
  - `MetadataProvider`
- **内部模块**:
  - `crate::base::{BridgeFontRef, BridgeNormalizedCoords}` - 基础类型
  - `crate::ffi::*` - FFI 数据类型和 C++ 接口

## 设计模式与设计决策

1. **适配器模式**: `ColorPainterImpl` 是典型的适配器，将 skrifa 的 `ColorPainter` trait 接口适配为 C++ 的 `ColorPainterWrapper` 虚函数调用
2. **边界模式优化**: 通过 `clip_level` 计数器在边界计算模式下跳过不影响边界的操作（变换、填充、图层），显著减少 C++ 回调次数
3. **渐变停止点的惰性迭代**: `BridgeColorStops` 使用动态迭代器而非预分配数组，C++ 侧可以按需逐个读取停止点
4. **调色板回退**: `resolve_palette` 在指定调色板不存在时自动回退到调色板 0，提高容错性
5. **合成操作的数值传递**: `CompositeMode` 和 `extend_mode` 以 `u8` 形式传递，避免在 FFI 边界定义额外的枚举映射
6. **裁剪优化**: 在 `fill_glyph` 中，边界模式下仅做裁剪不做填充；正常模式下使用 `fill_glyph_*` 合并操作

## 性能考量

- 边界计算模式（`is_bounds_mode()`）通过跳过裁剪层内的所有操作大幅减少计算量，这对于字形边界快速估算非常重要
- `fill_glyph_*` 系列方法将裁剪和填充合并为单次 C++ 回调，减少了虚函数调用和 Canvas 状态切换的开销
- `BridgeColorStops` 的迭代器模式避免了预先分配和填充颜色停止点数组
- 调色板数据按需解析，`resolve_palette` 仅在需要时从 CPAL 表读取
- `clip_level` 计数器使用简单的 `usize` 递增/递减，开销极低
- 变换矩阵通过引用传递（`&Transform`），避免了矩阵值的不必要复制
- `draw_colr_glyph` 通过 skrifa 的 `paint()` 方法以单次调用驱动整个绘制过程，避免了逐层手动遍历 COLR 表的开销
- 颜色停止点的 `num_stops` 字段允许 C++ 侧在接收停止点之前预分配精确大小的缓冲区

## 测试

模块包含单元测试（`mod test`），验证调色板相关功能：

### `test_palette_override`
- 测试有效的调色板覆盖：覆盖索引 9、10、11 的颜色
- 验证覆盖后的调色板长度（14 个条目）和覆盖值的正确性
- 测试越界的调色板覆盖（索引 15-17）被正确忽略
- 验证原有调色板条目不受越界覆盖的影响

### `test_default_palette_for_invalid_index`
- 测试当指定无效的调色板索引（65535）时，自动回退到默认调色板（索引 0）
- 验证回退后的调色板包含正确的颜色值

## 相关文件

- `src/ports/fontations/src/ffi.rs` - COLR 相关的 FFI 类型定义（`ColorStop`, `ClipBox`, `Transform`, 渐变参数, `PaletteOverride`）和函数声明
- `src/ports/fontations/src/skpath_bridge.h` - `ColorPainterWrapper` C++ 纯虚接口定义
- `src/ports/fontations/src/base.rs` - `BridgeFontRef` 和 `BridgeNormalizedCoords` 基础类型
- `src/ports/fontations/src/bitmap.rs` - 位图颜色字形模块（与本模块互补）
- `src/ports/SkScalerContext_fontations.cpp` - C++ 侧的 `ColorPainterWrapper` 具体实现
