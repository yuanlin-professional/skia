# VkTestContext

> 源文件：tools/ganesh/vk/VkTestContext.h, tools/ganesh/vk/VkTestContext.cpp

## 概述

VkTestContext 是 Skia Ganesh 测试框架中用于 Vulkan 后端的测试上下文实现。该类继承自 TestContext 基类，封装了 Vulkan API 的初始化、设备管理和上下文创建逻辑，为 Vulkan GPU 测试提供统一的测试环境。

VkTestContext 的主要职责包括：
- 加载 Vulkan 动态库并获取函数指针
- 创建 Vulkan 实例、物理设备和逻辑设备
- 管理 Vulkan 扩展和特性
- 支持调试消息和验证层
- 创建 Ganesh Vulkan 直接上下文
- 支持上下文共享（多个测试上下文共享同一 Vulkan 设备）
- 正确清理 Vulkan 资源

该模块利用 Vulkan 的跨平台特性，在 Windows、Linux、macOS 和 Android 等平台上提供一致的测试接口。它还支持可选的验证层和调试工具，帮助开发者捕获 Vulkan API 使用错误。

## 架构位置

VkTestContext 位于 Ganesh 测试工具的 Vulkan 平台实现层：

- **基类**：`tools/ganesh/TestContext` - 测试上下文抽象基类

- **同级实现**：
  - `tools/ganesh/gl/GLTestContext` - OpenGL 实现
  - `tools/ganesh/mtl/MtlTestContext` - Metal 实现
  - `tools/ganesh/d3d/D3DTestContext` - Direct3D 实现
  - `tools/ganesh/mock/MockTestContext` - Mock 实现

- **依赖的工具模块**：
  - `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试工具函数
  - `tools/gpu/vk/VulkanDefines.h` - Vulkan 定义
  - `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文
  - `include/gpu/vk/VulkanExtensions.h` - Vulkan 扩展管理

- **Ganesh Vulkan 后端**：
  - `include/gpu/ganesh/vk/GrVkDirectContext.h` - Vulkan 直接上下文
  - `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU 实现

VkTestContext 作为 Vulkan 测试的入口点，协调了 Vulkan 底层 API 和 Ganesh 高层接口。

## 主要类与结构体

### VkTestContext（抽象类）

```cpp
class VkTestContext : public TestContext {
public:
    GrBackendApi backend() override { return GrBackendApi::kVulkan; }

    const skgpu::VulkanBackendContext& getVkBackendContext() const;
    const skgpu::VulkanExtensions* getVkExtensions() const;
    const sk_gpu_test::TestVkFeatures* getVkFeatures() const;

protected:
    VkTestContext(const skgpu::VulkanBackendContext& vk,
                  const skgpu::VulkanExtensions* extensions,
                  const sk_gpu_test::TestVkFeatures* features,
                  bool ownsContext,
                  VkDebugUtilsMessengerEXT debugMessenger,
                  PFN_vkDestroyDebugUtilsMessengerEXT destroyCallback);

    skgpu::VulkanBackendContext fVk;
    const skgpu::VulkanExtensions* fExtensions;
    const sk_gpu_test::TestVkFeatures* fFeatures;
    bool fOwnsContext;
    VkDebugUtilsMessengerEXT fDebugMessenger;
    PFN_vkDestroyDebugUtilsMessengerEXT fDestroyDebugUtilsMessengerEXT;
};
```

VkTestContext 是一个中间抽象层，提供 Vulkan 特定的访问器，但不实现完整的创建逻辑。实际实现由内部的 VkTestContextImpl 类提供。

### CreatePlatformVkTestContext（工厂函数）

```cpp
VkTestContext* CreatePlatformVkTestContext(VkTestContext* sharedContext);
```

创建平台特定的 Vulkan 测试上下文。

**参数**：
- `sharedContext` - 可选的共享上下文。如果提供，新上下文将共享 Vulkan 设备和扩展

**返回值**：
- 成功时返回 VkTestContext 指针
- 失败时返回 `nullptr`（Vulkan 不可用、设备不支持等）

### VkTestContextImpl（内部实现类）

```cpp
class VkTestContextImpl : public sk_gpu_test::VkTestContext {
public:
    static VkTestContext* Create(VkTestContext* sharedContext);
    ~VkTestContextImpl() override;

    void testAbandon() override;
    sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override;

protected:
    void teardown() override;
    void onPlatformMakeNotCurrent() const override;
    void onPlatformMakeCurrent() const override;
    std::function<void()> onPlatformGetAutoContextRestore() const override;
};
```

位于匿名命名空间的完整实现类，处理 Vulkan 的所有细节。

## 公共 API 函数

### CreatePlatformVkTestContext

```cpp
VkTestContext* CreatePlatformVkTestContext(VkTestContext* sharedContext) {
    return VkTestContextImpl::Create(sharedContext);
}
```

公共工厂函数，委托给内部实现类的静态 Create 方法。

### backend()

```cpp
GrBackendApi backend() override { return GrBackendApi::kVulkan; }
```

返回 Vulkan 后端标识。

### getVkBackendContext()

```cpp
const skgpu::VulkanBackendContext& getVkBackendContext() const { return fVk; }
```

获取底层 Vulkan 后端上下文，包含 Vulkan 实例、设备、队列等信息。测试代码可以使用此上下文直接调用 Vulkan API。

### getVkExtensions()

```cpp
const skgpu::VulkanExtensions* getVkExtensions() const { return fExtensions; }
```

获取已启用的 Vulkan 扩展列表。测试可以查询特定扩展是否可用。

### getVkFeatures()

```cpp
const sk_gpu_test::TestVkFeatures* getVkFeatures() const { return fFeatures; }
```

获取设备特性信息，用于测试特定 Vulkan 特性的支持情况。

## 内部实现细节

### 上下文创建流程

VkTestContextImpl::Create 实现了完整的创建逻辑：

**共享上下文路径**：
```cpp
if (sharedContext) {
    backendContext = sharedContext->getVkBackendContext();
    extensions = sharedContext->getVkExtensions();
    features = sharedContext->getVkFeatures();
    ownsContext = false;  // 子上下文不负责清理
}
```

**新上下文路径**：
```cpp
else {
    PFN_vkGetInstanceProcAddr instProc;
    if (!sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs(&instProc)) {
        return nullptr;
    }

    skgpu::VulkanExtensions* ownedExtensions = new skgpu::VulkanExtensions();
    sk_gpu_test::TestVkFeatures* ownedFeatures = new sk_gpu_test::TestVkFeatures;

    if (!sk_gpu_test::CreateVkBackendContext(instProc,
                                             &backendContext,
                                             ownedExtensions,
                                             ownedFeatures,
                                             &debugMessenger,
                                             nullptr,
                                             sk_gpu_test::CanPresentFn(),
                                             createProtectedContext)) {
        delete ownedExtensions;
        delete ownedFeatures;
        return nullptr;
    }

    if (debugMessenger != VK_NULL_HANDLE) {
        destroyCallback = (PFN_vkDestroyDebugUtilsMessengerEXT)instProc(
                backendContext.fInstance, "vkDestroyDebugUtilsMessengerEXT");
    }
}
```

创建流程包括：
1. 加载 Vulkan 库和函数指针
2. 创建扩展和特性对象
3. 调用 CreateVkBackendContext 创建 Vulkan 设备
4. 设置调试消息（如果启用验证层）
5. 构造 VkTestContextImpl 实例

### makeContext() - Ganesh 上下文创建

```cpp
sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override {
    return GrDirectContexts::MakeVulkan(fVk, options);
}
```

使用 Vulkan 后端上下文创建 Ganesh 直接上下文。这是将低层 Vulkan 资源连接到高层 Ganesh API 的关键步骤。

### teardown() - 资源清理

```cpp
void teardown() override {
    INHERITED::teardown();
    fVk.fMemoryAllocator.reset();
    if (fOwnsContext) {
        ACQUIRE_VK_PROC_LOCAL(DeviceWaitIdle, fVk.fInstance);
        ACQUIRE_VK_PROC_LOCAL(DestroyDevice, fVk.fInstance);
        ACQUIRE_VK_PROC_LOCAL(DestroyInstance, fVk.fInstance);
        grVkDeviceWaitIdle(fVk.fDevice);
        grVkDestroyDevice(fVk.fDevice, nullptr);
#ifdef SK_ENABLE_VK_LAYERS
        if (fDebugMessenger != VK_NULL_HANDLE) {
            fDestroyDebugUtilsMessengerEXT(fVk.fInstance, fDebugMessenger, nullptr);
        }
#endif
        grVkDestroyInstance(fVk.fInstance, nullptr);

        delete fExtensions;
        delete fFeatures;
    }
}
```

清理流程：
1. 调用基类 teardown（清理 GPU 计时器等）
2. 重置内存分配器
3. 如果拥有上下文所有权：
   - 等待设备空闲
   - 销毁逻辑设备
   - 销毁调试消息（如果启用）
   - 销毁 Vulkan 实例
   - 删除扩展和特性对象

### ACQUIRE_VK_PROC_LOCAL 宏

```cpp
#define ACQUIRE_VK_PROC_LOCAL(name, inst)                                            \
    PFN_vk##name grVk##name =                                                        \
            reinterpret_cast<PFN_vk##name>(fVk.fGetProc("vk" #name, inst, nullptr)); \
    do {                                                                             \
        if (grVk##name == nullptr) {                                                 \
            SkDebugf("Function ptr for vk%s could not be acquired\n", #name);        \
            return;                                                                  \
        }                                                                            \
    } while (0)
```

这个宏简化了 Vulkan 函数指针的获取，包含错误检查。Vulkan 的动态加载模型要求通过函数指针访问 API。

### 上下文切换操作

```cpp
void onPlatformMakeNotCurrent() const override {}
void onPlatformMakeCurrent() const override {}
std::function<void()> onPlatformGetAutoContextRestore() const override { return nullptr; }
```

Vulkan 没有"当前上下文"的概念（不像 OpenGL），因此这些操作为空。

### 栅栏支持

```cpp
VkTestContextImpl(...) : VkTestContext(...) {
    fFenceSupport = true;
}
```

Vulkan 支持栅栏同步，构造函数中设置此标志。

### 保护内存支持

```cpp
extern bool gCreateProtectedContext;
static const bool& createProtectedContext = gCreateProtectedContext;
```

支持创建受保护的 Vulkan 上下文，用于安全内容渲染（如 DRM 视频）。这个全局变量由测试框架设置。

## 依赖关系

### Vulkan 核心 API
- Vulkan 动态库（`vulkan-1.dll` / `libvulkan.so` / `libvulkan.dylib`）
- Vulkan 头文件（通过 VulkanDefines.h 包含）

### Skia Vulkan 支持
- `skgpu::VulkanBackendContext` - 后端上下文结构
- `skgpu::VulkanExtensions` - 扩展管理
- `skgpu::VulkanMemoryAllocator` - 内存分配器
- `GrDirectContexts::MakeVulkan` - 上下文工厂

### 测试工具
- `sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs` - 库加载
- `sk_gpu_test::CreateVkBackendContext` - 后端创建
- `sk_gpu_test::TestVkFeatures` - 特性结构

### 调试工具
- `VkDebugUtilsMessengerEXT` - 调试消息
- `vkDestroyDebugUtilsMessengerEXT` - 调试消息销毁

## 设计模式与设计决策

### 条件编译

整个模块使用条件编译保护：
```cpp
#ifdef SK_VULKAN
// 所有 Vulkan 代码
#endif
```

这允许在不支持 Vulkan 的平台上编译 Skia，模块会被完全排除。

### 所有权语义

`fOwnsContext` 标志区分所有权：
- **ownsContext = true**：负责清理 Vulkan 资源
- **ownsContext = false**：共享上下文，不清理资源

这支持多个测试上下文共享单个 Vulkan 设备，提高测试性能。

### 延迟函数指针获取

Vulkan 函数指针在需要时获取（通过宏），而非预先加载所有函数。这减少了初始化开销。

### 两层抽象

设计分为两层：
- **VkTestContext**：公共接口，提供访问器
- **VkTestContextImpl**：内部实现，隐藏细节

这种分离提供了清晰的 API 边界和实现灵活性。

### 工厂模式

使用静态 Create 方法而非公共构造函数：
```cpp
static VkTestContext* Create(VkTestContext* sharedContext);
```

这允许创建过程中的复杂初始化和错误处理，失败时返回 nullptr。

## 性能考量

### 设备共享

支持共享 Vulkan 设备：
```cpp
VkTestContext* CreatePlatformVkTestContext(VkTestContext* sharedContext);
```

创建 Vulkan 设备很昂贵（可能需要数百毫秒），共享设备大幅提升测试套件性能。

### 验证层开销

调试消息和验证层有显著性能开销。生产构建中应禁用：
```cpp
#ifdef SK_ENABLE_VK_LAYERS
if (fDebugMessenger != VK_NULL_HANDLE) {
    fDestroyDebugUtilsMessengerEXT(fVk.fInstance, fDebugMessenger, nullptr);
}
#endif
```

### 内存分配器

使用高效的 Vulkan 内存分配器（VulkanMemoryAllocator），减少内存碎片和分配开销。

### 无上下文切换开销

Vulkan 不需要上下文切换（不像 OpenGL），避免了该开销。

## 相关文件

### 基类和同级实现
- `tools/ganesh/TestContext.h/cpp` - 测试上下文基类
- `tools/ganesh/gl/GLTestContext.h/cpp` - OpenGL 实现
- `tools/ganesh/mtl/MtlTestContext.h/.mm` - Metal 实现
- `tools/ganesh/d3d/D3DTestContext.h/cpp` - Direct3D 实现

### Vulkan 测试工具
- `tools/gpu/vk/VkTestUtils.h/cpp` - Vulkan 测试工具函数
- `tools/gpu/vk/VulkanDefines.h` - Vulkan 定义和包含

### Skia Vulkan 支持
- `include/gpu/vk/VulkanBackendContext.h` - 后端上下文
- `include/gpu/vk/VulkanExtensions.h` - 扩展管理
- `include/gpu/vk/VulkanMemoryAllocator.h` - 内存分配器
- `include/gpu/ganesh/vk/GrVkDirectContext.h` - Vulkan 直接上下文

### Ganesh Vulkan 实现
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU 实现
- `src/gpu/ganesh/vk/GrVkCaps.h` - Vulkan 能力
