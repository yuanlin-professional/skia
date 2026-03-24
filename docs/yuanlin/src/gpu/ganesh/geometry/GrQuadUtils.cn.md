# GrQuadUtils

> 源文件: src/gpu/ganesh/geometry/GrQuadUtils.h, src/gpu/ganesh/geometry/GrQuadUtils.cpp

## 概述

`GrQuadUtils` 是 Ganesh GPU 后端中专门用于四边形几何处理的工具命名空间。该模块提供了四边形的高级几何操作,包括抗锯齿边缘处理、透视裁剪、内缩外扩(inset/outset)以及边缘方程计算等功能。它是 GPU 纹理绘制和矩形渲染的核心支持模块,能够处理从简单轴对齐矩形到复杂透视变换四边形的各种情况。

核心功能包括:
- 四边形顶点的精确内缩和外扩(用于抗锯齿)
- W=0 平面裁剪(透视除法前的裁剪)
- 四边形到矩形的裁剪
- 边缘方程计算和退化情况处理
- 抗锯齿类型解析和边缘标志管理

## 架构位置

`GrQuadUtils` 位于 Ganesh 几何层,为四边形渲染提供底层支持:

```
src/gpu/ganesh/
  └── geometry/
      ├── GrQuad.h/cpp          # 四边形数据结构
      ├── GrQuadUtils.h/cpp     # 四边形几何工具(本模块)
      ├── GrShape.h/cpp         # 通用几何形状
      └── ops/
          ├── FillRectOp.cpp    # 使用者: 矩形填充操作
          └── TextureOp.cpp     # 使用者: 纹理绘制操作
```

该模块是 `GrQuad` 的扩展工具集,为上层绘制操作提供复杂的几何计算能力。

## 主要类与结构体

### TessellationHelper 类

**继承关系**: 无基类

**用途**: 提供四边形顶点的内缩/外扩计算,支持抗锯齿边缘渲染。这是 `GrQuadUtils` 中最核心的类。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fOriginal` | `Vertices` | 原始四边形顶点(设备和局部坐标) |
| `fEdgeVectors` | `EdgeVectors` | 预计算的边向量和角度信息 |
| `fEdgeEquations` | `EdgeEquations` | 边缘线性方程(惰性计算) |
| `fOutsetRequest` | `OutsetRequest` | 外扩请求的退化检测结果(惰性计算) |
| `fDeviceType` | `GrQuad::Type` | 设备坐标四边形类型 |
| `fLocalType` | `GrQuad::Type` | 局部坐标四边形类型 |

**嵌套结构体**:

#### EdgeVectors

存储四边形边的投影向量和角度信息:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fX2D`, `fY2D` | `float4` | 投影到 2D 的顶点坐标 |
| `fDX`, `fDY` | `float4` | 归一化的边向量 |
| `fInvLengths` | `float4` | 边长的倒数 |
| `fCosTheta` | `float4` | 相邻边夹角的余弦值 |
| `fInvSinTheta` | `float4` | 夹角正弦值的倒数 |

#### EdgeEquations

边缘的隐式直线方程 `ax + by + c = 0`:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fA`, `fB`, `fC` | `float4` | 四条边的方程系数,按 L,B,T,R 顺序 |

#### Vertices

四边形的 3D 顶点数据(设备坐标和可选的局部坐标):

| 成员 | 类型 | 说明 |
|------|------|------|
| `fX`, `fY`, `fW` | `float4` | 设备空间齐次坐标 |
| `fU`, `fV`, `fR` | `float4` | 局部坐标齐次坐标(可选) |
| `fUVRCount` | `int` | 局部坐标维度(0/2/3) |

### DrawQuad 结构体

**用途**: 表示一对设备和局部四边形,以及抗锯齿边缘标志。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDevice` | `GrQuad` | 设备空间四边形 |
| `fLocal` | `GrQuad` | 局部(纹理)坐标四边形 |
| `fEdgeFlags` | `GrQuadAAFlags` | 每条边的抗锯齿标志 |

## 公共 API 函数

### 抗锯齿解析

```cpp
void ResolveAAType(GrAAType requestedAAType, GrQuadAAFlags requestedEdgeFlags,
                   const GrQuad& quad, GrAAType* outAAtype, GrQuadAAFlags* outEdgeFlags)
```

解决抗锯齿类型和边缘标志之间的冲突,输出最终的 AA 配置。例如,如果四边形是轴对齐的且边缘在像素边界上,可以将 Coverage AA 降级为无 AA。

### 透视裁剪

```cpp
int ClipToW0(DrawQuad* quad, DrawQuad* extraVertices)
```

将四边形裁剪到 W=0 平面前方(避免透视除法错误)。返回值:
- `0`: 完全在平面后方,无需绘制
- `1`: 无需裁剪或裁剪后为单个四边形
- `2`: 裁剪产生五边形,需要两个四边形表示

### 矩形裁剪

```cpp
bool CropToRect(const SkRect& cropRect, GrAA cropAA, DrawQuad* quad, bool computeLocal=true)
```

将四边形裁剪到轴对齐矩形内。对于轴对齐四边形可以精确裁剪,非轴对齐四边形使用重心坐标判断是否完全包含裁剪矩形。

### 内缩与外扩

```cpp
// TessellationHelper 成员函数
float4 inset(const float4& edgeDistances, GrQuad* deviceInset, GrQuad* localInset);
void outset(const float4& edgeDistances, GrQuad* deviceOutset, GrQuad* localOutset);
```

- `inset`: 将四边形边缘向内移动指定距离,返回每个顶点的覆盖率
- `outset`: 将四边形边缘向外移动指定距离

边缘距离按 `L, B, T, R`(左,下,上,右)顺序排列。

### 边缘方程获取

```cpp
void getEdgeEquations(float4* a, float4* b, float4* c);
float4 getEdgeLengths();
bool isSubpixel();
```

- `getEdgeEquations`: 获取四条边的直线方程系数
- `getEdgeLengths`: 获取四条边的长度
- `isSubpixel`: 判断四边形是否小于 1 像素

### 辅助函数

```cpp
bool WillUseHairline(const GrQuad& quad, GrAAType aaType, GrQuadAAFlags edgeFlags);
void Outset(const float4& edgeDistances, GrQuad* quad);  // 简化的外扩接口
```

## 内部实现细节

### SIMD 优化策略

模块大量使用 `skvx::float4` 进行 SIMD 优化,将四个顶点的计算向量化:

```cpp
using float4 = skvx::float4;
float4 fX, fY, fW;  // 四个顶点的齐次坐标

// 向量化的边向量计算
float4 fDX = next_ccw(fX2D) - fX2D;
float4 fDY = next_ccw(fY2D) - fY2D;
```

通过 `shuffle` 操作实现顶点的旋转(`next_cw`, `next_ccw`, `next_diag`)。

### 内缩/外扩算法

核心思想是沿边向量移动顶点。对于非透视四边形:

```cpp
// 顶点沿其两条邻接边移动
float4 signedOutsets = -fInvSinTheta * next_cw(edgeDistances);
float4 signedOutsetsCW = fInvSinTheta * edgeDistances;
fX += signedOutsetsCW * next_cw(fDX) + signedOutsets * fDX;
```

关键: 使用 `1/sin(theta)` 系数确保移动距离正确。

### 退化处理

当四边形退化(边长为 0、角度接近 180°、内缩导致折叠)时,使用特殊算法:

1. **边缘方程法**: 计算边的交点作为新顶点
2. **距离检查**: 使用 `kDistTolerance = 1e-2f` 判断退化
3. **覆盖率估算**: 退化四边形返回估算的像素覆盖率

```cpp
float4 estimateCoverage(const float4& x2d, const float4& y2d) const {
    float4 w = max(0.f, min(1.f, d0 + d3));
    float4 h = max(0.f, min(1.f, d1 + d2));
    return w * h;  // 近似矩形面积
}
```

### 透视裁剪算法

对于透视四边形,需要裁剪到 `W >= kW0PlaneDistance` 的区域:

1. **计算交点**: 沿边缘线性插值找到 `W = kW0PlaneDistance` 的交点
2. **分类处理**:
   - 1 个顶点在后方: 产生五边形,拆分为两个四边形
   - 2-3 个顶点在后方: 替换为交点,仍为四边形
3. **处理退化**: 3 个顶点被裁剪时,复制交点避免产生三角形

### 数值稳定性技术

- **容差常量**: `kTolerance = 1e-9f` 用于除零检查
- **双精度中间值**: 边缘方程使用 double 计算再转换为 float
- **坐标裁剪**: 使用 `double_to_clamped_scalar` 防止坐标溢出
- **W 符号处理**: 当 W 变负时,翻转整个顶点坐标

```cpp
if (any(fW < 0.f)) {
    float4 scale = if_then_else(fW < 0.f, float4(-1.f), float4(1.f));
    fX *= scale; fY *= scale; fW *= scale;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrQuad` | 四边形数据结构 |
| `SkVx` | SIMD 向量化计算 |
| `SkPathPriv` | W 平面距离常量(`kW0PlaneDistance`) |
| `GrTypesPriv` | Ganesh 类型定义(`GrAAType`, `GrQuadAAFlags`) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `FillRectOp` | 矩形填充时的抗锯齿边缘计算 |
| `TextureOp` | 纹理绘制的四边形处理 |
| `GrQuadPerEdgeAA` | 每边抗锯齿的四边形渲染器 |
| `TessellateAtlasOp` | 图集镶嵌操作 |

## 设计模式与设计决策

### 命名空间组织

使用命名空间而非类,因为:
- 大部分函数是无状态的工具函数
- `TessellationHelper` 是唯一有状态的类,但也是 RAII 风格的临时对象
- 避免不必要的继承层次结构

### 惰性计算模式

`TessellationHelper` 采用惰性计算策略:

```cpp
const EdgeEquations& getEdgeEquations() {
    if (!fEdgeEquationsValid) {
        fEdgeEquations.reset(fEdgeVectors);
        fEdgeEquationsValid = true;
    }
    return fEdgeEquations;
}
```

优势:
- 避免不必要的计算(如只需 outset 不需要边缘方程)
- 缓存计算结果避免重复计算
- 允许相同边缘距离的 inset/outset 复用计算

### 分层抽象

模块分为三个抽象层次:

1. **底层**: `EdgeVectors`, `EdgeEquations`, `Vertices` - 数据结构和基础计算
2. **中层**: `TessellationHelper` - 组合底层结构提供高级操作
3. **顶层**: `ClipToW0`, `CropToRect` - 直接可用的几何操作

这种分层使得:
- 底层可以独立测试和优化
- 中层提供灵活的组合能力
- 顶层简化常见使用场景

### 输出参数模式

几何修改函数使用输出参数而非返回值:

```cpp
void inset(const float4& edgeDistances, GrQuad* deviceInset, GrQuad* localInset);
```

原因:
- 需要同时输出设备坐标和局部坐标两个四边形
- 允许原地修改(传入原始四边形指针)
- 避免大对象的值传递开销

## 性能考量

### SIMD 优化

- **向量化比率**: ~75% 的顶点操作使用 `float4` SIMD
- **消除分支**: 使用 `if_then_else` 替代条件分支,保持 SIMD 流水线
- **数据布局**: `Vertices` 结构使用 AoS(Array of Structures)布局,便于 SIMD 加载

### 预计算缓存

```cpp
struct EdgeVectors {
    float4 fInvLengths;  // 预计算的倒数,避免除法
    float4 fInvSinTheta; // 预计算的倒数,避免重复三角函数计算
};
```

这些预计算在 `reset()` 时一次性完成,后续 inset/outset 操作直接使用。

### 快速路径优化

```cpp
if (quadType == GrQuad::Type::kAxisAligned) {
    // 轴对齐四边形的快速路径
    float d = std::min(std::abs(quad.x(3) - quad.x(0)),
                      std::abs(quad.y(3) - quad.y(0)));
    return d < 1.f;
}
```

为常见的轴对齐矩形提供 O(1) 复杂度的实现,避免完整的边缘方程计算。

### 退化检测的性能平衡

退化检测引入了额外的分支,但避免了:
- 无效的 GPU 绘制调用
- 数值不稳定导致的渲染错误
- 后续管线中的异常处理开销

实测表明,退化情况虽然罕见但一旦发生代价高昂,提前检测是值得的。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/geometry/GrQuad.h` | 紧密耦合 | 四边形数据结构定义 |
| `src/gpu/ganesh/ops/QuadPerEdgeAA.h` | 被使用 | 每边 AA 的实现 |
| `src/gpu/ganesh/ops/FillRectOp.cpp` | 被使用 | 矩形填充操作 |
| `src/gpu/ganesh/ops/TextureOp.cpp` | 被使用 | 纹理绘制操作 |
| `tests/QuadPerEdgeAATest.cpp` | 测试 | 单元测试用例 |
| `src/base/SkVx.h` | 依赖 | SIMD 向量类型 |
