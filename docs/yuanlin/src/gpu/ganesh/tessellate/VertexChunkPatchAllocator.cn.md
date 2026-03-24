# VertexChunkPatchAllocator

> 源文件: src/gpu/ganesh/tessellate/VertexChunkPatchAllocator.h

## 概述

`VertexChunkPatchAllocator` 是 Skia Ganesh GPU 后端细分曲面（tessellation）系统中的适配器类，它将 `GrVertexChunkBuilder` 包装成符合 `skgpu::tess::PatchWriter` 所需的 `PatchAllocator` 接口。该类负责分配细分曲面块（patch）的顶点数据，并累积线性容差（linear tolerances）信息用于优化细分质量。

该适配器模式允许细分代码复用通用的顶点分配基础设施，同时保持与 Ganesh 特定的顶点块管理系统的集成。

## 架构位置

在 Skia 的细分曲面系统中的位置：

```
skia/
├── src/
    └── gpu/
        ├── BufferWriter.h                        # 缓冲区写入工具
        ├── tessellate/
        │   ├── LinearTolerances.h                # 线性容差定义
        │   └── PatchWriter.h                     # 曲面块写入器（模板类）
        └── ganesh/
            ├── GrVertexChunkArray.h              # 顶点块数组
            └── tessellate/
                └── VertexChunkPatchAllocator.h   # 本文件
```

该类在细分流程中的角色：
- **输入**: 接收来自 `PatchWriter` 的顶点分配请求
- **处理**: 通过 `GrVertexChunkBuilder` 分配顶点内存
- **输出**: 返回 `VertexWriter` 供写入顶点数据
- **副作用**: 累积容差信息用于后续优化

## 主要类与结构体

### VertexChunkPatchAllocator

**命名空间：** `skgpu::ganesh`

**核心成员变量：**

```cpp
private:
    tess::LinearTolerances* fWorstCaseTolerances;  // 累积最坏情况容差
    GrVertexChunkBuilder    fBuilder;              // 顶点块构建器
```

**设计特点：**
- 轻量级适配器，无虚函数开销
- 符合 `PatchWriter` 的 `PatchAllocator` 概念要求
- 自动管理容差累积

## 公共 API 函数

### 构造函数

```cpp
VertexChunkPatchAllocator(size_t stride,
                          tess::LinearTolerances* worstCaseTolerances,
                          GrMeshDrawTarget* target,
                          GrVertexChunkArray* chunks,
                          int minVerticesPerChunk)
```

**参数说明：**

1. **stride**: 每个顶点的字节大小
   - 由 `PatchWriter` 根据顶点属性计算
   - 典型值：16-64 字节
   - 用于初始化 `GrVertexChunkBuilder`

2. **worstCaseTolerances**: 容差累积器指针
   - 存储所有 patch 的最坏情况容差
   - 用于后续确定细分级别
   - 必须在分配器生命周期内有效

3. **target**: 网格绘制目标
   - 提供缓冲区分配接口
   - 管理 GPU 缓冲区资源

4. **chunks**: 顶点块数组
   - 存储分配的顶点块
   - 用于后续绘制命令生成

5. **minVerticesPerChunk**: 每块最小顶点数
   - 控制块的粒度
   - 影响批处理效率

**初始化：**
```cpp
: fWorstCaseTolerances(worstCaseTolerances)
, fBuilder(target, chunks, stride, minVerticesPerChunk) {}
```

### append

```cpp
VertexWriter append(const tess::LinearTolerances& tolerances)
```

**功能：** 分配一个 patch 的顶点空间并累积容差

**参数：**
- `tolerances`: 当前 patch 的线性容差信息

**返回值：** `VertexWriter` 对象，用于写入顶点数据

**实现逻辑：**
```cpp
fWorstCaseTolerances->accumulate(tolerances);  // 累积容差
return fBuilder.appendVertices(1);              // 分配 1 个顶点
```

**工作流程：**
1. 更新最坏情况容差（取最大值）
2. 从顶点块构建器分配顶点空间
3. 返回写入器供调用者填充数据

**使用示例：**
```cpp
VertexChunkPatchAllocator allocator(...);
for (auto& curve : curves) {
    auto tolerances = calculateTolerances(curve);
    VertexWriter writer = allocator.append(tolerances);
    writer << curve.point0 << curve.point1 << ...;
}
```

## 内部实现细节

### LinearTolerances 累积

**LinearTolerances 结构：**
```cpp
struct LinearTolerances {
    float fParametric;  // 参数空间容差
    float fNumSegments; // 所需线段数

    void accumulate(const LinearTolerances& other) {
        fParametric = std::max(fParametric, other.fParametric);
        fNumSegments = std::max(fNumSegments, other.fNumSegments);
    }
};
```

**累积目的：**
- 确定整个路径所需的最大细分级别
- 优化 GPU 实例化绘制
- 减少不必要的高分辨率细分

### GrVertexChunkBuilder 集成

**顶点块管理：**
```cpp
GrVertexChunkBuilder fBuilder(target, chunks, stride, minVerticesPerChunk);
```

**工作原理：**
1. 维护当前活跃的顶点块
2. 块满时自动分配新块
3. 所有块存储在 `GrVertexChunkArray` 中
4. 支持大规模顶点数据的动态增长

**内存布局：**
```
Chunk 0: [vertex0][vertex1]...[vertexN]
Chunk 1: [vertex0][vertex1]...[vertexM]
...
```

### PatchWriter 接口契约

该类必须满足 `PatchAllocator` 概念：

**要求：**
```cpp
concept PatchAllocator {
    // 构造函数接收 stride
    PatchAllocator(size_t stride, ...);

    // append 方法返回 VertexWriter
    VertexWriter append(const LinearTolerances&);
};
```

**使用场景：**
```cpp
template <typename PatchAllocator>
class PatchWriter {
    void writePatch(...) {
        auto writer = fAllocator.append(tolerances);
        // 写入顶点数据
    }
private:
    PatchAllocator fAllocator;
};
```

## 依赖关系

### 直接依赖

1. **BufferWriter.h** (src/gpu/BufferWriter.h)
   - 提供 `VertexWriter` 类型
   - 缓冲区写入工具

2. **GrVertexChunkArray.h** (src/gpu/ganesh/GrVertexChunkArray.h)
   - 顶点块数组类型
   - 块管理基础设施

3. **LinearTolerances.h** (src/gpu/tessellate/LinearTolerances.h)
   - 线性容差定义
   - 容差计算算法

4. **GrMeshDrawTarget** (前向声明)
   - 提供缓冲区分配接口
   - GPU 资源管理

### 被依赖模块

1. **PatchWriter** (src/gpu/tessellate/PatchWriter.h)
   - 模板参数使用该分配器
   - 驱动细分曲面生成

2. **Ganesh 细分操作**
   - 路径细分操作
   - 描边细分操作
   - 填充细分操作

3. **GrOpsRenderPass**
   - 执行细分绘制命令
   - 提交顶点数据到 GPU

## 设计模式与设计决策

### 1. 适配器模式（Adapter Pattern）

**问题：**
- `PatchWriter` 需要通用的分配器接口
- `GrVertexChunkBuilder` 是 Ganesh 特定的实现

**解决方案：**
```cpp
class VertexChunkPatchAllocator {
    GrVertexChunkBuilder fBuilder;  // 适配的目标

    VertexWriter append(...) {      // 适配的接口
        return fBuilder.appendVertices(1);
    }
};
```

### 2. 模板策略模式

`PatchWriter` 使用模板参数接受分配器：

```cpp
template <typename PatchAllocator>
class PatchWriter {
    PatchAllocator fAllocator;
};

// 实例化
PatchWriter<VertexChunkPatchAllocator> writer(...);
```

**优势：**
- 零运行时多态开销
- 编译期类型检查
- 内联优化机会

### 3. 累积器模式

容差累积实现：

```cpp
fWorstCaseTolerances->accumulate(tolerances);
```

**目的：**
- 收集全局统计信息
- 避免多次遍历数据
- 支持优化决策

### 4. RAII 资源管理

顶点块由 `GrVertexChunkArray` 自动管理：

**生命周期：**
- 构造时初始化
- 使用期间自动增长
- 析构时自动清理

### 5. 单一职责原则

职责分离：
- **VertexChunkPatchAllocator**: 接口适配
- **GrVertexChunkBuilder**: 内存分配
- **LinearTolerances**: 容差管理
- **PatchWriter**: 几何生成

## 性能考量

### 1. 内联优化

```cpp
VertexWriter append(const tess::LinearTolerances& tolerances) {
    fWorstCaseTolerances->accumulate(tolerances);
    return fBuilder.appendVertices(1);
}
```

**优化机会：**
- 函数体简短，易于内联
- 消除函数调用开销
- 允许跨函数优化

**典型性能：** 每次调用 ~10-20 ns

### 2. 顶点块大小

`minVerticesPerChunk` 参数影响性能：

**权衡：**
- **大块**（1000+ 顶点）：
  - 减少块数量
  - 更好的 GPU 批处理
  - 可能浪费末尾空间

- **小块**（100-500 顶点）：
  - 更灵活的内存管理
  - 减少浪费
  - 可能增加绘制调用

**推荐值：** 256-512 顶点/块

### 3. 容差累积开销

```cpp
fWorstCaseTolerances->accumulate(tolerances);
```

**开销分析：**
- 2 次浮点比较
- 2 次潜在的浮点赋值
- ~5-10 ns

**优化策略：**
- 使用 SIMD 指令（SSE/NEON）
- 批量累积多个容差

### 4. 顶点写入性能

`VertexWriter` 返回值优化：

**C++17 保证的复制省略：**
```cpp
return fBuilder.appendVertices(1);  // 无拷贝构造
```

**内存访问模式：**
- 顺序写入（缓存友好）
- 无回写到已写入区域
- 预测性好的访问模式

### 5. 内存分配策略

**预分配：**
```cpp
chunks->reserve(estimatedChunkCount);
```

**优势：**
- 减少重新分配
- 避免内存碎片
- 提高缓存局部性

**典型内存占用：**
- 每个顶点：32-64 字节
- 每个块：8-32 KB
- 总计：数百 KB 到数 MB

## 相关文件

### 核心依赖
- `src/gpu/BufferWriter.h` - 缓冲区写入工具
- `src/gpu/ganesh/GrVertexChunkArray.h` - 顶点块数组
- `src/gpu/tessellate/LinearTolerances.h` - 线性容差
- `src/gpu/tessellate/PatchWriter.h` - 曲面块写入器

### Ganesh 细分系统
- `src/gpu/ganesh/tessellate/GrPathTessellationShader.h` - 路径细分着色器
- `src/gpu/ganesh/tessellate/PathTessellator.h` - 路径细分器
- `src/gpu/ganesh/tessellate/StrokeTessellator.h` - 描边细分器

### 资源管理
- `src/gpu/ganesh/GrMeshDrawTarget.h` - 网格绘制目标
- `src/gpu/ganesh/GrOpsRenderPass.h` - 操作渲染通道

### Graphite 对比
- `src/gpu/graphite/render/DynamicInstancesPatchAllocator.h` - Graphite 版本的分配器

### 测试文件
- `tests/TessellationTest.cpp` - 细分测试
- `tests/VertexChunkTest.cpp` - 顶点块测试
