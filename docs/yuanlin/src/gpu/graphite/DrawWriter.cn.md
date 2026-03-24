# DrawWriter

> 源文件
> - src/gpu/graphite/DrawWriter.h
> - src/gpu/graphite/DrawWriter.cpp

## 概述

`DrawWriter` 是用于记录绘制调用的辅助类，它简化了动态顶点和实例数据的管理，特别是当绘制数量未知或数据需要在记录时计算的场景。该类自动处理缓冲区分配、数据映射和绘制命令的批处理，使调用者无需手动管理这些复杂的细节。

`DrawWriter` 支持多种绘制模式：简单绘制、索引绘制、实例化绘制和索引实例化绘制。它还提供了三个内部辅助类（`Vertices`、`Instances`、`DynamicInstances`）来以类型安全的方式追加动态数据。

## 主要类与结构体

### DrawWriter 类

```cpp
class DrawWriter {
public:
    DrawWriter(DrawPassCommands::List*, DrawBufferManager*);
    ~DrawWriter();

    // 刷新待处理绘制
    void flush();
    void newDynamicState();  // flush() 的可读性别名

    // 通知新管线状态
    void newPipelineState(PrimitiveType type,
                         size_t staticStride,
                         size_t appendStride,
                         SkEnumBitMask<RenderStateFlags> newRenderState,
                         BarrierType barrierType);

    // 内部辅助类
    class Vertices;             // 动态顶点数据
    class Instances;            // 固定数量的实例数据
    template<typename T> class DynamicInstances;  // 可变数量的实例数据
};
```

### Vertices 类

用于收集动态顶点数据：

```cpp
class Vertices {
public:
    Vertices(DrawWriter& writer);

    // 追加 n 个顶点，返回 VertexWriter
    VertexWriter append(unsigned int n);
};
```

**使用示例**：
```cpp
DrawWriter::Vertices verts{writer};
verts.append(3) << x1 << y1 << x2 << y2 << x3 << y3;
```

### Instances 类

用于收集固定顶点/索引数据的实例数据：

```cpp
class Instances {
public:
    // 实例化绘制（无索引）
    Instances(DrawWriter& writer,
             const BindBufferInfo& vertices,
             const BindBufferInfo& indices,  // 空表示无索引
             unsigned int vertexCount);

    // 追加 n 个实例，返回 VertexWriter
    VertexWriter append(unsigned int n);
};
```

**使用示例**：
```cpp
DrawWriter::Instances instances{writer, fixedVerts, {}, 6};
instances.append(10) << transform1 << color1 << transform2 << color2 << ...;
```

### DynamicInstances 类

用于可变顶点/索引数量的实例数据：

```cpp
template<typename VertexCountProxy>
class DynamicInstances {
public:
    DynamicInstances(DrawWriter& writer,
                    const BindBufferInfo& vertices,
                    const BindBufferInfo& indices);

    // 追加 n 个实例，使用代理对象计算最小顶点/索引数
    VertexWriter append(const VertexCountProxy& proxy, unsigned int n);
};
```

**VertexCountProxy 要求**：
- 默认构造函数
- `operator unsigned int()`：转换为实际顶点/索引数
- `operator<<(const V&)`：更新最坏情况

## 公共 API 函数

### newPipelineState

```cpp
void newPipelineState(PrimitiveType type,
                     size_t staticStride,
                     size_t appendStride,
                     SkEnumBitMask<RenderStateFlags> newRenderState,
                     BarrierType barrierType);
```

通知新管线需要绑定。参数：
- `type`：图元类型（三角形、线等）
- `staticStride`：静态顶点数据步长
- `appendStride`：追加数据（实例）步长
- `newRenderState`：渲染状态标志
- `barrierType`：绘制前需要的屏障类型

该方法会先 `flush()` 待处理绘制，然后更新内部状态。

### flush / newDynamicState

```cpp
void flush();
void newDynamicState();  // 等同于 flush()
```

发出待处理的绘制调用。`newDynamicState` 是 `flush` 的可读性别名，用于表示动态状态变化（如裁剪、uniform 绑定）。

## 内部实现细节

### 自动批处理

`DrawWriter` 自动将相邻的兼容绘制合并：
- 相同管线状态
- 相同动态状态（scissor、uniform、纹理）
- 连续的缓冲区数据

这减少了绘制调用数量，提高 GPU 效率。

### 缓冲区管理

通过 `DrawBufferManager` 管理缓冲区：
- 从当前缓冲区获取子范围
- 空间不足时分配新缓冲区
- 自动处理对齐要求

### 失败处理

`DrawWriter` 优雅处理缓冲区映射失败：
- 返回非空的 `VertexWriter`（指向临时存储）
- 在 `Recorder::snap()` 时丢弃失败的绘制
- 调用者无需额外的错误检查

### 对齐策略

`newPipelineState` 中的对齐逻辑：

```cpp
const uint32_t baseAlign = newRenderState & RenderStateFlags::kAppendVertices ?
    4 * fAppendStride : fAppendStride;
```

- **kAppendVertices 模式**：4 倍步长对齐（ARM 硬件要求）
- **其他模式**：步长对齐

### 屏障插入

如果 `barrierType != BarrierType::kNone`：
- 在首次绘制前插入 `AddBarrier` 命令
- 确保正确的内存同步（如高级混合）

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawPass.h/cpp` | 使用 DrawWriter 的上下文 |
| `src/gpu/graphite/DrawCommands.h` | 命令列表定义 |
| `src/gpu/graphite/BufferManager.h` | 缓冲区管理器 |
| `src/gpu/BufferWriter.h` | 顶点写入器 |
| `src/gpu/graphite/DrawTypes.h` | 绘制类型定义 |
| `src/gpu/graphite/ResourceTypes.h` | 资源类型定义 |
