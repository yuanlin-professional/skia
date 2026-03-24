# GrDrawIndirectCommand — GPU 间接绘制命令

> 源文件: `src/gpu/ganesh/GrDrawIndirectCommand.h`

## 概述

本文件定义了 GPU 间接绘制 (indirect draw) 所需的命令结构体和写入器。间接绘制是一种高级 GPU 技术，允许将绘制参数存储在 GPU 缓冲区中，由 GPU 直接读取这些参数来执行绘制调用，而无需 CPU 逐次发起绘制命令。文件包含两种命令结构体（非索引和索引）及其对应的写入器辅助类。

## 架构位置

```
GrOp (绘制操作)
    └── GrMeshDrawTarget (网格绘制目标)
        ├── makeDrawIndirectSpace() → GrDrawIndirectWriter
        └── makeDrawIndexedIndirectSpace() → GrDrawIndexedIndirectWriter
            └── GPU 间接绘制缓冲区
                ├── GrDrawIndirectCommand (非索引命令)
                └── GrDrawIndexedIndirectCommand (索引命令)
                    └── GPU 驱动执行 (glDrawArraysIndirect / vkCmdDrawIndirect 等)
```

## 主要类与结构体

### GrDrawIndirectCommand

非索引间接绘制命令，与 GPU API 标准布局兼容：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fVertexCount` | `uint32_t` | 每个实例的顶点数 |
| `fInstanceCount` | `uint32_t` | 实例数量 |
| `fBaseVertex` | `int32_t` | 第一个顶点的偏移（可为负值） |
| `fBaseInstance` | `uint32_t` | 第一个实例的偏移 |

大小：16 字节（通过 `static_assert` 严格验证紧凑打包）。

### GrDrawIndexedIndirectCommand

索引间接绘制命令：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fIndexCount` | `uint32_t` | 每个实例的索引数 |
| `fInstanceCount` | `uint32_t` | 实例数量 |
| `fBaseIndex` | `uint32_t` | 索引缓冲区中的起始索引 |
| `fBaseVertex` | `int32_t` | 添加到每个索引值上的顶点偏移 |
| `fBaseInstance` | `uint32_t` | 第一个实例的偏移 |

大小：20 字节（通过 `static_assert` 严格验证紧凑打包）。

### GrDrawIndirectWriter

非索引间接命令的写入器，提供流式写入接口：

| 方法 | 描述 |
|------|------|
| `GrDrawIndirectWriter(void*)` | 从原始内存指针构造 |
| `operator bool()` | 检查是否持有有效数据指针 |
| `makeOffset(int)` | 创建偏移后的写入器 |
| `write(instanceCount, baseInstance, vertexCount, baseVertex)` | 写入一条命令并自动推进指针 |

### GrDrawIndexedIndirectWriter

索引间接命令的写入器：

| 方法 | 描述 |
|------|------|
| `GrDrawIndexedIndirectWriter(void*)` | 从原始内存指针构造 |
| `operator bool()` | 检查是否持有有效数据指针 |
| `makeOffset(int)` | 创建偏移后的写入器 |
| `writeIndexed(indexCount, baseIndex, instanceCount, baseInstance, baseVertex)` | 写入一条索引命令并推进指针 |

## 公共 API 函数

两个写入器的核心方法：

```cpp
// 非索引写入
void GrDrawIndirectWriter::write(uint32_t instanceCount, uint32_t baseInstance,
                                  uint32_t vertexCount, int32_t baseVertex);

// 索引写入
void GrDrawIndexedIndirectWriter::writeIndexed(uint32_t indexCount, uint32_t baseIndex,
                                                uint32_t instanceCount, uint32_t baseInstance,
                                                int32_t baseVertex);
```

注意 `write()` 的参数顺序与 `GrDrawIndirectCommand` 的成员顺序不同——函数接受 `(instanceCount, baseInstance, vertexCount, baseVertex)` 但写入为 `{vertexCount, instanceCount, baseVertex, baseInstance}`，以匹配 GPU API 规范的布局。

## 内部实现细节

1. **紧凑打包验证**: 通过 `static_assert` 确保结构体大小精确匹配 GPU API 期望的布局（16 和 20 字节），无填充字节。

2. **仅移动语义**: 写入器类删除了拷贝操作，仅支持移动。移动后源对象的指针设为 null，防止对同一缓冲区的意外双重写入。

3. **流式写入**: `write()` / `writeIndexed()` 使用后自增操作 (`*fData++`)，自动推进写入位置，允许连续写入多条命令。

4. **makeOffset()**: 创建指向缓冲区特定偏移位置的新写入器，用于跳过已写入的命令。

## 依赖关系

- **`<cstdint>`**: 固定宽度整数类型
- **`<utility>`**: `std::move`

无其他 Skia 依赖，设计为最小化依赖的低级数据类型。

## 设计模式与设计决策

1. **GPU API 兼容布局**: 命令结构体的成员顺序和大小严格匹配 OpenGL (`glDrawArraysIndirect`)、Vulkan (`VkDrawIndirectCommand`) 和 Metal 的间接绘制命令格式，可直接写入 GPU 缓冲区无需转换。

2. **迭代器模式**: 写入器类似于前向迭代器，每次写入自动前进，简化了批量命令生成的代码。

3. **所有权转移**: 移动语义确保同一时间只有一个写入器指向缓冲区的特定位置，防止数据竞争。

4. **参数重排**: `write()` 方法有意将 `instanceCount` 放在第一个参数位置（而非结构体的 `vertexCount`），可能是因为在使用场景中实例信息通常先确定。

## 性能考量

- **零开销抽象**: 写入器的 `write()` 方法被标记为 `inline`，编译器可以将其优化为简单的内存写入和指针增量。
- **间接绘制优势**: 减少 CPU-GPU 同步点。多个绘制命令存储在单个 GPU 缓冲区中，GPU 一次性读取执行，显著降低驱动开销。
- **紧凑布局**: 无填充确保最小化 GPU 缓冲区内存使用和带宽消耗。
- **批量写入**: 流式写入模式使缓冲区写入具有良好的内存访问局部性（顺序写入）。

## 相关文件

- `src/gpu/ganesh/GrMeshDrawTarget.h` — 提供 makeDrawIndirectSpace 等分配方法
- `src/gpu/ganesh/GrOpsRenderPass.h` — 执行间接绘制调用
- `src/gpu/ganesh/ops/PathInnerTriangulateOp.cpp` — 使用间接绘制的路径操作
- `src/gpu/ganesh/GrBuffer.h` — GPU 缓冲区基类
