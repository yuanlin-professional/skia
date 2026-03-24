# VulkanGraphiteContext

> 源文件: `include/gpu/graphite/vk/VulkanGraphiteContext.h`

## 概述
VulkanGraphiteContext.h 定义了创建 Skia Graphite Vulkan 上下文的工厂函数。该文件是 Graphite 渲染系统中 Vulkan 后端的入口点,提供了将 Vulkan 设备和资源封装为 Graphite 上下文的标准接口,使应用能够使用 Graphite 的高性能渲染能力。

## 架构位置
该文件位于 Skia Graphite GPU 后端的公共接口层,属于 `skgpu::graphite` 命名空间。它是 Vulkan 后端初始化的顶层 API,连接客户端的 Vulkan 资源与 Graphite 内部实现,位于应用层和渲染系统内核之间。

## 主要 API

### ContextFactory 命名空间

#### `MakeVulkan`
```cpp
SK_API std::unique_ptr<Context> MakeVulkan(
    const VulkanBackendContext& backendContext,
    const ContextOptions& options);
```

**功能**: 从 Vulkan 后端上下文创建 Graphite 渲染上下文

**参数**:
- `backendContext`: Vulkan 后端上下文,包含 VkInstance、VkDevice、VkQueue 等必需资源
- `options`: Graphite 上下文选项,配置缓存、调试、线程模型等

**返回值**:
- 成功: 返回有效的 `std::unique_ptr<Context>`
- 失败: 返回 `nullptr` (通常由于资源不足或配置无效)

**前置条件**:
1. `backendContext` 中的所有 Vulkan 对象必须有效
2. Vulkan 设备必须支持 Graphite 需要的特性和扩展
3. 内存分配器必须已正确实现并设置
4. Vulkan API 版本至少为 1.1

**使用场景**:
- 应用启动时初始化 Graphite 渲染系统
- 切换渲染后端 (如从 CPU 渲染切换到 GPU)
- 创建多个独立的渲染上下文 (多窗口应用)

## 典型使用流程

### 1. 准备 Vulkan 资源
```cpp
#include "include/gpu/vk/VulkanBackendContext.h"
#include "include/gpu/vk/VulkanMemoryAllocator.h"

// 创建 Vulkan 实例
VkInstance instance = createVulkanInstance();

// 选择物理设备
VkPhysicalDevice physicalDevice = selectBestGpu(instance);

// 创建逻辑设备
VkDevice device = createLogicalDevice(physicalDevice);

// 获取图形队列
uint32_t queueFamilyIndex = findGraphicsQueueFamily(physicalDevice);
VkQueue queue;
vkGetDeviceQueue(device, queueFamilyIndex, 0, &queue);

// 创建内存分配器 (推荐使用 VMA)
sk_sp<skgpu::VulkanMemoryAllocator> memoryAllocator =
    createVulkanMemoryAllocator(instance, physicalDevice, device);
```

### 2. 填充后端上下文
```cpp
skgpu::VulkanBackendContext backendContext;
backendContext.fInstance = instance;
backendContext.fPhysicalDevice = physicalDevice;
backendContext.fDevice = device;
backendContext.fQueue = queue;
backendContext.fGraphicsQueueIndex = queueFamilyIndex;
backendContext.fMaxAPIVersion = VK_API_VERSION_1_1;
backendContext.fVkExtensions = &enabledExtensions;
backendContext.fDeviceFeatures2 = &enabledFeatures;
backendContext.fMemoryAllocator = memoryAllocator;
backendContext.fGetProc = [](const char* name, VkInstance inst, VkDevice dev) {
    if (dev != VK_NULL_HANDLE) return vkGetDeviceProcAddr(dev, name);
    return vkGetInstanceProcAddr(inst, name);
};
```

### 3. 配置 Graphite 选项
```cpp
#include "include/gpu/graphite/ContextOptions.h"

skgpu::graphite::ContextOptions options;

// 配置着色器缓存
options.fShaderCacheStrategy = ShaderCacheStrategy::kBackendSource;
options.fPersistentCache = myPersistentCache;

// 配置内存预算
options.fGpuBudgetInBytes = 256 * 1024 * 1024;  // 256 MB

// 启用调试功能 (开发版本)
#if SK_DEBUG
options.fAllowPathMaskCaching = true;
options.fReduceOpsTaskSplitting = ReduceOpsTaskSplitting::kDisabled;
#endif
```

### 4. 创建 Graphite 上下文
```cpp
#include "include/gpu/graphite/vk/VulkanGraphiteContext.h"

std::unique_ptr<skgpu::graphite::Context> graphiteContext =
    skgpu::graphite::ContextFactory::MakeVulkan(backendContext, options);

if (!graphiteContext) {
    // 处理失败情况
    fprintf(stderr, "Failed to create Graphite Vulkan context\n");
    return;
}

// 上下文创建成功,可以开始渲染
```

### 5. 使用 Graphite 进行渲染
```cpp
// 创建 Recorder
std::unique_ptr<skgpu::graphite::Recorder> recorder =
    graphiteContext->makeRecorder();

// 创建渲染表面
sk_sp<SkSurface> surface = SkSurfaces::RenderTarget(
    recorder.get(), imageInfo, surfaceProps);

// 绘制
SkCanvas* canvas = surface->getCanvas();
canvas->clear(SK_ColorWHITE);
canvas->drawRect(SkRect::MakeXYWH(10, 10, 100, 100), paint);

// 提交录制
std::unique_ptr<skgpu::graphite::Recording> recording = recorder->snap();
skgpu::graphite::InsertRecordingInfo info;
info.fRecording = recording.get();
graphiteContext->insertRecording(info);
graphiteContext->submit();
```

## 内部实现细节

### 初始化流程
`MakeVulkan` 内部执行以下步骤:
1. **验证后端上下文**: 检查所有必需字段非空
2. **查询设备能力**: 获取物理设备属性和特性
3. **创建资源管理器**: 初始化纹理、缓冲区、管线缓存
4. **初始化命令管理器**: 创建命令池和命令缓冲区
5. **设置同步机制**: 创建信号量和栅栏
6. **返回上下文**: 如果所有步骤成功,返回有效上下文

### 失败情况
返回 `nullptr` 的常见原因:
- `backendContext` 中的字段无效 (如 `VK_NULL_HANDLE`)
- 设备不支持必需的 Vulkan 特性 (如描述符索引)
- 内存分配器未提供或实现不正确
- 函数指针获取失败 (如 `fGetProc` 返回空)
- 内部资源创建失败 (内存不足、驱动问题)

### 线程模型
创建的 `Context` 对象线程安全性:
- **Context 本身**: 内部使用锁保护,可从多线程调用部分 API
- **Recorder**: 必须在单线程中使用
- **Recording**: 提交前不应修改
- **建议**: 每个线程创建独立的 Recorder

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAPI.h | SK_API 宏定义 |
| skgpu::VulkanBackendContext (前向声明) | Vulkan 后端配置 |
| skgpu::graphite::Context (前向声明) | Graphite 上下文类 |
| skgpu::graphite::ContextOptions (前向声明) | 上下文选项 |

### 被依赖的模块
- 应用初始化代码: 调用工厂函数创建上下文
- Graphite 内部实现: 具体的 Vulkan 上下文类
- 渲染管线: 使用上下文创建资源和提交命令

## 设计模式与设计决策

### 工厂方法模式 (Factory Method)
使用命名空间级别的工厂函数而非构造函数:
- **优势**:
  - 描述性命名 (`MakeVulkan` 清楚表明创建 Vulkan 后端)
  - 返回智能指针,明确所有权
  - 失败时可返回 `nullptr`,无需异常
  - 支持未来添加更多创建变体

### 依赖注入 (Dependency Injection)
通过 `VulkanBackendContext` 注入所有依赖:
- **解耦**: Graphite 不负责创建 Vulkan 资源
- **灵活性**: 客户端完全控制设备选择和配置
- **可测试性**: 可注入模拟对象进行单元测试

### 单一职责原则 (Single Responsibility)
该头文件只包含上下文创建功能:
- 不包含类型定义 (在 `VulkanGraphiteTypes.h`)
- 不包含资源创建 (在其他工具函数中)
- 专注于上下文工厂职责

## 性能考量

### 创建开销
`MakeVulkan` 的性能特征:
- **时间开销**: 通常 10-100ms (取决于驱动和硬件)
- **内存分配**: 分配管线缓存、命令池等资源
- **建议**: 在应用启动时创建,避免运行时动态创建

### 资源复用
多个 `Context` 共享底层资源:
- **物理设备**: 多个 Context 可使用同一 `VkDevice`
- **内存分配器**: 可共享同一分配器实例
- **管线缓存**: 通过 `ContextOptions` 共享持久化缓存

### 上下文切换
如果需要多个上下文:
- **单上下文**: 更简单,性能最佳
- **多上下文**: 用于不同窗口或隔离渲染任务
- **开销**: 每个上下文独立的命令缓冲区和同步对象

## 平台相关说明

### Android
- **Vulkan 1.1+**: 确保 API Level 28 (Android 9) 或更高
- **扩展**: 可能需要 `VK_ANDROID_external_memory_android_hardware_buffer`
- **内存管理**: 注意移动设备的内存限制

### Windows/Linux
- **驱动**: 确保 GPU 驱动支持 Vulkan 1.1+
- **验证层**: 开发时启用,发布版本禁用
- **扩展**: 可能需要 `VK_KHR_swapchain` 用于显示

### macOS (通过 MoltenVK)
- **MoltenVK 版本**: 需要较新版本支持 Vulkan 1.1
- **特性限制**: 某些 Vulkan 特性可能不支持或性能较差
- **Metal 底层**: 实际调用转换为 Metal API

## 错误处理

### 检查创建结果
```cpp
auto context = skgpu::graphite::ContextFactory::MakeVulkan(backendContext, options);
if (!context) {
    // 启用 Vulkan 验证层获取详细错误
    // 检查 backendContext 的所有字段
    // 验证设备特性支持
    // 检查内存分配器实现
    handleError("Graphite context creation failed");
    return;
}
```

### 调试失败
**启用 Vulkan 验证层**:
```cpp
std::vector<const char*> layers = {"VK_LAYER_KHRONOS_validation"};
VkInstanceCreateInfo instanceInfo = {
    .enabledLayerCount = layers.size(),
    .ppEnabledLayerNames = layers.data(),
};
```

**检查特性支持**:
```cpp
VkPhysicalDeviceFeatures2 features2 = {};
features2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;
vkGetPhysicalDeviceFeatures2(physicalDevice, &features2);
// 确认 Graphite 需要的特性已启用
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/vk/VulkanBackendContext.h | 定义 VulkanBackendContext 结构体 |
| include/gpu/graphite/Context.h | Graphite 上下文基类 |
| include/gpu/graphite/ContextOptions.h | 上下文配置选项 |
| include/gpu/graphite/vk/VulkanGraphiteTypes.h | Vulkan 特定类型 |
| include/gpu/graphite/vk/VulkanGraphiteUtils.h | 已弃用,重定向到此文件 |
| src/gpu/graphite/vk/VulkanGraphiteContext.cpp | 实际实现代码 |

## 常见问题与解决方案

### 问题 1: 创建返回 nullptr
**症状**: `MakeVulkan` 返回空指针
**原因**: 后端上下文配置错误或资源无效
**解决**:
1. 检查所有 Vulkan 对象是否有效 (非 `VK_NULL_HANDLE`)
2. 启用验证层查看错误信息
3. 确认内存分配器已正确实现
4. 验证 `fGetProc` 能正确返回函数指针

### 问题 2: 渲染结果不正确
**症状**: 黑屏、闪烁或图形错误
**原因**: 队列族选择错误或同步问题
**解决**:
- 确保 `fGraphicsQueueIndex` 对应的队列支持图形操作
- 检查 Swapchain 与 Graphite 的同步
- 验证图像布局转换

### 问题 3: 内存泄漏
**症状**: 内存使用持续增长
**原因**: 上下文未正确销毁或循环引用
**解决**:
```cpp
{
    std::unique_ptr<Context> context = ContextFactory::MakeVulkan(...);
    // 使用上下文
}  // 作用域结束时自动销毁

// 确保所有相关资源也已释放
recorder.reset();
surface.reset();
context.reset();  // 最后销毁上下文
```

### 问题 4: 多窗口渲染问题
**症状**: 多个窗口渲染互相干扰
**原因**: 共享上下文导致状态冲突
**解决**: 为每个窗口创建独立的 Recorder 或 Context

## 最佳实践

1. **单例模式**: 应用中通常只需一个 `Context` 实例
2. **延迟创建**: 在首次需要时创建,而非应用启动时
3. **资源预热**: 创建后立即提交一些简单绘制预热管线缓存
4. **持久化缓存**: 使用 `ContextOptions::fPersistentCache` 加速启动
5. **优雅关闭**: 确保所有 `Recording` 已完成再销毁 `Context`
6. **错误处理**: 始终检查返回值,准备降级方案 (如回退到软件渲染)

## 示例: 完整初始化流程
```cpp
std::unique_ptr<skgpu::graphite::Context> createGraphiteContext() {
    // 1. 创建 Vulkan 实例
    VkInstance instance = createInstance();
    if (!instance) return nullptr;

    // 2. 选择物理设备
    VkPhysicalDevice physicalDevice = pickPhysicalDevice(instance);
    if (!physicalDevice) return nullptr;

    // 3. 创建逻辑设备
    uint32_t queueFamilyIndex;
    VkDevice device = createDevice(physicalDevice, &queueFamilyIndex);
    if (!device) return nullptr;

    // 4. 获取队列
    VkQueue queue;
    vkGetDeviceQueue(device, queueFamilyIndex, 0, &queue);

    // 5. 创建内存分配器
    auto memoryAllocator = sk_make_sp<VmaAllocator>(instance, physicalDevice, device);

    // 6. 填充后端上下文
    skgpu::VulkanBackendContext backendContext = {
        .fInstance = instance,
        .fPhysicalDevice = physicalDevice,
        .fDevice = device,
        .fQueue = queue,
        .fGraphicsQueueIndex = queueFamilyIndex,
        .fMaxAPIVersion = VK_API_VERSION_1_1,
        .fVkExtensions = &gExtensions,
        .fDeviceFeatures2 = &gFeatures,
        .fMemoryAllocator = memoryAllocator,
        .fGetProc = &getVulkanProc,
    };

    // 7. 配置选项
    skgpu::graphite::ContextOptions options;
    options.fGpuBudgetInBytes = 256 * 1024 * 1024;

    // 8. 创建 Graphite 上下文
    return skgpu::graphite::ContextFactory::MakeVulkan(backendContext, options);
}
```

## 总结
VulkanGraphiteContext.h 提供了简洁而强大的 API,将复杂的 Vulkan 初始化与 Graphite 渲染系统连接起来。理解其使用方式和最佳实践对于构建高性能的 Skia Graphite 应用至关重要。
