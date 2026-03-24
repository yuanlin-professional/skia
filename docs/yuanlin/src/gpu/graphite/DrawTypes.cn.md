# DrawTypes

> 源文件
> - src/gpu/graphite/DrawTypes.h

## 概述

`DrawTypes.h` 定义了 Graphite 绘制系统使用的基础类型，包括图元类型、顶点属性类型、uniform 槽位、深度模板设置和渲染状态标志。这些类型是整个绘制管线的基础，被 `Renderer`、`RenderStep`、`DrawWriter` 等类广泛使用。

## 主要类型

### PrimitiveType 枚举

```cpp
enum class PrimitiveType : uint8_t {
    kTriangles,      // 三角形列表
    kTriangleStrip,  // 三角形带
    kPoints,         // 点精灵
};
```

### VertexAttribType 枚举

定义顶点属性数据类型：

```cpp
enum class VertexAttribType : uint8_t {
    kFloat, kFloat2, kFloat3, kFloat4,
    kHalf, kHalf2, kHalf4,
    kInt2, kInt3, kInt4,
    kUInt2,
    kByte, kByte2, kByte4,
    kUByte, kUByte2, kUByte4,
    kUByte_norm,  // [0, 255] → [0.0, 1.0]
    kUByte4_norm,
    kShort2, kShort4,
    kUShort2, kUShort2_norm,
    kInt, kUInt,
    kUShort_norm,
    kUShort4_norm,
};
```

**辅助函数**：
```cpp
constexpr size_t VertexAttribTypeSize(VertexAttribType type);
```

### UniformSlot 枚举

```cpp
enum class UniformSlot {
    kCombinedUniforms,  // 绘制和渲染步骤的组合 uniform
    kGradient           // 渐变存储缓冲区
};
```

### DepthStencilSettings

深度和模板测试的配置。

### RenderStateFlags 枚举

```cpp
enum class RenderStateFlags : uint32_t {
    kNone = 0,
    kAppendVertices = 1 << 0,  // 使用追加顶点数据
    // ... 其他标志
};
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/Renderer.h` | 使用这些类型定义渲染步骤 |
| `src/gpu/graphite/DrawWriter.h` | 使用图元和属性类型 |
| `src/gpu/graphite/PipelineData.h` | 管线数据收集 |
