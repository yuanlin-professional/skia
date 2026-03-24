# DrawCommands

> 源文件
> - src/gpu/graphite/DrawCommands.h

## 概述

`DrawCommands.h` 定义了 `DrawPass` 使用的所有低级 GPU 命令类型。这些命令直接对应 GPU API（如 Vulkan、Metal、D3D12）的操作，包括绑定管线、绑定资源、设置状态和执行绘制调用。

该文件采用基于 SkRecords 的设计，使用宏系统定义命令类型列表，并通过模板元编程实现类型安全的命令序列化和反序列化。所有命令类型都是 POD（Plain Old Data），支持平凡复制和销毁。

## 架构位置

在 Graphite 渲染管线中的位置：

1. **DrawList/DrawListLayer** → 记录高层绘制操作
2. **DrawPass** → 生成 DrawPassCommands
3. **DrawPassCommands::List** → 存储命令序列
4. **CommandBuffer** → 将命令翻译为后端 API 调用
5. **GPU** → 实际执行

## 主要类与结构体

### 命令类型枚举

```cpp
namespace DrawPassCommands {

enum class Type {
    kBindGraphicsPipeline,
    kSetBlendConstants,
    kBindUniformBuffer,
    kBindStaticDataBuffer,
    kBindAppendDataBuffer,
    kBindIndirectBuffer,
    kBindIndexBuffer,
    kBindTexturesAndSamplers,
    kSetScissor,
    kDraw,
    kDrawIndexed,
    kDrawInstanced,
    kDrawIndexedInstanced,
    kDrawIndirect,
    kDrawIndexedIndirect,
    kAddBarrier
};

} // namespace DrawPassCommands
```

### 命令结构体

所有命令都定义在 `DrawPassCommands` 命名空间中：

#### BindGraphicsPipeline

```cpp
struct BindGraphicsPipeline {
    static constexpr Type kType = Type::kBindGraphicsPipeline;
    uint32_t fPipelineIndex;  // 管线缓存索引
};
```

绑定图形管线状态对象（PSO）。

#### SetBlendConstants

```cpp
struct SetBlendConstants {
    static constexpr Type kType = Type::kSetBlendConstants;
    std::array<float, 4> fBlendConstants;  // RGBA 混合常量
};
```

设置混合常量颜色（用于某些混合模式）。

#### BindUniformBuffer

```cpp
struct BindUniformBuffer {
    static constexpr Type kType = Type::kBindUniformBuffer;
    BindBufferInfo fInfo;  // 缓冲区、偏移、大小
    UniformSlot fSlot;     // 绑定槽位
};
```

绑定 uniform 缓冲区或存储缓冲区。

#### BindStaticDataBuffer

```cpp
struct BindStaticDataBuffer {
    static constexpr Type kType = Type::kBindStaticDataBuffer;
    BindBufferInfo fStaticData;  // 静态顶点数据
};
```

绑定静态顶点属性数据（如位置、纹理坐标）。

#### BindAppendDataBuffer

```cpp
struct BindAppendDataBuffer {
    static constexpr Type kType = Type::kBindAppendDataBuffer;
    BindBufferInfo fAppendData;  // 实例数据
};
```

绑定实例/追加属性数据（如变换矩阵、颜色）。

#### BindIndexBuffer

```cpp
struct BindIndexBuffer {
    static constexpr Type kType = Type::kBindIndexBuffer;
    BindBufferInfo fIndices;  // 索引数据
};
```

绑定索引缓冲区（用于索引绘制）。

#### BindIndirectBuffer

```cpp
struct BindIndirectBuffer {
    static constexpr Type kType = Type::kBindIndirectBuffer;
    BindBufferInfo fIndirect;  // 间接绘制参数
};
```

绑定间接绘制参数缓冲区。

#### BindTexturesAndSamplers

```cpp
struct BindTexturesAndSamplers {
    static constexpr Type kType = Type::kBindTexturesAndSamplers;
    int fNumTexSamplers;                        // 纹理/采样器数量
    PODArray<const TextureProxy*> fTextures;    // 纹理代理数组
    PODArray<SamplerDesc> fSamplers;            // 采样器描述数组
};
```

绑定纹理和采样器状态。`PODArray` 是轻量级指针包装器。

#### SetScissor

```cpp
struct SetScissor {
    static constexpr Type kType = Type::kSetScissor;
    Scissor fScissor;  // 裁剪矩形
};
```

设置裁剪矩形（像素坐标）。

#### Draw

```cpp
struct Draw {
    static constexpr Type kType = Type::kDraw;
    PrimitiveType fType;      // 图元类型（三角形、线等）
    uint32_t fBaseVertex;     // 起始顶点索引
    uint32_t fVertexCount;    // 顶点数量
};
```

非索引绘制调用。

#### DrawIndexed

```cpp
struct DrawIndexed {
    static constexpr Type kType = Type::kDrawIndexed;
    PrimitiveType fType;
    uint32_t fBaseIndex;      // 起始索引
    uint32_t fIndexCount;     // 索引数量
    uint32_t fBaseVertex;     // 顶点基址偏移
};
```

索引绘制调用。

#### DrawInstanced

```cpp
struct DrawInstanced {
    static constexpr Type kType = Type::kDrawInstanced;
    PrimitiveType fType;
    uint32_t fBaseVertex;
    uint32_t fVertexCount;
    uint32_t fBaseInstance;   // 起始实例索引
    uint32_t fInstanceCount;  // 实例数量
};
```

实例化绘制（非索引）。

#### DrawIndexedInstanced

```cpp
struct DrawIndexedInstanced {
    static constexpr Type kType = Type::kDrawIndexedInstanced;
    PrimitiveType fType;
    uint32_t fBaseIndex;
    uint32_t fIndexCount;
    uint32_t fBaseVertex;
    uint32_t fBaseInstance;
    uint32_t fInstanceCount;
};
```

实例化索引绘制。

#### DrawIndirect

```cpp
struct DrawIndirect {
    static constexpr Type kType = Type::kDrawIndirect;
    PrimitiveType fType;
};
```

间接绘制调用（参数从间接缓冲区读取）。

#### DrawIndexedIndirect

```cpp
struct DrawIndexedIndirect {
    static constexpr Type kType = Type::kDrawIndexedIndirect;
    PrimitiveType fType;
};
```

索引间接绘制调用。

#### AddBarrier

```cpp
struct AddBarrier {
    static constexpr Type kType = Type::kAddBarrier;
    BarrierType fType;  // 屏障类型
};
```

插入内存屏障（用于同步）。

### List 类

命令列表容器：

```cpp
class List {
public:
    List() = default;
    ~List() = default;

    int count() const;

    // 添加命令的便利方法
    void bindGraphicsPipeline(uint32_t pipelineIndex);
    void setBlendConstants(std::array<float, 4> blendConstants);
    void bindUniformBuffer(BindBufferInfo info, UniformSlot slot);
    std::pair<const TextureProxy**, SamplerDesc*>
        bindDeferredTexturesAndSamplers(int numTexSamplers);
    void setScissor(SkIRect scissor);
    void bindStaticDataBuffer(BindBufferInfo staticAttribs);
    void bindAppendDataBuffer(BindBufferInfo appendAttribs);
    void bindIndexBuffer(BindBufferInfo indices);
    void bindIndirectBuffer(BindBufferInfo indirect);
    void draw(PrimitiveType type, unsigned int baseVertex, unsigned int vertexCount);
    void drawIndexed(PrimitiveType type, unsigned int baseIndex,
                    unsigned int indexCount, unsigned int baseVertex);
    void drawInstanced(PrimitiveType type,
                      unsigned int baseVertex, unsigned int vertexCount,
                      unsigned int baseInstance, unsigned int instanceCount);
    void drawIndexedInstanced(PrimitiveType type,
                             unsigned int baseIndex, unsigned int indexCount,
                             unsigned int baseVertex, unsigned int baseInstance,
                             unsigned int instanceCount);
    void drawIndirect(PrimitiveType type);
    void drawIndexedIndirect(PrimitiveType type);
    void addBarrier(BarrierType type);

    // 迭代命令
    using Command = std::pair<Type, void*>;
    using Iter = SkTBlockList<Command, 16>::CIter;
    Iter commands() const;

private:
    template <typename T, typename... Args>
    void add(Args&&... args);

    SkTBlockList<Command, 16> fCommands{SkBlockAllocator::GrowthPolicy::kFibonacci};
    SkArenaAlloc fAlloc{256};  // 命令数据分配器
};
```

### PODArray 模板

轻量级数组包装器：

```cpp
template <typename T>
class PODArray {
public:
    PODArray() {}
    PODArray(T* ptr) : fPtr(ptr) {}

    operator T*() const { return fPtr; }
    T* operator->() const { return fPtr; }

private:
    T* fPtr;
};
```

不拥有内存，仅持有指针（数据由 `fAlloc` 管理）。

## 内部实现细节

### 宏驱动设计

使用 `SKGPU_DRAW_PASS_COMMAND_TYPES` 宏定义所有命令类型：

```cpp
#define SKGPU_DRAW_PASS_COMMAND_TYPES(M) \
    M(BindGraphicsPipeline)              \
    M(SetBlendConstants)                 \
    M(BindUniformBuffer)                 \
    // ...
```

这允许：
1. 自动生成 `Type` 枚举
2. 静态断言所有类型是 POD
3. 访问者模式遍历

### 命令存储

命令存储为 `(Type, void*)` 对：
- **Type**：命令类型枚举
- **void***：指向具体命令结构的指针（从 `fAlloc` 分配）

### 延迟纹理绑定

`bindDeferredTexturesAndSamplers` 的特殊设计：

```cpp
auto [textures, samplers] = list.bindDeferredTexturesAndSamplers(2);
textures[0] = myTexture1;
textures[1] = myTexture2;
samplers[0] = mySampler1;
samplers[1] = mySampler2;
```

先分配数组空间，返回指针给调用者填充。避免复制，提高效率。

### POD 约束

所有命令类型静态断言：

```cpp
static_assert(std::is_trivially_destructible<T>::value);
static_assert(std::is_trivially_copyable<T>::value);
```

确保可以安全地从 arena 分配器批量释放，无需析构函数调用。

## 依赖关系

**核心类型**：
- `CommandTypes.h`：`BindBufferInfo`、`Scissor` 等
- `ResourceTypes.h`：`PrimitiveType`、`BarrierType`、`UniformSlot` 等
- `TextureProxy.h`：纹理代理

**容器**：
- `src/base/SkArenaAlloc.h`：Arena 分配器
- `src/base/SkTBlockList.h`：块分配列表

## 设计模式与设计决策

### 1. 命令模式（Command Pattern）

每个命令都是一个对象，封装操作和参数：
- 延迟执行
- 支持记录和回放
- 可序列化（理论上）

### 2. 访问者模式（Visitor Pattern）

通过 `Type` 枚举和 `void*` 实现类型擦除的访问者：

```cpp
for (auto [type, cmd] : list.commands()) {
    switch (type) {
        case Type::kDraw:
            auto* draw = static_cast<Draw*>(cmd);
            // 处理 draw
            break;
        // ...
    }
}
```

### 3. 对象池（Arena 分配器）

`fAlloc` 提供快速分配和批量释放：
- 所有命令数据从同一 arena 分配
- 列表销毁时自动释放所有内存
- 无需单独 delete

### 4. 类型安全的宏编程

`COMMAND` 宏确保：
- 每个命令有唯一的 `kType` 常量
- 统一的结构定义
- 编译时类型检查

### 5. 延迟分配（Deferred Allocation）

`bindDeferredTexturesAndSamplers` 先分配空间，后填充数据：
- 避免临时对象
- 减少复制
- 提高缓存局部性

## 性能考量

### 内存布局

- **命令列表**：`SkTBlockList` 块分配，良好的缓存局部性
- **命令数据**：`SkArenaAlloc` 连续分配，减少碎片
- **POD 类型**：无虚表，最小内存开销

### 分配效率

- **批量分配**：Arena 一次性分配大块内存
- **无锁分配**：单线程访问，无同步开销
- **零碎片**：重置时整体释放

### 遍历性能

- **顺序访问**：块列表支持高效迭代
- **预测分支**：`switch` 语句通常有良好的分支预测
- **紧凑表示**：`(Type, void*)` 仅 16 字节（64 位系统）

### POD 优势

- **平凡复制**：可以使用 `memcpy` 批量复制
- **平凡析构**：无需逐个调用析构函数
- **简单布局**：编译器可以进行更积极的优化

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/DrawPass.h/cpp` | 使用命令列表的主要类 |
| `src/gpu/graphite/CommandBuffer.h` | 执行命令的后端接口 |
| `src/gpu/graphite/CommandTypes.h` | 命令相关类型定义 |
| `src/gpu/graphite/ResourceTypes.h` | 资源类型枚举 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/base/SkArenaAlloc.h` | Arena 分配器 |
| `src/base/SkTBlockList.h` | 块分配列表容器 |
| `src/gpu/graphite/mtl/MtlCommandBuffer.mm` | Metal 后端实现 |
| `src/gpu/graphite/vk/VulkanCommandBuffer.cpp` | Vulkan 后端实现 |
| `src/gpu/graphite/dawn/DawnCommandBuffer.cpp` | Dawn/WebGPU 后端实现 |
