# GrMockOpTarget

> 源文件
> - src/gpu/ganesh/mock/GrMockOpTarget.h

## 概述

`GrMockOpTarget` 是 Skia 图形库中用于测试的模拟绘制目标类,实现了 `GrMeshDrawTarget` 接口。它提供了预分配的 CPU 缓冲区来模拟 GPU 缓冲区分配操作,避免在单元测试中创建真实的 GPU 资源。该类主要用于测试渲染管线的几何数据处理逻辑,而无需真正提交到 GPU。

## 架构位置

`GrMockOpTarget` 位于 Skia 的 GPU Ganesh 测试框架中,是 Mock 后端的关键组件之一。

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrMeshDrawTarget    (网格绘制目标接口)
    └── mock/               (Mock测试后端)
        ├── GrMockGpu       (模拟GPU)
        ├── GrMockOpTarget  (模拟绘制目标) ← 当前类
        └── GrMockOpsRenderPass
```

## 主要类与结构体

### GrMockOpTarget

模拟绘制目标,用于单元测试的轻量级 `GrMeshDrawTarget` 实现。

**继承关系:**
- 基类: `GrMeshDrawTarget`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMockContext` | `sk_sp<GrDirectContext>` | Mock 渲染上下文引用 |
| `fStaticVertexData` | `char[6MB]` | 预分配的顶点数据缓冲区 |
| `fStaticVertexBuffer` | `sk_sp<GrGpuBuffer>` | 顶点缓冲区对象(不分配 GPU 内存) |
| `fStaticIndirectData` | `char[32 * sizeof(cmd)]` | 预分配的间接绘制命令缓冲区 |
| `fStaticIndirectBuffer` | `sk_sp<GrGpuBuffer>` | 间接绘制缓冲区对象 |
| `fAllocator` | `SkSTArenaAllocWithReset<1MB>` | 竞技场内存分配器 |
| `fDstProxyView` | `GrDstProxyView` | 目标代理视图(空实现) |

## 公共 API 函数

### 构造函数

```cpp
GrMockOpTarget(sk_sp<GrDirectContext> mockContext);
```
创建 Mock 绘制目标,关联到指定的 Mock 上下文。

### 能力查询方法

| 方法 | 返回值 | 说明 |
|-----|--------|------|
| `mockContext()` | `const GrDirectContext*` | 获取 Mock 上下文 |
| `caps()` | `const GrCaps&` | 获取设备能力 |
| `allocator()` | `SkArenaAlloc*` | 获取内存分配器 |

### 缓冲区分配方法

#### makeVertexSpace
```cpp
void* makeVertexSpace(size_t vertexSize, int vertexCount,
                      sk_sp<const GrBuffer>* buffer,
                      int* startVertex) override;
```
分配顶点数据空间,返回 CPU 缓冲区指针。

**实现特点:**
- 检查请求大小不超过 6MB 限制
- 返回预分配的 `fStaticVertexData` 指针
- 无真实 GPU 内存分配

#### makeVertexSpaceAtLeast
```cpp
void* makeVertexSpaceAtLeast(size_t vertexSize, int minVertexCount,
                             int fallbackVertexCount,
                             sk_sp<const GrBuffer>* buffer,
                             int* startVertex, int* actualVertexCount) override;
```
分配至少指定大小的顶点空间,返回实际可用数量。

#### makeDrawIndirectSpace
```cpp
GrDrawIndirectWriter makeDrawIndirectSpace(int drawCount,
                                           sk_sp<const GrBuffer>* buffer,
                                           size_t* offsetInBytes) override;
```
分配间接绘制命令空间。

#### makeDrawIndexedIndirectSpace
```cpp
GrDrawIndexedIndirectWriter makeDrawIndexedIndirectSpace(
    int drawCount, sk_sp<const GrBuffer>* buffer,
    size_t* offsetInBytes) override;
```
分配索引间接绘制命令空间。

### 测试辅助方法

```cpp
const void* peekStaticVertexData() const;
const void* peekStaticIndirectData() const;
void resetAllocator();
```
用于测试验证的数据访问和重置方法。

### 未实现方法(抛出异常)

以下方法通过 `SK_ABORT` 宏标记为未实现:

| 方法 | 用途 |
|-----|------|
| `recordDraw` | 记录绘制调用 |
| `makeIndexSpace` | 分配索引缓冲区 |
| `rtProxy` | 获取渲染目标代理 |
| `writeView` | 获取写入视图 |
| `strikeCache` | 获取字形缓存 |
| `atlasManager` | 获取图集管理器 |

## 内部实现细节

### 缓冲区容量管理

#### 顶点缓冲区
```cpp
char fStaticVertexData[6 * 1024 * 1024];  // 6MB 固定大小
```
如果请求超过容量,触发断言终止:
```cpp
if (vertexSize * vertexCount > sizeof(fStaticVertexData)) {
    SK_ABORT("FATAL: wanted %zu bytes; only have %zu.\n",
             vertexSize * vertexCount, sizeof(fStaticVertexData));
}
```

#### 间接绘制缓冲区
```cpp
char fStaticIndirectData[sizeof(GrDrawIndexedIndirectCommand) * 32];
```
支持最多 32 个间接绘制命令。

### 内存分配器

使用竞技场分配器避免频繁的堆分配:
```cpp
SkSTArenaAllocWithReset<1024 * 1024> fAllocator;  // 1MB 竞技场
```
测试可通过 `resetAllocator()` 重置分配器状态。

### 空操作实现

部分方法返回安全的默认值:
```cpp
GrAppliedClip detachAppliedClip() override {
    return GrAppliedClip::Disabled();  // 无裁剪
}
GrXferBarrierFlags renderPassBarriers() const override {
    return GrXferBarrierFlags::kNone;  // 无屏障
}
void putBackVertices(int vertices, size_t vertexStride) override {
    /* no-op */  // 不回收顶点
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrMeshDrawTarget` | 基类接口 |
| `GrDirectContext` | 渲染上下文 |
| `GrGpuBuffer` | GPU 缓冲区抽象 |
| `SkArenaAlloc` | 竞技场内存分配器 |
| `GrAppliedClip` | 裁剪状态 |
| `GrDstProxyView` | 目标视图 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| 单元测试 | 测试 GrOp 几何数据生成逻辑 |
| `GrMockGpu` | Mock GPU 创建绘制目标 |
| 管线测试 | 验证顶点/索引数据格式 |

## 设计模式与设计决策

### 静态缓冲区模式
使用固定大小的静态数组模拟 GPU 缓冲区,优点:
- **零开销:** 无动态内存分配
- **确定性:** 测试行为可预测
- **简单性:** 避免 GPU 资源管理复杂性

缺点:
- **容量限制:** 无法测试超大网格
- **不真实:** 与实际 GPU 行为有差异

### 明确失败策略
超出缓冲区容量时使用 `SK_ABORT` 立即终止,而非静默失败:
```cpp
SK_ABORT("FATAL: wanted %zu bytes of static vertex data; only have %zu.\n",
         vertexSize * vertexCount, sizeof(fStaticVertexData));
```
确保测试问题能被快速发现。

### 接口最小化
仅实现测试所需的核心方法,其他方法通过 `UNIMPL` 宏标记为未实现:
```cpp
#define UNIMPL(...) __VA_ARGS__ override { SK_ABORT("unimplemented."); }
UNIMPL(void recordDraw(...))
```
避免维护不必要的代码。

### 竞技场分配器
使用 `SkSTArenaAllocWithReset` 提供高效的临时对象分配:
- 单次分配大块内存
- 对象构造无锁
- 批量释放

## 性能考量

### 内存预分配
预分配 6MB 顶点缓冲区和 32 个间接命令槽位,避免测试时的分配延迟。

### 零拷贝
直接返回静态缓冲区指针,无需 memcpy:
```cpp
*buffer = fStaticVertexBuffer;
*startVertex = 0;
return fStaticVertexData;  // 直接返回指针
```

### 竞技场分配器的优势
- **分配速度:** 比 malloc 快 10-100 倍
- **缓存友好:** 连续内存布局
- **批量释放:** O(1) 重置操作

### 测试隔离性
每个测试可通过 `resetAllocator()` 清理状态,避免测试间干扰。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 接口 | 定义网格绘制目标抽象 |
| `src/gpu/ganesh/mock/GrMockGpu.h` | 协作 | Mock GPU 实现 |
| `src/gpu/ganesh/mock/GrMockOpsRenderPass.h` | 协作 | Mock 渲染通道 |
| `src/gpu/ganesh/GrOp.h` | 使用者 | 绘制操作使用绘制目标 |
| `include/gpu/ganesh/GrDirectContext.h` | 依赖 | 渲染上下文 |
| `src/base/SkArenaAlloc.h` | 工具 | 竞技场内存分配器 |
