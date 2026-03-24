# GrProcessorAnalysis

> 源文件: src/gpu/ganesh/GrProcessorAnalysis.h, src/gpu/ganesh/GrProcessorAnalysis.cpp

## 概述

`GrProcessorAnalysis` 模块提供了对片段处理器（Fragment Processor）链进行静态分析的功能，用于识别可以简化生成的着色器代码或提高混合效率的优化机会。该模块包含两个主要类：`GrProcessorAnalysisColor` 和 `GrColorFragmentProcessorAnalysis`。

主要功能包括：
- 分析颜色处理器链的输出特性（不透明度、常量颜色等）
- 识别可以消除的冗余处理器
- 检测处理器是否与 coverage-as-alpha 优化兼容
- 确定是否需要读取目标颜色或纹理
- 分析是否使用本地坐标

这些分析结果用于优化 GrPipeline 的构建，减少不必要的着色器计算，提升渲染性能。

## 架构位置

`GrProcessorAnalysis` 位于 Ganesh 渲染管线的分析层，在处理器集合（ProcessorSet）和最终管线（Pipeline）之间：

```
GrPaint (用户输入)
    ↓
GrProcessorSet (处理器集合)
    ↓
GrProcessorAnalysis (分析优化) ← 本模块
    ↓
GrPipeline (最终渲染管线)
    ↓
GrOpsRenderPass (执行绘制)
```

它与以下模块密切协作：
- `GrFragmentProcessor`: 被分析的对象
- `GrProcessorSet`: 使用分析结果优化处理器集合
- `GrCaps`: 根据硬件能力决定优化策略

## 主要类与结构体

### GrProcessorAnalysisColor

表示处理器分析中的颜色信息，可以是未知、不透明或已知的常量颜色。

**继承关系**: 独立类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFlags` | `uint32_t` | 颜色状态标志位 |
| `fColor` | `SkPMColor4f` | 预乘 RGBA 颜色值 |

**核心枚举**:

```cpp
enum class Opaque {
    kNo,   // 颜色可能有透明度
    kYes,  // 颜色完全不透明
};

enum Flags {
    kColorIsKnown_Flag = 0x1,  // 颜色值已知
    kIsOpaque_Flag = 0x2,       // 颜色不透明
};
```

### GrColorFragmentProcessorAnalysis

对一组颜色片段处理器进行全面分析的结果。

**继承关系**: 独立类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fIsOpaque` | `bool` | 输出是否不透明 |
| `fCompatibleWithCoverageAsAlpha` | `bool` | 是否兼容 coverage-as-alpha 优化 |
| `fUsesLocalCoords` | `bool` | 是否使用本地坐标 |
| `fWillReadDstColor` | `bool` | 是否读取目标颜色 |
| `fOutputColorKnown` | `bool` | 输出颜色是否已知 |
| `fProcessorsToEliminate` | `int` | 可消除的初始处理器数量 |
| `fLastKnownOutputColor` | `SkPMColor4f` | 最后已知的输出颜色 |

## 公共 API 函数

### GrProcessorAnalysisColor 方法

#### 构造函数

```cpp
constexpr GrProcessorAnalysisColor(Opaque opaque = Opaque::kNo);
GrProcessorAnalysisColor(const SkPMColor4f& color);
```

创建未知、不透明或常量颜色对象。

#### setToConstant()

```cpp
void setToConstant(const SkPMColor4f& color);
```

设置为已知的常量颜色，自动检测不透明度。

#### 查询方法

```cpp
bool isUnknown() const;     // 颜色完全未知
bool isOpaque() const;      // 颜色不透明
bool isConstant(SkPMColor4f* color = nullptr) const;  // 是否常量
```

#### Combine()

```cpp
static GrProcessorAnalysisColor Combine(
    const GrProcessorAnalysisColor& a,
    const GrProcessorAnalysisColor& b
);
```

合并两个颜色分析结果，返回公共属性：
- 如果两者都是相同的已知颜色，保留该颜色
- 如果两者都不透明，保留不透明标志
- 否则返回未知颜色

### GrColorFragmentProcessorAnalysis 方法

#### 构造函数

```cpp
GrColorFragmentProcessorAnalysis(
    const GrProcessorAnalysisColor& input,
    std::unique_ptr<GrFragmentProcessor> const fps[],
    int count
);
```

分析给定输入颜色和处理器数组，计算所有分析结果。

#### 查询方法

```cpp
bool isOpaque() const;
bool allProcessorsCompatibleWithCoverageAsAlpha() const;
bool usesLocalCoords() const;
bool willReadDstColor() const;
bool requiresDstTexture(const GrCaps& caps) const;
```

#### initialProcessorsToEliminate()

```cpp
int initialProcessorsToEliminate(SkPMColor4f* newPipelineInputColor) const;
```

返回可以消除的初始处理器数量。如果 > 0，将更新 `newPipelineInputColor` 为新的输入颜色。

#### outputColor()

```cpp
GrProcessorAnalysisColor outputColor() const;
```

返回处理器链最终输出颜色的分析结果。

## 内部实现细节

### 处理器消除逻辑

分析器遍历处理器链，对每个处理器调用 `hasConstantOutputForConstantInput()`：

```cpp
for (int i = 0; i < count; ++i) {
    const GrFragmentProcessor* fp = fps[i].get();
    if (fOutputColorKnown &&
        fp->hasConstantOutputForConstantInput(fLastKnownOutputColor,
                                              &fLastKnownOutputColor)) {
        ++fProcessorsToEliminate;
        // 重置标志，因为前面的处理器被消除了
        fCompatibleWithCoverageAsAlpha = true;
        fUsesLocalCoords = false;
        fWillReadDstColor = false;
        continue;
    }
    // 处理器不能消除，停止分析
    fOutputColorKnown = false;
    // ...
}
```

这实现了一个重要优化：如果前 N 个处理器可以化简为单个常量颜色，直接消除这些处理器，将常量颜色作为后续处理器的输入。

### 不透明度追踪

```cpp
if (fIsOpaque && !fp->preservesOpaqueInput()) {
    fIsOpaque = false;
}
```

只要有一个处理器不保留不透明度，整个链的输出就可能透明。

### Coverage-as-Alpha 兼容性

```cpp
if (fCompatibleWithCoverageAsAlpha && !fp->compatibleWithCoverageAsAlpha()) {
    fCompatibleWithCoverageAsAlpha = false;
}
```

所有处理器都必须兼容才能启用此优化。

### 目标纹理需求判断

```cpp
bool GrColorFragmentProcessorAnalysis::requiresDstTexture(const GrCaps& caps) const {
    return this->willReadDstColor() && !caps.shaderCaps()->fDstReadInShaderSupport;
}
```

只有在需要读取目标颜色且硬件不支持着色器内读取时才需要目标纹理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrFragmentProcessor` | 被分析的处理器对象 |
| `GrCaps` | 查询硬件能力 |
| `SkPMColor4f` | 颜色表示 |
| `SkColorData` | 颜色工具函数 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrProcessorSet` | 使用分析结果优化处理器集合 |
| `GrPipeline` | 根据分析结果构建渲染管线 |
| `GrDrawOp` | 在绘制操作中应用优化 |
| `GrPaint` | 分析绘制状态 |

## 设计模式与设计决策

### 值类型设计

`GrProcessorAnalysisColor` 被设计为轻量级值类型：
- 可以 constexpr 构造
- 默认拷贝和移动
- 大小固定（12 字节）

这使得它可以高效地在栈上传递和存储。

### 渐进式分析策略

分析过程是渐进的：
1. 从输入颜色开始
2. 逐个处理器分析
3. 遇到不可消除的处理器时停止优化
4. 继续收集其他属性（坐标使用、dst 读取等）

这种策略在保持准确性的同时最大化了优化机会。

### 保守分析原则

当无法确定某个属性时，采用保守策略：
- 假设颜色未知（而非随机猜测）
- 假设不兼容优化（而非冒险启用）
- 假设使用复杂特性（而非假设简单情况）

这确保了分析结果的安全性。

### 分离的关注点

将颜色分析（`GrProcessorAnalysisColor`）和处理器分析（`GrColorFragmentProcessorAnalysis`）分离：
- 颜色分析可以独立使用
- 处理器分析构建在颜色分析之上
- 清晰的责任划分

## 性能考量

### 编译时优化

通过消除处理器减少着色器复杂度：
- 减少生成的 GLSL/SPIR-V 代码量
- 降低编译时间
- 减少寄存器压力

### 运行时优化

#### Coverage-as-Alpha

当兼容时，可以将 coverage 直接合并到 alpha 通道：
- 减少一次混合操作
- 简化片段着色器
- 提升填充率

#### 目标纹理避免

通过分析避免不必要的目标纹理创建：
- 节省显存
- 减少纹理拷贝
- 降低带宽需求

### 分析开销

分析本身的开销很小：
- 单次遍历处理器数组
- 简单的布尔逻辑
- 没有复杂的数据结构
- 通常只有 1-3 个处理器

收益远大于成本。

### 缓存友好性

`GrProcessorAnalysisColor` 紧凑的设计（12 字节）使其易于缓存，减少内存访问延迟。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 定义被分析的处理器基类 |
| `src/gpu/ganesh/GrProcessorSet.h` | 使用分析结果优化处理器集合 |
| `src/gpu/ganesh/GrPipeline.h` | 根据分析结果构建管线 |
| `src/gpu/ganesh/GrCaps.h` | 提供硬件能力查询 |
| `src/gpu/ganesh/GrShaderCaps.h` | 着色器相关能力 |
| `src/core/SkColorData.h` | 颜色数据结构 |
| `src/gpu/ganesh/GrPaint.h` | 绘制状态包含处理器 |
