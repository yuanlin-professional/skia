# FuzzGradients

> 源文件: fuzz/oss_fuzz/FuzzGradients.cpp

## 概述

`FuzzGradients.cpp` 是 Skia 中用于模糊测试渐变(Gradients)功能的工具。该模块通过 OSS-Fuzz 框架对各种渐变着色器(线性渐变、径向渐变、角度渐变、双点圆锥渐变、扫描渐变)进行自动化安全测试,验证在处理各种参数组合和边界条件时的稳定性。渐变是图形渲染中的基础功能,广泛用于背景填充、按钮效果和视觉设计。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzGradients.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: Skia 的渐变着色器功能

## 主要类与结构体

### 核心函数

#### `fuzz_Gradients`
```cpp
void fuzz_Gradients(Fuzz* f);
```
**功能**: 执行渐变的模糊测试(外部定义)
**职责**:
- 生成随机的渐变类型选择
- 生成随机的渐变参数(颜色、位置、变换等)
- 创建渐变着色器并应用于绘制

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```
**功能**: LibFuzzer 入口点,输入限制 4000 字节

## 公共 API 函数

使用的 Skia 渐变 API:
- `SkGradientShader::MakeLinear()`: 创建线性渐变
- `SkGradientShader::MakeRadial()`: 创建径向渐变
- `SkGradientShader::MakeTwoPointConical()`: 创建双点圆锥渐变
- `SkGradientShader::MakeSweep()`: 创建扫描渐变

渐变参数:
- 颜色数组和位置数组
- 起点和终点(线性)
- 中心点和半径(径向)
- 平铺模式(Clamp, Repeat, Mirror)
- 颜色插值方式

## 内部实现细节

### 测试流程
```
输入数据 → Fuzz 对象
  → 选择渐变类型
  → 生成颜色数组
  → 生成位置数组(可选)
  → 生成几何参数(起点、终点、半径等)
  → 选择平铺模式和插值方式
  → 创建渐变着色器
  → 应用于绘制并渲染
```

### 渐变类型

**支持的渐变**:
1. **线性渐变**: 沿直线插值颜色
2. **径向渐变**: 从中心点向外辐射
3. **角度渐变**: 围绕中心点旋转
4. **双点圆锥渐变**: 在两个圆之间插值
5. **扫描渐变**: 角度扫描方式

### 参数生成

**颜色数组**:
- 随机数量的颜色(通常 2-10 个)
- 随机的 RGBA 值

**位置数组**:
- 可选(nullptr 表示均匀分布)
- 必须递增且在 [0, 1] 范围内

**平铺模式**:
- `Clamp`: 边界外使用边界颜色
- `Repeat`: 重复渐变
- `Mirror`: 镜像重复

## 依赖关系

- `include/effects/SkGradientShader.h`: 渐变着色器接口
- `src/shaders/gradients/`: 渐变实现
- `fuzz/Fuzz.h`: 模糊测试框架

## 设计模式与设计决策

### 1. 类型枚举模式

通过随机选择渐变类型,测试所有渐变变体。

### 2. 参数验证

测试边界条件:
- 空颜色数组
- 单一颜色
- 无效的位置数组(未排序、越界)
- 退化的几何参数(零半径、重合点)

## 性能考量

### 1. 颜色数量

**影响**:
- 更多颜色增加插值计算
- 影响着色器生成和执行时间

**输入限制**: 4000 字节间接控制颜色数量

### 2. 渐变类型的性能差异

**复杂度**:
- 线性渐变: 最快(简单插值)
- 径向渐变: 中等(需要距离计算)
- 双点圆锥: 最慢(复杂的几何计算)

## 相关文件

1. **`fuzz/fuzz_gradients.cpp`**: 包含 `fuzz_Gradients` 实现
2. **`include/effects/SkGradientShader.h`**: 渐变着色器接口
3. **`src/shaders/gradients/SkLinearGradient.cpp`**: 线性渐变实现
4. **`src/shaders/gradients/SkRadialGradient.cpp`**: 径向渐变实现
5. **`tests/GradientTest.cpp`**: 渐变单元测试
6. **`gm/gradients.cpp`**: 渐变视觉测试

该模糊测试器为 Skia 的渐变功能提供了全面的安全性测试,覆盖所有渐变类型和参数组合,确保在处理各种配置时的稳定性,是着色器渲染质量保证的重要组成部分。
