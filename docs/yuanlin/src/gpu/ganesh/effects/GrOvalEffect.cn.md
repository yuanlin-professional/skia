# GrOvalEffect

> 源文件: src/gpu/ganesh/effects/GrOvalEffect.h, src/gpu/ganesh/effects/GrOvalEffect.cpp

## 概述

`GrOvalEffect` 是 Ganesh GPU 后端中用于实现椭圆形裁剪效果的工厂命名空间。它提供了一个智能的优化机制，能够自动检测椭圆是否为圆形，并根据形状特征选择最优的片段处理器实现。该模块是 Skia 图形渲染管线中实现高效几何裁剪的关键组件之一。

`GrOvalEffect` 并不定义具体的类，而是作为一个命名空间提供工厂方法 `Make`，该方法根据输入的椭圆参数自动选择使用圆形或椭圆形的片段处理器。这种设计模式简化了上层调用代码，同时确保了渲染性能的最优化。

## 架构位置

`GrOvalEffect` 位于 Skia 的 GPU 渲染架构中的 Ganesh 后端效果层：

- **层级**: GPU 渲染后端 -> Ganesh 引擎 -> 效果处理层
- **模块**: `src/gpu/ganesh/effects/`
- **功能定位**: 作为片段处理器（Fragment Processor）的工厂，专门处理椭圆形状的裁剪效果
- **渲染管线位置**: 片段着色阶段，用于实现基于几何形状的裁剪和遮罩效果

该模块与 `GrFragmentProcessor` 基类紧密集成，是 Ganesh 渲染管线中处理复杂几何裁剪的重要工具。

## 主要类与结构体

由于 `GrOvalEffect` 是命名空间而非类，它主要提供工厂函数。相关的核心概念包括：

### 命名空间结构

| 元素 | 类型 | 说明 |
|------|------|------|
| `GrOvalEffect` | 命名空间 | 提供椭圆效果的工厂方法 |
| `Make` | 静态工厂函数 | 创建椭圆裁剪效果的片段处理器 |

### 依赖的外部类型

| 类型 | 作用 | 来源 |
|------|------|------|
| `GrFragmentProcessor` | 基础片段处理器类 | Ganesh 核心 |
| `GrClipEdgeType` | 裁剪边缘类型枚举 | Ganesh 核心 |
| `SkRect` | 矩形结构体，定义椭圆边界 | Skia 核心 |
| `GrShaderCaps` | 着色器能力查询接口 | Ganesh 核心 |

### 返回类型

`GrFPResult` 是一个包装类型，用于返回片段处理器的创建结果，可能包含成功创建的处理器或错误信息。

## 公共 API 函数

### Make 工厂函数

```cpp
GrFPResult Make(std::unique_ptr<GrFragmentProcessor> inputFP,
                GrClipEdgeType edgeType,
                const SkRect& oval,
                const GrShaderCaps& caps);
```

**功能**: 创建一个执行椭圆裁剪的片段处理器。

**参数说明**:
- `inputFP`: 输入的片段处理器，椭圆效果将作用于其输出
- `edgeType`: 裁剪边缘类型，定义如何处理椭圆边界（如抗锯齿、填充等）
- `oval`: 定义椭圆边界的矩形区域
- `caps`: 着色器能力对象，用于查询硬件支持的特性

**返回值**: `GrFPResult` 类型，包含创建的片段处理器

**特性**:
- 自动优化：当椭圆的宽高近似相等时，自动使用更高效的圆形处理器
- 智能分发：根据形状特征选择最优实现（圆形或椭圆形）
- 透明集成：调用者无需关心底层使用的具体处理器类型

## 内部实现细节

### 形状检测与优化

`Make` 函数的核心逻辑是检测椭圆是否为圆形：

```cpp
SkScalar w = oval.width();
SkScalar h = oval.height();
if (SkScalarNearlyEqual(w, h)) {
    // 宽高近似相等，使用圆形处理器
    w /= 2;
    return GrFragmentProcessor::Circle(std::move(inputFP), edgeType,
                                       SkPoint::Make(oval.fLeft + w, oval.fTop + w), w);
} else {
    // 使用椭圆处理器
    w /= 2;
    h /= 2;
    return GrFragmentProcessor::Ellipse(std::move(inputFP), edgeType,
                                        SkPoint::Make(oval.fLeft + w, oval.fTop + h),
                                        SkPoint::Make(w, h), caps);
}
```

### 几何参数转换

1. **圆形情况**:
   - 计算半径: `r = width / 2`
   - 计算圆心: `center = (left + r, top + r)`
   - 调用 `GrFragmentProcessor::Circle`

2. **椭圆情况**:
   - 计算半轴: `rx = width / 2, ry = height / 2`
   - 计算中心: `center = (left + rx, top + ry)`
   - 调用 `GrFragmentProcessor::Ellipse`

### 优化策略

- **形状识别**: 使用 `SkScalarNearlyEqual` 进行浮点数比较，避免精度问题
- **性能优先**: 圆形处理器通常比椭圆处理器更高效，因此优先选择
- **参数传递**: 使用 `std::move` 转移 `inputFP` 的所有权，避免不必要的复制

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 用途 |
|------|------|------|
| `GrFragmentProcessor` | Ganesh 核心类 | 提供 Circle 和 Ellipse 工厂方法 |
| `SkRect` | Skia 核心结构 | 定义椭圆的边界矩形 |
| `SkPoint` | Skia 核心结构 | 表示中心点坐标 |
| `SkScalar` | Skia 核心类型 | 浮点数计算 |
| `GrClipEdgeType` | Ganesh 枚举 | 定义裁剪边缘处理方式 |
| `GrShaderCaps` | Ganesh 能力查询 | 查询着色器硬件能力 |

### 被依赖的模块

| 模块 | 关系 | 用途 |
|------|------|------|
| 裁剪系统 | 上层调用 | 使用椭圆效果实现裁剪 |
| 形状渲染器 | 上层调用 | 渲染椭圆形状时应用效果 |
| 效果组合器 | 效果链 | 将椭圆效果与其他效果组合 |
| GPU 操作生成器 | 渲染管线 | 在构建渲染操作时创建椭圆效果 |

## 设计模式与设计决策

### 工厂模式

`GrOvalEffect` 采用工厂模式，通过 `Make` 函数统一创建接口，隐藏具体实现细节：

- **抽象创建**: 调用者不需要知道返回的是圆形还是椭圆形处理器
- **智能选择**: 工厂方法根据输入参数自动选择最优实现
- **扩展性**: 未来可以添加更多优化分支而不影响调用代码

### 命名空间而非类

选择命名空间而非类的设计决策：

- **无状态**: 不需要保存任何状态，纯粹的工厂函数
- **避免实例化**: 防止创建无意义的对象实例
- **清晰语义**: 明确表示这是一个工具集而非数据类型

### 智能优化策略

- **透明优化**: 在不影响正确性的前提下自动选择最快的实现
- **精度容忍**: 使用 `SkScalarNearlyEqual` 而非精确比较，处理浮点数误差
- **性能优先**: 圆形算法比椭圆算法简单，GPU 执行效率更高

### 所有权转移

使用 `std::move` 转移 `inputFP` 的所有权：

- **避免复制**: 片段处理器通常包含复杂数据，移动语义避免深拷贝
- **清晰语义**: 明确表示输入处理器的所有权被转移
- **资源管理**: 通过智能指针自动管理内存生命周期

## 性能考量

### 形状检测开销

- **计算成本**: 宽高比较和判断的开销极小，远低于渲染一帧的成本
- **收益**: 对圆形使用优化算法可以显著提升 GPU 着色器性能
- **trade-off**: CPU 侧少量判断换取 GPU 侧大量性能提升

### GPU 着色器性能

1. **圆形处理器优势**:
   - 距离计算简单: `distance = length(pos - center)`
   - 指令更少，寄存器占用更少
   - 适合 GPU 的向量运算

2. **椭圆处理器成本**:
   - 需要计算标准化距离: `(x/rx)^2 + (y/ry)^2`
   - 涉及更多算术运算
   - 可能需要额外的着色器能力支持

### 内存效率

- **智能指针**: 使用 `std::unique_ptr` 避免内存泄漏
- **移动语义**: 避免片段处理器的深拷贝
- **栈分配**: 临时变量（如中心点、半径）在栈上分配，无堆开销

### 批处理友好

- **无状态设计**: 工厂函数不保存状态，支持并发调用
- **确定性输出**: 相同输入始终产生相同输出，利于缓存和优化

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 依赖 | 基础片段处理器类，提供 Circle 和 Ellipse 方法 |
| `src/gpu/ganesh/effects/GrRRectEffect.h` | 同级 | 圆角矩形效果，类似的工厂模式 |
| `include/core/SkRect.h` | 依赖 | 矩形定义，用于描述椭圆边界 |
| `include/core/SkPoint.h` | 依赖 | 点结构，用于表示中心坐标 |
| `src/gpu/ganesh/GrClip.h` | 上层使用 | 裁剪系统，调用椭圆效果 |
| `src/gpu/ganesh/GrShaderCaps.h` | 依赖 | 着色器能力查询接口 |
| `src/gpu/ganesh/effects/GrConvexPolyEffect.h` | 同级 | 凸多边形效果，类似的裁剪功能 |
