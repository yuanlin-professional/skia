# GrPathUtils

> 源文件: src/gpu/ganesh/geometry/GrPathUtils.h, src/gpu/ganesh/geometry/GrPathUtils.cpp

## 概述

`GrPathUtils` 是 Skia Ganesh GPU 后端中用于路径求值和几何转换的工具命名空间。该模块提供了一系列静态函数,用于将复杂的曲线(二次贝塞尔曲线、三次贝塞尔曲线、圆锥曲线)线性化为线段序列,以便在 GPU 上进行高效渲染。它还支持将三次贝塞尔曲线转换为二次贝塞尔曲线序列,这对于某些渲染路径非常重要。

核心功能包括:
- 曲线细分与线性化(基于容差值)
- 二次/三次贝塞尔曲线的点计数估算
- 二次曲线 UV 坐标映射矩阵计算
- 圆锥曲线的 KLM 隐式方程计算
- 三次曲线到二次曲线的转换

## 架构位置

`GrPathUtils` 位于 Ganesh GPU 后端的几何处理层中:

```
src/gpu/ganesh/
  └── geometry/
      ├── GrPathUtils.h/cpp     # 路径几何工具(本模块)
      ├── GrQuad.h/cpp          # 四边形几何
      ├── GrShape.h/cpp         # 几何形状抽象
      └── GrTriangulator.h/cpp  # 路径三角化
```

该模块为上层的路径渲染器提供基础的几何计算能力,是路径渲染管线的基础组件之一。

## 主要类与结构体

### QuadUVMatrix 类

**继承关系**: 无基类

**用途**: 计算二次贝塞尔曲线在 UV 空间中的映射矩阵,用于着色器中的曲线渲染。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fM` | `float[6]` | 2x3 变换矩阵,将 2D 坐标映射到 UV 空间 |

**关键方法**:
- `set(const SkPoint controlPts[3])`: 从控制点计算矩阵
- `apply(void* vertices, int count, size_t stride, size_t uvOffset)`: 将矩阵应用于顶点数据

## 公共 API 函数

### 容差缩放

```cpp
SkScalar scaleToleranceToSrc(SkScalar devTol,
                              const SkMatrix& viewM,
                              const SkRect& pathBounds)
```

将设备空间的容差值转换为源空间(路径空间)的容差值。考虑了视图矩阵的缩放因子。

### 二次贝塞尔曲线处理

```cpp
uint32_t quadraticPointCount(const SkPoint points[], SkScalar tol)
```

计算将二次曲线线性化所需的最大顶点数(2 的幂次,不超过 `kMaxPointsPerCurve`)。

```cpp
uint32_t generateQuadraticPoints(const SkPoint& p0, const SkPoint& p1, const SkPoint& p2,
                                  SkScalar tolSqd, SkPoint** points, uint32_t pointsLeft)
```

递归生成二次曲线的线性化点序列,返回实际生成的点数。

### 三次贝塞尔曲线处理

```cpp
uint32_t cubicPointCount(const SkPoint points[], SkScalar tol)
```

计算将三次曲线线性化所需的最大顶点数。

```cpp
uint32_t generateCubicPoints(const SkPoint& p0, p1, p2, p3,
                              SkScalar tolSqd, SkPoint** points, uint32_t pointsLeft)
```

递归生成三次曲线的线性化点序列。

### 圆锥曲线处理

```cpp
void getConicKLM(const SkPoint p[3], const SkScalar weight, SkMatrix* klm)
```

计算圆锥曲线的 KLM 隐式方程系数。输出 3x3 矩阵,其中每行代表 K、L、M 线性函数。

### 三次到二次转换

```cpp
void convertCubicToQuads(const SkPoint p[4], SkScalar tolScale,
                         skia_private::TArray<SkPoint, true>* quads)
```

将三次贝塞尔曲线转换为二次曲线序列,保留起点和终点的切线向量。

```cpp
void convertCubicToQuadsConstrainToTangents(const SkPoint p[4], SkScalar tolScale,
                                             SkPathDirection dir,
                                             skia_private::TArray<SkPoint, true>* quads)
```

带约束的三次到二次转换,确保新控制点位于原始切线之间(用于凸路径渲染器)。

## 内部实现细节

### 曲线细分策略

模块采用递归细分策略进行曲线线性化:

1. **容差检查**: 使用 `SkPointPriv::DistanceToLineSegmentBetweenSqd` 检查控制点到弦的距离
2. **中点细分**: 使用 `sk_float_midpoint` 计算精确的中点,避免浮点误差
3. **递归深度限制**: 通过 `kMaxPointsPerCurve = 1024` 限制最大点数

### Wang's Formula 应用

点数估算使用 Wang's Formula 的优化版本:

```cpp
uint32_t quadraticPointCount(const SkPoint points[], SkScalar tol) {
    return max_bezier_vertices(skgpu::wangs_formula::quadratic_log2(
            tolerance_to_wangs_precision(tol), points));
}
```

Wang's Formula 提供了曲线细分次数的理论上界,避免了过度细分。

### 三次到二次转换算法

转换过程分为两步:

1. **拐点检测**: 使用 `SkChopCubicAtInflections` 在拐点处分割曲线
2. **外推法**: 沿起点和终点的切线方向外推,计算新的二次控制点

```cpp
// 切线外推系数
static const SkScalar kLengthScale = 3 * SK_Scalar1 / 2;
SkPoint c0 = p[0] + ab * kLengthScale;
SkPoint c1 = p[3] + dc * kLengthScale;
```

### 数值稳定性处理

- **容差下限**: `kMinCurveTol = 0.0001f` 防止除零错误
- **退化几何处理**: 检测并处理零长度边和重合点
- **双精度计算**: QuadUVMatrix 使用 double 进行中间计算,提高精度

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkGeometry` | 提供贝塞尔曲线分割函数(`SkChopCubicAtHalf`, `SkChopCubicAtInflections`) |
| `SkMatrix` | 视图变换和坐标映射 |
| `SkPathPriv` | 路径方向和其他私有路径操作 |
| `skgpu::wangs_formula` | Wang's Formula 的优化实现 |

### 被依赖的模块

该工具模块被以下组件使用:

| 模块 | 使用场景 |
|------|---------|
| `GrAAConvexPathRenderer` | 凸路径的抗锯齿渲染 |
| `GrAALinearizingConvexPathRenderer` | 线性化凸路径渲染 |
| `GrDefaultPathRenderer` | 默认路径渲染器 |
| `GrTessellationPathRenderer` | 镶嵌路径渲染器 |
| `GrCCPathParser` | 覆盖计数路径解析器 |

## 设计模式与设计决策

### 命名空间设计

使用命名空间而非类来组织工具函数,原因:
- 所有函数都是无状态的静态函数
- 避免不必要的实例化开销
- 清晰地表明这是工具函数集合而非对象

### 模板容器策略

使用 `skia_private::TArray<SkPoint, true>` 作为输出容器:
- 模板参数 `true` 启用栈上小对象优化(SOO)
- 避免小规模数组的堆分配开销
- 适合曲线转换这种输出大小可预测的场景

### 容差传递模式

- **输入**: 设备空间容差(`devTol`)
- **转换**: 通过 `scaleToleranceToSrc` 转换为源空间容差
- **使用**: 在递归算法中使用平方容差(`tolSqd`)避免开方运算

这种设计避免了在递归过程中重复进行坐标变换。

### 双精度浮点策略

QuadUVMatrix 在计算过程中使用 double,但存储为 float:

```cpp
double det = a2 + a5 + a8;
// ... 计算过程使用 double ...
fM[0] = (float)((0.5*a3 + a6)*scale);  // 最后转换为 float
```

权衡了精度需求和内存/性能开销。

## 性能考量

### 关键优化点

1. **预分配缓冲区**: 调用者通过 `pointsLeft` 参数预分配缓冲区,避免递归中的内存分配
2. **平方容差**: 使用 `tolSqd` 避免在比较中进行 `sqrt` 运算
3. **SIMD 友好**: 点数据使用连续内存布局,便于 SIMD 优化
4. **Wang's Formula**: O(1) 复杂度估算点数,避免试探性递归

### 性能常量

```cpp
static const SkScalar kDefaultTolerance = 0.25;  // 四分之一像素精度
static const int kMaxPointsPerCurve = 1024;     // 防止病态曲线导致的内存爆炸
```

这些常量在渲染质量和性能之间取得平衡。

### 退化处理开销

退化几何的特殊处理(如 QuadUVMatrix 中的退化三角形检测)虽然增加了代码复杂度,但避免了后续渲染管线中的数值问题,整体上提高了鲁棒性。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/tessellate/WangsFormula.h` | 依赖 | Wang's Formula 实现 |
| `src/core/SkGeometry.h` | 依赖 | 贝塞尔曲线几何算法 |
| `src/gpu/ganesh/ops/PathInnerTriangulateOp.cpp` | 被使用 | 路径内部三角化操作 |
| `src/gpu/ganesh/ops/PathStencilCoverOp.cpp` | 被使用 | 路径模板覆盖操作 |
| `tests/PathTest.cpp` | 测试 | 单元测试用例 |
