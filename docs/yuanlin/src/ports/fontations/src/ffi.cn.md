# Fontations FFI 模块 - CXX 桥接接口定义

> 源文件: `src/ports/fontations/src/ffi.rs`

## 概述

`ffi.rs` 是 Skia Fontations 字体后端的核心接口定义文件，使用 CXX crate 的 `#[cxx::bridge]` 宏定义了 Rust 与 C++ 之间的完整 FFI（Foreign Function Interface）边界。该文件是整个 Fontations 模块的入口点，包含模块声明、所有共享数据类型定义、Rust 函数导出声明以及 C++ 函数导入声明。

所有其他 Fontations Rust 模块（base、hinting、bitmap、colr、names、verbs_points_pen）的公共函数都通过此文件声明并暴露给 C++ 侧。同时，C++ 侧的两个纯虚接口（`AxisWrapper` 和 `ColorPainterWrapper`）也通过此文件声明并对 Rust 侧可用。

## 架构位置

`ffi.rs` 是 Fontations 桥接层的顶层文件，同时扮演模块注册中心和接口定义的角色：

```
ffi.rs (本文件)
├── mod base       (字体基础操作)
├── mod bitmap     (位图字形)
├── mod colr       (COLR 颜色字形)
├── mod hinting    (字体 hinting)
├── mod names      (字体名称)
└── mod verbs_points_pen  (路径提取)

ffi::ffi module (CXX bridge)
├── 共享类型定义 (Rust <-> C++ 共享)
├── extern "Rust" (Rust -> C++ 导出)
└── unsafe extern "C++" (C++ -> Rust 导入)
```

## 主要类与结构体

### 共享数据类型（Rust 与 C++ 共享）

#### `ColorStop`
```rust
pub struct ColorStop {
    stop: f32,          // 渐变停止位置 [0.0, 1.0]
    palette_index: u16, // 调色板颜色索引
    alpha: f32,         // 不透明度
}
```
COLR 表颜色渐变中的颜色停止点。

#### `Metrics`
```rust
#[derive(Default)]
pub struct Metrics {
    top: f32, ascent: f32, descent: f32, bottom: f32,
    leading: f32, avg_char_width: f32, max_char_width: f32,
    x_min: f32, x_max: f32, x_height: f32, cap_height: f32,
    underline_position: f32, underline_thickness: f32,
    strikeout_position: f32, strikeout_thickness: f32,
}
```
字体度量信息结构体，包含所有关键的垂直度量、字符宽度和装饰线参数。

#### `FfiPoint`
```rust
#[derive(Clone, Copy, Default, PartialEq)]
struct FfiPoint { x: f32, y: f32 }
```
二维浮点坐标点，用于路径数据传递。

#### `BridgeLocalizedName`
```rust
pub struct BridgeLocalizedName {
    string: String,   // 名称内容
    language: String,  // 语言标识
}
```
本地化字体名称，包含名称字符串和对应的语言标识。

#### `SkiaDesignCoordinate`
```rust
#[derive(PartialEq, Debug, Default)]
struct SkiaDesignCoordinate {
    axis: u32,   // 轴标签（四字符标签的 u32 编码）
    value: f32,  // 设计坐标值
}
```
可变字体的设计坐标，每个坐标由轴标签和对应值组成。

#### `BridgeScalerMetrics`
```rust
struct BridgeScalerMetrics {
    has_overlaps: bool,         // 字形是否有重叠区域
    has_adjusted_advance: bool, // 是否有调整后的前进宽度
    adjusted_advance: f32,      // 调整后的前进宽度值
}
```
缩放器度量，从字形绘制过程中获取的额外信息。

#### `PaletteOverride`
```rust
pub struct PaletteOverride {
    index: u16,       // 调色板条目索引
    color_8888: u32,  // ARGB 8888 格式颜色值
}
```
调色板颜色覆盖条目，用于自定义 COLR/CPAL 颜色。

#### `ClipBox`
```rust
struct ClipBox {
    x_min: f32, y_min: f32, x_max: f32, y_max: f32,
}
```
COLRv1 字形的裁剪框。

#### `Transform`
```rust
struct Transform {
    xx: f32, xy: f32, yx: f32, yy: f32, dx: f32, dy: f32,
}
```
2x3 仿射变换矩阵。

#### 渐变参数类型
- `FillLinearParams { x0, y0, x1, y1 }` - 线性渐变参数
- `FillRadialParams { x0, y0, r0, x1, y1, r1 }` - 径向渐变参数
- `FillSweepParams { x0, y0, start_angle, end_angle }` - 扫描渐变参数

#### `BridgeFontStyle`
```rust
#[derive(Default)]
pub struct BridgeFontStyle {
    pub weight: i32,  // 字重（如 400=Normal, 700=Bold）
    pub slant: i32,   // 倾斜（0=Upright, 1=Italic, 2=Oblique）
    pub width: i32,   // 宽度（1-9 对应 UltraCondensed-UltraExpanded）
}
```
镜像 `SkFontStyle` 的值。

#### `BitmapMetrics`
```rust
#[derive(Default)]
struct BitmapMetrics {
    bearing_x: f32,        // 外部水平方位（字体单位）
    bearing_y: f32,        // 外部垂直方位（字体单位）
    ppem_x: f32,           // 水平缩放因子
    ppem_y: f32,           // 垂直缩放因子
    placement_origin_bottom_left: bool, // 原点是否在左下角
    inner_bearing_x: f32,  // 内部水平偏移（像素值）
    inner_bearing_y: f32,  // 内部垂直偏移（像素值）
    advance: f32,          // 位图字形前进宽度
}
```
位图字形度量信息，区分外部方位（影响边界计算）和内部方位（用于图像放置），以适配 SBIX 和 CBDT/CBLC 不同的放置原点定义。

### 枚举类型

#### `AutoHintingControl`
```rust
pub enum AutoHintingControl {
    ForceForGlyf,        // 仅对 glyf 格式强制自动提示
    ForceForGlyfAndCff,  // 对 glyf 和 CFF 格式均强制自动提示
    ForceOff,            // 强制关闭自动提示
    Fallback,            // 自动回退策略
}
```

#### `OutlineFormat`
```rust
pub enum OutlineFormat {
    NoOutlines, // 无轮廓
    Glyf,       // TrueType glyf 表
    Cff,        // CFF (Compact Font Format)
    Cff2,       // CFF2 (Compact Font Format version 2)
}
```

## 公共 API 函数

### Rust 导出到 C++ 的函数 (`extern "Rust"`)

**字体创建与管理:**
- `make_font_ref` - 从字体数据创建字体引用
- `font_ref_is_valid` - 验证字体引用有效性
- `has_any_color_table` - 检查是否有颜色表
- `font_or_collection` - 判断字体或集合
- `get_outline_collection` - 获取轮廓集合
- `get_bridge_glyph_styles` - 获取字形样式

**字形操作:**
- `make_mapping_index` - 创建字符映射索引
- `lookup_glyph_or_zero` - 查找字形 ID
- `outline_format` - 获取轮廓格式
- `get_path_verbs_points` - 提取路径数据
- `shrink_verbs_points_if_needed` - 收缩路径缓冲区
- `num_glyphs` - 字形总数
- `fill_glyph_to_unicode_map` - 填充字形到 Unicode 映射

**度量与属性:**
- `unhinted_advance_width_or_zero` - 未提示前进宽度
- `units_per_em_or_zero` - 每 em 单位数
- `get_skia_metrics` / `get_unscaled_metrics` - 字体度量
- `get_font_style` - 字体样式
- `is_embeddable` / `is_subsettable` / `is_fixed_pitch` / `is_serif_style` / `is_script_style` / `italic_angle` - 字体属性查询

**Hinting:**
- `hinting_reliant` - 是否依赖 hinting
- `make_hinting_instance` - 创建 hinting 实例
- `make_mono_hinting_instance` - 创建单色 hinting 实例
- `no_hinting_instance` - 无 hinting 实例

**可变字体:**
- `resolve_into_normalized_coords` - 解析规范化坐标
- `normalized_coords_equal` - 比较坐标
- `variation_position` - 获取变体位置
- `coordinates_for_shifted_named_instance_index` - 命名实例坐标
- `num_axes` / `populate_axes` - 轴信息
- `num_named_instances` - 命名实例数

**颜色字形:**
- `resolve_palette` - 解析调色板
- `has_colrv1_glyph` / `has_colrv0_glyph` - 检查 COLR 字形
- `get_colrv1_clip_box` - 获取裁剪框
- `draw_colr_glyph` - 绘制 COLR 字形
- `next_color_stop` / `num_color_stops` - 颜色停止点迭代

**位图字形:**
- `has_bitmap_glyph` - 检查位图字形
- `bitmap_glyph` - 获取位图字形数据
- `png_data` - 获取 PNG 数据
- `bitmap_metrics` - 获取位图度量

**字体表:**
- `table_data` / `table_tags` - 表数据访问

**名称:**
- `family_name` / `postscript_name` - 字体名称
- `get_localized_strings` / `localized_name_next` - 本地化名称迭代

### C++ 导入到 Rust 的函数 (`unsafe extern "C++"`)

**AxisWrapper 接口:**
- `populate_axis(i, axis, min, def, max, hidden) -> bool` - 填充变体轴参数
- `size() -> usize` - 获取轴数组大小

**ColorPainterWrapper 接口:**
- `is_bounds_mode() -> bool` - 是否处于边界计算模式
- `push_transform` / `pop_transform` - 变换栈操作
- `push_clip_glyph` / `push_clip_rectangle` / `pop_clip` - 裁剪栈操作
- `fill_solid` / `fill_linear` / `fill_radial` / `fill_sweep` - 基础填充操作
- `fill_glyph_solid` / `fill_glyph_linear` / `fill_glyph_radial` / `fill_glyph_sweep` - 优化的字形填充操作
- `push_layer` / `pop_layer` - 图层操作（COLRv1 合成模式）

## 内部实现细节

### 模块组织
文件开头声明了所有子模块（`mod base`, `mod bitmap`, `mod colr`, `mod hinting`, `mod names`, `mod verbs_points_pen`），然后通过 `use` 语句将各模块的公共 API 导入到当前作用域，以便在 CXX bridge 块中引用。

### CXX Bridge 命名空间
使用 `#[cxx::bridge(namespace = "fontations_ffi")]` 将所有生成的 C++ 代码放入 `fontations_ffi` 命名空间，避免与 Skia 其他代码的命名冲突。

### Opaque 类型
在 `extern "Rust"` 块中声明的 `type` 条目（如 `BridgeFontRef`, `BridgeOutlineCollection` 等）是 CXX 的不透明类型，C++ 侧只能通过指针/引用操作，不能直接访问其内部字段。

### 生命周期标注
多处使用 `unsafe fn` 和生命周期标注 `'a`，因为 CXX bridge 需要显式标注跨语言边界的引用生命周期。这些 `unsafe` 标注是 CXX bridge 的要求，并不意味着实现本身不安全。

### C++ 头文件包含
`unsafe extern "C++"` 块通过 `include!("src/ports/fontations/src/skpath_bridge.h")` 引入 C++ 侧的类型定义。

## 依赖关系

- **cxx crate**: 提供 `#[cxx::bridge]` 宏，生成 Rust 和 C++ 之间的安全 FFI 绑定
- **内部模块**: `base`, `bitmap`, `colr`, `hinting`, `names`, `verbs_points_pen` - 各功能模块的实现
- **C++ 头文件**: `src/ports/fontations/src/skpath_bridge.h` - C++ 侧的接口定义

## 设计模式与设计决策

1. **集中式接口定义**: 所有 FFI 类型和函数声明集中在一个文件中，便于审查和维护跨语言边界
2. **共享类型 vs 不透明类型**: 简单的值类型（如 `Metrics`, `FfiPoint`）定义为共享类型以实现零拷贝传递；复杂的有状态类型（如 `BridgeFontRef`）定义为不透明类型以隐藏实现细节
3. **Pin 引用**: C++ 回调接口（`AxisWrapper`, `ColorPainterWrapper`）使用 `Pin<&mut T>` 确保 Rust 侧不会移动 C++ 对象
4. **优化的 fill_glyph_* 函数**: 除了基础的 fill_* 操作外，还提供了 fill_glyph_* 变体，允许 C++ 侧将裁剪和填充合并为单次 `SkCanvas::drawPath()` 调用
5. **命名空间隔离**: 使用 `fontations_ffi` 命名空间避免符号冲突
6. **枚举类型安全**: `AutoHintingControl` 和 `OutlineFormat` 使用 CXX 的枚举映射，确保 Rust 和 C++ 侧的值保持同步

## 性能考量

- 共享类型通过值传递或引用传递，避免不必要的序列化/反序列化开销
- 不透明类型通过 `Box<T>` 在堆上分配，CXX 自动管理跨语言所有权转移
- 优化的 `fill_glyph_*` 系列函数减少了 COLR 字形渲染中的回调次数和临时对象创建
- `Vec<u8>` 和 `Vec<FfiPoint>` 直接作为可变引用传递，允许 Rust 侧直接写入 C++ 侧分配的内存

## 相关文件

- `src/ports/fontations/src/skpath_bridge.h` - C++ 侧的 `AxisWrapper` 和 `ColorPainterWrapper` 纯虚类定义
- `src/ports/fontations/src/base.rs` - 基础功能实现
- `src/ports/fontations/src/hinting.rs` - Hinting 功能实现
- `src/ports/fontations/src/bitmap.rs` - 位图字形实现
- `src/ports/fontations/src/colr.rs` - COLR 颜色字形实现
- `src/ports/fontations/src/names.rs` - 字体名称实现
- `src/ports/fontations/src/verbs_points_pen.rs` - 路径提取实现
- `src/ports/SkTypeface_fontations.cpp` - C++ 侧使用本 FFI 的 Typeface 实现
- `src/ports/SkScalerContext_fontations.cpp` - C++ 侧使用本 FFI 的 ScalerContext 实现
