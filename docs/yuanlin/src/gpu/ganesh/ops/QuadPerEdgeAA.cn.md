# QuadPerEdgeAA

> 源文件
> - `src/gpu/ganesh/ops/QuadPerEdgeAA.h`
> - `src/gpu/ganesh/ops/QuadPerEdgeAA.cpp`

## 概述

`QuadPerEdgeAA` 是 Ganesh GPU 后端中用于每边抗锯齿四边形渲染的核心模块。该模块提供了一套完整的工具和类，用于高效地渲染带有逐边抗锯齿的四边形，这是纹理绘制操作（TextureOp）的基础。

模块支持多种四边形类型（轴对齐、缩放平移、透视），以及不同的索引策略和颜色模式，能够在保证渲染质量的同时最大化GPU性能。

## 架构位置

```
skia/
  src/
    gpu/
      ganesh/
        ops/
          QuadPerEdgeAA/ (命名空间)
            ├── VertexSpec (顶点规格)
            ├── Tessellator (细分器)
            ├── 几何处理器工厂
            └── 索引缓冲区管理
```

它是纹理操作和矩形绘制的底层支撑。

## 主要类与结构体

### VertexSpec

顶点规格，描述四边形的顶点配置。

**关键成员（位域）：**

| 成员 | 位数 | 说明 |
|------|------|------|
| `fDeviceQuadType` | 2 | 设备四边形类型 |
| `fLocalQuadType` | 2 | 本地四边形类型 |
| `fIndexBufferOption` | 2 | 索引缓冲区选项 |
| `fHasLocalCoords` | 1 | 是否有本地坐标 |
| `fColorType` | 2 | 颜色类型 |
| `fHasSubset` | 1 | 是否有子集 |
| `fUsesCoverageAA` | 1 | 是否使用覆盖率抗锯齿 |
| `fCompatibleWithCoverageAsAlpha` | 1 | 是否兼容覆盖率作为Alpha |
| `fRequiresGeometrySubset` | 1 | 是否需要几何子集 |

### Tessellator

四边形细分器，将四边形数据写入顶点缓冲区。

**关键方法：**
```cpp
void append(
    GrQuad* deviceQuad,
    GrQuad* localQuad,
    const SkPMColor4f& color,
    const SkRect& uvSubset,
    GrQuadAAFlags aaFlags
)
```

### 枚举类型

```cpp
enum class CoverageMode {
    kNone,         // 无覆盖率
    kWithPosition, // 覆盖率在位置中
    kWithColor     // 覆盖率在颜色中
};

enum class ColorType {
    kNone,   // 无颜色
    kByte,   // 字节颜色
    kFloat,  // 浮点颜色
    kLast = kFloat
};

enum class IndexBufferOption {
    kPictureFramed,  // 图片帧：8顶点/四边形 + 索引
    kIndexedRects,   // 索引矩形：4顶点/四边形 + 索引
    kTriStrips,      // 三角带：4顶点/四边形，无索引
    kLast = kTriStrips
};
```

## 公共 API 函数

### 工厂方法

```cpp
GrGeometryProcessor* MakeProcessor(
    SkArenaAlloc* arena,
    const VertexSpec& spec
)
```
创建标准几何处理器。

```cpp
GrGeometryProcessor* MakeTexturedProcessor(
    SkArenaAlloc* arena,
    const VertexSpec& spec,
    const GrShaderCaps& shaderCaps,
    const GrBackendFormat& backendFormat,
    GrSamplerState samplerState,
    const skgpu::Swizzle& swizzle,
    sk_sp<GrColorSpaceXform> textureColorSpaceXform,
    Saturate saturate
)
```
创建带纹理的几何处理器。

### 索引管理

```cpp
sk_sp<const GrBuffer> GetIndexBuffer(
    GrMeshDrawTarget* target,
    IndexBufferOption indexBufferOption
)
```
获取适当的索引缓冲区。

```cpp
int QuadLimit(IndexBufferOption indexBufferOption)
```
返回索引选项支持的最大四边形数量。

### 绘制配置

```cpp
void IssueDraw(
    const GrCaps& caps,
    GrOpsRenderPass* renderPass,
    const VertexSpec& spec,
    int runningQuadCount,
    int quadCount,
    int maxVerts,
    int absVertBufferOffset
)
```
执行绘制调用。

### 工具函数

```cpp
IndexBufferOption CalcIndexBufferOption(
    GrAAType aaType,
    int numQuads
)
```
计算最佳索引缓冲区选项。

```cpp
ColorType MinColorType(SkPMColor4f color)
```
确定颜色的最小表示类型。

## 内部实现细节

### 顶点布局计算

```cpp
size_t VertexSpec::vertexSize() const {
    // 位置：2D 或 3D
    size_t size = this->deviceDimensionality() * sizeof(float);

    // 本地坐标
    if (fHasLocalCoords) {
        size += this->localDimensionality() * sizeof(float);
    }

    // 颜色
    switch (this->colorType()) {
        case ColorType::kByte:
            size += sizeof(uint32_t);
            break;
        case ColorType::kFloat:
            size += 4 * sizeof(float);
            break;
        default:
            break;
    }

    // 子集
    if (fHasSubset) {
        size += 4 * sizeof(float);
    }

    // 覆盖率AA
    if (fUsesCoverageAA) {
        size += 4 * sizeof(float);  // 边缘方程
    }

    return size;
}
```

### 抗锯齿实现

**每边AA的原理：**
1. 为每个四边形生成8个顶点（内圈4个，外圈4个）
2. 外圈顶点沿AA边缘向外延伸
3. 每个顶点携带边缘方程系数
4. 片段着色器根据距离边缘的位置计算覆盖率

```cpp
// 简化的边缘方程生成
float4 edgeEquation = compute_edge_equation(p0, p1);
```

### 索引策略选择

```cpp
IndexBufferOption CalcIndexBufferOption(GrAAType aaType, int numQuads) {
    if (GrAAType::kCoverage == aaType) {
        // AA需要8顶点布局
        return IndexBufferOption::kPictureFramed;
    } else if (numQuads > 1) {
        // 多个四边形使用索引
        return IndexBufferOption::kIndexedRects;
    } else {
        // 单个四边形使用三角带
        return IndexBufferOption::kTriStrips;
    }
}
```

### 写入优化

针对常见情况的特殊化写入路径：
- 轴对齐无AA：最快路径
- 缩放平移带AA：优化路径
- 通用透视：完整计算路径

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrGeometryProcessor` | 几何处理器基类 |
| `GrQuad` | 四边形表示 |
| `GrQuadUtils` | 四边形工具 |
| `TextureOp` | 纹理操作 |
| `GrSamplerState` | 采样状态 |
| `GrColorSpaceXform` | 颜色空间变换 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `TextureOp` | 主要使用者 |
| `FillRectOp` | 矩形填充操作 |
| 其他矩形操作 | 各种矩形绘制 |

## 设计模式与设计决策

### 策略模式

不同的索引策略封装为枚举：
- `kPictureFramed`：复杂AA
- `kIndexedRects`：批量矩形
- `kTriStrips`：单个四边形

### 紧凑位域设计

`VertexSpec` 使用位域压缩所有配置到13位。

### 特化写入路径

通过函数指针选择最优的写入函数。

## 性能考量

### 顶点数据最小化

- 字节颜色 vs 浮点颜色
- 2D vs 3D 坐标
- 按需子集和覆盖率

### 索引缓冲区复用

静态索引缓冲区在多次绘制间共享。

### 批处理优化

相同规格的四边形可以批量写入和绘制。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `TextureOp.h` | 使用者 | 纹理操作 |
| `GrQuad.h` | 依赖 | 四边形类 |
| `GrQuadUtils.h` | 依赖 | 四边形工具 |
| `FillRectOp.h` | 使用者 | 矩形填充 |
