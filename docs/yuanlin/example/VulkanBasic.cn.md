# VulkanBasic

> 源文件: example/VulkanBasic.cpp

## 概述

VulkanBasic 是一个演示如何使用 Skia Ganesh Vulkan 后端的最小化示例程序。该程序展示了创建 Vulkan 实例、设备、Skia 上下文、渲染表面,以及执行简单绘制操作的完整流程。程序创建一个 16x16 像素的离屏表面,用红色清空,然后正确清理所有 Vulkan 资源。

这是 Skia 官方提供的外部客户端参考实现,展示了如何在不依赖 Skia 内部工具的情况下正确初始化和使用 Vulkan 后端。

## 架构位置

```
skia/
└── example/
    ├── VulkanBasic.cpp              # Vulkan 基础示例(140行)
    ├── HelloWorld.cpp               # 完整的窗口示例
    └── external_client/src/
        └── ganesh_vulkan.cpp        # 另一个 Vulkan 示例
```

## 主要类与结构体

### 使用的核心 Skia 类型

```cpp
skgpu::VulkanBackendContext      // Vulkan 后端上下文
GrDirectContext                  // Skia GPU 上下文
SkSurface                        // 渲染表面
SkCanvas                         // 绘图接口
```

### 使用的 Vulkan 类型

```cpp
VkInstance                       // Vulkan 实例
VkDevice                         // 逻辑设备
VkDebugUtilsMessengerEXT        // 调试信使
```

## 公共 API 函数

### main()

```cpp
int main(int argc, char** argv);
```

**功能**: 程序入口,执行完整的 Vulkan 渲染流程

**返回值**:
- `0`: 成功
- `1`: 任何步骤失败

**执行流程**:
1. 创建 Vulkan 实例和设备
2. 创建 GrDirectContext
3. 创建 SkSurface
4. 执行绘制操作
5. 清理所有资源

## 内部实现细节

### Vulkan 初始化

```cpp
skgpu::VulkanBackendContext backendContext;
VkDebugUtilsMessengerEXT debugMessenger;
std::unique_ptr<skgpu::VulkanExtensions> extensions(new skgpu::VulkanExtensions());
std::unique_ptr<sk_gpu_test::TestVkFeatures> features(new sk_gpu_test::TestVkFeatures);

if (!sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs(&instProc)) {
    return 1;
}

if (!sk_gpu_test::CreateVkBackendContext(
            instProc, &backendContext, extensions.get(), features.get(), &debugMessenger)) {
    return 1;
}
```

**关键点**:
- 使用 Skia 测试辅助函数简化设置
- 实际应用应使用 `skgpu::VulkanPreferredFeatures` 获取优化特性
- 调试信使用于开发期间的错误报告

### 内存分配器创建

```cpp
backendContext.fMemoryAllocator = skgpu::VulkanMemoryAllocators::Make(
        backendContext, skgpu::ThreadSafe::kNo);
```

**说明**:
- Skia 使用 Vulkan Memory Allocator (VMA) 管理 GPU 内存
- `ThreadSafe::kNo` 适用于单线程场景,性能更好
- 多线程应用应使用 `ThreadSafe::kYes`

### GrDirectContext 创建

```cpp
sk_sp<GrDirectContext> context = GrDirectContexts::MakeVulkan(backendContext);
if (!context) {
    fVkDestroyDevice(backendContext.fDevice, nullptr);
    if (debugMessenger != VK_NULL_HANDLE) {
        fVkDestroyDebugUtilsMessengerEXT(backendContext.fInstance, debugMessenger, nullptr);
    }
    fVkDestroyInstance(backendContext.fInstance, nullptr);
    return 1;
}
```

**错误处理**: 如果上下文创建失败,正确清理 Vulkan 资源

### 表面创建与绘制

```cpp
SkImageInfo imageInfo = SkImageInfo::Make(16, 16, kRGBA_8888_SkColorType, kPremul_SkAlphaType);

sk_sp<SkSurface> surface =
        SkSurfaces::RenderTarget(context.get(), skgpu::Budgeted::kYes, imageInfo);

surface->getCanvas()->clear(SK_ColorRED);

context->flush(surface.get());
context->submit();
```

**渲染流程**:
1. **表面创建**: 16x16 RGBA8888 格式
2. **清空**: 用红色填充
3. **flush**: 将绘制命令转换为 Vulkan 命令缓冲
4. **submit**: 提交到 GPU 队列执行

### 资源清理顺序

```cpp
surface.reset();        // 1. 先释放表面
context.reset();        // 2. 再释放上下文

// 3. 最后释放 Vulkan 对象
fVkDestroyDevice(backendContext.fDevice, nullptr);
if (debugMessenger != VK_NULL_HANDLE) {
    fVkDestroyDebugUtilsMessengerEXT(backendContext.fInstance, debugMessenger, nullptr);
}
fVkDestroyInstance(backendContext.fInstance, nullptr);
```

**关键**: 必须在销毁 Vulkan 对象之前清理所有 Skia 对象

### 函数指针获取宏

```cpp
#define ACQUIRE_INST_VK_PROC(name)                                                           \
    do {                                                                                     \
    fVk##name = reinterpret_cast<PFN_vk##name>(getProc("vk" #name, backendContext.fInstance, \
                                                       VK_NULL_HANDLE));                     \
    if (fVk##name == nullptr) {                                                              \
        SkDebugf("Function ptr for vk%s could not be acquired\n", #name);                    \
        return 1;                                                                            \
    }                                                                                        \
    } while(false)

ACQUIRE_INST_VK_PROC(DestroyInstance);
ACQUIRE_INST_VK_PROC(DestroyDebugUtilsMessengerEXT);
ACQUIRE_INST_VK_PROC(DestroyDevice);
```

**目的**: 动态获取 Vulkan 函数指针用于资源清理

## 依赖关系

### Skia 核心头文件
```cpp
#include "include/core/SkCanvas.h"
#include "include/core/SkSurface.h"
#include "include/core/SkImageInfo.h"
```

### Ganesh Vulkan 头文件
```cpp
#include "include/gpu/ganesh/GrDirectContext.h"
#include "include/gpu/ganesh/vk/GrVkDirectContext.h"
#include "include/gpu/vk/VulkanBackendContext.h"
#include "include/gpu/vk/VulkanExtensions.h"
#include "include/gpu/vk/VulkanMemoryAllocator.h"
```

### 私有头文件(仅供参考)
```cpp
#include "src/gpu/vk/vulkanmemoryallocator/VulkanMemoryAllocatorPriv.h"
#include "src/gpu/GpuTypesPriv.h"
#include "tools/gpu/vk/VkTestUtils.h"
```

**注意**: 外部客户端应实现类似功能,不应直接依赖这些私有文件

## 设计模式与设计决策

### 1. RAII 模式

使用智能指针管理资源生命周期:
```cpp
sk_sp<GrDirectContext> context;  // 自动引用计数
std::unique_ptr<skgpu::VulkanExtensions> extensions;  // 自动销毁
```

### 2. 显式清理顺序

示例展示了正确的资源释放顺序,这对 Vulkan 至关重要。

### 3. 设计决策

#### (1) 为何使用测试辅助函数?

```cpp
sk_gpu_test::CreateVkBackendContext(...)
```

- **简化示例**: 减少样板代码,聚焦核心流程
- **参考实现**: 展示了需要考虑的配置项
- **警告**: 文档明确说明不应在生产代码中依赖

#### (2) 为何创建 16x16 小表面?

- **最小化**: 展示基本功能,不需要大表面
- **快速**: 初始化和绘制都很快
- **离屏**: 不需要窗口系统

#### (3) 为何只是清空颜色?

```cpp
surface->getCanvas()->clear(SK_ColorRED);
```

- **简单性**: 验证基本绘制管线工作
- **可扩展**: 可替换为任何 SkCanvas 操作
- **教学目的**: 展示 flush/submit 流程

## 性能考量

### 1. 内存分配器配置

```cpp
skgpu::VulkanMemoryAllocators::Make(backendContext, skgpu::ThreadSafe::kNo);
```

- **单线程**: 避免同步开销
- **多线程应用**: 应使用 `ThreadSafe::kYes`

### 2. Budgeted 表面

```cpp
SkSurfaces::RenderTarget(context.get(), skgpu::Budgeted::kYes, imageInfo);
```

- **kYes**: 允许 Skia 缓存和重用 GPU 资源
- **kNo**: 适用于临时表面,避免占用缓存配额

### 3. flush vs submit

```cpp
context->flush(surface.get());  // 录制命令
context->submit();              // 提交到 GPU
```

- **flush**: 将 Skia 命令转换为 GPU 命令
- **submit**: 实际提交到 GPU 执行
- **分离的优点**: 可以批量提交多个表面

## 相关文件

### 相关示例
- **example/HelloWorld.cpp**: 完整的窗口应用示例
- **example/external_client/src/ganesh_vulkan.cpp**: 简化的 Vulkan 示例
- **example/external_client/src/ganesh_gl.cpp**: OpenGL 对比示例

### 工具文件
- **tools/gpu/vk/VkTestUtils.h**: Vulkan 测试辅助函数
- **src/gpu/vk/vulkanmemoryallocator/**: VMA 集成

### Skia Vulkan 文档
- **site/docs/user/api/skcanvas_*.md**: SkCanvas API 文档
- **site/docs/user/api/sksurface.md**: SkSurface 文档

该示例是学习 Skia Vulkan 后端的极佳起点,展示了从零开始创建 Vulkan 上下文并执行渲染的完整流程。
