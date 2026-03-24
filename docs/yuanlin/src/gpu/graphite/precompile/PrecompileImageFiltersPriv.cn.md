# PrecompileImageFiltersPriv - 内部图像滤镜预编译管线构建

> 源文件: `src/gpu/graphite/precompile/PrecompileImageFiltersPriv.h`

## 概述

`PrecompileImageFiltersPriv` 是 Skia Graphite 预编译系统中的内部图像滤镜管线构建命名空间。它目前仅提供一个函数 `CreateBlurImageFilterPipelines()`，用于为模糊图像滤镜创建预编译管线。该函数同时被模糊遮罩滤镜（BlurMaskFilter）和模糊图像滤镜（BlurImageFilter）共享使用。

## 架构位置

```
预编译图像滤镜体系
  ├── PrecompileImageFilters (公共工厂)
  │     ├── Blur, ColorFilter, Displacement, ...
  └── PrecompileImageFiltersPriv (本文件 - 内部管线构建)
        └── CreateBlurImageFilterPipelines()
              ├── 被 BlurMaskFilter 预编译使用
              └── 被 BlurImageFilter 预编译使用
```

## 主要类与结构体

本文件定义的是命名空间，不包含类定义。

## 公共 API 函数

| 函数 | 返回类型 | 说明 |
|------|----------|------|
| `CreateBlurImageFilterPipelines(const KeyContext&, const RenderPassDesc&, const ProcessCombination&)` | `void` | 为模糊滤镜创建预编译管线 |

### 参数说明

```cpp
void CreateBlurImageFilterPipelines(
    const KeyContext& keyContext,                        // 键构建上下文
    const RenderPassDesc& renderPassDesc,               // 渲染通道描述
    const PaintOptionsPriv::ProcessCombination& proc);  // 组合处理回调
```

- `keyContext`: 提供管线键构建所需的全局上下文（Caps、字典等）
- `renderPassDesc`: 目标渲染通道描述，影响管线兼容性
- `proc`: 回调函数，处理每个生成的管线组合

## 内部实现细节

### 模糊管线共享

模糊效果在 Skia 中有两个入口：
1. **BlurMaskFilter**: 应用于路径/形状的遮罩模糊
2. **BlurImageFilter**: 应用于图像的通用高斯模糊

两者在 GPU 实现层面使用相同的模糊着色器管线，因此预编译也共享同一个管线创建函数。这避免了重复定义相同的管线变体。

### ProcessCombination 回调

该函数使用 `PaintOptionsPriv::ProcessCombination` 类型别名作为回调类型，与 `PaintOptions::buildCombinations()` 保持一致。每个生成的模糊管线配置通过此回调传递给调用者进行缓存检查和编译。

## 依赖关系

- **src/gpu/graphite/precompile/PaintOptionsPriv.h**: `PaintOptionsPriv::ProcessCombination` 类型
- 前向声明: `KeyContext`, `PipelineDataGatherer`

注意 `PipelineDataGatherer` 被前向声明但未在头文件的函数签名中使用，可能在 `.cpp` 实现中使用。

## 设计模式与设计决策

### 共享管线创建

将模糊管线创建提取为独立的命名空间函数，而非作为某个预编译类的方法，是因为此功能被多个不相关的预编译类（MaskFilter 和 ImageFilter）共享。命名空间函数避免了引入不自然的类继承关系。

### 回调驱动模式

与 `PaintOptions::buildCombinations()` 一致，使用回调而非返回列表，保持了整个预编译系统的一致性。

## 性能考量

- 模糊是最常用的图像滤镜之一，预编译其管线可以显著减少首帧延迟
- 函数本身不执行 GPU 操作，仅生成管线描述并调用回调
- 管线共享减少了编译时间和缓存空间

## 相关文件

- `src/gpu/graphite/precompile/PaintOptionsPriv.h` - ProcessCombination 类型定义
- `include/gpu/graphite/precompile/PrecompileImageFilter.h` - PrecompileImageFilter 基类
- `src/gpu/graphite/precompile/PrecompileImageFilterPriv.h` - ImageFilter 内部访问
- `src/gpu/graphite/precompile/PrecompileShadersPriv.h` - 包含 Blur 着色器工厂
