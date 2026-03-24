# DynamicInstancesPatchAllocator - 动态实例补丁分配器

> 源文件: `src/gpu/graphite/render/DynamicInstancesPatchAllocator.h`

## 概述

`DynamicInstancesPatchAllocator` 是 Skia Graphite 中连接曲线细分系统（Tessellation）与绘制写入器（DrawWriter）的适配器类。它实现了 `skgpu::tess::PatchWriter` 所需的 `PatchAllocator` 模板接口，将补丁（Patch）数据通过 `DrawWriter::DynamicInstances` 写入 GPU 缓冲区。该类负责根据曲线的线性容差（Linear Tolerance）动态确定每个补丁所需的固定计数顶点数。

## 架构位置

```
曲线细分与渲染流程
  ├── PatchWriter (曲线补丁生成器)
  │     └── PatchAllocator 接口
  │           └── DynamicInstancesPatchAllocator (本文件 - 适配器)
  │                 └── DrawWriter::DynamicInstances (实例写入)
  ├── FixedCountVariant (顶点计数策略)
  │     ├── FixedCountCurves
  │     ├── FixedCountWedges
  │     └── FixedCountStrokes
  └── DrawWriter (GPU 缓冲区写入)
```

## 主要类与结构体

### `DynamicInstancesPatchAllocator<FixedCountVariant>`

模板类，`FixedCountVariant` 参数指定固定计数变体策略类：

| FixedCountVariant | 说明 |
|-------------------|------|
| `FixedCountCurves` | 曲线补丁的顶点计数 |
| `FixedCountWedges` | 扇形补丁的顶点计数 |
| `FixedCountStrokes` | 描边补丁的顶点计数 |

### `LinearToleranceProxy` (内部)

代理类型，将 `tess::LinearTolerances` 转换为 `uint32_t` 顶点计数：

```cpp
struct LinearToleranceProxy {
    operator uint32_t() const { return FixedCountVariant::VertexCount(fTolerances); }
    void operator <<(const tess::LinearTolerances& t) { fTolerances.accumulate(t); }
    tess::LinearTolerances fTolerances;
};
```

## 公共 API 函数

### 构造函数

```cpp
DynamicInstancesPatchAllocator(
    size_t stride,                      // 每实例数据步长（由 PatchWriter 提供）
    DrawWriter& writer,                 // 目标绘制写入器
    BindBufferInfo fixedVertexBuffer,   // 实例模板的固定顶点缓冲区
    BindBufferInfo fixedIndexBuffer,    // 实例模板的固定索引缓冲区
    unsigned int reserveCount           // 预分配的实例数量
);
```

### append 方法

```cpp
VertexWriter append(const tess::LinearTolerances& tolerances);
```

追加一个补丁实例，返回用于写入实例数据的 `VertexWriter`。`tolerances` 参数提供曲线的线性容差信息，用于累积并最终确定最大顶点计数。

## 内部实现细节

### LinearToleranceProxy 机制

`DrawWriter::DynamicInstances` 需要一个可转换为 `uint32_t` 的类型来确定绘制的顶点计数。`LinearToleranceProxy` 通过两个运算符实现此桥接：

1. **`operator <<`**: 累积线性容差值（每次 `append()` 调用时触发）
2. **`operator uint32_t()`**: 根据累积的容差计算所需的顶点数

`FixedCountVariant::VertexCount(tolerances)` 静态方法根据容差值确定离散化曲线所需的最小顶点数。容差值越大（曲线越复杂），需要的顶点越多。

### 断言检查

构造函数中 `SkASSERT(stride == writer.appendStride())` 确保 PatchWriter 期望的步长与 DrawWriter 的实际步长一致，防止缓冲区布局不匹配。

### 预分配策略

`fInstances.reserve(reserveCount)` 在构造时预分配空间。源码注释提出了一个待讨论的问题：预分配耗尽后是否值得重新分配较大的块，还是逐个追加即可（因为底层来自大型顶点缓冲区分配）。

## 依赖关系

- **src/gpu/BufferWriter.h**: `VertexWriter` 类型
- **src/gpu/graphite/DrawWriter.h**: `DrawWriter` 和 `DrawWriter::DynamicInstances`
- **src/gpu/tessellate/LinearTolerances.h**: `tess::LinearTolerances` 类型

## 设计模式与设计决策

### 适配器模式（Adapter Pattern）

这是经典的适配器模式应用。`PatchWriter` 需要的 `PatchAllocator` 接口（`append()` 方法）与 `DrawWriter::DynamicInstances` 的 API 不完全匹配。`DynamicInstancesPatchAllocator` 在两者之间提供适配层，将容差信息转换为顶点计数。

### 模板策略模式

`FixedCountVariant` 模板参数实现了策略模式——不同的曲线类型（曲线、扇形、描边）使用不同的顶点计数计算策略，但分配器的整体逻辑保持不变。

### 代理类型转换

`LinearToleranceProxy` 的设计巧妙地利用了 C++ 的隐式转换和运算符重载，将容差累积和顶点计数计算无缝集成到 `DynamicInstances` 的模板框架中。

## 性能考量

- 预分配减少了多次小型缓冲区分配的开销
- `LinearToleranceProxy` 在每次 `append()` 时累积容差，最终只计算一次顶点数
- 固定计数渲染避免了动态细分的 GPU 端开销，用顶点过量换取简单性
- 类本身为栈分配的轻量对象，无堆分配
- `VertexWriter` 返回值提供无拷贝的直接缓冲区写入

## 相关文件

- `src/gpu/graphite/DrawWriter.h` - DrawWriter 和 DynamicInstances
- `src/gpu/tessellate/PatchWriter.h` - 补丁写入器（使用此分配器）
- `src/gpu/tessellate/LinearTolerances.h` - 线性容差计算
- `src/gpu/tessellate/FixedCountBufferUtils.h` - FixedCountCurves/Wedges/Strokes
- `src/gpu/graphite/render/TessellateCurvesRenderStep.cpp` - 使用此分配器的具体渲染步骤
