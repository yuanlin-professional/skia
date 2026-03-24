# Fontations Base 模块 - 字体基础操作与元数据

> 源文件: `src/ports/fontations/src/base.rs`

## 概述

`base.rs` 是 Skia Fontations 字体后端的基础模块，提供了字体引用管理、字形映射、度量信息获取、可变字体坐标处理、字体表数据访问以及字体样式属性查询等核心功能。该文件是整个 Fontations FFI 桥接层中最大、最核心的模块，实现了字体操作的大部分基础功能。

该模块将 Rust 字体解析库 `skrifa` 和 `read_fonts` 提供的能力封装为 C++ 可调用的 FFI 接口，是 Skia 使用 Google Fontations 字体栈的基石。

## 架构位置

`base.rs` 在 Fontations 桥接层中居于核心位置，其他所有模块（hinting、bitmap、colr、names、verbs_points_pen）都依赖于此模块定义的基础类型：

```
Skia C++ (SkTypeface_Fontations, SkScalerContext_Fontations)
    -> ffi.rs (CXX bridge 定义)
        -> base.rs (本模块 - 核心类型与函数)
        -> hinting.rs (使用 BridgeOutlineCollection, BridgeNormalizedCoords)
        -> bitmap.rs (使用 BridgeFontRef)
        -> colr.rs (使用 BridgeFontRef, BridgeNormalizedCoords)
        -> names.rs (使用 BridgeFontRef)
        -> verbs_points_pen.rs (使用 BridgeOutlineCollection, BridgeNormalizedCoords)
```

## 主要类与结构体

### `BridgeFontRef<'a>`
```rust
pub struct BridgeFontRef<'a> {
    font: Option<FontRef<'a>>,
    has_any_color: bool,
}
```
- 核心字体引用类型，封装了 `read_fonts::FontRef`
- 使用 `Option` 允许表示无效字体的状态
- 缓存 `has_any_color` 标志，表示字体是否包含任何颜色表（CBDT、SBIX 或 COLR）
- 提供 `with_font()` 辅助方法，安全地访问内部 `FontRef`

### `BridgeOutlineCollection<'a>`
```rust
#[derive(Default)]
pub struct BridgeOutlineCollection<'a>(pub Option<OutlineGlyphCollection<'a>>);
```
- 字形轮廓集合的桥接类型，封装 skrifa 的 `OutlineGlyphCollection`
- 在 hinting 和路径提取中被广泛使用

### `BridgeNormalizedCoords`
```rust
#[derive(Default)]
pub struct BridgeNormalizedCoords {
    pub normalized_coords: Location,
    filtered_user_coords: Vec<VariationSetting>,
}
```
- 可变字体的规范化坐标，包含两个维度的数据：
  - `normalized_coords`: 规范化后的坐标（Location），用于字形渲染
  - `filtered_user_coords`: 过滤后的用户坐标（VariationSetting），用于样式查询和位置报告

### `BridgeMappingIndex`
```rust
pub struct BridgeMappingIndex(MappingIndex);
```
- 字符到字形映射索引的桥接类型，封装 skrifa 的 `MappingIndex`
- 用于加速字符映射查询

## 公共 API 函数

### 字体创建与验证

#### `make_font_ref(font_data: &[u8], index: u32) -> Box<BridgeFontRef>`
从原始字体数据创建字体引用。支持单个字体文件和 TrueType Collection (TTC)。对于单字体文件，仅低 16 位为 0 时有效（高位用于命名实例索引）。同时检测字体是否包含颜色表（CBDT、SBIX、COLR）。

#### `font_ref_is_valid(bridge_font_ref: &BridgeFontRef) -> bool`
检查字体引用是否有效（即内部 `FontRef` 是否成功创建）。

#### `has_any_color_table(bridge_font_ref: &BridgeFontRef) -> bool`
快速检查字体是否包含任何颜色表，无需逐表查询。

#### `font_or_collection(font_data: &[u8], num_fonts: &mut u32) -> bool`
判断字体数据是单个字体还是字体集合（TTC），并返回集合中的字体数量。单字体文件 `num_fonts` 设为 0，TTC 设为实际数量。

### 字形映射

#### `make_mapping_index(font_ref: &BridgeFontRef) -> Box<BridgeMappingIndex>`
创建字符到字形的映射索引，加速后续的字形查找。

#### `lookup_glyph_or_zero(font_ref, map, codepoints, glyphs)`
批量查找 Unicode 码点对应的字形 ID。未找到的码点对应的字形 ID 设为 0。当前使用 u16 字形 ID，待 Skia 支持大字形 ID 后会升级。

#### `fill_glyph_to_unicode_map(font_ref: &BridgeFontRef, map: &mut [u32])`
填充字形 ID 到 Unicode 码点的反向映射表。每个字形仅保留第一个映射到它的码点。

### 度量信息

#### `num_glyphs(font_ref: &BridgeFontRef) -> u16`
返回字体中的字形总数（从 `maxp` 表获取）。

#### `units_per_em_or_zero(font_ref: &BridgeFontRef) -> u16`
返回字体的 UPM（units per em）值，失败时返回 0。

#### `unhinted_advance_width_or_zero(font_ref, size, coords, glyph_id) -> f32`
获取指定字形在给定字号和可变字体坐标下的未提示前进宽度。

#### `get_skia_metrics(font_ref, size, coords) -> Metrics`
获取缩放后的字体度量信息，包括上升、下降、行距、字符宽度、x 高度、大写字母高度、下划线和删除线参数。

#### `get_unscaled_metrics(font_ref, coords) -> Metrics`
获取未缩放的字体度量信息（设计空间中的原始值）。

#### `convert_metrics(skrifa_metrics: &SkrifaMetrics) -> Metrics`
将 skrifa 的度量类型转换为 FFI 定义的 `Metrics` 结构。注意 `x_height` 和 `cap_height` 取负值以匹配 Skia 的坐标约定。

### 字体表访问

#### `table_data(font_ref, tag, offset, data) -> usize`
获取字体表数据，实现 `SkTypeface::getTableData` 的行为：
- 空目标缓冲区: 返回表大小，不复制数据
- 缓冲区小于剩余数据: 截断复制
- 偏移超过表长度: 返回 0

#### `table_tags(font_ref, tags) -> u16`
获取字体中所有表的标签列表。

### 可变字体支持

#### `resolve_into_normalized_coords(font_ref, design_coords) -> Box<BridgeNormalizedCoords>`
将设计坐标转换为规范化坐标。先将用户坐标与轴默认值合并，再进行过滤和规范化。

#### `normalized_coords_equal(a, b) -> bool`
比较两个规范化坐标是否相等。

#### `variation_position(coords, coordinates) -> isize`
获取当前的可变字体位置（用户坐标形式）。返回坐标数量。

#### `coordinates_for_shifted_named_instance_index(font_ref, shifted_index, coords) -> isize`
获取移位命名实例索引对应的轴坐标。移位索引格式为 `(index + 1) << 16`，模仿 FreeType 通过 TTC 索引携带命名实例标识的行为。

#### `num_axes(font_ref) -> usize`
返回可变字体的轴数量。

#### `num_named_instances(font_ref) -> usize`
返回可变字体的命名实例数量。

#### `populate_axes(font_ref, axis_wrapper) -> isize`
填充变体轴的详细信息（标签、最小值、默认值、最大值、是否隐藏）到 C++ 侧的 `AxisWrapper`。

### 轮廓信息

#### `get_outline_collection(font_ref) -> Box<BridgeOutlineCollection>`
获取字体的字形轮廓集合。

#### `outline_format(outlines) -> OutlineFormat`
返回字体的轮廓格式：`NoOutlines`、`Glyf`、`Cff` 或 `Cff2`。

### 字体样式属性

#### `get_font_style(font_ref, coords, style) -> bool`
获取字体的样式信息（weight、width、slant），考虑可变字体坐标的影响。包含复杂的 `ital`/`slnt` 轴交互逻辑。

#### `is_embeddable(font_ref) -> bool`
检查字体是否允许嵌入（基于 OS/2 表的 `fsType` 字段，位 2 和位 9 必须清除）。

#### `is_subsettable(font_ref) -> bool`
检查字体是否允许子集化（基于 OS/2 表的 `fsType` 字段，位 8 必须清除）。

#### `is_fixed_pitch(font_ref) -> bool`
检查字体是否为等宽字体（基于 `post` 表的 `isFixedPitch` 或 `hhea` 表的水平度量数为 1）。

#### `is_serif_style(font_ref) -> bool`
通过 OS/2 表的 PANOSE 分类检查字体是否为衬线体。

#### `is_script_style(font_ref) -> bool`
通过 OS/2 表的 PANOSE 分类检查字体是否为手写体。

#### `italic_angle(font_ref) -> i32`
从 `post` 表获取字体的斜体角度。

## 内部实现细节

### 字体样式计算的复杂逻辑 (`get_font_style`)
该函数的 `ital`/`slnt` 轴交互逻辑较为复杂，遵循以下真值表：

```
         ital 轴
slnt轴    未设置    0值     正值
未设置    初始值   非斜    斜体
  0值    非oblq   正立    斜体
 正值     oblq    oblq   斜体
```

宽度值的映射使用两种标度：
- 从字体属性中读取时使用比例值（0.5-2.0 映射到 1-9）
- 从用户坐标读取时使用百分比值（50-200 映射到 1-9）

### 字体引用创建 (`make_font_ref_internal`)
支持两种输入：
1. 单字体文件：低 16 位索引必须为 0（高位保留给命名实例）
2. TTC 集合：使用完整索引定位特定字体

### 度量转换约定
`convert_metrics` 中 `x_height` 和 `cap_height` 取负值（`-skrifa_metrics.x_height`），这是为了匹配 Skia 的坐标系约定。下划线和删除线参数在缺失时返回 `f32::NAN`。

## 依赖关系

- **font_types**: `GlyphId` - 字形标识
- **read_fonts**: `FileRef`, `FontRef`, `ReadError`, `TableProvider` - 底层字体文件读取
- **skrifa**:
  - `attribute::Style` - 字体样式属性
  - `charmap::MappingIndex` - 字符映射索引
  - `instance::{Location, Size}` - 可变字体实例
  - `metrics::{GlyphMetrics, Metrics}` - 度量信息
  - `outline::OutlineGlyphFormat` - 轮廓格式
  - `setting::VariationSetting` - 变体设置
  - `MetadataProvider`, `OutlineGlyphCollection`, `Tag` - 元数据和轮廓集合
- **内部模块**: `crate::ffi` - CXX bridge 类型定义

## 设计模式与设计决策

1. **Option 包装模式**: `BridgeFontRef` 使用 `Option<FontRef>` 而非裸引用，优雅地处理无效字体的情况。`with_font()` 方法提供安全的访问模式
2. **FreeType 兼容性**: 多处设计决策明确对标 FreeType/DWrite 的行为，如 `is_embeddable`、`is_fixed_pitch` 等函数的注释中均引用了对应的参考实现
3. **零值默认**: 大量函数在失败时返回 0 或默认值（`unwrap_or_default()`），而非 panic，确保 FFI 边界的安全性
4. **命名实例索引编码**: 采用 FreeType 的移位编码方案（`(index + 1) << 16`），通过 TTC 索引的高位携带命名实例信息，保持 API 兼容性
5. **双重坐标存储**: `BridgeNormalizedCoords` 同时保存规范化坐标和过滤后的用户坐标，前者用于渲染计算，后者用于属性查询和报告

## 性能考量

- `has_any_color` 标志在 `make_font_ref` 时一次性计算并缓存，避免后续重复检查三个颜色表
- `MappingIndex` 预构建字符映射索引，加速批量字形查找
- `lookup_glyph_or_zero` 支持批量查询，减少 FFI 调用次数
- `table_data` 的偏移和长度计算使用 `saturating_sub` 避免溢出，并在空缓冲区时仅返回大小信息
- 可变字体坐标的规范化在 `resolve_into_normalized_coords` 中一次性完成，后续操作直接使用缓存的 `Location`

## 相关文件

- `src/ports/fontations/src/ffi.rs` - CXX bridge 定义，包含所有 FFI 类型和函数声明
- `src/ports/fontations/src/hinting.rs` - Hinting 模块，使用 `BridgeOutlineCollection` 和 `BridgeNormalizedCoords`
- `src/ports/fontations/src/bitmap.rs` - 位图字形模块，使用 `BridgeFontRef`
- `src/ports/fontations/src/colr.rs` - COLR 颜色字形模块，使用 `BridgeFontRef` 和 `BridgeNormalizedCoords`
- `src/ports/fontations/src/names.rs` - 字体名称模块，使用 `BridgeFontRef`
- `src/ports/fontations/src/verbs_points_pen.rs` - 路径提取模块，使用 `BridgeOutlineCollection`
- `src/ports/SkTypeface_fontations.cpp` - C++ 侧 Typeface 实现，调用本模块的 FFI 接口
- `src/ports/SkScalerContext_fontations.cpp` - C++ 侧 ScalerContext 实现
