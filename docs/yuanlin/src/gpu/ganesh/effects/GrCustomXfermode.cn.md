# GrCustomXfermode

> 源文件: `src/gpu/ganesh/effects/GrCustomXfermode.h`, `src/gpu/ganesh/effects/GrCustomXfermode.cpp`

## 概述

`GrCustomXfermode` 命名空间提供了不能用混合系数表示的高级混合模式（Overlay、Darken、Lighten、ColorDodge、ColorBurn 等 14 种 Porter-Duff 之外的模式）的 GPU 实现。它根据硬件能力选择两种实现路径：硬件高级混合方程或着色器中的软件混合。

## 架构位置

位于 Ganesh 效果层的混合处理（XferProcessor）子系统中。`GrCustomXfermode::Get()` 返回的 `GrXPFactory` 被管线用于创建 `GrXferProcessor`，后者决定最终的颜色输出和混合状态。

## 主要类与结构体

### `GrCustomXfermode` 命名空间
- `IsSupportedMode()` - 判断混合模式是否属于高级混合（Overlay 到 Luminosity）
- `Get()` - 返回指定混合模式的 `GrXPFactory`（constexpr 静态单例）

### `CustomXP`（内部 XferProcessor）
- 两种模式：HW 混合方程模式和软件读取目标颜色模式
- HW 模式：设置混合方程，覆盖率直接乘入源颜色
- 软件模式：读取目标颜色，在着色器中执行混合函数

### `CustomXPFactory`（内部 XPFactory）
- 编译时常量（constexpr）工厂
- 持有 `SkBlendMode` 和对应的 `skgpu::BlendEquation`
- 根据 GPU 能力决定使用 HW 还是软件混合

## 公共 API 函数

### `IsSupportedMode()`
```cpp
bool IsSupportedMode(SkBlendMode mode);
```
返回 `true` 当模式在 `kLastCoeffMode` 之后且在 `kLastMode` 之内（即 Overlay 到 Luminosity）。

### `Get()`
```cpp
const GrXPFactory* Get(SkBlendMode mode);
```
返回一个静态 constexpr 的 `CustomXPFactory` 指针。14 种模式各有一个全局单例。

## 内部实现细节

### HW 混合方程映射
- `hw_blend_equation()` 通过固定偏移将 `SkBlendMode` 映射到 `skgpu::BlendEquation`
- 使用大量 `static_assert` 确保映射正确

### HW 可用性检查
- `can_use_hw_blend_equation()` 要求：
  1. GPU 支持高级混合方程
  2. 非 LCD 覆盖率（LCD 需要后处理）
  3. 特定方程未被禁用

### 覆盖率兼容性证明
- CPP 文件中包含了完整的数学证明，证明所有高级混合模式都与 `canTweakAlphaForCoverage` 兼容
- 核心等式：`blend(f*Sca, Dca, f*Sa, Da) == f * blend(Sca, Dca, Sa, Da) + (1-f) * Dca`
- 这意味着可以将覆盖率预乘到源颜色中，无需额外的覆盖率混合步骤

### 着色器软件混合
- 使用 `GrGLSLBlend::BlendExpression()` 在着色器中实现混合函数
- `DefaultCoverageModulation()` 处理覆盖率的后混合应用

### 屏障需求
- HW 高级混合 + 非相干支持时，需要 `kBlend_GrXferBarrierType` 屏障
- 相干支持或软件混合时不需要屏障

## 依赖关系

- **GrXferProcessor / GrXPFactory** - 混合处理器基类和工厂基类
- **GrGLSLBlend** - 着色器中的混合函数实现
- **GrCaps** - 高级混合方程支持查询
- **skgpu::BlendEquation / BlendInfo** - 混合方程和信息

## 设计模式与设计决策

1. **constexpr 单例**: 14 个 `CustomXPFactory` 为编译时常量，零运行时分配
2. **双路径策略**: HW 混合方程优先，不支持时回退到着色器混合
3. **覆盖率优化**: 通过数学证明确认可将覆盖率折叠到 alpha，减少混合步骤
4. **诊断抑制**: 使用 `#pragma` 抑制 `Wnon-virtual-dtor` 警告（XPFactory 设计约束）

## 性能考量

- HW 高级混合方程最高效，但需要硬件支持
- 非相干 HW 混合需要屏障，可能影响并行性
- 软件混合需要读取目标颜色（额外的纹理读取或输入附件读取）
- 覆盖率折叠避免了额外的混合通道

## 相关文件

- `src/gpu/ganesh/GrXferProcessor.h` - 混合处理器基类
- `src/gpu/ganesh/glsl/GrGLSLBlend.h` - 着色器混合实现
- `src/gpu/Blend.h` - 混合方程和常量
- `include/core/SkBlendMode.h` - 混合模式枚举
