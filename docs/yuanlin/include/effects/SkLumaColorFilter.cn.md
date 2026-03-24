# SkLumaColorFilter

> 源文件: `include/effects/SkLumaColorFilter.h`

## 概述

`SkLumaColorFilter` 是 Skia 图形库中的一个颜色滤镜工具类，用于将输入颜色的亮度（luma）值映射到 Alpha 通道中，同时将 RGB 通道设置为零。其核心计算公式为：

```
SkLumaColorFilter(r, g, b, a) = {0, 0, 0, a * luma(r, g, b)}
```

其中 `luma(r, g, b)` 是对 gamma 编码的颜色通道进行点积计算得到的亮度值（通常基于 BT.709 标准：`0.2126 * R + 0.7152 * G + 0.0722 * B`）。该滤镜与 SVG 规范中的 `feColorMatrix` 的 `luminanceToAlpha` 类型类似，但有一个关键区别：`SkLumaColorFilter` 会将原始 Alpha 值与亮度值相乘，而 `feColorMatrix` 的 `luminanceToAlpha` 模式不会考虑原始 Alpha 值：

```
feColorMatrix(luminanceToAlpha; r, g, b, a) = {0, 0, 0, luma(r, g, b)}
```

这使得 `SkLumaColorFilter` 在需要基于亮度生成透明度遮罩的场景中非常有用，例如文字渲染中的亮度遮罩效果、SVG 遮罩处理等。对于半透明内容，该滤镜能够正确地保留原始 Alpha 信息，产生更符合直觉的遮罩结果。

## 架构位置

`SkLumaColorFilter` 位于 Skia 的 effects 模块中，属于公共 API 层：

```
Skia 架构层次:
┌─────────────────────────────────────────────────┐
│              应用层 (Application)                 │
├─────────────────────────────────────────────────┤
│        公共 API (include/effects/)               │
│   ┌──────────────────────────────────────────┐  │
│   │  SkLumaColorFilter  (本文件)              │  │
│   │  SkOverdrawColorFilter                   │  │
│   │  SkRuntimeEffect                         │  │
│   └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│    核心实现层 (src/effects/colorfilters/)         │
│   ┌──────────────────────────────────────────┐  │
│   │  SkRuntimeColorFilter (实际实现)          │  │
│   │  SkKnownRuntimeEffects (内置效果注册)     │  │
│   └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│       后端渲染层 (Ganesh / Graphite / CPU)       │
└─────────────────────────────────────────────────┘
```

`SkLumaColorFilter` 本身仅作为公共 API 的入口点，实际的亮度计算逻辑由 `SkRuntimeColorFilter` 通过内置的 SkSL 运行时效果实现。

- **上游调用者**: SVG 渲染引擎（`modules/svg/src/SkSVGMask.cpp`）、Scene Graph 遮罩效果（`modules/sksg/src/SkSGMaskEffect.cpp`）、CanvasKit WebAssembly 绑定。
- **下游依赖**: `SkColorFilter` 颜色滤镜框架，通过 `SkRuntimeColorFilter` 和 `SkKnownRuntimeEffects` 实现。

## 主要类与结构体

### `SkLumaColorFilter` 结构体

```cpp
struct SK_API SkLumaColorFilter {
    static sk_sp<SkColorFilter> Make();
};
```

| 成员 | 类型 | 说明 |
|------|------|------|
| `Make()` | 静态工厂方法 | 创建并返回一个亮度颜色滤镜实例 |

该结构体定义为 `struct` 而非 `class`，因为它仅作为工厂方法的命名空间使用，不包含任何实例状态或成员变量。返回的对象类型为 `sk_sp<SkColorFilter>`，即 Skia 的智能指针包装的通用颜色滤镜接口。

## 公共 API 函数

### `SkLumaColorFilter::Make()`

```cpp
static sk_sp<SkColorFilter> Make();
```

**功能**: 创建一个将亮度映射到 Alpha 通道的颜色滤镜。

**参数**: 无。

**返回值**: `sk_sp<SkColorFilter>` -- 一个引用计数管理的颜色滤镜对象。

**使用示例**:

```cpp
#include "include/effects/SkLumaColorFilter.h"
#include "include/core/SkPaint.h"

SkPaint paint;
paint.setColorFilter(SkLumaColorFilter::Make());
canvas->drawRect(rect, paint);
```

**行为说明**:
- 输入像素 `(r, g, b, a)` 会被转换为 `(0, 0, 0, a * luma(r, g, b))`
- 亮度 luma 是基于 gamma 编码颜色通道的加权点积计算（非线性亮度）
- 原始 Alpha 值会被保留并与亮度值相乘，这是与 SVG `luminanceToAlpha` 的核心差异

## 内部实现细节

`SkLumaColorFilter::Make()` 的内部实现位于 `src/effects/colorfilters/SkRuntimeColorFilter.cpp` 中：

```cpp
sk_sp<SkColorFilter> SkLumaColorFilter::Make() {
    using namespace SkKnownRuntimeEffects;
    const SkRuntimeEffect* lumaEffect = GetKnownRuntimeEffect(StableKey::kLuma);
    return lumaEffect->makeColorFilter(SkData::MakeEmpty());
}
```

实现采用了 Skia 的 **已知运行时效果（Known Runtime Effects）** 机制：

1. 通过 `StableKey::kLuma` 查找预注册的 SkSL 运行时效果
2. 使用空的 uniform 数据（无需额外参数）创建颜色滤镜实例
3. 返回的 `SkRuntimeColorFilter` 对象在渲染时通过 SkSL 程序执行亮度计算

这种设计意味着亮度计算的 SkSL 着色器代码内置于 Skia 引擎中，可以在 CPU（通过 Raster Pipeline）和 GPU（通过 Ganesh 或 Graphite 后端）上高效执行。

### Luma 与 Luminance 的区别

头文件注释中明确指出了两者的区别：

- **Luma**: 基于 gamma 编码颜色通道的加权点积（即作用于非线性 sRGB 值）
- **Luminance**: 基于线性颜色通道的加权点积（即需要先进行 gamma 解码）

尽管 SVG 的 `luminanceToAlpha` 名称暗示使用的是线性光照下的 luminance，但 SVG 规范实际计算的也是 luma。因此 `SkLumaColorFilter` 和 SVG `feColorMatrix+luminanceToAlpha` 在计算方法上保持一致。

### 与 SVG feColorMatrix 的对比

| 特性 | SkLumaColorFilter | feColorMatrix (luminanceToAlpha) |
|------|-------------------|----------------------------------|
| RGB 输出 | (0, 0, 0) | (0, 0, 0) |
| Alpha 输出 | `a * luma(r,g,b)` | `luma(r,g,b)` |
| 是否保留原始 Alpha | 是 | 否 |

## 依赖关系

| 依赖文件 | 用途 |
|----------|------|
| `include/core/SkRefCnt.h` | 提供 `sk_sp` 智能指针模板 |
| `include/core/SkTypes.h` | 提供 `SK_API` 导出宏及基础类型定义 |
| `SkColorFilter` (前向声明) | 工厂方法的返回类型 |
| `src/effects/colorfilters/SkRuntimeColorFilter.cpp` | 实际实现代码所在文件 |
| `src/core/SkKnownRuntimeEffects.h` | 管理内置运行时效果的注册与查找 |

### 被依赖关系

以下模块使用了 `SkLumaColorFilter`：

- `modules/svg/src/SkSVGMask.cpp` -- SVG 遮罩处理中使用亮度遮罩
- `modules/sksg/src/SkSGMaskEffect.cpp` -- Scene Graph 遮罩效果
- `modules/canvaskit/canvaskit_bindings.cpp` -- CanvasKit (WebAssembly) 绑定
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` -- Graphite 后端预编译支持

## 设计模式与设计决策

### 工厂模式

`SkLumaColorFilter` 使用静态工厂方法 `Make()` 而非公开构造函数，这是 Skia 中一贯的设计惯例。该模式具有以下优点：

- **解耦接口与实现**：调用方仅依赖 `SkColorFilter` 基类接口，不需要了解内部使用的 `SkRuntimeColorFilter` 实现
- **返回值灵活性**：工厂方法返回智能指针，便于生命周期管理
- **实现可替换**：底层可在不改变公共 API 的前提下切换实现方式

### 运行时效果机制

亮度滤镜的计算逻辑使用 SkSL 编写并注册为"已知运行时效果"，而非硬编码的 C++ 实现。这种设计：

- 使得同一份 SkSL 代码可以在所有后端（CPU、Ganesh GPU、Graphite GPU）上运行
- 利用 Skia 的 Raster Pipeline 优化 CPU 执行路径
- 通过 GPU 着色器编译实现硬件加速

### 无参数设计

由于亮度计算公式是固定的（权重系数由标准决定），`Make()` 方法不需要任何参数。这使得 API 极其简洁，同时也意味着实现可以缓存并复用同一个滤镜实例以节省内存。

### Alpha 通道保留设计

设计上选择将亮度值乘以原始 Alpha（而非替换），这使得滤镜在半透明内容上的行为更符合直觉——半透明像素生成的遮罩值也应该较低。

## 性能考量

- **零开销抽象**：`SkLumaColorFilter` 结构体本身不包含任何数据成员，`Make()` 方法仅是对内部实现的简单封装
- **运行时效果缓存**：内置运行时效果（如 Luma）在首次使用后会被缓存，后续调用 `Make()` 不会重复编译 SkSL 代码
- **GPU 加速**：在使用 GPU 后端渲染时，亮度计算完全在 GPU 着色器中执行，无需 CPU 回读
- **Raster Pipeline 优化**：在 CPU 渲染路径中，亮度计算通过 Skia 的 Raster Pipeline 系统进行矢量化执行，充分利用 SIMD 指令集
- **内存效率**：返回的 `SkColorFilter` 使用引用计数管理（`sk_sp`），可安全地在多个 `SkPaint` 之间共享同一实例
- **轻量级计算**：亮度计算仅需三次乘法和两次加法（加权点积），再乘以 Alpha 通道，计算量极小

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/effects/SkLumaColorFilter.h` | 本文件，公共 API 声明 |
| `src/effects/colorfilters/SkRuntimeColorFilter.h` | 运行时颜色滤镜内部头文件 |
| `src/effects/colorfilters/SkRuntimeColorFilter.cpp` | `Make()` 的实际实现 |
| `src/core/SkKnownRuntimeEffects.h` | 已知运行时效果注册表 |
| `include/core/SkColorFilter.h` | `SkColorFilter` 基类定义 |
| `include/effects/SkOverdrawColorFilter.h` | 类似架构的颜色滤镜工具类 |
| `modules/svg/src/SkSVGMask.cpp` | SVG 遮罩中使用 Luma 滤镜 |
| `modules/sksg/src/SkSGMaskEffect.cpp` | Scene Graph 遮罩效果 |
| `include/core/SkColor.h` | 颜色类型定义 |
