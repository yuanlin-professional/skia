# PaintOptionsPriv - 绘制选项内部访问接口

> 源文件: `src/gpu/graphite/precompile/PaintOptionsPriv.h`

## 概述

`PaintOptionsPriv` 是 Skia Graphite 预编译系统中 `PaintOptions` 类的内部特权访问类。`PaintOptions` 是预编译框架的核心入口，用于描述绘制操作可能使用的着色器、混合器、颜色滤镜等组合。`PaintOptionsPriv` 暴露了添加内部颜色滤镜、设置裁剪着色器、原始混合模式、颜色变换跳过等内部配置方法，以及组合枚举和管线构建接口。

## 架构位置

```
预编译管线构建流程
  ├── PaintOptions (公共 API - 用户指定可能的绘制配置)
  │     └── PaintOptionsPriv (本文件 - 内部配置与构建)
  │           ├── 内部颜色滤镜添加
  │           ├── 裁剪着色器设置
  │           ├── 原始混合模式设置
  │           └── buildCombinations() → 管线键生成
  └── PrecompileBase 层次结构 (着色器/滤镜/混合器的预编译表示)
```

## 主要类与结构体

### `PaintOptionsPriv`

标准 Priv 类模式，额外定义了类型别名：

```cpp
using ProcessCombination = PaintOptions::ProcessCombination;
```

`ProcessCombination` 是一个回调类型，用于处理每个生成的管线组合。

## 公共 API 函数

### 内部配置方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `addColorFilter(sk_sp<PrecompileColorFilter>)` | `void` | 添加内部颜色滤镜 |
| `setClipShaders(SkSpan<const sk_sp<PrecompileShader>>)` | `void` | 设置裁剪着色器列表 |
| `setPrimitiveBlendMode(SkBlendMode)` | `void` | 设置原始混合模式 |
| `setSkipColorXform(bool)` | `void` | 设置是否跳过颜色变换 |

### 组合查询与构建

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `numCombinations()` | `int` | 返回总组合数量 |
| `buildCombinations(...)` | `void` | 枚举所有组合并调用回调 |

### buildCombinations 参数

```cpp
void buildCombinations(
    const KeyContext& keyContext,           // 键构建上下文
    DrawTypeFlags drawTypes,               // 绘制类型标志
    bool withPrimitiveBlender,             // 是否包含原始混合器
    Coverage coverage,                     // 覆盖度类型
    const RenderPassDesc& renderPassDesc,  // 渲染通道描述
    const ProcessCombination& processCombination  // 组合处理回调
) const;
```

## 内部实现细节

### 内部颜色滤镜

`addColorFilter()` 不同于公共 API 的颜色滤镜设置——它用于添加 Skia 内部自动生成的颜色滤镜，如色彩空间转换滤镜、工作格式转换滤镜等。这些滤镜对用户透明，但需要参与管线预编译。

### 裁剪着色器

`setClipShaders()` 设置裁剪着色器（Clip Shaders），这是 Graphite 中用于实现复杂裁剪效果的内部机制。目前仅通过 `PaintOptions::setClipShaders` 设置单个着色器。

### 颜色变换跳过

`setSkipColorXform(bool)` 控制是否跳过自动的颜色空间变换。某些内部渲染路径（如已经在线性空间中操作的路径）可以安全跳过此步骤。

### 组合枚举流程

`buildCombinations()` 方法遍历所有配置组合（着色器 x 颜色滤镜 x 混合器 x ...），为每个组合生成管线键，然后调用 `ProcessCombination` 回调。回调通常会检查管线缓存并触发缺失管线的编译。

## 依赖关系

- **include/gpu/graphite/precompile/PaintOptions.h**: 宿主类 `PaintOptions`
- 隐式依赖: `PrecompileColorFilter`, `PrecompileShader`, `KeyContext`, `DrawTypeFlags`, `Coverage`, `RenderPassDesc`

## 设计模式与设计决策

### 回调驱动的组合处理

`buildCombinations()` 使用回调（`ProcessCombination`）而非返回组合列表。这种设计：
1. 避免分配临时容器存储所有组合
2. 允许调用者在回调中进行早期终止或过滤
3. 管线编译可以在组合枚举过程中并行进行

### 内部与公共配置分离

`addColorFilter()` 等方法存在于 Priv 类而非公共 API 中，因为内部颜色滤镜（如色彩空间转换）是由 Skia 框架自动添加的实现细节，不应暴露给用户。

## 性能考量

- 组合数量可能呈指数增长（多维选项的笛卡尔积），需要谨慎配置选项范围
- `buildCombinations()` 的内联回调模式避免了中间存储开销
- 颜色变换跳过（`setSkipColorXform`）可以减少管线变体数量

## 相关文件

- `include/gpu/graphite/precompile/PaintOptions.h` - PaintOptions 公共 API
- `src/gpu/graphite/precompile/PrecompileBasePriv.h` - PrecompileBase 内部访问
- `src/gpu/graphite/precompile/PrecompileColorFiltersPriv.h` - 内部颜色滤镜工厂
- `src/gpu/graphite/precompile/PrecompileShadersPriv.h` - 内部着色器工厂
- `src/gpu/graphite/PrecompileInternal.h` - 内部预编译类型（DrawTypeFlags, Coverage）
