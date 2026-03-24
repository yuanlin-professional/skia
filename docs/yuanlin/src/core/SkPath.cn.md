# SkPath

> 源文件
> - include/core/SkPath.h
> - src/core/SkPath.cpp

## 概述

`SkPath` 是 Skia 图形库中用于描述任意二维几何形状的核心类。它可以表示线条、曲线、多边形以及由这些基本元素组成的复杂形状。SkPath 支持多种曲线类型(直线、二次贝塞尔曲线、圆锥曲线、三次贝塞尔曲线),并提供了丰富的几何操作和查询功能。

SkPath 采用写时复制(Copy-on-Write)机制,使得路径复制非常高效。它延迟计算边界框和凸性等属性,在多线程环境中使用前需要调用 `updateBoundsCache()`。

## 架构位置

`SkPath` 位于 Skia 核心绘图层,是图形渲染管线的基础数据结构:

- 公共 API 层: `include/core/SkPath.h` 提供给应用程序使用
- 实现层: `src/core/SkPath.cpp` 包含核心逻辑
- 与 SkCanvas、SkPaint 协同工作完成绘制
- 被路径效果(SkPathEffect)、遮罩滤镜(SkMaskFilter)等高级功能使用
- 与 SkPathBuilder 配合实现路径构建

## 主要类与结构体

### SkPath

#### 继承关系

SkPath 本身不继承自其他类,但与以下类型紧密关联:
- 使用 `SkPathData` 存储实际数据(内部共享指针)
- 支持 `SkPathIter` 和 `Iter` 进行遍历
- 可通过 `SkPathBuilder` 构建

#### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPathData` | `sk_sp<SkPathData>` | 共享指针,存储路径的点、动词和圆锥权重 |
| `fFillType` | `SkPathFillType` | 填充规则(Winding/EvenOdd/Inverse) |
| `fIsVolatile` | `bool` | 标记路径是否易变(影响缓存策略) |

### 嵌套类

#### SkPath::Iter

路径迭代器,提供顺序访问路径动词和点的能力,支持自动闭合选项。

| 方法 | 功能 |
|------|------|
| `next(SkPoint pts[4])` | 返回下一个动词并填充对应的点 |
| `conicWeight()` | 返回当前圆锥曲线的权重 |
| `isCloseLine()` | 判断当前线段是否由闭合动词生成 |
| `isClosedContour()` | 判断当前轮廓是否闭合 |

#### SkPath::RawIter

原始迭代器,不进行任何转换,直接返回路径中的原始动词和点。

### 枚举类型

| 枚举 | 说明 |
|------|------|
| `Verb` | 路径动词(Move/Line/Quad/Conic/Cubic/Close/Done) |
| `SegmentMask` | 路径包含的曲线类型掩码 |
| `AddPathMode` | 添加路径时的模式(追加/扩展) |

## 公共 API 函数

### 静态工厂方法

| 方法 | 功能 |
|------|------|
| `SkPath::Raw()` | 从点、动词、权重数组创建路径 |
| `SkPath::Rect()` | 创建矩形路径 |
| `SkPath::Oval()` | 创建椭圆/圆形路径 |
| `SkPath::RRect()` | 创建圆角矩形路径 |
| `SkPath::Circle()` | 创建圆形路径 |
| `SkPath::Polygon()` | 创建多边形路径 |
| `SkPath::Line()` | 创建线段路径 |

### 形状查询方法

| 方法 | 功能 |
|------|------|
| `isEmpty()` | 判断路径是否为空 |
| `isFinite()` | 判断路径点是否都是有限值 |
| `isConvex()` | 判断路径是否凸 |
| `isRect()` | 判断路径是否为矩形 |
| `isOval()` | 判断路径是否为椭圆 |
| `isRRect()` | 判断路径是否为圆角矩形 |
| `isLine()` | 判断路径是否仅包含一条线段 |
| `isLastContourClosed()` | 判断最后一个轮廓是否闭合 |

### 几何查询方法

| 方法 | 功能 |
|------|------|
| `getBounds()` | 获取路径边界框(缓存) |
| `computeTightBounds()` | 计算精确边界框(考虑曲线控制点) |
| `contains()` | 判断点是否在路径内 |
| `conservativelyContainsRect()` | 保守判断矩形是否被包含 |

### 变换方法

| 方法 | 功能 |
|------|------|
| `makeTransform()` | 应用矩阵变换返回新路径 |
| `tryMakeTransform()` | 安全的变换(失败返回 nullopt) |
| `makeOffset()` | 平移路径 |
| `makeScale()` | 缩放路径 |

### 填充类型操作

| 方法 | 功能 |
|------|------|
| `getFillType()` | 获取填充类型 |
| `setFillType()` | 设置填充类型 |
| `makeFillType()` | 返回指定填充类型的路径副本 |
| `toggleInverseFillType()` | 切换填充类型的反转状态 |

### 插值方法

| 方法 | 功能 |
|------|------|
| `isInterpolatable()` | 判断是否可与另一路径插值 |
| `makeInterpolate()` | 创建插值路径 |
| `interpolate()` | 插值到输出路径 |

### 数据访问方法

| 方法 | 功能 |
|------|------|
| `points()` | 返回点数组的只读视图 |
| `verbs()` | 返回动词数组的只读视图 |
| `conicWeights()` | 返回圆锥权重数组的只读视图 |
| `countPoints()` | 返回点数量 |
| `countVerbs()` | 返回动词数量 |
| `getLastPt()` | 获取最后一个点 |

### 序列化方法

| 方法 | 功能 |
|------|------|
| `serialize()` | 序列化为 SkData |
| `writeToMemory()` | 写入内存缓冲区 |
| `ReadFromMemory()` | 从内存读取 |

### 其他工具方法

| 方法 | 功能 |
|------|------|
| `ConvertConicToQuads()` | 将圆锥曲线转换为二次曲线近似 |
| `IsLineDegenerate()` | 判断线段是否退化 |
| `IsQuadDegenerate()` | 判断二次曲线是否退化 |
| `IsCubicDegenerate()` | 判断三次曲线是否退化 |
| `getGenerationID()` | 获取路径的唯一生成 ID |
| `approximateBytesUsed()` | 估算内存占用 |
| `reset()` | 重置为空路径 |
| `swap()` | 与另一路径交换内容 |

## 内部实现细节

### 写时复制机制

SkPath 使用 `sk_sp<SkPathData>` 共享指针存储数据。复制路径时只复制指针,仅在修改时才真正复制底层数据。这使得路径复制和传递非常高效。

### 延迟计算与缓存

- **边界框**: `getBounds()` 首次调用时计算并缓存在 `SkPathData` 中
- **凸性**: `getConvexity()` 首次调用时通过 `computeConvexity()` 计算
- **线段掩码**: `getSegmentMasks()` 缓存路径包含的曲线类型信息

### 错误处理

路径在以下情况返回错误单例:
- 输入数据无效(动词序列不合法)
- 坐标包含非有限值(NaN, Inf)
- 变换后产生非有限值

错误路径通过 `PeekErrorSingleton()` 返回唯一的错误实例。

### 迭代器实现

**Iter**: 支持 `forceClose` 选项,会在开放轮廓末尾自动插入闭合线段。内部维护 `fNeedClose` 状态跟踪是否需要插入闭合动作。

**RawIter**: 基于 `RangeIter` 实现,直接遍历原始动词和点,不做任何修改。

### 透视裁剪

`SkPathPriv::PerspectiveClip()` 实现了透视变换的裁剪功能,防止在 w < 0 的区域产生无效坐标。使用半平面裁剪算法。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPathData` | 存储路径的实际数据 |
| `SkPathBuilder` | 构建路径 |
| `SkMatrix` | 坐标变换 |
| `SkRRect` | 圆角矩形表示 |
| `SkPathPriv` | 私有辅助功能 |
| `SkGeometry` | 几何计算(贝塞尔曲线等) |
| `SkEdgeClipper` | 边缘裁剪 |
| `SkPathRawShapes` | 基本形状生成 |

### 被依赖的模块

- **SkCanvas**: 使用 SkPath 绘制形状
- **SkPathEffect**: 修改路径外观
- **SkStrokeRec**: 路径描边
- **SkRegion**: 路径到区域转换
- **SkTextBlob**: 文本路径
- **GPU 后端**: Ganesh/Graphite 渲染路径

## 设计模式与设计决策

### 不可变性与写时复制

SkPath 的核心设计是值语义配合写时复制。这允许安全地在多线程环境中共享路径,同时保持高效的复制性能。修改操作通过创建新路径完成,保持原路径不变。

### 工厂模式

提供丰富的静态工厂方法(`Rect()`, `Oval()` 等)创建常见形状,避免暴露复杂的构建细节。

### 迭代器模式

通过 `Iter` 和 `RawIter` 提供两种迭代方式,分别适用于不同场景(需要自动闭合 vs 原始数据访问)。

### 延迟计算策略

边界框、凸性等属性采用延迟计算,避免不必要的开销。对于从未查询这些属性的路径,节省大量计算时间。

### 类型安全的动词表示

使用强类型枚举 `SkPathVerb` 替代原始整数,提升类型安全性。同时保留 `Verb` 枚举用于向后兼容。

### Span 接口

使用 `SkSpan<const T>` 返回数组视图,避免暴露内部指针,同时提供安全的数组访问接口。

## 性能考量

### 内存效率

- 写时复制避免不必要的数据复制
- 紧凑的内部表示(动词和点分离存储)
- 圆锥权重仅在需要时存储

### 计算优化

- 边界框和凸性缓存减少重复计算
- `isRect()`, `isOval()` 等快速路径检测
- 简单形状使用专用数据结构(OvalInfo, RRectInfo)
- 线段掩码快速判断路径复杂度

### 序列化优化

- 识别特殊形状(矩形、椭圆)采用压缩格式
- 仅序列化必要的计算信息
- 向后兼容的版本化格式

### 多线程安全

路径本身是线程安全的(读操作),但延迟计算的属性需要通过 `updateBoundsCache()` 显式准备,避免多线程竞态。

### 退化检测

`IsLineDegenerate()` 等方法快速检测无效几何,允许渲染器跳过不可见的元素。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `include/core/SkPathTypes.h` | 路径类型定义 |
| `include/core/SkPathIter.h` | 路径迭代器定义 |
| `src/core/SkPathPriv.h` | 路径私有功能 |
| `src/core/SkPathData.h` | 路径数据存储 |
| `src/core/SkPathRawShapes.h` | 基本形状生成 |
| `src/core/SkGeometry.h` | 几何计算 |
| `src/core/SkEdgeClipper.h` | 边缘裁剪 |
| `include/core/SkRRect.h` | 圆角矩形 |
| `include/core/SkMatrix.h` | 变换矩阵 |
| `include/core/SkCanvas.h` | 画布(使用者) |
