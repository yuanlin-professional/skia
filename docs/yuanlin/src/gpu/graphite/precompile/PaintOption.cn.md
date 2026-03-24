# PaintOption

> 源文件: `src/gpu/graphite/precompile/PaintOption.h`, `src/gpu/graphite/precompile/PaintOption.cpp`

## 概述

`PaintOption` 是 Skia Graphite 预编译（Precompile）系统中的核心类，表示一种特定的绘制参数组合。它封装了着色器、颜色滤镜、混合器、裁剪着色器等绘制效果的一个具体变体，并能将其转换为用于管线缓存查找的 `PaintParamsKey`。

在预编译过程中，Graphite 会枚举所有可能的绘制参数组合，为每种组合创建一个 `PaintOption` 实例，然后通过 `toKey()` 方法生成对应的管线键，从而提前编译所需的着色器管线。

## 架构位置

`PaintOption` 位于 Graphite 预编译子系统中：

- **上层**: 由预编译系统的组合枚举逻辑创建
- **协作**: 与 `KeyContext`、`PaintParamsKeyBuilder`、`PipelineDataGatherer` 协同工作
- **下游**: 生成的键用于管线缓存和着色器编译

## 主要类与结构体

### `PaintOption` 类

表示绘制参数的一种具体组合，包含：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fOpaquePaintColor` | `bool` | 画笔颜色是否不透明 |
| `fFinalBlender` | `pair<sk_sp<PrecompileBlender>, int>` | 最终混合器及其变体索引 |
| `fShader` | `pair<sk_sp<PrecompileShader>, int>` | 着色器及其变体索引 |
| `fColorFilter` | `pair<sk_sp<PrecompileColorFilter>, int>` | 颜色滤镜及其变体索引 |
| `fHasPrimitiveBlender` | `bool` | 是否有图元混合器 |
| `fPrimitiveBlendMode` | `SkBlendMode` | 图元混合模式 |
| `fSkipColorXform` | `bool` | 是否跳过颜色空间转换 |
| `fClipShader` | `pair<sk_sp<PrecompileShader>, int>` | 裁剪着色器 |
| `fRendererCoverage` | `Coverage` | 渲染器覆盖模式 |
| `fTargetFormat` | `TextureFormat` | 目标纹理格式 |
| `fDither` | `bool` | 是否开启抖动 |
| `fAnalyticClip` | `bool` | 是否使用解析裁剪 |

## 公共 API 函数

- **`PaintOption(...)`** — 构造函数，接受所有绘制参数的具体组合。构造时会执行优化：如果没有图元混合器且着色器是常量，则清除着色器；如果没有着色器，则清除颜色滤镜
- **`finalBlender()`** — 返回最终混合器的裸指针
- **`toKey(const KeyContext&)`** — 将此绘制选项转换为管线键，这是预编译的核心方法

## 内部实现细节

### 键生成流程（toKey）

`toKey()` 方法按照 Graphite 的绘制管线节点结构生成键：

1. **根节点 0（源颜色）**: 通过 `handleDithering()` 生成，包含整个效果链
2. **根节点 1（最终混合器）**: 处理硬件混合或软件混合的选择
3. **根节点 2（裁剪，可选）**: 通过 `handleClipping()` 生成

### 效果链处理

效果链从内到外依次处理：

```
addPaintColorToKey → handlePrimitiveColor → handlePaintAlpha → handleColorFilter → handleDithering
```

- **`addPaintColorToKey()`** — 如果有着色器则使用着色器，否则使用 `RGBPaintColorBlock`
- **`handlePrimitiveColor()`** — 处理图元颜色与画笔颜色的混合
- **`handlePaintAlpha()`** — 处理非不透明画笔颜色时的 alpha 混合（使用 SrcIn 混合模式）
- **`handleColorFilter()`** — 使用 Compose 将颜色滤镜包裹在已有效果链外
- **`handleDithering()`** — 在需要时添加抖动处理

### 混合模式决策

`toKey()` 中的混合处理根据以下条件决定使用硬件混合还是需要目标读取（dst read）：
- 如果是标准混合模式且硬件支持 → 使用 `AddFixedBlendMode`（硬件混合）
- 如果不支持硬件混合或是自定义混合器 → 使用 `AddBlendMode` 或自定义混合器的键

### 裁剪处理

`handleClipping()` 根据裁剪配置生成不同的节点：
- 解析裁剪 + 裁剪着色器 → 使用 Modulate 混合组合两者
- 仅解析裁剪 → 直接使用 `NonMSAAClipBlock`
- 仅裁剪着色器 → 直接使用着色器的键

### 抖动判断

`shouldDither()` 的逻辑与 `SkPaintPriv::ShouldDither` 和 `PaintParams::should_dither` 保持同步：
- 565 和 4444 格式始终接受抖动请求
- 其他格式仅在着色器非常量时启用抖动

### 构造时优化

构造函数中进行了两项关键优化：
1. 如果无图元混合器且着色器是常量 → 清除着色器（因为常量着色器等同于纯色）
2. 如果没有着色器且有颜色滤镜 → 清除颜色滤镜（因为无源颜色时颜色滤镜无意义）

## 依赖关系

### 上游依赖
- `PrecompileBlender`, `PrecompileShader`, `PrecompileColorFilter` — 预编译效果基类

### 核心依赖
- `KeyContext` — 键生成上下文，提供 Caps、目标颜色信息等
- `KeyHelpers.h` — 提供各种 Block 的 `AddBlock` 方法
- `PaintParamsKey.h` — 管线键构建器

### 辅助依赖
- `ContextUtils.h` — 上下文工具函数
- `PaintParams.h` — 运行时绘制参数
- `Caps.h` — 硬件能力查询（判断是否支持硬件混合）

## 设计模式与设计决策

### 组合枚举模式

每个 `PaintOption` 代表一种具体的效果组合。预编译系统通过枚举着色器、混合器、颜色滤镜的所有变体来生成完整的组合集，每个组合创建一个 `PaintOption`。

### 变体索引

每个预编译效果使用 `pair<sk_sp<T>, int>` 格式存储，其中 `int` 是变体索引。这允许同一个预编译对象表示多种可能的实现（例如不同精度的着色器），通过索引选择具体变体。

### 与运行时路径的一致性

`PaintOption` 的效果链处理顺序和逻辑必须与运行时的 `PaintParams` 完全一致，以确保预编译生成的管线与实际绘制使用的管线匹配。

## 性能考量

- **预编译开销平衡**: 构造时的优化（清除常量着色器和无意义的颜色滤镜）减少了需要预编译的管线数量
- **硬件混合优先**: 优先使用硬件混合避免昂贵的目标纹理读取
- **覆盖模式提升**: 当存在裁剪着色器或解析裁剪时，自动将 `Coverage::kNone` 提升为 `Coverage::kSingleChannel`

## 相关文件

- `include/gpu/graphite/precompile/PrecompileBlender.h` — 预编译混合器接口
- `include/gpu/graphite/precompile/PrecompileShader.h` — 预编译着色器接口
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` — 预编译颜色滤镜接口
- `src/gpu/graphite/KeyContext.h` — 键生成上下文
- `src/gpu/graphite/KeyHelpers.h` — 键帮助函数
- `src/gpu/graphite/PaintParams.h` — 运行时绘制参数对应类
