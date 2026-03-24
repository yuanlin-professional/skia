# GrMeshDrawTarget

> 源文件
> - src/gpu/ganesh/GrMeshDrawTarget.h
> - src/gpu/ganesh/GrMeshDrawTarget.cpp

## 概述

`GrMeshDrawTarget` 是 Ganesh GPU 后端中的抽象接口，为创建顶点、索引、网格以及调用 GPU 绘制操作提供统一的抽象层。它定义了 Op（操作）在准备和执行绘制时需要的所有资源分配和状态访问方法。该接口隐藏了底层缓冲区管理和 GPU 资源的复杂性，为各种绘制操作提供清晰、类型安全的 API。主要实现类是 `GrOpFlushState`。

## 架构位置

`GrMeshDrawTarget` 位于 Ganesh 渲染管线的中间层，作为 Op 和底层资源管理之间的抽象接口：

```
GrOp (各种绘制操作)
    │
    └── GrMeshDrawTarget (抽象接口)
        │
        └── GrOpFlushState (具体实现)
            ├── GrVertexBufferAllocPool (顶点缓冲池)
            ├── GrIndexBufferAllocPool (索引缓冲池)
            ├── GrDrawIndirectBufferAllocPool (间接绘制缓冲池)
            ├── GrResourceProvider (资源提供者)
            └── GrDeferredUploadTarget (延迟上传)
```

它通过纯虚接口将 Op 的准备逻辑与具体的资源管理实现解耦。

## 主要类与结构体

### GrMeshDrawTarget

抽象基类，定义网格绘制目标的接口。

**继承关系**
- 基类：无
- 子类：`GrOpFlushState`（主要实现）

**接口方法分类**

#### 绘制记录
- `recordDraw()` - 记录网格绘制

#### 缓冲区分配
- `makeVertexSpace()` - 分配顶点空间
- `makeIndexSpace()` - 分配索引空间
- `makeVertexSpaceAtLeast()` - 分配至少指定大小的顶点空间
- `makeIndexSpaceAtLeast()` - 分配至少指定大小的索引空间
- `makeDrawIndirectSpace()` - 分配间接绘制空间
- `makeDrawIndexedIndirectSpace()` - 分配索引间接绘制空间

#### 缓冲区回收
- `putBackIndices()` - 归还索引
- `putBackVertices()` - 归还顶点
- `putBackIndirectDraws()` - 归还间接绘制
- `putBackIndexedIndirectDraws()` - 归还索引间接绘制

#### 状态访问
- `rtProxy()` - 获取渲染目标代理
- `writeView()` - 获取写入视图
- `appliedClip()` - 获取应用的裁剪
- `detachAppliedClip()` - 分离应用的裁剪
- `dstProxyView()` - 获取目标代理视图
- `usesMSAASurface()` - 是否使用 MSAA 表面
- `renderPassBarriers()` - 获取渲染通道屏障
- `colorLoadOp()` - 获取颜色加载操作

#### 资源访问
- `threadSafeCache()` - 获取线程安全缓存
- `resourceProvider()` - 获取资源提供者
- `strikeCache()` - 获取字形缓存
- `atlasManager()` - 获取图集管理器
- `smallPathAtlasManager()` - 获取小路径图集管理器
- `sampledProxyArray()` - 获取采样代理数组
- `caps()` - 获取 GPU 能力
- `deferredUploadTarget()` - 获取延迟上传目标
- `allocator()` - 获取内存分配器

#### 辅助方法
- `allocMesh()` - 分配单个网格
- `allocMeshes()` - 分配网格数组
- `allocPrimProcProxyPtrs()` - 分配图元处理器代理指针数组

## 公共 API 函数

### 绘制记录

| 函数签名 | 说明 |
|----------|------|
| `virtual void recordDraw(const GrGeometryProcessor*, const GrSimpleMesh[], int meshCnt, const GrSurfaceProxy* const primProcProxies[], GrPrimitiveType) = 0` | 记录网格绘制，primProcProxies 必须有 numTextureSamplers() 个条目 |
| `void recordDraw(const GrGeometryProcessor* gp, const GrSimpleMesh meshes[], int meshCnt, GrPrimitiveType primitiveType)` | 无纹理的绘制记录辅助方法 |

### 顶点缓冲区分配

| 函数签名 | 说明 |
|----------|------|
| `virtual void* makeVertexSpace(size_t vertexSize, int vertexCount, sk_sp<const GrBuffer>*, int* startVertex) = 0` | 分配顶点空间，返回写入指针 |
| `virtual void* makeVertexSpaceAtLeast(size_t vertexSize, int minVertexCount, int fallbackVertexCount, sk_sp<const GrBuffer>*, int* startVertex, int* actualVertexCount) = 0` | 分配至少 minVertexCount 的顶点空间，可能分配更多 |
| `skgpu::VertexWriter makeVertexWriter(size_t vertexSize, int vertexCount, sk_sp<const GrBuffer>*, int* startVertex)` | 返回 VertexWriter 的便利方法 |
| `skgpu::VertexWriter makeVertexWriterAtLeast(size_t vertexSize, int minVertexCount, int fallbackVertexCount, sk_sp<const GrBuffer>*, int* startVertex, int* actualVertexCount)` | 返回 VertexWriter 的至少版本 |

### 索引缓冲区分配

| 函数签名 | 说明 |
|----------|------|
| `virtual uint16_t* makeIndexSpace(int indexCount, sk_sp<const GrBuffer>*, int* startIndex) = 0` | 分配索引空间，返回写入指针 |
| `virtual uint16_t* makeIndexSpaceAtLeast(int minIndexCount, int fallbackIndexCount, sk_sp<const GrBuffer>*, int* startIndex, int* actualIndexCount) = 0` | 分配至少 minIndexCount 的索引空间 |

### 间接绘制缓冲区分配

| 函数签名 | 说明 |
|----------|------|
| `virtual GrDrawIndirectWriter makeDrawIndirectSpace(int drawCount, sk_sp<const GrBuffer>* buffer, size_t* offsetInBytes) = 0` | 分配间接绘制命令空间 |
| `virtual GrDrawIndexedIndirectWriter makeDrawIndexedIndirectSpace(int drawCount, sk_sp<const GrBuffer>*, size_t* offsetInBytes) = 0` | 分配索引间接绘制命令空间 |

### 缓冲区回收

| 函数签名 | 说明 |
|----------|------|
| `virtual void putBackIndices(int indices) = 0` | 归还过度分配的索引 |
| `virtual void putBackVertices(int vertices, size_t vertexStride) = 0` | 归还过度分配的顶点 |
| `virtual void putBackIndirectDraws(int count) = 0` | 归还间接绘制 |
| `virtual void putBackIndexedIndirectDraws(int count) = 0` | 归还索引间接绘制 |

### 内存分配辅助

| 函数签名 | 说明 |
|----------|------|
| `GrSimpleMesh* allocMesh()` | 从 allocator 分配单个网格 |
| `GrSimpleMesh* allocMeshes(int n)` | 从 allocator 分配 n 个网格 |
| `const GrSurfaceProxy** allocPrimProcProxyPtrs(int n)` | 分配代理指针数组 |

### 状态访问

| 函数签名 | 说明 |
|----------|------|
| `virtual GrRenderTargetProxy* rtProxy() const = 0` | 获取渲染目标代理 |
| `virtual const GrSurfaceProxyView& writeView() const = 0` | 获取写入视图 |
| `virtual const GrAppliedClip* appliedClip() const = 0` | 获取应用的裁剪 |
| `virtual GrAppliedClip detachAppliedClip() = 0` | 分离并获取裁剪 |
| `virtual const GrDstProxyView& dstProxyView() const = 0` | 获取目标视图 |
| `virtual bool usesMSAASurface() const = 0` | 是否使用 MSAA |
| `virtual GrXferBarrierFlags renderPassBarriers() const = 0` | 获取屏障标志 |
| `virtual GrLoadOp colorLoadOp() const = 0` | 获取颜色加载操作 |

### 资源访问

| 函数签名 | 说明 |
|----------|------|
| `virtual GrThreadSafeCache* threadSafeCache() const = 0` | 获取线程安全缓存 |
| `virtual GrResourceProvider* resourceProvider() const = 0` | 获取资源提供者 |
| `uint32_t contextUniqueID() const` | 获取上下文唯一 ID |
| `virtual sktext::gpu::StrikeCache* strikeCache() const = 0` | 获取字形缓存 |
| `virtual GrAtlasManager* atlasManager() const = 0` | 获取图集管理器 |
| `virtual skgpu::ganesh::SmallPathAtlasMgr* smallPathAtlasManager() const = 0` | 获取小路径图集管理器（非大小优化构建） |
| `virtual skia_private::TArray<GrSurfaceProxy*, true>* sampledProxyArray() = 0` | 获取采样代理数组，用于记录额外的代理依赖 |
| `virtual const GrCaps& caps() const = 0` | 获取 GPU 能力 |
| `virtual GrDeferredUploadTarget* deferredUploadTarget() = 0` | 获取延迟上传目标 |
| `virtual SkArenaAlloc* allocator() = 0` | 获取内存分配器 |

## 内部实现细节

### VertexWriter 辅助函数

实现文件提供了两个便利方法，将原始指针包装为 `skgpu::VertexWriter`：

```cpp
template<typename W>
static W make_writer(void* p, int count, size_t elementSize) {
    // 如果 p 非空，假设分配已验证，计算字节大小是安全的
    return p ? W{p, count * elementSize} : W{};
}

skgpu::VertexWriter GrMeshDrawTarget::makeVertexWriter(
        size_t vertexSize, int vertexCount,
        sk_sp<const GrBuffer>* buffer, int* startVertex) {
    void* p = this->makeVertexSpace(vertexSize, vertexCount, buffer, startVertex);
    return make_writer<skgpu::VertexWriter>(p, vertexCount, vertexSize);
}
```

关键特性：
- 如果分配失败（p 为 null），返回空的 `VertexWriter`
- 自动计算总字节大小
- 类型安全的封装

### 上下文 ID 访问

`contextUniqueID()` 通过资源提供者获取上下文 ID：

```cpp
uint32_t GrMeshDrawTarget::contextUniqueID() const {
    return this->resourceProvider()->contextUniqueID();
}
```

这是唯一的非虚方法实现，作为便利方法避免重复代码。

### 零纹理绘制辅助

提供重载的 `recordDraw` 方法简化无纹理采样的情况：

```cpp
void recordDraw(const GrGeometryProcessor* gp,
                const GrSimpleMesh meshes[],
                int meshCnt,
                GrPrimitiveType primitiveType) {
    this->recordDraw(gp, meshes, meshCnt, nullptr, primitiveType);
}
```

### 内存分配辅助实现

`allocMesh()` 等方法直接委托给 allocator：

```cpp
GrSimpleMesh* allocMesh() {
    return this->allocator()->make<GrSimpleMesh>();
}

GrSimpleMesh* allocMeshes(int n) {
    return this->allocator()->makeArray<GrSimpleMesh>(n);
}
```

这些内联方法避免了 Op 直接访问 allocator 的重复代码。

## 依赖关系

### 依赖的模块

| 模块名 | 用途 |
|--------|------|
| `GrBuffer` | 缓冲区基类 |
| `GrSimpleMesh` | 网格数据结构 |
| `GrGeometryProcessor` | 几何处理器 |
| `GrSurfaceProxy` | 表面代理 |
| `GrSurfaceProxyView` | 表面视图 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrAppliedClip` | 应用的裁剪 |
| `GrDstProxyView` | 目标代理视图 |
| `GrDrawIndirectCommand` | 间接绘制命令 |
| `GrResourceProvider` | 资源提供者 |
| `GrCaps` | GPU 能力 |
| `GrDeferredUploadTarget` | 延迟上传 |
| `GrThreadSafeCache` | 线程安全缓存 |
| `GrAtlasManager` | 图集管理 |
| `skgpu::ganesh::SmallPathAtlasMgr` | 小路径图集 |
| `sktext::gpu::StrikeCache` | 字形缓存 |
| `SkArenaAlloc` | Arena 分配器 |
| `skgpu::VertexWriter` | 顶点写入器 |
| `skgpu::IndexWriter` | 索引写入器 |

### 被依赖的模块

| 模块名 | 使用方式 |
|--------|----------|
| `GrOp` 及其子类 | 通过接口准备和记录绘制 |
| `GrDrawOp` | 主要使用者，各种绘制操作 |
| `GrMeshDrawOp` | 专门用于网格绘制的 Op |
| `GrOpFlushState` | 主要实现类 |

## 设计模式与设计决策

### 接口隔离原则（Interface Segregation Principle）

`GrMeshDrawTarget` 定义了 Op 在准备绘制时需要的最小接口集合，不包含执行相关的方法（那些在 `GrOpsRenderPass` 中）。

### 依赖反转原则（Dependency Inversion Principle）

高层模块（`GrOp`）依赖抽象接口（`GrMeshDrawTarget`），而不是具体实现（`GrOpFlushState`）。这允许：
- 测试时使用 mock 实现
- 未来可能的其他实现
- 清晰的职责分离

### 模板方法模式的变体

接口定义了绘制准备的"算法骨架"：
1. 分配缓冲区（`makeVertexSpace`/`makeIndexSpace`）
2. 填充数据（Op 的责任）
3. 记录绘制（`recordDraw`）
4. 可选的归还未使用空间（`putBackVertices`/`putBackIndices`）

### 资源管理的 RAII 思想

虽然接口本身不直接使用 RAII，但设计鼓励 Op 使用 RAII 模式：
- 分配返回智能指针和偏移量
- 归还方法允许清理过度分配

### 分配和回收的对称性

每种分配方法都有对应的回收方法：
- `makeVertexSpace` ↔ `putBackVertices`
- `makeIndexSpace` ↔ `putBackIndices`
- `makeDrawIndirectSpace` ↔ `putBackIndirectDraws`
- `makeDrawIndexedIndirectSpace` ↔ `putBackIndexedIndirectDraws`

这种对称性使资源管理更清晰。

### 至少分配策略

`makeVertexSpaceAtLeast` 和 `makeIndexSpaceAtLeast` 支持过度分配：

```cpp
virtual void* makeVertexSpaceAtLeast(size_t vertexSize,
                                     int minVertexCount,
                                     int fallbackVertexCount,
                                     sk_sp<const GrBuffer>*,
                                     int* startVertex,
                                     int* actualVertexCount) = 0;
```

参数说明：
- `minVertexCount`：最少需要的数量
- `fallbackVertexCount`：如果需要新缓冲区，分配这么多
- `actualVertexCount`：实际可用的数量（可能大于 min）

这种设计允许 Op 利用缓冲区池中的剩余空间，减少分配次数。

### 纯虚析构函数

声明虚析构函数确保通过基类指针删除时正确调用子类析构：

```cpp
virtual ~GrMeshDrawTarget() {}
```

### 便利方法分层

接口包含三层方法：
1. **核心虚方法**：必须由子类实现
2. **便利重载**：简化常见用例（如无纹理的 `recordDraw`）
3. **辅助方法**：包装和类型转换（如 `makeVertexWriter`）

这种分层提供灵活性同时保持易用性。

### 代理数组的特殊处理

`sampledProxyArray()` 提供特殊机制让 Op 报告额外的代理依赖：

```cpp
// This should be called during onPrepare of a GrOp. The caller should add any proxies
// to the array it will use that it did not access during a call to visitProxies.
// This is usually the case for atlases.
virtual skia_private::TArray<GrSurfaceProxy*, true>* sampledProxyArray() = 0;
```

这是针对图集等动态依赖的特殊设计，因为图集在 `visitProxies` 时可能还未创建。

## 性能考量

### 缓冲区池化

接口设计支持缓冲区池实现：
- `makeVertexSpace` 可以从池中分配
- `putBackVertices` 允许归还到池
- 减少系统调用和驱动开销

### 过度分配优化

"AtLeast" 系列方法支持过度分配策略：
- 利用池中的剩余空间
- 减少分配次数
- 可能避免缓冲区碎片

### Arena 分配

`allocMesh()` 等方法使用 arena 分配器：
- 避免逐个对象的堆分配
- 更好的缓存局部性
- 批量释放，无需逐个析构

### VertexWriter 类型安全

`makeVertexWriter` 返回类型安全的写入器：
- 编译时检查越界写入
- 内联的辅助方法（如 `write<T>()`）
- 零运行时开销的抽象

### 间接绘制支持

`makeDrawIndirectSpace` 和 `makeDrawIndexedIndirectSpace` 支持现代 GPU 的间接绘制：
- 减少 CPU-GPU 同步
- 支持 GPU 驱动的渲染
- 批量绘制命令

### 内联便利方法

便利方法如 `allocMesh()` 在头文件中内联：

```cpp
GrSimpleMesh* allocMesh() { return this->allocator()->make<GrSimpleMesh>(); }
```

编译器可以完全内联这些调用，消除函数调用开销。

### 最小虚函数开销

虽然接口包含多个虚方法，但：
- 通常通过具体类型（`GrOpFlushState`）调用，编译器可以去虚化
- 虚函数调用只在 Op 准备阶段，不在热循环中
- 相比灵活性，虚函数开销可以接受

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrOpFlushState.h/cpp` | 主要实现 | 实现接口的具体类 |
| `src/gpu/ganesh/GrOp.h` | 使用者 | Op 基类，使用接口准备绘制 |
| `src/gpu/ganesh/GrDrawOp.h` | 使用者 | 绘制 Op 基类 |
| `src/gpu/ganesh/GrSimpleMesh.h` | 数据结构 | 网格定义 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 依赖 | 几何处理器 |
| `src/gpu/ganesh/GrBuffer.h` | 依赖 | 缓冲区基类 |
| `src/gpu/ganesh/GrDrawIndirectCommand.h` | 数据结构 | 间接绘制命令 |
| `src/gpu/ganesh/GrAppliedClip.h` | 状态 | 裁剪状态 |
| `src/gpu/ganesh/GrDeferredUploadTarget.h` | 相关接口 | 延迟上传接口 |
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 资源提供者 |
| `src/gpu/BufferWriter.h` | 工具 | VertexWriter/IndexWriter 实现 |
| `src/base/SkArenaAlloc.h` | 工具 | Arena 分配器 |
