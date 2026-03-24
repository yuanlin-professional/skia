# GrBlendFragmentProcessor

> 源文件
> - src/gpu/ganesh/effects/GrBlendFragmentProcessor.h
> - src/gpu/ganesh/effects/GrBlendFragmentProcessor.cpp

## 概述

`GrBlendFragmentProcessor` 是实现颜色混合的片段处理器，支持 Porter-Duff 混合模式和高级混合模式（如叠加、颜色减淡）。该处理器接受两个输入片段处理器（源和目标），根据指定混合模式在 GPU 着色器中计算混合结果。支持编译时优化（如 src-over 简化）、混合模式降级（不支持的模式回退到 CPU），是 Skia 混合操作的 GPU 实现核心。

## 架构位置

- **模块层级**：`src/gpu/ganesh/effects/` - Ganesh 效果层
- **继承关系**：`GrBlendFragmentProcessor` -> `GrFragmentProcessor`
- **使用者**：`GrPaint`、图层混合、图像合成
- **支持模式**：26+ 种 `SkBlendMode`

## 主要类与结构体

### GrBlendFragmentProcessor

**静态工厂**：
```cpp
template<SkBlendMode mode>
static std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> src,
    std::unique_ptr<GrFragmentProcessor> dst);
```

**运行时工厂**：
```cpp
static std::unique_ptr<GrFragmentProcessor> Make(
    SkBlendMode mode,
    std::unique_ptr<GrFragmentProcessor> src,
    std::unique_ptr<GrFragmentProcessor> dst);
```

## 内部实现细节

### 混合模式分类

**简单模式**（Porter-Duff）：
- Clear, Src, Dst, SrcOver, DstOver, SrcIn, DstIn, ...
- 直接映射到 GPU 混合硬件

**复杂模式**（高级混合）：
- Overlay, Screen, Multiply, ColorBurn, ColorDodge, ...
- 需要自定义着色器计算

### 着色器生成

**SkSL 混合函数**：
```sksl
half4 blend_overlay(half4 src, half4 dst) {
    // 实现 Overlay 混合算法
}
```

**模板生成**：
根据混合模式插入对应 SkSL 函数。

### 优化策略

**SrcOver 优化**：
- 检测 SrcOver + 不透明源
- 简化为直接返回源

**透明度折叠**：
- Alpha = 0 的输入直接跳过

**子效果内联**：
- 简单子效果内联到混合着色器

### 硬件支持检测

**混合方程**：
- 检查 GPU 是否支持特定混合方程
- 不支持则回退到自定义着色器

**高级混合扩展**：
- OpenGL：`GL_KHR_blend_equation_advanced`
- Vulkan：`VK_EXT_blend_operation_advanced`

## 设计模式与设计决策

### 模板特化

模板 `Make<mode>()` 允许编译时混合模式优化。

### 策略模式

不同混合模式对应不同着色器生成策略。

### 降级策略

GPU 不支持的模式自动回退到 CPU 实现或软件着色器。

## 性能考量

### 硬件混合

Porter-Duff 模式使用 GPU 固定功能混合单元，最快。

### 自定义着色器

高级混合模式使用着色器计算，比固定功能慢但比 CPU 快。

### 优化检测

编译时检测简单情况，避免不必要的着色器复杂度。

## 相关文件

- `src/core/SkBlendMode.h` - 混合模式枚举
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/gpu/ganesh/GrXferProcessor.h` - 传输处理器（混合硬件）
