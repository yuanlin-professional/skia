# GrD3DDescriptorHeap

> 源文件
> - src/gpu/ganesh/d3d/GrD3DDescriptorHeap.h
> - src/gpu/ganesh/d3d/GrD3DDescriptorHeap.cpp

## 概述

`GrD3DDescriptorHeap` 是 Skia 图形库中 Ganesh D3D 后端的描述符堆封装类,用于管理 Direct3D 12 的 `ID3D12DescriptorHeap` 对象。描述符堆是 D3D12 中用于存储资源视图(如纹理、缓冲区、采样器等)的内存池,GPU 通过描述符访问这些资源。该类提供了对描述符堆的创建、索引访问和句柄管理功能。

描述符堆是 D3D12 资源绑定模型的核心组件,不同于传统的绑定槽模型,D3D12 要求所有资源描述符集中管理在堆中。该类通过封装堆的创建和句柄计算,简化了上层代码对描述符的访问,并通过唯一 ID 机制保证句柄的有效性验证。

## 架构位置

`GrD3DDescriptorHeap` 位于 Skia 图形库的 GPU 资源管理层次结构中:

```
Skia
└── src/gpu/ganesh (Ganesh GPU 后端)
    └── d3d (Direct3D 12 实现)
        ├── GrD3DGpu (D3D GPU 主类)
        ├── GrD3DDescriptorHeap (描述符堆基类)
        ├── GrD3DDescriptorTableManager (描述符表管理器)
        └── GrD3DCpuDescriptorManager (CPU 描述符管理器)
```

该类作为描述符管理的基础组件,为上层的描述符分配器和管理器提供底层的堆访问接口。

## 主要类与结构体

### GrD3DDescriptorHeap

**继承关系**:
- 无直接继承关系(纯封装类)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHeap` | `gr_cp<ID3D12DescriptorHeap>` | D3D12 描述符堆对象的智能指针 |
| `fHandleIncrementSize` | `size_t` | 描述符句柄之间的字节偏移量(由硬件决定) |
| `fCPUHeapStart` | `D3D12_CPU_DESCRIPTOR_HANDLE` | CPU 可见的堆起始句柄 |
| `fGPUHeapStart` | `D3D12_GPU_DESCRIPTOR_HANDLE` | GPU 可见的堆起始句柄 |
| `fUniqueID` | `uint32_t` | 堆的全局唯一标识符,用于句柄验证 |

### CPUHandle 结构体

```cpp
struct CPUHandle {
    D3D12_CPU_DESCRIPTOR_HANDLE fHandle;  // D3D CPU 句柄
    uint32_t fHeapID;                      // 所属堆的 ID
};
```

CPU 可见的描述符句柄包装,携带堆 ID 用于验证句柄归属。

### GPUHandle 结构体

```cpp
struct GPUHandle {
    D3D12_GPU_DESCRIPTOR_HANDLE fHandle;  // D3D GPU 句柄
    uint32_t fHeapID;                      // 所属堆的 ID
};
```

GPU 可见的描述符句柄包装,用于着色器可见的堆(如 CBV/SRV/UAV 和采样器堆)。

## 公共 API 函数

### 静态工厂方法

```cpp
static std::unique_ptr<GrD3DDescriptorHeap> Make(
    GrD3DGpu* gpu,
    D3D12_DESCRIPTOR_HEAP_TYPE type,
    unsigned int numDescriptors,
    D3D12_DESCRIPTOR_HEAP_FLAGS flags);
```

创建描述符堆对象:
- **参数**:
  - `gpu`: D3D GPU 设备对象
  - `type`: 堆类型(CBV_SRV_UAV、SAMPLER、RTV、DSV)
  - `numDescriptors`: 描述符数量
  - `flags`: 堆标志(如是否着色器可见)
- **返回值**: 唯一指针包装的堆对象

### 句柄获取

```cpp
CPUHandle getCPUHandle(unsigned int index);
GPUHandle getGPUHandle(unsigned int index);
```

根据索引获取描述符句柄:
- **参数**: 描述符在堆中的索引
- **返回值**: 携带堆 ID 的句柄结构体
- **注意**: 着色器可见堆的 CPU 句柄仅用于写入

### 索引计算

```cpp
size_t getIndex(const CPUHandle& handle);
size_t getIndex(const GPUHandle& handle);
```

从句柄反向计算索引位置:
- **参数**: CPU 或 GPU 句柄
- **返回值**: 描述符在堆中的索引
- **验证**: 检查句柄是否属于当前堆

### 访问器

```cpp
uint32_t uniqueID() const;
ID3D12DescriptorHeap* descriptorHeap() const;
size_t handleIncrementSize();
```

获取堆的属性信息,用于底层操作和调试。

## 内部实现细节

### 堆创建流程

`Make` 方法实现了描述符堆的创建:

1. **配置堆描述符**:
   ```cpp
   D3D12_DESCRIPTOR_HEAP_DESC heapDesc = {};
   heapDesc.Type = type;               // 堆类型
   heapDesc.NumDescriptors = numDescriptors;  // 容量
   heapDesc.Flags = flags;             // 标志(如 SHADER_VISIBLE)
   ```

2. **创建 D3D 堆对象**:
   ```cpp
   gpu->device()->CreateDescriptorHeap(&heapDesc, IID_PPV_ARGS(&heap));
   ```

3. **查询句柄增量**: 从设备获取硬件相关的句柄步长:
   ```cpp
   gpu->device()->GetDescriptorHandleIncrementSize(type)
   ```

4. **构造封装对象**: 传递堆对象和增量大小给构造函数

### 构造函数初始化

构造函数执行关键的初始化操作:

```cpp
GrD3DDescriptorHeap::GrD3DDescriptorHeap(const gr_cp<ID3D12DescriptorHeap>& heap,
                                         unsigned int handleIncrementSize)
    : fHeap(heap)
    , fHandleIncrementSize(handleIncrementSize)
    , fUniqueID(GenID()) {
    fCPUHeapStart = fHeap->GetCPUDescriptorHandleForHeapStart();
    fGPUHeapStart = fHeap->GetGPUDescriptorHandleForHeapStart();
}
```

- 保存堆对象和增量大小
- 生成全局唯一 ID
- 获取 CPU 和 GPU 的起始句柄

### 句柄计算机制

句柄获取基于指针算术:

```cpp
// CPU 句柄计算
D3D12_CPU_DESCRIPTOR_HANDLE handle = fCPUHeapStart;
handle.ptr += index * fHandleIncrementSize;
```

关键点:
- 描述符句柄本质是指向 GPU 内存的指针(64 位整数)
- 增量大小由硬件决定,不同 GPU 可能不同
- 每次访问都进行边界检查: `index < fHeap->GetDesc().NumDescriptors`

### 索引反向计算

从句柄恢复索引的算法:

```cpp
size_t index = (handle.fHandle.ptr - fCPUHeapStart.ptr) / fHandleIncrementSize;
```

包含三重验证:
1. 堆 ID 匹配检查
2. 索引范围检查
3. 句柄对齐检查(确保指针能整除增量)

### 唯一 ID 生成

使用原子计数器生成全局唯一 ID:

```cpp
static uint32_t GenID() {
    static std::atomic<uint32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID++;
    } while (id == SK_InvalidUniqueID);  // 跳过无效 ID
    return id;
}
```

线程安全且保证不重复。

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrD3DTypes.h` | D3D 类型定义和 `gr_cp<>` 智能指针 |
| `GrManagedResource` | 资源管理基类(虽未直接继承,但相关) |
| `SkBitSet.h` | 位集工具(用于描述符分配追踪) |
| `GrD3DGpu` | D3D GPU 设备接口,提供设备对象 |
| `ID3D12DescriptorHeap` | D3D12 描述符堆 COM 接口 |
| `ID3D12Device` | D3D12 设备对象 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DDescriptorTableManager` | GPU 可见描述符表管理,用于着色器资源绑定 |
| `GrD3DCpuDescriptorManager` | CPU 描述符管理,用于渲染目标和深度模板视图 |
| `GrD3DGpu` | 创建各类描述符堆 |
| `GrD3DCommandList` | 设置描述符堆到命令列表 |

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 方法创建对象:
- 封装复杂的 D3D API 调用
- 返回 `std::unique_ptr` 表达所有权转移
- 允许未来扩展堆创建逻辑

### 句柄携带堆 ID

`CPUHandle` 和 `GPUHandle` 结构体包含堆 ID:
- **安全性**: 防止使用错误堆的句柄
- **调试性**: 便于追踪句柄来源
- **验证性**: `getIndex` 方法可验证句柄有效性

### 原子唯一 ID 生成

使用 `std::atomic` 而非 `static` 变量:
- 线程安全,支持并发创建堆
- 跳过无效 ID,保证 ID 语义正确
- 全局唯一,即使跨多个 GPU 设备

### 基于指针的句柄计算

直接操作 D3D 句柄的 `ptr` 成员:
- 高性能,避免额外的 API 调用
- 利用硬件保证的线性布局
- 零开销抽象

### 智能指针管理

使用 `gr_cp<>` 自动管理 D3D 对象:
- 自动调用 `Release()` 释放 COM 对象
- 支持拷贝和移动语义
- 防止资源泄漏

## 性能考量

### 句柄缓存

缓存起始句柄避免重复查询:
- `fCPUHeapStart` 和 `fGPUHeapStart` 在构造时获取
- 每次 `getCPUHandle/getGPUHandle` 只需简单的指针加法
- 避免调用 `GetCPUDescriptorHandleForHeapStart()` 的开销

### 内联候选

关键方法适合内联:
- `uniqueID()`: 单行返回
- `descriptorHeap()`: 单行返回
- `handleIncrementSize()`: 单行返回
- `getIndex()`: 简单算术,已在头文件定义

### 硬件相关的增量

使用设备查询的增量大小而非假设固定值:
- 不同硬件的增量可能不同(通常 32 或 64 字节)
- 保证跨 GPU 的兼容性
- 一次查询,多次使用

### 边界检查

使用 `SkASSERT` 进行调试时边界检查:
- Release 构建时零开销
- Debug 构建时捕获越界访问
- 三重验证保证句柄正确性

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 创建者 | 负责创建各类描述符堆 |
| `src/gpu/ganesh/d3d/GrD3DDescriptorTableManager.h/cpp` | 派生/使用者 | GPU 可见描述符表管理 |
| `src/gpu/ganesh/d3d/GrD3DCpuDescriptorManager.h/cpp` | 派生/使用者 | CPU 描述符分配器 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h/cpp` | 使用者 | 设置描述符堆到命令列表 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 类型依赖 | 定义 D3D 相关类型 |
| `src/gpu/ganesh/GrManagedResource.h` | 相关基类 | 资源管理模式 |
| `src/utils/SkBitSet.h` | 工具依赖 | 位集用于追踪描述符分配状态 |
