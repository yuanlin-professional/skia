# GrDistanceFieldGenFromVector - 矢量路径距离场生成

> 源文件: `src/gpu/ganesh/GrDistanceFieldGenFromVector.h`, `src/gpu/ganesh/GrDistanceFieldGenFromVector.cpp`

## 概述

`GrDistanceFieldGenFromVector` 提供了从矢量路径（`SkPath`）生成有符号距离场（Signed Distance Field, SDF）的功能。距离场是一种将矢量图形转换为像素纹理的技术，其中每个像素存储到最近边缘的有符号距离。该技术主要用于 GPU 加速的文本渲染，允许在不同缩放级别下保持文本清晰度，同时避免传统位图文本在放大时的锯齿问题。

## 架构位置

```
文本渲染管线
    |
GrDistanceFieldGenFromVector (本文件 - SDF 生成)
    |
SkPath / SkGeometry (路径和几何工具)
    |
GrAtlasTextOp / GrDistanceFieldTextureEffect (GPU SDF 渲染)
```

该模块位于 Ganesh 文本渲染管线中，由 ARM 贡献（2017年），条件编译在 `SK_ENABLE_OPTIMIZE_SIZE` 未定义时启用。

## 主要类与结构体

### `DPoint` (内部)

双精度浮点点结构体，用于高精度距离计算。提供 `distanceSquared` 和 `distance` 方法。

### `DAffineMatrix` (内部)

双精度仿射变换矩阵（2x3），用于路径分段的高精度变换。

### `SegSide` 枚举 (内部)

```cpp
enum SegSide { kLeft_SegSide = -1, kOn_SegSide = 0, kRight_SegSide = 1, kNA_SegSide = 2 };
```

表示扫描线相对于路径段的方位，用于缠绕数（winding number）计算。

### `DFData` 结构体 (内部)

```cpp
struct DFData { float fDistSq; int fDeltaWindingScore; };
```

存储距离场中每个像素的距离平方和缠绕评分增量。

## 公共 API 函数

### `GrGenerateDistanceFieldFromPath()`

```cpp
bool GrGenerateDistanceFieldFromPath(unsigned char* distanceField,
                                      const SkPath& path, const SkMatrix& viewMatrix,
                                      int width, int height, size_t rowBytes);
```

从矢量路径生成距离场。调用者需预分配输出缓冲区（包含 `SkDistanceFieldGen.h` 中定义的边距）。变换矩阵用于将路径转换到距离场坐标空间。

### `IsDistanceFieldSupportedFillType()`

```cpp
inline bool IsDistanceFieldSupportedFillType(SkPathFillType fFillType);
```

检查填充类型是否支持距离场生成。仅支持 `kEvenOdd` 和 `kInverseEvenOdd`。

## 内部实现细节

### 算法概述

1. **路径分段**: 将 SkPath 的动词（move, line, quad, conic, cubic）解析为分段列表。
2. **变换**: 使用双精度仿射矩阵变换分段到距离场坐标空间。
3. **距离计算**: 对每个像素，计算到所有分段的最短距离。
4. **缠绕数**: 通过从左到右累加缠绕评分确定像素位于路径内部还是外部。
5. **符号确定**: 结合缠绕数和最短距离生成有符号距离值。

### 缠绕评分机制

代码注释详细解释了扫描线穿越路径段时的缠绕评分规则：
- 从右侧穿越到左侧：+1
- 从左侧穿越到右侧：-1
- 不穿越：0

### 精度策略

使用双精度 (`double`) 进行距离和变换计算，避免在复杂路径上出现浮点精度问题。最终结果转换回单精度存储。

## 依赖关系

- **上游依赖**: `SkPath`、`SkMatrix`、`SkGeometry`（贝塞尔曲线工具）、`GrPathUtils`。
- **内部依赖**: `SkDistanceFieldGen.h`（距离场生成通用工具）。
- **条件编译**: `SK_ENABLE_OPTIMIZE_SIZE` 时禁用（以减小二进制大小）。
- **被依赖**: Ganesh 文本渲染管线中的 SDF 文本功能。

## 设计模式与设计决策

1. **EvenOdd 限制**: 仅支持 EvenOdd 填充规则，简化了缠绕数计算。
2. **双精度计算**: 牺牲一些性能换取数值稳定性，适用于离线/半离线的纹理生成场景。
3. **条件编译**: 通过 `SK_ENABLE_OPTIMIZE_SIZE` 允许在尺寸敏感的构建中完全移除此功能。

## 性能考量

- 距离场生成是 CPU 密集型操作，通常在字形首次遇到时执行一次。
- 生成的距离场纹理被缓存在 GPU 图集中，后续绘制仅需纹理采样。
- 双精度计算比单精度慢，但距离场生成不在渲染热路径上。
- 输出的距离场支持 MipMap，在不同缩放级别下均能高效渲染。

## 相关文件

- `src/core/SkDistanceFieldGen.h` - 距离场生成通用工具
- `src/gpu/ganesh/geometry/GrPathUtils.h` - 路径工具
- `src/gpu/ganesh/ops/AtlasTextOp.h` - SDF 文本渲染 Op
- `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.h` - SDF 几何处理器
