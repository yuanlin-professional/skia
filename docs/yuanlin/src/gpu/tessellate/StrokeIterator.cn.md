# StrokeIterator - 笔画几何迭代器

> 源文件: `src/gpu/tessellate/StrokeIterator.h`

## 概述

StrokeIterator 是 Skia GPU 细分系统中用于遍历笔画（stroke）几何的迭代器。它在路径的几何动词（verb）之上提供了一个更高层的抽象，自动处理以下复杂情况：

- 将 `close` 动词转换为回到起点的直线
- 将方形端帽（square cap）转换为直线段
- 将圆形端帽（round cap）转换为圆形标记
- 在每个位置提供当前动词和"前一个动词"，为连接（join）计算提供上下文
- 自动跳过退化的零长度线段

## 架构位置

```
Skia GPU 笔画细分
  -> StrokeIterator (笔画迭代器)
    -> SkPath 原始路径数据
    -> SkStrokeRec 笔画参数
    -> SkMatrix 视图矩阵（发丝笔画用）
  -> PatchWriter (使用迭代结果写入补丁)
```

StrokeIterator 将路径和笔画参数的复杂组合简化为线性的（前一动词, 当前动词）对序列，供 PatchWriter 消费。

## 主要类与结构体

### `StrokeIterator`
- **职责**: 将路径的笔画几何展开为带有连接上下文的动词序列
- **状态机**: 内部使用环形队列（circular buffer）管理动词序列

### `Verb` 枚举
| 值 | 说明 |
|----|------|
| `kLine` | 直线段（对应 SkPathVerb::kLine） |
| `kQuad` | 二次贝塞尔（对应 SkPathVerb::kQuad） |
| `kConic` | 圆锥曲线（对应 SkPathVerb::kConic） |
| `kCubic` | 三次贝塞尔（对应 SkPathVerb::kCubic） |
| `kCircle` | 圆形标记（180 度点笔画，用于圆形端帽） |
| `kMoveWithinContour` | 轮廓内移动（通知调用者更新迭代状态） |
| `kContourFinished` | 轮廓结束 |

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `StrokeIterator(path, stroke, viewMatrix)` | 构造函数 |
| `next()` | 前进到下一对"前一/当前"笔画，完成时返回 false |
| `prevVerb()` | 当前位置的前一个动词（用于连接计算） |
| `prevPts()` | 前一个动词的控制点 |
| `verb()` | 当前动词 |
| `pts()` | 当前动词的控制点 |
| `w()` | 当前圆锥曲线的权重 |
| `firstVerbInContour()` | 当前轮廓的第一个动词 |
| `firstPtsInContour()` | 当前轮廓第一个动词的控制点 |
| `IsVerbGeometric(Verb)` | 静态方法：判断动词是否为几何类型 |

## 内部实现细节

### 环形队列（Ring Buffer）
内部使用大小为 8 的环形队列存储动词序列：
- `fVerbs[8]`, `fPts[8]`, `fW[8]`: 分别存储动词、控制点指针和权重指针
- `fQueueFrontIdx`: 队列头部索引
- `fQueueCount`: 队列中的元素数量
- 索引使用 `& (kQueueBufferCount - 1)` 实现环形回绕

### next() 的处理流程
1. 如果队列中有 >= 2 个元素，弹出队头并返回
2. 遍历路径动词：
   - **kMove**: 尝试结束当前开放轮廓
   - **kLine/kQuad/kConic/kCubic**: 跳过退化（所有点相同）的动词，将非退化动词入队
   - **kClose**: 如果关闭点与起点不同，添加回连线段；重复第一个动词作为"当前"动词
3. 第一个非退化动词被延迟到轮廓结束时才作为"当前"动词处理

### 退化线段处理
通过嵌套的 fallthrough switch 检测退化：
```cpp
case kCubic: if (pts[3] == pts[2])
case kConic/kQuad: if (pts[2] == pts[1])
case kLine: if (pts[1] == pts[0])
    // 退化，记录位置但不入队
```
退化点被保存在 `fLastDegenerateStrokePt` 中，以便在零长度子路径需要生成端帽时使用。

### 开放轮廓的端帽处理 (finishOpenContour)
根据端帽类型生成不同的几何：
- **kButt_Cap**: 插入 `kMoveWithinContour` 防止首尾连接
- **kRound_Cap**: 在末尾和开头各插入 `kCircle`
- **kSquare_Cap**: 调用 `fillSquareCapPoints()` 计算方形端帽的端点，生成两条直线

### 方形端帽计算 (fillSquareCapPoints)
- **末端端帽**: 从最后一个动词的末端沿切线方向延伸 `strokeWidth/2`
- **起始端帽**: 从第一个动词的起点沿反向切线方向延伸 `strokeWidth/2`
- **发丝笔画**: 延伸量通过视图矩阵的逆变换计算，确保在设备空间中延伸半个像素

### 发丝笔画的矩阵逆变换
对于发丝笔画（hairline），方形端帽需要在设备空间中精确为半个像素。通过手动求解 2x2 矩阵的逆来计算路径空间中的等效偏移量：
```cpp
float det = a*d - b*c;
outset = SkVector{d, -c} * (.5f / det);
```

### 零长度子路径的特殊处理
根据 SVG 规范，零长度子路径（如 `moveTo + lineTo(same point)`）在 round cap 时生成圆形，在 square cap 时生成线宽的正方形。butt cap 不生成任何几何。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `include/core/SkPath.h` / `SkPathPriv.h` | 路径数据和迭代 |
| `include/core/SkStrokeRec.h` | 笔画参数（宽度、端帽类型等） |
| `include/core/SkMatrix.h` | 视图矩阵（发丝笔画计算） |
| `include/core/SkPaint.h` | 端帽枚举 SkPaint::Cap |
| `include/core/SkPoint.h` | SkPoint 点类型 |

## 设计模式与设计决策

1. **迭代器模式**: 将复杂的笔画几何展开隐藏在 `next()` 方法后面，调用者只需处理简单的（prevVerb, verb）对。

2. **延迟首动词**: 将轮廓的第一个动词延迟到轮廓结束时处理，因为此时才知道它将与什么连接（关闭轮廓时与末尾连接，开放轮廓时作为端帽）。

3. **环形队列**: 使用固定大小的环形队列而非动态容器，因为队列中最多只有少量元素（通常 2-4 个），避免堆分配。

4. **多级 fallthrough**: 利用 C++ 的 fallthrough 特性巧妙地检测所有级别的退化（3 点相同 -> 2 点相同 -> 1 点相同）。

## 性能考量

1. **环形队列效率**: 固定大小数组 + 位掩码索引，所有操作 O(1)，无堆分配。
2. **指针存储**: 存储控制点的指针而非拷贝，避免重复的数据拷贝。
3. **退化跳过**: 零长度线段在迭代阶段即被过滤，避免下游不必要的计算。
4. **端帽内联生成**: 方形和圆形端帽在迭代过程中直接生成几何，无需额外的后处理阶段。

## 相关文件

- `src/gpu/tessellate/PatchWriter.h` - 消费 StrokeIterator 输出的补丁写入器
- `src/gpu/tessellate/Tessellation.h` - 细分常量
- `src/gpu/tessellate/WangsFormula.h` - 曲线段数计算
- `src/gpu/graphite/render/TessellateStrokesRenderStep.cpp` - Graphite 笔画渲染步骤
- `include/core/SkStrokeRec.h` - 笔画参数
