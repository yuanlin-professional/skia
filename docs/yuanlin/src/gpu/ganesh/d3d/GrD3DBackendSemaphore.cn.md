# GrD3DBackendSemaphore

> 源文件
> - include/gpu/ganesh/d3d/GrD3DBackendSemaphore.h
> - src/gpu/ganesh/d3d/GrD3DBackendSemaphore.cpp

## 概述

`GrD3DBackendSemaphore` 模块提供了 Direct3D 12 后端信号量(Fence)的创建和查询接口。在 D3D12 中,信号量以 Fence 的形式存在,用于 GPU 和 CPU 之间的同步,以及多个命令队列之间的同步。该模块是 Skia Ganesh 架构中 D3D12 后端同步原语的封装,将 D3D12 特定的 `GrD3DFenceInfo` 与通用的 `GrBackendSemaphore` 进行桥接。

该模块非常轻量,仅提供两个函数:
- **MakeD3D**: 从 D3D12 Fence 信息创建后端信号量
- **GetD3DFenceInfo**: 从后端信号量提取 D3D12 Fence 信息

这些函数使得 Skia 能够与外部 D3D12 代码进行同步,例如在多线程渲染或跨进程纹理共享场景中。

## 架构位置

在 Skia GPU 同步机制中的位置:

```
应用层 (SkSurface, GrDirectContext)
    ↓
同步抽象层 (GrBackendSemaphore)
    ↓
后端特定实现
    ├─ GrGLBackendSemaphore (OpenGL Sync)
    ├─ GrVkBackendSemaphore (Vulkan Semaphore)
    ├─ GrMtlBackendSemaphore (Metal Event)
    └─ GrD3DBackendSemaphore (D3D12 Fence) ← 当前模块
    ↓
D3D12 同步原语 (ID3D12Fence)
```

## 主要类与结构体

### GrD3DBackendSemaphoreData

封装 Direct3D 12 Fence 信息的内部类。

**继承关系:**
```
GrBackendSemaphoreData
    ↓
GrD3DBackendSemaphoreData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFenceInfo` | `GrD3DFenceInfo` | D3D12 Fence 信息,包含 Fence 对象和信号值 |

## 公共 API 函数

### GrBackendSemaphores 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendSemaphore MakeD3D(const GrD3DFenceInfo&)` | 从 D3D12 Fence 信息创建后端信号量 |
| `GrD3DFenceInfo GetD3DFenceInfo(const GrBackendSemaphore&)` | 从后端信号量提取 D3D12 Fence 信息 |

## 内部实现细节

### 数据类实现

```cpp
class GrD3DBackendSemaphoreData final : public GrBackendSemaphoreData {
public:
    GrD3DBackendSemaphoreData(const GrD3DFenceInfo& info) : fFenceInfo(info) {}

    GrD3DFenceInfo fenceInfo() const { return fFenceInfo; }

private:
    void copyTo(AnySemaphoreData& data) const override {
        data.emplace<GrD3DBackendSemaphoreData>(fFenceInfo);
    }

#if defined(SK_DEBUG)
    GrBackendApi type() const override { return GrBackendApi::kDirect3D; }
#endif

    GrD3DFenceInfo fFenceInfo;
};
```

### 创建后端信号量

```cpp
GrBackendSemaphore MakeD3D(const GrD3DFenceInfo& info) {
    return GrBackendSemaphorePriv::MakeGrBackendSemaphore<GrD3DBackendSemaphoreData>(
            GrBackendApi::kDirect3D, {info});
}
```

使用模板函数 `MakeGrBackendSemaphore` 创建,传入后端类型和数据。

### 提取 Fence 信息

```cpp
GrD3DFenceInfo GetD3DFenceInfo(const GrBackendSemaphore& sem) {
    SkASSERT(sem.backend() == GrBackendApi::kDirect3D);
    const GrD3DBackendSemaphoreData* data = get_and_cast_data(sem);
    SkASSERT(data);
    return data->fenceInfo();
}
```

先验证后端类型,然后提取数据。

### 类型安全的数据提取

```cpp
static const GrD3DBackendSemaphoreData* get_and_cast_data(const GrBackendSemaphore& sem) {
    auto data = GrBackendSemaphorePriv::GetBackendData(sem);
    SkASSERT(!data || data->type() == GrBackendApi::kDirect3D);
    return static_cast<const GrD3DBackendSemaphoreData*>(data);
}
```

包含类型断言的辅助函数,确保类型安全。

### GrD3DFenceInfo 的内容

虽然该头文件不定义 `GrD3DFenceInfo`,但通常包含:
- `ID3D12Fence*`: Fence 对象指针
- `uint64_t`: 信号值,用于标识特定的同步点

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrBackendSemaphore` | 后端无关的信号量抽象 |
| `GrBackendSemaphorePriv` | 后端信号量私有实现辅助 |
| `GrD3DTypes` | D3D12 类型定义,包含 `GrD3DFenceInfo` |
| `GrD3DTypesMinimal` | D3D12 最小类型定义 |
| `SkAssert` | 断言宏 |
| `SkDebug` | 调试辅助 |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrD3DGpu` | GPU 命令队列同步 |
| `GrDirectContext` | 刷新操作的同步点 |
| `SkSurface` | 表面刷新后的信号量 |
| 跨线程渲染 | 多个线程之间的同步 |
| 外部互操作 | 与应用程序的 D3D12 代码同步 |

## 设计模式与设计决策

### 命名空间组织

使用 `GrBackendSemaphores` 命名空间,与其他后端保持一致:

```cpp
// 一致的 API 模式
GrBackendSemaphores::MakeGL(...);
GrBackendSemaphores::MakeVulkan(...);
GrBackendSemaphores::MakeMetal(...);
GrBackendSemaphores::MakeD3D(...);
```

### 内部数据类封装

使用 `final` 类封装后端特定数据,隐藏 D3D12 实现细节:

```cpp
class GrD3DBackendSemaphoreData final : public GrBackendSemaphoreData { ... };
```

### 值语义

`GrD3DFenceInfo` 通过值传递和返回,包含的通常是指针和整数,拷贝开销很小:

```cpp
GrBackendSemaphore MakeD3D(const GrD3DFenceInfo& info);  // 通过引用传入
GrD3DFenceInfo GetD3DFenceInfo(const GrBackendSemaphore&);  // 通过值返回
```

### 类型断言

使用 `SkASSERT` 确保类型正确:

```cpp
SkASSERT(sem.backend() == GrBackendApi::kDirect3D);
```

Debug 模式下验证,Release 模式下优化掉。

### 最小化接口

模块只提供两个函数,保持简单:
- 创建:从 D3D12 到 Skia
- 提取:从 Skia 到 D3D12

### 不拥有 Fence 对象

模块不管理 `ID3D12Fence` 的生命周期,这是应用程序的责任:

```cpp
// 应用程序负责:
// 1. 创建 ID3D12Fence
// 2. 使用 MakeD3D 封装
// 3. 在适当时机销毁 Fence
```

## 性能考量

### 轻量级封装

`GrD3DBackendSemaphoreData` 只包含 `GrD3DFenceInfo`,通常是一个指针加一个整数,非常轻量。

### 无额外分配

创建后端信号量时,数据直接存储在 `GrBackendSemaphore` 的内部存储中,无额外堆分配。

### 内联优化

创建和提取函数足够小,可以被编译器内联。

### 值拷贝开销低

`GrD3DFenceInfo` 通常只包含指针和整数,拷贝开销可忽略。

### Debug 断言零开销

类型检查只在 Debug 模式下执行,Release 模式下完全优化掉。

### 直接访问

从信号量中提取 Fence 信息是简单的内存访问,无虚函数调用:

```cpp
return data->fenceInfo();  // 直接返回成员
```

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/GrBackendSemaphore.h` | 后端无关的信号量抽象 |
| `src/gpu/ganesh/GrBackendSemaphorePriv.h` | 后端信号量私有实现辅助 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | D3D12 类型定义,包含 `GrD3DFenceInfo` |
| `include/private/gpu/ganesh/GrD3DTypesMinimal.h` | D3D12 最小类型定义 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | D3D12 GPU 实现,使用信号量同步 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h` | D3D12 命令列表,可能使用 Fence 同步 |
| `include/gpu/ganesh/GrTypes.h` | GPU 通用类型定义 |
