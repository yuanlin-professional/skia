# tools/gpu/vk/ - Vulkan 专用测试工具

## 概述

`tools/gpu/vk/` 目录提供了一套专门用于 Vulkan GPU 后端测试的辅助工具。Vulkan 作为 Skia 支持的跨平台低级图形 API，其初始化和资源管理过程比 OpenGL 或 Metal 更加复杂，因此需要专门的工具类来简化测试代码的编写。

该目录中的工具覆盖了 Vulkan 测试的四个关键领域：
1. **后端上下文创建** (`VkTestUtils`): 封装了 VkInstance、VkDevice 的创建过程，包括物理设备选择、队列族查找、扩展加载和验证层配置
2. **测试环境管理** (`VkTestHelper`): 提供了面向 Ganesh 和 Graphite 两种后端的完整 Vulkan 测试环境，包括上下文创建、Surface 生成和同步操作
3. **内存管理** (`VkTestMemoryAllocator`): 基于 VulkanMemoryAllocator (VMA) 库实现的测试用内存分配器，提供图像和缓冲区的内存分配、映射和刷新
4. **YCbCr 采样器** (`VkYcbcrSamplerHelper`): 管理 Vulkan 的 YCbCr 转换采样器，这种采样器因其不可变性而在测试中特别重要

这些工具类被 Skia 的 GPU 测试套件（`tests/` 目录）、窗口上下文（`tools/window/`）和 Viewer 等多个组件广泛使用。它们同时支持 Ganesh（传统 GPU 后端）和 Graphite（新 GPU 后端）两种模式。

## 架构图

```
+------------------------------------------------------------------+
|                  tools/gpu/vk/ Vulkan 测试工具                     |
|                                                                   |
|  +----------------------------+  +-----------------------------+  |
|  |      VkTestUtils           |  |      VkTestHelper           |  |
|  |  底层后端上下文创建          |  |  高层测试环境管理             |  |
|  |                            |  |                             |  |
|  |  LoadVkLibraryAndGetProc() |  |  Make(TestType, isProtected)|  |
|  |  CreateVkBackendContext()  |  |  createSurface()            |  |
|  |                            |  |  submitAndWaitForCompletion()|  |
|  |  输出:                     |  |                             |  |
|  |  - VulkanBackendContext    |  |  提供:                       |  |
|  |  - VulkanExtensions        |  |  - directContext() [Ganesh] |  |
|  |  - TestVkFeatures          |  |  - context() [Graphite]     |  |
|  |  - VkDebugUtilsMessenger   |  |  - recorder() [Graphite]    |  |
|  +----------------------------+  +-----------------------------+  |
|              ^                              |                      |
|              |                              | 使用                  |
|              +------------------------------+                      |
|                                                                   |
|  +----------------------------+  +-----------------------------+  |
|  |  VkTestMemoryAllocator     |  |  VkYcbcrSamplerHelper       |  |
|  |  测试用内存分配器           |  |  YCbCr 采样器管理            |  |
|  |                            |  |                             |  |
|  |  继承: VulkanMemoryAlloc   |  |  Ganesh:                    |  |
|  |  基于: VMA (vk_mem_alloc)  |  |  - createGrBackendTexture() |  |
|  |                            |  |  - grBackendTexture()       |  |
|  |  - allocateImageMemory()   |  |                             |  |
|  |  - allocateBufferMemory()  |  |  Graphite:                  |  |
|  |  - freeMemory()            |  |  - createBackendTexture()   |  |
|  |  - mapMemory/unmapMemory() |  |  - backendTexture()         |  |
|  |  - flushMemory()           |  |                             |  |
|  |  - totalAllocatedAndUsed() |  |  - isYCbCrSupported()       |  |
|  +----------------------------+  |  - GetExpectedY/UV()        |  |
|                                  +-----------------------------+  |
|                                                                   |
|  +----------------------------+                                   |
|  |  VulkanDefines.h           |                                   |
|  |  平台相关 Vulkan 头文件     |                                   |
|  |  引入正确的 vulkan.h       |                                   |
|  +----------------------------+                                   |
+------------------------------------------------------------------+
```

## 目录结构

```
tools/gpu/vk/
|-- BUILD.bazel                   # Bazel 构建定义
|-- VulkanDefines.h               # Vulkan 平台头文件引入
|-- VkTestUtils.h                 # Vulkan 后端上下文创建工具
|-- VkTestUtils.cpp               # 实现（VkInstance/VkDevice 创建）
|-- VkTestHelper.h                # Vulkan 测试环境辅助器
|-- VkTestHelper.cpp              # 实现（Ganesh/Graphite 环境管理）
|-- VkTestMemoryAllocator.h       # 测试用 Vulkan 内存分配器
|-- VkTestMemoryAllocator.cpp     # 实现（基于 VMA）
|-- VkYcbcrSamplerHelper.h        # YCbCr 采样器辅助器
+-- VkYcbcrSamplerHelper.cpp      # 实现（YCbCr 纹理创建与采样）
```

## 关键类与函数

### VkTestUtils - 底层后端上下文创建

```cpp
// tools/gpu/vk/VkTestUtils.h
namespace sk_gpu_test {

// Vulkan 设备特征集合
struct TestVkFeatures {
    VkPhysicalDeviceFeatures2 deviceFeatures;
    skgpu::VulkanPreferredFeatures skiaFeatures;     // Skia 需要的特性
    VkPhysicalDeviceProtectedMemoryFeatures protectedMemoryFeatures;
};

// 加载 Vulkan 库并获取实例函数指针
bool LoadVkLibraryAndGetProcAddrFuncs(PFN_vkGetInstanceProcAddr*);

// 呈现能力检查回调
using CanPresentFn = std::function<bool(VkInstance, VkPhysicalDevice, uint32_t queueFamilyIndex)>;

// 创建完整的 Vulkan 后端上下文
bool CreateVkBackendContext(
    PFN_vkGetInstanceProcAddr getInstProc,
    skgpu::VulkanBackendContext* ctx,        // 输出: 后端上下文
    skgpu::VulkanExtensions*,                // 输出: 扩展信息
    TestVkFeatures*,                         // 输出: 设备特征
    VkDebugUtilsMessengerEXT* debugMessenger,// 输出: 调试消息器
    uint32_t* presentQueueIndexPtr = nullptr,// 输出: 呈现队列索引
    const CanPresentFn& canPresent = {},     // 呈现能力检查
    bool isProtected = false                 // 是否创建受保护上下文
);
}
```

### VkTestHelper - 高层测试环境管理

```cpp
// tools/gpu/vk/VkTestHelper.h
class VkTestHelper {
public:
    // 工厂方法，根据测试类型创建 Ganesh 或 Graphite 版本
    static std::unique_ptr<VkTestHelper> Make(skiatest::TestType, bool isProtected);

    virtual bool isValid() const = 0;

    // 创建测试用 SkSurface
    virtual sk_sp<SkSurface> createSurface(SkISize, bool textureable, bool isProtected) = 0;

    // 提交并等待 GPU 完成
    virtual void submitAndWaitForCompletion(bool* completionMarker) = 0;

    // GPU 上下文访问（Ganesh 或 Graphite）
    virtual GrDirectContext* directContext() { return nullptr; }
    virtual skgpu::graphite::Recorder* recorder() { return nullptr; }
    virtual skgpu::graphite::Context* context() { return nullptr; }

protected:
    bool setupBackendContext();   // 调用 CreateVkBackendContext
    virtual bool init() = 0;     // 子类特定初始化

    // Vulkan 函数指针（通过 DECLARE_VK_PROC 宏声明）
    // 包括: DestroyInstance, DeviceWaitIdle, DestroyDevice,
    //       CreateImage, DestroyImage, AllocateMemory, FreeMemory,
    //       BindImageMemory, MapMemory, UnmapMemory, 等

    VkDevice fDevice;
    skgpu::VulkanExtensions fExtensions;
    TestVkFeatures fFeatures;
    VkDebugUtilsMessengerEXT fDebugMessenger;
    skgpu::VulkanBackendContext fBackendContext;
};
```

### VkTestMemoryAllocator - 测试用内存分配器

```cpp
// tools/gpu/vk/VkTestMemoryAllocator.h
namespace sk_gpu_test {
class VkTestMemoryAllocator : public skgpu::VulkanMemoryAllocator {
public:
    static sk_sp<VulkanMemoryAllocator> Make(
        VkInstance, VkPhysicalDevice, VkDevice,
        uint32_t physicalDeviceVersion,
        const skgpu::VulkanExtensions*,
        const skgpu::VulkanInterface*
    );

    // VulkanMemoryAllocator 接口实现
    VkResult allocateImageMemory(VkImage, uint32_t flags, VulkanBackendMemory*) override;
    VkResult allocateBufferMemory(VkBuffer, BufferUsage, uint32_t flags, VulkanBackendMemory*) override;
    void freeMemory(const VulkanBackendMemory&) override;
    void getAllocInfo(const VulkanBackendMemory&, VulkanAlloc*) const override;
    VkResult mapMemory(const VulkanBackendMemory&, void** data) override;
    void unmapMemory(const VulkanBackendMemory&) override;
    VkResult flushMemory(const VulkanBackendMemory&, VkDeviceSize offset, VkDeviceSize size) override;
    VkResult invalidateMemory(const VulkanBackendMemory&, VkDeviceSize offset, VkDeviceSize size) override;
    std::pair<uint64_t, uint64_t> totalAllocatedAndUsedMemory() const override;

private:
    VmaAllocator fAllocator;  // VMA 分配器实例
};
}
```

### VkYcbcrSamplerHelper - YCbCr 采样器

```cpp
// tools/gpu/vk/VkYcbcrSamplerHelper.h
class VkYcbcrSamplerHelper {
public:
    // Graphite 构造
    VkYcbcrSamplerHelper(const graphite::VulkanSharedContext*);
    bool createBackendTexture(uint32_t width, uint32_t height);
    const graphite::BackendTexture& backendTexture() const;

    // Ganesh 构造
    VkYcbcrSamplerHelper(GrDirectContext*);
    bool createGrBackendTexture(uint32_t width, uint32_t height);
    const GrBackendTexture& grBackendTexture() const;

    // 通用
    bool isYCbCrSupported();
    static int GetExpectedY(int x, int y, int width, int height);
    static std::pair<int, int> GetExpectedUV(int x, int y, int width, int height);

private:
    VkImage fImage;               // Vulkan 图像（YCbCr 格式）
    VkDeviceMemory fImageMemory;  // 图像内存
};
```

## 依赖关系

```
tools/gpu/vk/
    |
    +---> Vulkan SDK
    |       +---> vulkan/vulkan.h (通过 VulkanDefines.h)
    |       +---> VkInstance, VkDevice, VkPhysicalDevice
    |       +---> VkImage, VkDeviceMemory, VkSampler
    |       +---> VkDebugUtilsMessengerEXT
    |
    +---> VulkanMemoryAllocator (VMA)
    |       +---> vk_mem_alloc.h (第三方库)
    |
    +---> Skia GPU 抽象
    |       +---> skgpu::VulkanBackendContext
    |       +---> skgpu::VulkanExtensions
    |       +---> skgpu::VulkanInterface
    |       +---> skgpu::VulkanMemoryAllocator
    |       +---> skgpu::VulkanPreferredFeatures
    |
    +---> Ganesh (SK_GANESH, 条件编译)
    |       +---> GrDirectContext, GrBackendTexture
    |       +---> GrVkGpu, GrVkTypes
    |
    +---> Graphite (SK_GRAPHITE, 条件编译)
    |       +---> graphite::Context, graphite::Recorder
    |       +---> graphite::BackendTexture
    |       +---> graphite::VulkanSharedContext
    |
    +---> Skia Core
            +---> SkSurface, SkRefCnt
            +---> SkTypes, SkISize
```

## 设计模式分析

### 1. 工厂方法 + 策略模式

`VkTestHelper::Make()` 根据 `TestType` 参数创建不同的子类实例（Ganesh 版本或 Graphite 版本），体现了工厂方法模式。子类通过覆盖虚函数实现不同的 GPU 后端策略。

### 2. 外观模式 (Facade)

`CreateVkBackendContext()` 作为外观函数，封装了 Vulkan 初始化的大量步骤：加载实例级函数、创建 VkInstance、枚举物理设备、选择队列族、创建 VkDevice、加载设备级函数。调用者只需一次函数调用即可获得完整的 Vulkan 上下文。

### 3. 适配器模式 (Adapter)

`VkTestMemoryAllocator` 将 VMA 库的接口适配为 Skia 的 `VulkanMemoryAllocator` 接口。VMA 是一个独立的第三方库，其 API 风格与 Skia 不同，适配器在两者之间提供了平滑的转换。

### 4. 辅助器模式 (Helper)

`VkYcbcrSamplerHelper` 封装了 YCbCr 纹理的创建和管理逻辑。YCbCr 格式的 Vulkan 纹理需要特殊的采样器转换和内存布局，该辅助器隐藏了这些复杂性，提供简单的 `createBackendTexture()` 接口。

### 5. 条件编译双模式

整个目录的代码同时支持 Ganesh 和 Graphite 两种 GPU 后端，通过 `#if defined(SK_GANESH)` 和 `#if defined(SK_GRAPHITE)` 条件编译实现。这种设计允许在不同的构建配置下复用相同的测试工具。

## 相关文档与参考

- **GPU 测试工具**: `tools/gpu/README.md`
- **Vulkan 规范**: https://www.khronos.org/registry/vulkan/
- **VulkanMemoryAllocator**: https://gpuopen.com/vulkan-memory-allocator/
- **Vulkan YCbCr 采样**: `VK_KHR_sampler_ycbcr_conversion` 扩展
- **Skia Vulkan 集成**: `include/gpu/vk/` 头文件
- **Ganesh Vulkan 后端**: `src/gpu/ganesh/vk/`
- **Graphite Vulkan 后端**: `src/gpu/graphite/vk/`
