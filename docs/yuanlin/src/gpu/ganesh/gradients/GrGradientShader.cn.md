# GrGradientShader

> 源文件
> - src/gpu/ganesh/gradients/GrGradientShader.h
> - src/gpu/ganesh/gradients/GrGradientShader.cpp

## 概述

`GrGradientShader` 是 Skia Ganesh GPU 后端的渐变着色器基类，提供线性、径向、锥形、扫掠等渐变类型的统一接口和共享逻辑。该类封装渐变参数（颜色、位置、插值模式、平铺模式），生成对应的片段处理器，并管理渐变纹理/缓冲区。支持硬停止渐变、预乘 Alpha 插值、颜色空间转换等高级特性，是 GPU 渐变渲染的核心抽象层。

## 架构位置

- **模块层级**：`src/gpu/ganesh/gradients/` - Ganesh 渐变处理
- **作用**：渐变着色器基类和工厂
- **子类**：`GrLinearGradient`、`GrRadialGradient`、`GrSweepGradient`、`GrConicGradient`
- **输出**：`GrFragmentProcessor` 链

## 主要类与结构体

### GrGradientShader

**静态工厂方法**：
```cpp
static std::unique_ptr<GrFragmentProcessor> MakeGradientFP(
    const SkGradientShaderBase&, const GrFPArgs&);
```

根据渐变类型分发到具体子类实现。

**共享功能**：
- 颜色插值
- 平铺模式处理（clamp, repeat, mirror）
- 硬停止检测
- 颜色缓冲区生成

## 内部实现细节

### 渐变类型识别

根据 `SkGradientShaderBase` 类型动态分发：
- `kLinear_Type` -> `GrLinearGradient`
- `kRadial_Type` -> `GrRadialGradient`
- `kSweep_Type` -> `GrSweepGradient`
- `kConical_Type` -> `GrConicGradient`

### 颜色插值策略

**平滑渐变**：
- 使用纹理或 Uniform 数组存储颜色
- GPU 插值器自动插值

**硬停止渐变**：
- 检测相邻停止点位置相同
- 生成特殊几何或着色器逻辑

### 平铺模式

**Clamp**：边界外钳位到边缘颜色

**Repeat**：重复渐变图案（模运算）

**Mirror**：镜像重复（奇偶翻转）

### 颜色空间

支持 sRGB、线性 RGB、显示 P3 等颜色空间，自动插入转换处理器。

## 设计模式与设计决策

### 工厂方法模式

静态工厂根据渐变类型创建具体实现，隐藏子类细节。

### 模板方法模式

基类定义渐变处理流程，子类实现几何生成逻辑。

### 策略模式

平铺模式、插值模式作为可配置策略。

## 性能考量

### 纹理 vs Uniform

小型渐变（<8 停止点）使用 Uniform，大型渐变使用纹理，平衡性能。

### 硬停止优化

硬停止渐变避免纹理采样，使用条件分支或几何分割。

### 颜色预乘

在 CPU 端预乘 Alpha，减少 GPU 计算。

## 相关文件

- `src/gpu/ganesh/gradients/GrGradientBitmapCache.h` - 渐变纹理缓存
- `src/shaders/gradients/SkGradientShaderBase.h` - 渐变着色器基类
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
