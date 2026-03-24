# GrD3DBuffer

> 源文件: src/gpu/ganesh/d3d/GrD3DBuffer.h, src/gpu/ganesh/d3d/GrD3DBuffer.cpp

## 概述

`GrD3DBuffer` 是 Skia Ganesh Direct3D 12 后端中 GPU 缓冲区的实现类。它封装了 D3D12 的 `ID3D12Resource` 缓冲区对象,支持顶点缓冲区、索引缓冲区、常量缓冲区和传输缓冲区等多种用途。该类管理缓冲区的生命周期、映射/解映射操作以及资源状态转换。

## 架构位置

`GrD3DBuffer` 位于 Ganesh D3D12 后端的资源管理层:
- **基类**: `GrGpuBuffer` (跨平台缓冲区抽象)
- **D3D12 层**: 封装 `ID3D12Resource` 和资源状态管理
- **协作**: 与 `GrD3DGpu` 和 `GrD3DMemoryAllocator` 交互

## 主要类与结构体

### GrD3DBuffer 类
```cpp
class GrD3DBuffer : public GrGpuBuffer {
public:
    static sk_sp<GrD3DBuffer> Make(GrD3DGpu*, size_t size, GrGpuBufferType, GrAccessPattern);

    ID3D12Resource* d3dResource() const;
    void setResourceState(const GrD3DGpu* gpu, D3D12_RESOURCE_STATES newResourceState);

protected:
    GrD3DBuffer(GrD3DGpu*, size_t, GrGpuBufferType, GrAccessPattern,
                gr_cp<ID3D12Resource>, sk_sp<GrD3DAlloc>,
                D3D12_RESOURCE_STATES, std::string_view label);
};
```

**继承关系**:
- 基类: `GrGpuBuffer` -> `GrGpuResource`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fD3DResource` | `gr_cp<ID3D12Resource>` | D3D12 资源对象 |
| `fAlloc` | `sk_sp<GrD3DAlloc>` | 内存分配信息 |
| `fResourceState` | `D3D12_RESOURCE_STATES` | 当前资源状态 |
| `fStagingBuffer` | `ID3D12Resource*` | 暂存缓冲区(用于读回和动态更新) |
| `fStagingOffset` | `size_t` | 暂存缓冲区偏移量 |

## 公共 API 函数

### 工厂方法

**Make**
```cpp
static sk_sp<GrD3DBuffer> Make(GrD3DGpu* gpu, size_t size,
                               GrGpuBufferType intendedType,
                               GrAccessPattern accessPattern);
```
创建 D3D12 缓冲区。根据类型和访问模式选择合适的堆类型:
- **kStatic**: `D3D12_HEAP_TYPE_DEFAULT` (GPU 专用)
- **kXferGpuToCpu**: `D3D12_HEAP_TYPE_READBACK` (GPU -> CPU)
- **其他**: `D3D12_HEAP_TYPE_UPLOAD` (CPU -> GPU)

### 资源访问

**d3dResource**
```cpp
ID3D12Resource* d3dResource() const;
```
获取底层的 D3D12 资源指针。

### 资源状态管理

**setResourceState**
```cpp
void setResourceState(const GrD3DGpu* gpu, D3D12_RESOURCE_STATES newResourceState);
```
转换资源到新状态,自动插入资源屏障。如果状态已匹配或被 `GENERIC_READ` 包含,则跳过转换。

## 内部实现细节

### 堆类型选择

```cpp
D3D12_HEAP_TYPE heapType;
if (accessPattern == kStatic_GrAccessPattern) {
    heapType = D3D12_HEAP_TYPE_DEFAULT;  // GPU 独占,需要传输缓冲区上传
    *resourceState = D3D12_RESOURCE_STATE_COPY_DEST;
} else if (intendedType == GrGpuBufferType::kXferGpuToCpu) {
    heapType = D3D12_HEAP_TYPE_READBACK;  // CPU 读取
    *resourceState = D3D12_RESOURCE_STATE_COPY_DEST;
} else {
    heapType = D3D12_HEAP_TYPE_UPLOAD;  // CPU 写入
    *resourceState = D3D12_RESOURCE_STATE_GENERIC_READ;
}
```

**设计原理**:
- **DEFAULT 堆**: 最快的 GPU 访问,但 CPU 不可访问
- **UPLOAD 堆**: CPU 可写,GPU 可读,用于动态更新
- **READBACK 堆**: GPU 可写,CPU 可读,用于读回结果

### 资源状态转换

D3D12 要求显式管理资源状态:
```cpp
D3D12_RESOURCE_TRANSITION_BARRIER barrier = {
    .pResource = this->d3dResource(),
    .Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,
    .StateBefore = fResourceState,
    .StateAfter = newResourceState
};
gpu->addBufferResourceBarriers(this, 1, &barrier);
fResourceState = newResourceState;
```

**常见状态**:
- `GENERIC_READ`: 包含多种读取状态(顶点缓冲区、索引缓冲区等)
- `COPY_DEST`: 作为拷贝目标
- `COPY_SOURCE`: 作为拷贝源

### 映射/解映射实现

**onMap**
```cpp
void onMap(MapType type) {
    fMapPtr = this->internalMap(type, 0, this->size());
}
```

`internalMap` 根据堆类型选择策略:
- **UPLOAD 堆**: 直接映射 D3D12 资源
- **DEFAULT 堆**: 使用暂存缓冲区(UPLOAD 堆)

**onUnmap**
```cpp
void onUnmap(MapType type) {
    this->internalUnmap(type, 0, this->size());
}
```

对于 DEFAULT 堆,解映射时需要拷贝暂存缓冲区到 GPU 缓冲区。

### 数据更新

**onUpdateData**
```cpp
bool onUpdateData(const void* src, size_t offset, size_t size, bool preserve);
```
更新缓冲区数据:
1. **preserve = false**: 可以丢弃旧内容,直接映射并写入
2. **preserve = true**: 需要保留未更新部分,可能需要暂存缓冲区

**onClearToZero**
```cpp
bool onClearToZero();
```
将缓冲区清零,映射后使用 `memset`。

### 资源释放

**releaseResource**
```cpp
void releaseResource() {
    if (fMapPtr) {
        this->unmap();  // 确保解映射
    }
    fD3DResource.reset();  // 释放 D3D12 资源
    fAlloc.reset();        // 释放内存分配
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGpuBuffer` | 基类,定义跨平台缓冲区接口 |
| `GrD3DGpu` | D3D12 GPU 实现,执行资源操作 |
| `GrD3DMemoryAllocator` | 内存分配器,管理 D3D12 资源分配 |
| `GrD3DAlloc` | 内存分配记录 |
| `ID3D12Resource` | D3D12 资源对象 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrD3DGpu` | 使用 `GrD3DBuffer` 作为各种 GPU 缓冲区 |
| Ganesh 渲染管线 | 通过 `GrGpuBuffer` 接口使用缓冲区 |

## 设计模式与设计决策

### 设计模式

1. **适配器模式**: 将 D3D12 资源适配到 Ganesh 缓冲区接口
2. **资源管理模式**: RAII 风格的资源生命周期管理
3. **策略模式**: 根据访问模式选择不同的堆类型和映射策略

### 设计决策

**为什么需要暂存缓冲区?**
- DEFAULT 堆不支持 CPU 访问
- 动态更新需要先写入 UPLOAD 堆,再拷贝到 DEFAULT 堆
- 权衡: 额外内存开销换取最佳 GPU 性能

**资源状态管理的必要性**
- D3D12 要求显式状态转换
- 错误的状态会导致验证层错误或崩溃
- 自动状态跟踪简化上层代码

**GENERIC_READ 的特殊处理**
```cpp
if (fResourceState == D3D12_RESOURCE_STATE_GENERIC_READ &&
    SkToBool(newResourceState | fResourceState)) {
    return;  // 已经在 GENERIC_READ,无需转换
}
```
- `GENERIC_READ` 包含多个读取状态的组合
- 从 `GENERIC_READ` 到任何读取状态无需屏障
- 减少不必要的状态转换

**为什么区分不同的缓冲区类型?**
- **顶点/索引缓冲区**: 高频访问,使用 DEFAULT 堆
- **常量缓冲区**: 每帧更新,使用 UPLOAD 堆
- **传输缓冲区**: CPU-GPU 数据交换,使用 UPLOAD/READBACK 堆

## 性能考量

### 优化策略

1. **堆类型选择**: 根据访问模式选择最优堆类型
2. **减少状态转换**: 合并屏障,批量提交
3. **持久映射**: UPLOAD 堆可以保持映射状态(TODO 注释中提到)
4. **对齐要求**: D3D12 缓冲区自动 256 字节对齐

### 性能陷阱

- **频繁映射/解映射 DEFAULT 堆**: 每次需要暂存缓冲区和拷贝
- **过多小缓冲区**: 考虑使用子分配(suballocation)
- **不必要的状态转换**: 检查当前状态再转换
- **READBACK 堆读取**: 需要 GPU 同步,阻塞 CPU

### 内存考量

- **DEFAULT 堆**: GPU 独占内存,容量大
- **UPLOAD 堆**: 系统内存,有限制
- **暂存缓冲区**: 动态 DEFAULT 缓冲区需要额外的 UPLOAD 暂存空间

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuBuffer.h/.cpp` | 基类 | 跨平台缓冲区抽象 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/.cpp` | 使用者 | D3D12 GPU 实现 |
| `src/gpu/ganesh/d3d/GrD3DMemoryAllocator.h` | 依赖 | 内存分配 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 类型定义 |
| `src/gpu/ganesh/d3d/GrD3DUtil.h` | 依赖 | D3D12 工具函数 |
