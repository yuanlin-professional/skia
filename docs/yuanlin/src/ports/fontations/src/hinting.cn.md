# Fontations Hinting 模块 - 字体 Hinting 实例管理

> 源文件: `src/ports/fontations/src/hinting.rs`

## 概述

`hinting.rs` 是 Skia Fontations 字体后端中负责字体提示（hinting）功能的 Rust 模块。字体提示是一种优化字体在低分辨率屏幕上渲染质量的技术，通过调整字形轮廓使其更好地对齐到像素网格。

该模块提供了创建和管理 `HintingInstance` 的桥接功能，将 Skia C++ 侧的 hinting 配置需求转换为 skrifa（Rust 字体解析库）能够理解的参数。模块支持多种 hinting 模式，包括轻量级提示（light hinting）、LCD 抗锯齿、以及单色（monochrome）强提示等。

Hinting 技术对于小字号文本的可读性至关重要。在没有 hinting 的情况下，字形轮廓会被直接缩放到目标尺寸进行光栅化，可能导致笔画粗细不一致、像素模糊等问题。通过 hinting 指令或自动提示算法，字形轮廓被微调以更好地适配像素网格，从而获得更清晰锐利的渲染效果。

## 架构位置

该模块位于 Fontations FFI 桥接层内部，是 Skia 通过 Rust 使用 Google Fontations 字体栈的关键组件之一：

```
Skia C++ ScalerContext
    -> fontations_ffi (CXX bridge)
        -> hinting.rs (本模块)
            -> skrifa::outline::HintingInstance
```

在 Skia 的字体渲染流水线中，hinting 实例在 `ScalerContext` 初始化时被创建，并在后续的字形轮廓提取过程中被重复使用。一个 hinting 实例绑定到特定的字号、可变字体坐标和渲染模式，当这些参数发生变化时需要重新创建实例。

## 主要类与结构体

### `BridgeGlyphStyles`
```rust
#[derive(Default)]
pub struct BridgeGlyphStyles {
    glyph_styles: OnceLock<GlyphStyles>,
}
```
- 封装了 skrifa 的 `GlyphStyles`，使用 `OnceLock` 实现惰性初始化
- `GlyphStyles` 用于自动提示（autohinting）引擎，计算成本较高
- 仅在首次需要时计算，后续调用直接复用缓存的值

### `BridgeHintingInstance`
```rust
pub struct BridgeHintingInstance(pub Option<HintingInstance>);
```
- 封装了 skrifa 的 `HintingInstance`，使用 `Option` 允许表示"无 hinting"状态
- 是 hinting 配置的核心载体，存储了字号、坐标、hinting 目标等参数
- 通过 CXX bridge 传递给 C++ 侧使用

## 公共 API 函数

### `get_bridge_glyph_styles() -> Box<BridgeGlyphStyles>`
创建一个新的默认 `BridgeGlyphStyles` 实例。GlyphStyles 将在首次需要时惰性计算。

### `hinting_reliant(font_ref: &BridgeOutlineCollection) -> bool`
检查字体是否依赖于 hinting 指令。如果字体包含 TrueType 指令且需要解释器来正确渲染，则返回 `true`。

### `no_hinting_instance() -> Box<BridgeHintingInstance>`
创建一个不包含任何 hinting 实例的空桥接对象（内部为 `None`），用于不需要 hinting 的场景。

### `make_hinting_instance(...) -> Box<BridgeHintingInstance>`
创建完整的 hinting 实例，参数包括：
- `outlines`: 字体轮廓集合（`BridgeOutlineCollection` 引用）
- `bridge_glyph_styles`: 字形样式（用于 autohinting），惰性计算的 `BridgeGlyphStyles` 引用
- `size`: 字号大小（f32，单位为像素）
- `coords`: 可变字体的规范化坐标（`BridgeNormalizedCoords` 引用）
- `do_light_hinting`: 是否使用轻量级提示（仅调整垂直方向）
- `do_lcd_antialiasing`: 是否启用 LCD 子像素抗锯齿
- `lcd_orientation_vertical`: LCD 像素排列方向是否为垂直（影响子像素渲染方向）
- `autohinting_control`: 自动提示控制策略（`AutoHintingControl` 枚举）

该函数内部依次完成以下步骤：
1. 根据布尔参数组合确定 `SmoothMode`
2. 构建 `Target::Smooth` hinting 目标
3. 根据 `AutoHintingControl` 和轮廓格式选择引擎类型
4. 调用 `HintingInstance::new()` 创建实例

### `make_mono_hinting_instance(...) -> Box<BridgeHintingInstance>`
创建单色（monochrome）强提示实例，使用 `HintingMode::Strong`，适用于黑白位图渲染。参数：
- `outlines`: 字体轮廓集合
- `size`: 字号大小
- `coords`: 可变字体的规范化坐标

与 `make_hinting_instance` 不同，此函数不接受 SmoothMode 相关参数和 autohinting 控制，始终使用强提示模式。该模式对字形轮廓进行更积极的像素对齐，以确保黑白渲染的清晰度。

## 内部实现细节

### SmoothMode 映射逻辑
`make_hinting_instance` 内部根据三个布尔参数组合确定 `SmoothMode`：
| `do_light_hinting` | `do_lcd_antialiasing` | `lcd_orientation_vertical` | SmoothMode |
|---|---|---|---|
| true | - | - | Light |
| false | true | false | Lcd |
| false | true | true | VerticalLcd |
| false | false | - | Normal |

### Hinting Target 配置
所有平滑模式使用统一的 `Target::Smooth` 变体，并配置：
- `symmetric_rendering: true` - 启用对称渲染
- `preserve_linear_metrics: false` - 不保留线性度量

这些参数被配置为与 FreeType 的行为匹配。

### AutoHinting Engine 选择
根据 `AutoHintingControl` 枚举和字体轮廓格式选择引擎类型：
| AutoHintingControl | 字体格式 | Engine |
|---|---|---|
| ForceForGlyf | Glyf | Auto (带 GlyphStyles) |
| ForceForGlyfAndCff | 任何 | Auto (带 GlyphStyles) |
| ForceOff | 任何 | Interpreter |
| Fallback (默认) | 任何 | AutoFallback |

关键设计决策：不对 CFF 字体强制使用 autohinting，以匹配 FreeType 的行为。`Engine::AutoFallback` 对 PostScript (CFF/CFF2) 字体使用内置的 PostScript 提示引擎，仅对缺少 `fpgm`/`prep` 表的 TrueType 字体回退到自动提示。

### GlyphStyles 的角色
当选择 `Engine::Auto` 时，需要传入 `GlyphStyles` 对象。该对象包含了自动提示引擎所需的字形分析数据，如蓝区（blue zones）信息和笔画检测结果。`GlyphStyles` 的计算遍历字体中所有字形的轮廓，因此计算成本较高，适合通过 `OnceLock` 进行惰性初始化和缓存。

### Mono Hinting 模式
`make_mono_hinting_instance` 使用 `HintingMode::Strong` 而非 `Target::Smooth`，这是专门为黑白（1-bit）渲染设计的模式。在此模式下，hinting 引擎会更激进地将笔画对齐到完整像素边界，因为没有子像素灰度值可以用来平滑过渡。

该函数的参数列表比 `make_hinting_instance` 简单得多，不需要 SmoothMode、LCD 抗锯齿和 autohinting 控制参数，因为强提示模式的行为是固定的。

## 依赖关系

- **skrifa**: `outline::HintingInstance`, `outline::HintingOptions`, `outline::HintingMode`, `outline::Engine`, `outline::Target`, `outline::SmoothMode`, `outline::GlyphStyles`, `outline::OutlineGlyphFormat`, `prelude::Size`
- **内部模块**: `crate::ffi::AutoHintingControl`, `crate::BridgeNormalizedCoords`, `crate::BridgeOutlineCollection`
- **标准库**: `std::sync::OnceLock` 用于线程安全的惰性初始化（Rust 1.70+ 标准库提供）

## 设计模式与设计决策

1. **惰性初始化模式**: `BridgeGlyphStyles` 使用 `OnceLock` 延迟 `GlyphStyles` 的计算，因为该计算仅在需要自动提示时才有必要。`OnceLock` 是线程安全的，确保在多线程环境中只初始化一次
2. **FreeType 兼容性**: Hinting 参数的配置明确对标 FreeType 的行为，包括 CFF 字体的处理策略和平滑渲染参数。源码中多处引用了 FreeType 源码的具体行号作为参考
3. **Option 包装模式**: `BridgeHintingInstance` 使用 `Option<HintingInstance>` 优雅地表示"有 hinting"和"无 hinting"两种状态，避免了空指针或哨兵值的使用
4. **Box 返回模式**: 所有公共函数返回 `Box<T>` 以满足 CXX bridge 对跨语言所有权传递的要求。Box 在堆上分配并通过 CXX 的所有权语义传递给 C++ 侧
5. **match 表达式驱动**: 核心逻辑（SmoothMode 选择、Engine 选择）均使用 Rust 的 match 表达式实现，确保所有情况被穷举处理，编译器可以验证完整性

## 性能考量

- `GlyphStyles` 的计算通过 `OnceLock` 确保最多执行一次，避免在每次创建 hinting 实例时重复计算
- `BridgeGlyphStyles` 在 Fontations ScalerContext 级别被共享，多次调用 `make_hinting_instance` 可以复用已计算的样式
- `HintingInstance` 的创建本身涉及字体表的读取和参数初始化，建议在 ScalerContext 初始化时一次性完成
- `hinting_reliant` 函数快速检查字体是否需要 hinting 解释器，可用于在不需要 hinting 的情况下完全跳过实例创建
- `no_hinting_instance` 返回一个轻量级的空对象（仅包含 `None`），在无需 hinting 时几乎零开销
- 单色 hinting 实例（`make_mono_hinting_instance`）相比平滑 hinting 实例参数更少，创建成本略低

## 相关文件

- `src/ports/fontations/src/ffi.rs` - 定义 `AutoHintingControl` 枚举和 CXX bridge 接口中的 hinting 相关函数声明
- `src/ports/fontations/src/base.rs` - 定义 `BridgeNormalizedCoords` 和 `BridgeOutlineCollection`，本模块的核心依赖类型
- `src/ports/fontations/src/verbs_points_pen.rs` - 使用 hinting 实例进行字形轮廓提取，`DrawSettings::hinted()` 接受本模块创建的 `BridgeHintingInstance`
- `src/ports/SkFontHost_FreeType.cpp` - FreeType 后端的对应 hinting 实现，作为本模块行为对标的参考实现
- `src/ports/SkScalerContext_fontations.cpp` - C++ 侧 ScalerContext 实现，创建和使用本模块导出的 hinting 实例
- `src/ports/SkTypeface_fontations.cpp` - C++ 侧 Typeface 实现，管理 `BridgeGlyphStyles` 的生命周期
