# PrecompileShadersPriv - 内部着色器预编译工厂

> 源文件: `src/gpu/graphite/precompile/PrecompileShadersPriv.h`

## 概述

`PrecompileShadersPriv` 是 Skia Graphite 预编译系统中的内部着色器工厂命名空间。它提供了一系列着色器工厂函数，主要用于实现图像滤镜效果和内部着色器包装。这些工厂函数创建的预编译着色器不直接暴露给用户，而是被图像滤镜预编译系统和 PaintOptions 内部流程使用。

## 架构位置

```
预编译着色器工厂体系
  ├── PrecompileShaders (公共工厂命名空间)
  │     ├── Color, Image, Blend, LinearGradient, ...
  └── PrecompileShadersPriv (本文件 - 内部工厂命名空间)
        ├── 图像滤镜着色器 (Blur, Displacement, Lighting, ...)
        ├── CTM 裁剪着色器
        └── LocalMatrix 变体工厂
```

## 主要类与结构体

本文件定义的是命名空间函数集合，不包含类定义。

## 公共 API 函数

### 图像滤镜着色器工厂

| 工厂函数 | 参数 | 说明 |
|----------|------|------|
| `Blur(wrapped)` | 被包装的着色器 | 模糊效果着色器 |
| `Displacement(displacement, color)` | 位移和颜色着色器 | 位移映射着色器 |
| `Lighting(wrapped)` | 被包装的着色器 | 光照效果着色器 |
| `MatrixConvolution(wrapped)` | 被包装的着色器 | 矩阵卷积着色器 |
| `LinearMorphology(wrapped)` | 被包装的着色器 | 线性形态学着色器 |
| `SparseMorphology(wrapped)` | 被包装的着色器 | 稀疏形态学着色器 |

所有工厂函数返回 `sk_sp<PrecompileShader>`。

### 内部包装着色器

| 工厂函数 | 参数 | 说明 |
|----------|------|------|
| `CTM(wrapped)` | 着色器列表 | CTM（Current Transform Matrix）裁剪着色器 |
| `Picture(withLM)` | 是否带 LocalMatrix | Picture 着色器（已知 LM 存在性） |
| `LocalMatrixBothVariants(wrapped)` | 着色器列表 | 同时创建有/无 LocalMatrix 的变体 |

## 内部实现细节

### 图像滤镜着色器

前 6 个工厂函数专门用于图像滤镜效果的预编译。它们各自包装一个输入着色器，添加特定效果的管线键数据：

- **Blur**: 高斯模糊核的应用
- **Displacement**: 使用位移贴图扭曲颜色着色器
- **Lighting**: 点光源/方向光光照计算
- **MatrixConvolution**: 通用矩阵卷积核
- **LinearMorphology**: 线性膨胀/腐蚀操作
- **SparseMorphology**: 稀疏形态学操作（优化版本）

### CTM 着色器

`CTM()` 创建应用当前变换矩阵的着色器包装器，用于裁剪着色器（Clip Shader）场景。注释指出该函数接受 `SkSpan` 参数，但实际上目前只从 `PaintOptions::setClipShaders` 传入单个着色器。保留 Span 接口是为了可能的未来扩展。

### Picture 着色器

`Picture(bool withLM)` 是 `PrecompileShaders::Picture()` 的内部变体，当 LocalMatrix 的存在与否已知时使用：
- `withLM = true`: 仅创建 LMShader 包装版本
- `withLM = false`: 不包装 LMShader

这比公共版本（同时创建两种变体）更精确，减少了不必要的管线组合。

### LocalMatrixBothVariants

`LocalMatrixBothVariants()` 同时创建有和无 LocalMatrix 包装的两种变体。目前仅由公共 `PrecompileShaders::Picture` 入口使用。注释建议该工厂函数最终应该被移除。

## 依赖关系

- **include/core/SkRefCnt.h**: `sk_sp` 智能指针
- **src/base/SkEnumBitMask.h**: 枚举位掩码
- **src/gpu/graphite/precompile/PaintOptionsPriv.h**: 隐式依赖于 PaintOptions 类型
- 前向声明: `PrecompileShader`

## 设计模式与设计决策

### 效果着色器包装模式

大多数工厂函数遵循相同的模式：接受一个 `wrapped` 着色器并返回添加了效果处理的新着色器。这对应了运行时图像滤镜将中间纹理作为着色器输入的方式。

### 已知状态优化

`Picture(bool withLM)` 展示了"在已知更多信息时提供更精确预编译"的策略。与公共 API 的"覆盖所有可能"不同，内部代码可以在确定性更高的上下文中使用更窄的预编译范围。

### 演化中的 API

代码注释多处标注了 TODO，表明这些工厂函数的 API 仍在演化中。`LocalMatrixBothVariants` 被标记为最终应移除，`CTM` 的 Span 参数可能被简化。

## 性能考量

- 工厂函数仅创建描述对象，不触发实际编译
- `Picture(bool withLM)` 通过精确控制变体数量，减少了 50% 的不必要管线组合
- 每个图像滤镜着色器通常增加 1-2 个管线变体

## 相关文件

- `include/gpu/graphite/precompile/PrecompileShaders.h` - 公共着色器工厂
- `src/gpu/graphite/precompile/PrecompileShaderPriv.h` - Shader Priv 访问
- `src/gpu/graphite/precompile/PrecompileImageFiltersPriv.h` - 图像滤镜管线构建
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` - PaintOptions 内部（setClipShaders）
