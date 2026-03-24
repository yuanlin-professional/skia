# SkOverdrawColorFilter

> 源文件: `include/effects/SkOverdrawColorFilter.h`

## 概述

`SkOverdrawColorFilter` 是 Skia 图形库中用于**过度绘制（Overdraw）可视化**的颜色滤镜。它根据输入像素的 Alpha 通道值（表示该像素被绘制的次数）将像素映射为预定义的颜色，从而直观地展示渲染过程中的过度绘制情况。

该滤镜的映射规则如下：

| Alpha 值 | 映射结果 | 含义 |
|-----------|----------|------|
| 0 | `colors[0]` | 未绘制 |
| 1 | `colors[1]` | 绘制 1 次 |
| 2 | `colors[2]` | 绘制 2 次 |
| 3 | `colors[3]` | 绘制 3 次 |
| 4 | `colors[4]` | 绘制 4 次 |
| 5 或更大 | `colors[5]` | 绘制 5 次及以上 |

过度绘制可视化是图形性能调试的重要手段。当同一像素被多次绘制时，意味着 GPU 在做无用功。通过颜色编码可以快速定位渲染管线中的性能瓶颈。通常的配色方案使用从蓝（低过度绘制）到红（高过度绘制）的渐变色。

Skia 官方提供了该滤镜的在线交互示例：https://fiddle.skia.org/c/@overdrawcolorfilter_grid

## 架构位置

`SkOverdrawColorFilter` 位于 Skia 的 effects 层，是公共 API 的一部分：

```
应用层 / 调试工具
        │
        ▼
┌─────────────────────────────────────┐
│  include/effects/                    │
│  SkOverdrawColorFilter (公共 API)    │  ◄── 本文件
└──────────────┬──────────────────────┘
               │ 调用
               ▼
┌─────────────────────────────────────┐
│  src/effects/colorfilters/           │
│  SkRuntimeColorFilter               │  ◄── 运行时颜色滤镜实现
│   └── StableKey::kOverdraw          │
└──────────────┬──────────────────────┘
               │ 执行
               ▼
┌─────────────────────────────────────┐
│  渲染后端                            │
│  ├── CPU Raster Pipeline            │
│  ├── Ganesh (OpenGL / Vulkan)       │
│  └── Graphite                       │
└─────────────────────────────────────┘
```

该滤镜常与 `SkOverdrawCanvas` 配合使用。`SkOverdrawCanvas` 记录每个像素被绘制的次数（写入 Alpha 通道），而 `SkOverdrawColorFilter` 负责将绘制次数转换为可视化颜色。

- **上游调用者**: 性能调试工具、`SkOverdrawCanvas`、Android 的过度绘制可视化功能、Ganesh GPU 后端测试。
- **下游依赖**: `SkColorFilter` 颜色滤镜框架，通过 `SkRuntimeColorFilter` 和 `SkKnownRuntimeEffects` 实现。

## 主要类与结构体

### `SkOverdrawColorFilter` 类

```cpp
class SK_API SkOverdrawColorFilter {
public:
    static constexpr int kNumColors = 6;

    static sk_sp<SkColorFilter> MakeWithSkColors(const SkColor[kNumColors]);
};
```

| 成员 | 类型 | 说明 |
|------|------|------|
| `kNumColors` | `static constexpr int` | 颜色数组大小，固定为 6 |
| `MakeWithSkColors()` | 静态工厂方法 | 根据给定的 6 种颜色创建过度绘制颜色滤镜 |

`kNumColors = 6` 表示该滤镜支持 0 到 5（含）共 6 个级别的过度绘制可视化。Alpha 值大于等于 5 的像素统一使用第 6 种颜色，这在实际使用中已足够覆盖绝大多数场景。

## 公共 API 函数

### `SkOverdrawColorFilter::MakeWithSkColors()`

```cpp
static sk_sp<SkColorFilter> MakeWithSkColors(const SkColor colors[kNumColors]);
```

**功能**: 创建一个过度绘制颜色滤镜，根据 Alpha 值索引到用户提供的颜色数组。

**参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `colors` | `const SkColor[6]` | 长度为 6 的颜色数组，分别对应 0~5 次绘制的显示颜色 |

**返回值**: `sk_sp<SkColorFilter>` -- 引用计数管理的颜色滤镜对象。

**使用示例**:

```cpp
#include "include/effects/SkOverdrawColorFilter.h"
#include "include/core/SkColor.h"
#include "include/core/SkPaint.h"

// 定义过度绘制颜色方案：从冷色到暖色
const SkColor overdrawColors[SkOverdrawColorFilter::kNumColors] = {
    0x00000000,  // 0 次：透明（未绘制区域）
    0x770000FF,  // 1 次：蓝色（正常）
    0x7700FF00,  // 2 次：绿色（轻微过度绘制）
    0x77FFFF00,  // 3 次：黄色（中度过度绘制）
    0x77FF8800,  // 4 次：橙色（较高过度绘制）
    0x77FF0000,  // 5+ 次：红色（严重过度绘制）
};

SkPaint paint;
paint.setColorFilter(
    SkOverdrawColorFilter::MakeWithSkColors(overdrawColors));
canvas->drawImage(overdrawImage, 0, 0, SkSamplingOptions(), &paint);
```

## 内部实现细节

`MakeWithSkColors()` 的实现位于 `src/effects/colorfilters/SkRuntimeColorFilter.cpp`：

```cpp
sk_sp<SkColorFilter> SkOverdrawColorFilter::MakeWithSkColors(
        const SkColor colors[kNumColors]) {
    using namespace SkKnownRuntimeEffects;

    const SkRuntimeEffect* overdrawEffect =
        GetKnownRuntimeEffect(StableKey::kOverdraw);

    auto data = SkData::MakeUninitialized(kNumColors * sizeof(SkPMColor4f));
    SkPMColor4f* premul = (SkPMColor4f*)data->writable_data();
    for (int i = 0; i < kNumColors; ++i) {
        premul[i] = SkColor4f::FromColor(colors[i]).premul();
    }
    return overdrawEffect->makeColorFilter(std::move(data));
}
```

实现流程如下：

1. **获取运行时效果**: 通过 `StableKey::kOverdraw` 从已知运行时效果注册表中获取预编译的 SkSL 程序
2. **颜色预乘转换**: 将 6 个 `SkColor`（未预乘的 8 位 ARGB）转换为 `SkPMColor4f`（预乘的浮点 RGBA），因为 Skia 内部渲染管线统一使用预乘颜色格式
3. **构建 uniform 数据**: 将预乘颜色数组打包为 `SkData`，作为 SkSL 程序的 uniform 输入
4. **创建滤镜**: 通过 `SkRuntimeEffect::makeColorFilter()` 创建最终的颜色滤镜对象

SkSL 着色器在运行时会读取像素的 Alpha 值，将其夹紧到 `[0, 5]` 范围内，然后用作颜色数组的索引，实现离散的颜色查表映射。

### Alpha 通道作为绘制计数器

该滤镜假设输入像素的 Alpha 通道存储了该像素被绘制的次数（整数值），而非传统的透明度信息。这个值通常由 `SkOverdrawCanvas` 在每次绘制操作时递增写入。

### 离散映射而非插值

颜色映射是离散的查表操作（0-5 对应 6 种颜色），不进行颜色插值。这种设计使得过度绘制级别一目了然，便于开发者快速判断。

## 依赖关系

### 直接依赖

| 依赖文件 | 用途 |
|----------|------|
| `include/core/SkColor.h` | 提供 `SkColor` 类型定义（32 位 ARGB 颜色） |
| `include/core/SkRefCnt.h` | 提供 `sk_sp` 智能指针 |
| `include/core/SkTypes.h` | 提供 `SK_API` 导出宏 |
| `SkColorFilter` (前向声明) | 工厂方法的返回类型 |

### 实现依赖

| 依赖文件 | 用途 |
|----------|------|
| `src/effects/colorfilters/SkRuntimeColorFilter.cpp` | 工厂方法的实现代码 |
| `src/core/SkKnownRuntimeEffects.h` | 已知运行时效果注册表 |
| `include/effects/SkRuntimeEffect.h` | 运行时效果基础设施 |

### 被依赖关系

- `gm/overdrawcanvas.cpp` -- Skia 测试用 GM（Golden Master）
- `src/gpu/ganesh/effects/GrSkSLFP.cpp` -- Ganesh GPU 后端的片段处理器测试
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` -- Graphite 后端预编译支持
- `src/ports/SkGlobalInitialization_default.cpp` -- 全局初始化

## 设计模式与设计决策

### 工厂模式与类型擦除

与 `SkLumaColorFilter` 类似，`SkOverdrawColorFilter` 使用静态工厂方法返回 `sk_sp<SkColorFilter>` 基类指针。调用方不需要知道实际创建的是 `SkRuntimeColorFilter` 对象。

### 固定颜色数量的设计

`kNumColors = 6` 是一个刻意的设计选择：
- 0 次绘制（通常为透明色）加上 5 个级别的过度绘制强度
- 过度绘制 5 次以上的情况在实际应用中极少出现且通常意味着严重的性能问题
- 固定数组大小使得 SkSL uniform 布局在编译期确定，避免运行时动态分配

### 用户可自定义颜色

允许调用者传入自定义的颜色数组，而非硬编码颜色方案，使其可以适应不同的显示需求或色觉无障碍需求。

### 颜色预乘处理

输入颜色为 `SkColor`（未预乘的 32 位 ARGB），但内部会转换为预乘浮点格式 `SkPMColor4f`。这是因为 Skia 的渲染管线在内部统一使用预乘 Alpha 格式，在入口处进行转换可以避免渲染时的重复计算。

### 运行时效果机制

使用 SkSL 运行时效果而非硬编码实现，确保该滤镜可以在所有渲染后端（CPU Raster Pipeline、Ganesh GPU、Graphite GPU）上一致地工作，无需为每个后端编写专门的代码。

### 头文件包含风格

值得注意的是，该头文件将 `#include` 指令放在了 `#ifndef` 包含守卫之前，这与 Skia 中大多数头文件的风格略有不同，但不影响功能正确性。

## 性能考量

- **预乘转换成本**：`MakeWithSkColors()` 在创建时进行一次颜色预乘转换（6 次浮点运算），这是一次性成本，不会影响逐像素的渲染性能
- **简单查表操作**：SkSL 着色器的颜色查找操作（基于 Alpha 值的数组索引）是 O(1) 操作，在 GPU 上可以高效执行
- **调试专用**：该滤镜主要用于开发调试阶段，不建议在生产环境的渲染管线中使用，因为它会替换掉所有原始颜色信息
- **内存占用**：uniform 数据仅为 6 个 `SkPMColor4f`（96 字节），非常轻量
- **实例共享**：返回的 `sk_sp<SkColorFilter>` 使用引用计数，同一配色方案可在多个 `SkPaint` 之间安全共享
- **GPU 友好**：颜色映射可以在 GPU 着色器中高效实现为简单的纹理查找或条件分支

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/effects/SkOverdrawColorFilter.h` | 本文件，公共 API 声明 |
| `src/effects/colorfilters/SkRuntimeColorFilter.h` | 运行时颜色滤镜内部头文件 |
| `src/effects/colorfilters/SkRuntimeColorFilter.cpp` | `MakeWithSkColors()` 的实际实现 |
| `include/core/SkColorFilter.h` | `SkColorFilter` 基类定义 |
| `include/core/SkColor.h` | `SkColor` 和 `SkPMColor4f` 类型定义 |
| `gm/overdrawcanvas.cpp` | 过度绘制可视化的 GM 测试 |
| `include/effects/SkLumaColorFilter.h` | 类似架构的颜色滤镜 |
| `include/gpu/graphite/precompile/PrecompileColorFilter.h` | Graphite 预编译支持 |
| `src/gpu/ganesh/effects/GrSkSLFP.cpp` | Ganesh GPU 后端集成 |
