# Fontations VerbsPointsPen 模块 - 字形轮廓路径提取

> 源文件: `src/ports/fontations/src/verbs_points_pen.rs`

## 概述

`verbs_points_pen.rs` 是 Skia Fontations 字体后端中负责将字形轮廓转换为 Skia 路径数据的模块。该模块实现了 skrifa 的 `OutlinePen` trait，将字体中的字形轮廓绘制命令（move、line、quad、curve、close）转换为 Skia 路径所需的动词（verbs）和点（points）序列。

该模块是字形渲染流水线的关键环节：字体文件中的轮廓数据经过 skrifa 解析（可选 hinting 处理）后，通过本模块的 `VerbsPointsPen` 转换为 Skia 能够理解的路径格式，最终用于光栅化或矢量输出。

## 架构位置

```
skrifa OutlineGlyph::draw()
    -> VerbsPointsPen (实现 OutlinePen trait)
        -> verbs: Vec<u8> (SkPathVerb 值)
        -> points: Vec<FfiPoint> (路径控制点)
            -> C++ 侧组装 SkPath
```

该模块在 Fontations 桥接层中处于字形轮廓输出的终端位置，接收来自 skrifa 的绘制回调，产出 Skia 可消费的路径数据。

## 主要类与结构体

### `VerbsPointsPen<'a>`
```rust
pub struct VerbsPointsPen<'a> {
    verbs: &'a mut Vec<u8>,
    points: &'a mut Vec<FfiPoint>,
    started: bool,
    current: FfiPoint,
}
```
- 核心路径构建器，接收字形绘制回调并输出路径数据
- `verbs`: 路径动词缓冲区，每个值对应一个 `SkPathVerb`
- `points`: 路径点缓冲区，与 verbs 对应
- `started`: 追踪当前子路径是否已开始（已输出 MoveTo）
- `current`: 记录当前点位置，用于去重和隐式 MoveTo

### `PathVerb` 枚举
```rust
#[repr(u8)]
enum PathVerb {
    MoveTo = 0,
    LineTo = 1,
    QuadTo = 2,
    CubicTo = 4,
    Close = 5,
}
```
- 路径动词枚举，值与 `SkPathVerb` 完全对应
- 使用 `#[repr(u8)]` 确保内存布局与 C++ 侧兼容

### `FfiPoint` 扩展
```rust
impl FfiPoint {
    fn new(x: f32, y: f32) -> Self { Self { x, y } }
}
```
- 为 FFI 定义的点类型添加构造方法

## 公共 API 函数

### `get_path_verbs_points(...) -> bool`
核心函数，获取指定字形的路径数据：
- **参数**:
  - `outlines`: 字形轮廓集合
  - `glyph_id`: 字形 ID
  - `size`: 字号大小
  - `coords`: 可变字体规范化坐标
  - `hinting_instance`: Hinting 实例（可选）
  - `verbs` / `points`: 输出缓冲区
  - `scaler_metrics`: 输出的缩放器度量
- **返回**: 成功返回 `true`，失败返回 `false`
- **行为**: 根据是否提供 hinting 实例选择有提示或无提示的绘制设置，然后通过 `VerbsPointsPen` 提取路径数据。同时报告字形是否有重叠以及调整后的前进宽度。

### `shrink_verbs_points_if_needed(verbs, points)`
在路径提取完成后，将 verbs 和 points 缓冲区收缩到预留大小（150）。避免因个别复杂字形导致缓冲区持续占用过多内存。

## 内部实现细节

### OutlinePen trait 实现

#### Y 轴翻转
所有从 skrifa 接收的 Y 坐标都被取反（`-y`），因为 skrifa 使用向上为正的坐标系，而 Skia 使用向下为正的坐标系。

#### 隐式 MoveTo
`going_to()` 方法实现了隐式 MoveTo 逻辑：当收到第一个绘制命令（line/quad/curve）但尚未发出 MoveTo 时，自动插入一个 MoveTo 到当前位置。

#### 去重优化
- `line_to`: 如果目标点与当前点相同，跳过该线段
- `quad_to`: 如果两个控制点都与当前点相同，跳过该曲线
- `curve_to`: 如果三个控制点都与当前点相同，跳过该曲线

#### close 语义
`close()` 方法仅在最后一个动词是 MoveTo、LineTo、QuadTo 或 CubicTo 时才添加 Close 动词，避免在空子路径上添加无意义的关闭。

#### move_to 的自动关闭
当收到新的 `move_to` 且当前子路径已开始时，自动调用 `close()` 关闭前一个子路径，然后重置 `started` 标志。

### 缓冲区管理
- 预分配常量 `PATH_EXTRACTION_RESERVE = 150`，为大多数字形提供足够的初始容量
- `VerbsPointsPen::new()` 清空并预分配缓冲区
- `shrink_verbs_points_if_needed()` 将缓冲区收缩回预留大小

### DrawSettings 选择
```rust
let draw_settings = match &hinting_instance.0 {
    Some(instance) => DrawSettings::hinted(instance, false),
    _ => DrawSettings::unhinted(Size::new(size), &coords.normalized_coords),
};
```
- 有 hinting 实例时使用 `hinted` 模式，第二个参数 `false` 表示不需要归一化路径
- 无 hinting 实例时使用 `unhinted` 模式，使用指定字号和坐标

## 依赖关系

- **skrifa**: `outline::{DrawSettings, OutlinePen}`, `prelude::Size`, `GlyphId`
- **内部模块**:
  - `crate::ffi::{BridgeScalerMetrics, FfiPoint}` - FFI 数据类型
  - `crate::hinting::BridgeHintingInstance` - Hinting 实例
  - `crate::BridgeNormalizedCoords`, `crate::BridgeOutlineCollection` - 基础类型

## 设计模式与设计决策

1. **Pen 模式（访问者模式变体）**: 通过实现 `OutlinePen` trait，将字形轮廓的遍历与处理解耦。skrifa 负责解析轮廓数据并驱动回调，本模块负责将回调转换为路径数据
2. **零拷贝输出**: verbs 和 points 通过可变引用直接写入调用方提供的缓冲区，避免额外的数据复制
3. **Y 轴翻转**: 在 Pen 层统一处理坐标系转换，上层无需关心。这是一个明确的设计决策，将坐标变换集中在一个位置而非分散到多个调用点
4. **退化路径过滤**: 通过 `current_is_not` 检查过滤零长度的线段和曲线，避免产生退化路径段。这可以减少后续光栅化阶段的无效工作
5. **隐式 MoveTo**: `going_to` 方法中的隐式 MoveTo 机制简化了调用方的逻辑，确保每个子路径都以 MoveTo 开始
6. **自动 Close**: `move_to` 中自动关闭前一个子路径的设计确保了路径数据的完整性，符合 SkPath 对闭合路径的预期
7. **常量预留容量**: `PATH_EXTRACTION_RESERVE` 作为编译期常量定义，既用于初始预分配又用于收缩目标，保持一致性

## 性能考量

- 预分配 150 个元素的缓冲区容量，覆盖大多数字形的需求，减少动态扩容次数
- `shrink_verbs_points_if_needed` 防止个别复杂字形（如 CJK 组合字形）导致内存浪费
- 去重检查（`current_is_not`）使用简单的浮点比较，成本极低但可以有效过滤冗余路径段
- 路径数据直接写入 `Vec<u8>` 和 `Vec<FfiPoint>`，避免中间数据结构的开销
- `VerbsPointsPen` 不拥有缓冲区，仅持有可变引用，避免了创建和销毁时的内存分配
- 缓冲区在 `new()` 中被 `clear()` 但保留已有容量，多次调用同一对缓冲区时可复用内存
- 对于典型的拉丁字形（20-40 个控制点），150 的预留容量足以避免任何扩容操作
- `PathVerb` 使用 `#[repr(u8)]` 确保每个动词仅占 1 字节，紧凑的内存布局有利于缓存效率

## 相关文件

- `src/ports/fontations/src/ffi.rs` - 定义 `FfiPoint`、`BridgeScalerMetrics` 和 `get_path_verbs_points` 的 FFI 声明
- `src/ports/fontations/src/hinting.rs` - 提供 `BridgeHintingInstance`
- `src/ports/fontations/src/base.rs` - 提供 `BridgeOutlineCollection` 和 `BridgeNormalizedCoords`
- `src/ports/fontations/src/skpath_bridge.h` - C++ 侧的路径桥接头文件
- `include/core/SkPath.h` - Skia 路径类定义，`PathVerb` 值与之对应
