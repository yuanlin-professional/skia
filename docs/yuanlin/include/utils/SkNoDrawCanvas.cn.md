# SkNoDrawCanvas 无渲染画布

> 源文件: `include/utils/SkNoDrawCanvas.h`

## 概述

`SkNoDrawCanvas` 是 `SkCanvas` 的一个特殊子类,用于不需要实际光栅化像素的场景,例如绘制调用分析、边界计算、命令记录等。它提供了一个轻量级的画布实现,跳过实际的像素绘制过程,但保留了完整的变换、裁剪和绘制命令追踪能力。

## 架构位置

本模块位于 Skia 的工具(utils)子系统中,属于画布抽象层的扩展工具。它作为 `SkCanvas` 的分析和调试辅助类,被广泛应用于性能分析、绘制命令检查、边界计算等不需要实际渲染的场景。

## 主要类与结构体

### SkNoDrawCanvas

**职责**: 提供一个不执行实际光栅化的画布实现,用于绘制命令的分析和处理。

**继承关系**: `SkCanvas` → `SkCanvasVirtualEnforcer<SkCanvas>` → `SkNoDrawCanvas`

**关键特性**:
- 不由任何设备/像素缓冲区支持
- 使用保守的矩形裁剪(只使用矩形进行裁剪)
- 所有绘制操作都是空操作(no-op)
- 保留完整的变换和裁剪栈追踪

**关键成员变量**:

虽然头文件没有显式列出成员变量,但从继承关系可知,它使用基类 `SkCanvas` 的成员来维护:
- 变换矩阵栈
- 裁剪区域栈
- 画布尺寸信息

## 公共 API 函数

### 构造函数

#### `SkNoDrawCanvas(int width, int height)`
- **功能**: 创建指定宽高的无渲染画布
- **参数**:
  - `width`: 画布宽度(像素)
  - `height`: 画布高度(像素)
- **使用场景**: 需要已知画布尺寸进行绘制分析

#### `explicit SkNoDrawCanvas(const SkIRect& rect)`
- **功能**: 从矩形区域创建无渲染画布
- **参数**:
  - `rect`: 指定画布的矩形区域
- **使用场景**: 当画布区域不从原点开始时使用

### 状态重置函数

#### `void resetCanvas(int w, int h)`
- **功能**: 重置画布状态为初始构造状态
- **参数**: 新的宽度和高度
- **用途**: 优化性能,复用画布对象而不重新分配内存

#### `void resetCanvas(const SkIRect& rect)`
- **功能**: 重置画布状态并指定新的矩形区域
- **参数**: 新的矩形区域
- **用途**: 在循环处理多个图片时复用画布对象

## 保护方法(子类可重写)

### 图层和状态管理

#### `SaveLayerStrategy getSaveLayerStrategy(const SaveLayerRec& rec) override`
- **功能**: 返回保存图层的策略
- **返回值**: 决定如何处理图层保存操作
- **说明**: 可能返回不创建实际图层的策略以优化性能

#### `bool onDoSaveBehind(const SkRect*) override`
- **功能**: 处理"保存背景"操作
- **返回值**: 是否成功执行操作
- **说明**: 空实现,不执行实际操作

### 绘制操作(所有方法都是空实现)

所有以下方法都被重写为空操作,不执行任何实际的像素渲染:

#### 基础形状绘制
- `onDrawPaint()`: 绘制整个画布
- `onDrawRect()`: 绘制矩形
- `onDrawOval()`: 绘制椭圆
- `onDrawRRect()`: 绘制圆角矩形
- `onDrawPath()`: 绘制路径
- `onDrawArc()`: 绘制弧形
- `onDrawRegion()`: 绘制区域
- `onDrawDRRect()`: 绘制双圆角矩形(甜甜圈形状)
- `onDrawPoints()`: 绘制点集

#### 图像绘制
- `onDrawImage2()`: 绘制图像
- `onDrawImageRect2()`: 绘制图像到指定矩形
- `onDrawImageLattice2()`: 使用九宫格方式绘制图像
- `onDrawAtlas2()`: 绘制图集(多个精灵)

#### 高级绘制
- `onDrawTextBlob()`: 绘制文本块
- `onDrawVerticesObject()`: 绘制顶点对象
- `onDrawPatch()`: 绘制贝塞尔曲面片
- `onDrawShadowRec()`: 绘制阴影
- `onDrawPicture()`: 绘制图片(命令集合)
- `onDrawDrawable()`: 绘制可绘制对象
- `onDrawAnnotation()`: 绘制注解
- `onDrawBehind()`: 在背后绘制

#### 特殊效果
- `onDrawEdgeAAQuad()`: 绘制边缘抗锯齿的四边形
- `onDrawEdgeAAImageSet2()`: 绘制边缘抗锯齿的图像集

## 内部实现细节

### 性能优化策略

`SkNoDrawCanvas` 的核心优势是性能优化:

1. **跳过光栅化**: 所有绘制方法都是空实现,避免了昂贵的像素操作
2. **保守裁剪**: 只使用矩形裁剪,避免了复杂路径裁剪的计算开销
3. **无设备依赖**: 不创建 `SkDevice` 对象,节省内存和初始化时间
4. **提前终止**: 相比使用 `SkNullBlitter` 在光栅化阶段终止,在更早阶段就终止操作

### 变换和裁剪追踪

虽然不执行实际绘制,`SkNoDrawCanvas` 仍然维护:

- **变换矩阵栈**: 记录所有 `translate()`, `rotate()`, `scale()` 等操作
- **裁剪区域栈**: 记录所有 `clipRect()`, `clipPath()` 等操作(转换为矩形)
- **保存/恢复栈**: 记录 `save()` 和 `restore()` 调用

这使得基于这些信息的分析(如边界计算)仍然准确。

### 保守裁剪的含义

"保守裁剪"意味着:
- 路径裁剪被转换为包围该路径的矩形裁割
- 结果可能比实际裁剪区域更大
- 对于分析目的这是可接受的,因为它保证了不会遗漏任何可能被绘制的区域

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkCanvas.h` | 基类,提供画布核心功能 |
| `include/core/SkCanvasVirtualEnforcer.h` | 强制虚函数重写的 CRTP 辅助类 |
| `SkIRect` | 定义画布的矩形区域 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRecorder` | 可能使用 `SkNoDrawCanvas` 记录绘制命令 |
| `SkPictureAnalyzer` | 分析 `SkPicture` 的绘制调用 |
| 测试框架 | 验证绘制命令序列而不实际渲染 |
| 边界计算工具 | 计算绘制操作的边界框 |

## 设计模式与设计决策

### 空对象模式 (Null Object Pattern)

`SkNoDrawCanvas` 是空对象模式的经典应用:
- 提供与 `SkCanvas` 相同的接口
- 所有操作都是有效的,但不执行实际工作
- 客户端代码无需特殊处理,可以像使用普通画布一样使用

### CRTP (Curiously Recurring Template Pattern)

通过 `SkCanvasVirtualEnforcer<SkCanvas>` 使用 CRTP:
- 编译时检查确保所有虚函数都被正确重写
- 避免因忘记重写某个绘制方法而导致的意外渲染

### 模板方法模式

基类 `SkCanvas` 定义了公共接口,而 `SkNoDrawCanvas` 重写了所有的 `onDraw*` 保护方法,这是模板方法模式的应用。

## 性能考量

### 性能优势

1. **零像素操作**: 完全避免像素读写,速度可提升 10-100 倍
2. **低内存占用**: 不分配像素缓冲区,节省大量内存
3. **快速重置**: `resetCanvas()` 方法允许复用对象,避免频繁分配

### 适用场景

**推荐使用**:
- 绘制命令序列分析
- 边界框计算(获取绘制区域)
- 绘制调用统计和性能分析
- 测试绘制逻辑而不需要验证像素输出
- 命令记录和回放系统

**不推荐使用**:
- 需要实际像素输出的场景
- 需要精确裁剪区域的分析(因为使用保守裁剪)
- 需要像素级精确度验证的测试

### 使用示例

```cpp
// 场景: 计算绘制操作的边界
SkNoDrawCanvas canvas(1000, 1000);
SkRect bounds;

// 执行一系列绘制操作
drawComplexScene(&canvas);

// 获取实际绘制的边界(通过裁剪信息推断)
bounds = canvas.getLocalClipBounds();

// 复用画布处理下一个场景
canvas.resetCanvas(1000, 1000);
drawAnotherScene(&canvas);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkCanvas.h` | 基类定义 |
| `include/core/SkCanvasVirtualEnforcer.h` | CRTP 辅助类 |
| `src/core/SkCanvas.cpp` | 基类实现 |
| `src/utils/SkNoDrawCanvas.cpp` | 本类的实现文件 |
| `include/core/SkNullBlitter.h` | 另一种跳过渲染的机制(在更晚的阶段) |
| `tools/debugger/` | 调试工具可能使用此类 |

## 总结

`SkNoDrawCanvas` 是 Skia 工具集中一个设计精巧的类,它通过空对象模式提供了一个高性能的画布分析工具。其核心价值在于保留了画布的状态追踪能力(变换、裁剪),同时完全跳过了昂贵的像素操作。这使得它成为绘制命令分析、性能测试和边界计算等场景的理想选择。设计上的克制和专注使其在特定领域表现出色,是"做好一件事"设计哲学的优秀范例。
