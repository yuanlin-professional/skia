# GrD3DTypes

> 源文件: `include/gpu/ganesh/d3d/GrD3DTypes.h`

## 概述
GrD3DTypes 定义了 Ganesh Direct3D 12 后端的核心类型系统,包括 COM 智能指针封装(gr_cp)、内存分配器接口、纹理资源信息结构体、同步对象(Fence)和表面信息等。该文件是 Ganesh D3D 后端与 Direct3D 12 API 之间的类型桥梁,为跨平台 GPU 编程提供统一的 D3D12 资源抽象。

## 架构位置
该文件位于 `include/gpu/ganesh/d3d` Direct3D 后端的核心类型层,被 Ganesh D3D 后端的所有模块依赖。它封装了 D3D12 的 COM 对象管理和资源描述,为上层提供类型安全和 RAII 保证的 D3D 资源操作接口。

## 头文件包含警告

该文件包含 `d3d12.h`,进而包含 `windows.h`,会重定义多个常见标识符(详见 GrD3DBackendContext.md)。使用时需注意符号污染问题。

## 核心工具函数

### GrSafeComAddRef
```cpp
template <typename T>
static inline T* GrSafeComAddRef(T* obj) {
    if (obj) {
        obj->AddRef();
    }
    return obj;
}
```
- **功能**: 安全地增加 COM 对象引用计数
- **空指针安全**: 自动检查 nullptr
- **返回值**: 返回原指针,便于链式调用

### GrSafeComRelease
```cpp
template <typename T>
static inline void GrSafeComRelease(T* obj) {
    if (obj) {
        obj->Release();
    }
}
```
- **功能**: 安全地释放 COM 对象引用
- **空指针安全**: 自动检查 nullptr
- **应用**: 析构函数、智能指针实现

## gr_cp 智能指针模板

### 类定义
```cpp
template <typename T>
class gr_cp {
public:
    using element_type = T;

    constexpr gr_cp() : fObject(nullptr) {}
    constexpr gr_cp(std::nullptr_t) : fObject(nullptr) {}
    gr_cp(const gr_cp<T>& that);
    gr_cp(gr_cp<T>&& that);
    explicit gr_cp(T* obj);
    ~gr_cp();

    gr_cp<T>& operator=(const gr_cp<T>& that);
    gr_cp<T>& operator=(gr_cp<T>&& that);

    explicit operator bool() const;
    T* get() const;
    T* operator->() const;
    T** operator&();

    void reset(T* object = nullptr);
    void retain(T* object);
    [[nodiscard]] T* release();

private:
    T* fObject;
};
```

**设计目标**: 提供类似 std::shared_ptr 的 COM 智能指针,自动管理 AddRef/Release

### 构造函数

#### 拷贝构造
```cpp
gr_cp(const gr_cp<T>& that) : fObject(GrSafeComAddRef(that.get())) {}
```
- **行为**: 共享所有权,调用 AddRef
- **语义**: 两个 gr_cp 都持有引用

#### 移动构造
```cpp
gr_cp(gr_cp<T>&& that) : fObject(that.release()) {}
```
- **行为**: 转移所有权,不调用 AddRef/Release
- **性能**: 避免原子操作,更高效
- **移动后**: 源对象指向 nullptr

#### 采用构造
```cpp
explicit gr_cp(T* obj) {
    fObject = obj;
}
```
- **行为**: 采用裸指针,不调用 AddRef
- **假设**: 调用者已持有引用,或转移所有权
- **显式**: 避免意外转换

### 析构函数
```cpp
~gr_cp() {
    GrSafeComRelease(fObject);
    SkDEBUGCODE(fObject = nullptr);
}
```
- **行为**: 释放引用,调用 Release
- **调试**: Debug 构建中置空指针,检测悬空引用

### 赋值运算符

#### 拷贝赋值
```cpp
gr_cp<T>& operator=(const gr_cp<T>& that) {
    if (this != &that) {
        this->reset(GrSafeComAddRef(that.get()));
    }
    return *this;
}
```
- **自赋值检查**: 避免无效操作
- **先 AddRef 后 Release**: 防止对象在赋值中被销毁

#### 移动赋值
```cpp
gr_cp<T>& operator=(gr_cp<T>&& that) {
    this->reset(that.release());
    return *this;
}
```
- **高效转移**: 无引用计数操作
- **异常安全**: noexcept 保证

### 访问操作符

#### 解引用
```cpp
T* operator->() const { return fObject; }
```
- **用途**: 访问 COM 对象成员
- **示例**: `device->CreateTexture2D(...)`

#### 取地址
```cpp
T** operator&() { return &fObject; }
```
- **用途**: 作为 D3D API 的输出参数
- **示例**:
  ```cpp
  gr_cp<ID3D12Device> device;
  D3D12CreateDevice(adapter, level, IID_PPV_ARGS(&device));
  ```
- **危险**: 可能覆盖现有指针,导致泄漏
- **建议**: 仅用于空指针

#### 布尔转换
```cpp
explicit operator bool() const { return this->get() != nullptr; }
```
- **用途**: 条件判断
- **示例**: `if (device) { ... }`

### 修改操作

#### reset
```cpp
void reset(T* object = nullptr) {
    T* oldObject = fObject;
    fObject = object;
    GrSafeComRelease(oldObject);
}
```
- **功能**: 采用新对象,释放旧对象
- **不调用 AddRef**: 假设接收已持有引用的指针
- **空安全**: object 可为 nullptr

#### retain
```cpp
void retain(T* object) {
    if (this->fObject != object) {
        this->reset(GrSafeComAddRef(object));
    }
}
```
- **功能**: 共享新对象所有权
- **调用 AddRef**: 增加引用计数
- **自赋值检查**: 避免无效的 AddRef/Release

#### release
```cpp
[[nodiscard]] T* release() {
    T* obj = fObject;
    fObject = nullptr;
    return obj;
}
```
- **功能**: 释放所有权,返回裸指针
- **不调用 Release**: 调用者承担所有权
- **nodiscard**: 强制使用返回值,防止泄漏

### 比较运算符
```cpp
template <typename T>
inline bool operator==(const gr_cp<T>& a, const gr_cp<T>& b) {
    return a.get() == b.get();
}

template <typename T>
inline bool operator!=(const gr_cp<T>& a, const gr_cp<T>& b) {
    return a.get() != b.get();
}
```
- **功能**: 比较底层指针地址
- **语义**: 指向同一对象则相等

## 内存分配器接口

### GrD3DAlloc
```cpp
class GrD3DAlloc : public SkRefCnt {
public:
    ~GrD3DAlloc() override = default;
};
```
- **职责**: 表示一次内存分配的抽象基类
- **生命周期**: 引用计数管理
- **扩展**: 子类可携带分配器特定元数据(内存块、偏移等)

### GrD3DMemoryAllocator
```cpp
class GrD3DMemoryAllocator : public SkRefCnt {
public:
    virtual gr_cp<ID3D12Resource> createResource(
        D3D12_HEAP_TYPE heapType,
        const D3D12_RESOURCE_DESC* desc,
        D3D12_RESOURCE_STATES initialResourceState,
        sk_sp<GrD3DAlloc>* allocation,
        const D3D12_CLEAR_VALUE* clearValue) = 0;

    virtual gr_cp<ID3D12Resource> createAliasingResource(
        sk_sp<GrD3DAlloc>& allocation,
        uint64_t localOffset,
        const D3D12_RESOURCE_DESC* desc,
        D3D12_RESOURCE_STATES initialResourceState,
        const D3D12_CLEAR_VALUE* clearValue) = 0;
};
```

**职责**: 自定义 D3D12 资源内存分配策略

#### createResource
**功能**: 创建新的 D3D12 资源

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| heapType | D3D12_HEAP_TYPE | 堆类型(DEFAULT/UPLOAD/READBACK) |
| desc | const D3D12_RESOURCE_DESC* | 资源描述(尺寸、格式等) |
| initialResourceState | D3D12_RESOURCE_STATES | 初始资源状态 |
| allocation | sk_sp<GrD3DAlloc>* | 输出分配信息 |
| clearValue | const D3D12_CLEAR_VALUE* | 优化的清除值,可为 nullptr |

**返回值**: gr_cp<ID3D12Resource> - 创建的资源

**典型实现**:
```cpp
gr_cp<ID3D12Resource> MyAllocator::createResource(...) {
    // 1. 从内存池分配
    MyAllocation* alloc = memoryPool->allocate(desc->Width);
    *allocation = sk_sp<GrD3DAlloc>(alloc);

    // 2. 创建资源
    gr_cp<ID3D12Resource> resource;
    device->CreateCommittedResource(
        &heapProps, heapFlags, desc,
        initialResourceState, clearValue,
        IID_PPV_ARGS(&resource));

    return resource;
}
```

#### createAliasingResource
**功能**: 在已分配的内存上创建别名资源

**参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| allocation | sk_sp<GrD3DAlloc>& | 已存在的分配 |
| localOffset | uint64_t | 分配内偏移量 |
| desc | const D3D12_RESOURCE_DESC* | 资源描述 |
| initialResourceState | D3D12_RESOURCE_STATES | 初始状态 |
| clearValue | const D3D12_CLEAR_VALUE* | 清除值 |

**返回值**: gr_cp<ID3D12Resource> - 别名资源

**应用场景**: 内存复用,临时资源

## 资源信息结构体

### GrD3DTextureResourceInfo
```cpp
struct GrD3DTextureResourceInfo {
    gr_cp<ID3D12Resource>    fResource             = nullptr;
    sk_sp<GrD3DAlloc>        fAlloc                = nullptr;
    D3D12_RESOURCE_STATES    fResourceState        = D3D12_RESOURCE_STATE_COMMON;
    DXGI_FORMAT              fFormat               = DXGI_FORMAT_UNKNOWN;
    uint32_t                 fSampleCount          = 1;
    uint32_t                 fLevelCount           = 0;
    unsigned int             fSampleQualityPattern = DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN;
    skgpu::Protected         fProtected            = skgpu::Protected::kNo;

    GrD3DTextureResourceInfo() = default;
    GrD3DTextureResourceInfo(ID3D12Resource* resource, ...);
    GrD3DTextureResourceInfo(const GrD3DTextureResourceInfo& info, D3D12_RESOURCE_STATES resourceState);
};
```

**职责**: 封装 D3D12 纹理资源的完整信息

**成员说明**:

| 成员 | 类型 | 说明 |
|------|------|------|
| fResource | gr_cp<ID3D12Resource> | D3D12 资源对象 |
| fAlloc | sk_sp<GrD3DAlloc> | 关联的内存分配 |
| fResourceState | D3D12_RESOURCE_STATES | 当前资源状态(用于状态跟踪) |
| fFormat | DXGI_FORMAT | 像素格式 |
| fSampleCount | uint32_t | MSAA 采样数 |
| fLevelCount | uint32_t | Mipmap 层级数 |
| fSampleQualityPattern | unsigned int | MSAA 质量模式 |
| fProtected | skgpu::Protected | 是否受保护资源 |

**构造函数变体**:

1. **默认构造**: 所有成员初始化为默认值
2. **完整构造**: 提供所有参数
   ```cpp
   GrD3DTextureResourceInfo(
       ID3D12Resource* resource,
       const sk_sp<GrD3DAlloc> alloc,
       D3D12_RESOURCE_STATES resourceState,
       DXGI_FORMAT format,
       uint32_t sampleCount,
       uint32_t levelCount,
       unsigned int sampleQualityLevel,
       skgpu::Protected isProtected = skgpu::Protected::kNo);
   ```
3. **状态更新构造**: 从现有信息创建,仅更新状态
   ```cpp
   GrD3DTextureResourceInfo(
       const GrD3DTextureResourceInfo& info,
       D3D12_RESOURCE_STATES resourceState);
   ```

**所有权说明**:
> Note: there is no notion of Borrowed or Adopted resources in the D3D backend,
> so Ganesh will ref fResource once it's asked to wrap it.
> Clients are responsible for releasing their own ref to avoid memory leaks.

- Ganesh 会调用 AddRef 增加引用计数
- 客户端必须释放自己的引用,避免泄漏

**相等比较** (GPU_TEST_UTILS):
```cpp
#if defined(GPU_TEST_UTILS)
bool operator==(const GrD3DTextureResourceInfo& that) const {
    return fResource == that.fResource &&
           fResourceState == that.fResourceState &&
           fFormat == that.fFormat &&
           fSampleCount == that.fSampleCount &&
           fLevelCount == that.fLevelCount &&
           fSampleQualityPattern == that.fSampleQualityPattern &&
           fProtected == that.fProtected;
}
#endif
```
- 仅在测试代码中启用
- 比较所有成员(除 fAlloc)

### GrD3DFenceInfo
```cpp
struct GrD3DFenceInfo {
    GrD3DFenceInfo()
        : fFence(nullptr)
        , fValue(0) {
    }

    gr_cp<ID3D12Fence> fFence;
    uint64_t           fValue;  // signal value for the fence
};
```

**职责**: 封装 D3D12 Fence 同步对象

**成员**:
- `fFence`: D3D12 Fence 对象
- `fValue`: 信号值,用于等待特定的 GPU 完成点

**使用场景**:
```cpp
GrD3DFenceInfo fenceInfo;
fenceInfo.fFence = fence;
fenceInfo.fValue = fenceValue++;

// 信号 fence
commandQueue->Signal(fence.get(), fenceValue);

// 等待 fence
if (fence->GetCompletedValue() < fenceValue) {
    fence->SetEventOnCompletion(fenceValue, event);
    WaitForSingleObject(event, INFINITE);
}
```

### GrD3DSurfaceInfo
```cpp
struct GrD3DSurfaceInfo {
    uint32_t fSampleCount = 1;
    uint32_t fLevelCount = 0;
    skgpu::Protected fProtected = skgpu::Protected::kNo;

    DXGI_FORMAT fFormat = DXGI_FORMAT_UNKNOWN;
    unsigned int fSampleQualityPattern = DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN;
};
```

**职责**: 描述 D3D12 表面(Surface)的基本属性

**成员**:
| 成员 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| fSampleCount | uint32_t | 1 | MSAA 采样数 |
| fLevelCount | uint32_t | 0 | Mipmap 层级数 |
| fProtected | skgpu::Protected | kNo | 是否受保护 |
| fFormat | DXGI_FORMAT | UNKNOWN | 像素格式 |
| fSampleQualityPattern | unsigned int | STANDARD | MSAA 质量模式 |

**应用**: 创建渲染目标、查询表面能力

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | sk_sp 智能指针,SkRefCnt 基类 |
| include/gpu/GpuTypes.h | skgpu::Protected 等通用类型 |
| d3d12.h | Direct3D 12 API |
| dxgi1_4.h | DXGI 格式定义 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| GrD3DBackendContext | 使用 gr_cp 和分配器接口 |
| GrD3DGpu | D3D GPU 后端实现 |
| GrD3DTexture | 纹理资源管理 |
| GrD3DRenderTarget | 渲染目标管理 |

## 设计模式与设计决策

### RAII 资源管理
gr_cp 实现 RAII:
- 构造时增加引用
- 析构时释放引用
- 异常安全

### 值语义
GrD3DTextureResourceInfo 等结构体:
- 可拷贝
- 可移动
- 聚合初始化

### 接口隔离
分离分配和资源:
- GrD3DAlloc: 内存分配元数据
- ID3D12Resource: 实际 GPU 资源
- 支持别名资源和内存复用

## 性能考量

### 引用计数开销
- COM AddRef/Release 是原子操作
- 移动语义避免引用计数
- 优先使用移动而非拷贝

### 内存分配器选择
- 默认分配器: 每次调用 CreateCommittedResource
- 自定义分配器: 池化分配,减少系统调用
- D3D12MA: 成熟的第三方解决方案

### 状态跟踪
- fResourceState 避免冗余状态转换
- 减少资源屏障开销

## 平台相关说明

### Windows 特定
- 依赖 Windows SDK
- COM 是 Windows 原生技术

### Xbox 平台
- 使用相同的 D3D12 API
- 某些扩展可能不同

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/d3d/GrD3DBackendContext.h | 使用 gr_cp 和分配器 |
| src/gpu/ganesh/d3d/GrD3DGpu.h | D3D GPU 实现 |
| src/gpu/ganesh/d3d/GrD3DResourceProvider.h | 资源创建和管理 |
| src/gpu/ganesh/d3d/GrD3DTexture.h | 纹理封装 |
