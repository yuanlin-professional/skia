# VulkanBackendContext

> 源文件: `include/gpu/vk/VulkanBackendContext.h`

## 概述
VulkanBackendContext 定义了初始化 Skia Vulkan 后端所需的所有基础对象和配置信息。它充当客户端代码与 Skia GPU 上下文之间的桥梁,封装了 Vulkan 实例、设备、队列以及扩展特性等核心资源的引用。

## 架构位置
该文件位于 Skia 的 GPU 公共接口层,属于 `skgpu` 命名空间。它是 Ganesh (传统 GPU 后端) 和 Graphite (新一代 GPU 后端) 共享的 Vulkan 初始化接口,位于平台抽象层和具体后端实现之间。

## 主要类与结构体

### VulkanBackendContext
Vulkan 后端上下文的配置结构体,包含创建 Skia GPU 上下文所需的所有 Vulkan 资源引用。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fInstance | VkInstance | Vulkan 实例句柄 |
| fPhysicalDevice | VkPhysicalDevice | 物理设备句柄 |
| fDevice | VkDevice | 逻辑设备句柄 |
| fQueue | VkQueue | 图形队列句柄 |
| fGraphicsQueueIndex | uint32_t | 图形队列族索引 |
| fMaxAPIVersion | uint32_t | 最大 API 版本 (至少为 Vulkan 1.1) |
| fVkExtensions | const VulkanExtensions* | 启用的 Vulkan 扩展集合 |
| fDeviceFeatures | const VkPhysicalDeviceFeatures* | 设备特性 (版本 1) |
| fDeviceFeatures2 | const VkPhysicalDeviceFeatures2* | 设备特性 (版本 2,包含扩展链) |
| fMemoryAllocator | sk_sp<VulkanMemoryAllocator> | 内存分配器实现 |
| fGetProc | VulkanGetProc | 函数指针获取函数 |
| fProtectedContext | Protected | 是否启用受保护内存 |
| fDeviceLostContext | VulkanDeviceLostContext | 设备丢失回调上下文 |
| fDeviceLostProc | VulkanDeviceLostProc | 设备丢失回调函数 |

## 内部实现细节

### 初始化流程
客户端代码需要按以下顺序准备资源:
1. **创建 Vulkan 实例**: 使用 `vkCreateInstance` 创建 `VkInstance`
2. **选择物理设备**: 通过 `vkEnumeratePhysicalDevices` 选择合适的 GPU
3. **创建逻辑设备**: 使用 `vkCreateDevice` 创建 `VkDevice` 时需启用 Skia 需要的扩展
4. **获取图形队列**: 通过 `vkGetDeviceQueue` 获取支持图形操作的队列
5. **创建内存分配器**: 实现 `VulkanMemoryAllocator` 接口 (推荐使用 VMA 库)
6. **填充上下文结构**: 将上述资源填入 `VulkanBackendContext` 结构体
7. **创建 Skia 上下文**: 调用 `GrDirectContext::MakeVulkan()` 或 `skgpu::graphite::ContextFactory::MakeVulkan()`

### 特性检测与版本管理
```cpp
// fMaxAPIVersion 应匹配 VkApplicationInfo::apiVersion
VkApplicationInfo appInfo = {
    .apiVersion = VK_API_VERSION_1_1  // 最低要求
};
// 填充上下文时保持一致
backendContext.fMaxAPIVersion = VK_API_VERSION_1_1;
```

### 设备特性的双轨制
Skia 支持两种特性查询方式:
- **旧版本 (Vulkan 1.0)**: 使用 `fDeviceFeatures` 指向 `VkPhysicalDeviceFeatures`
- **新版本 (Vulkan 1.1+)**: 使用 `fDeviceFeatures2` 指向包含 pNext 扩展链的结构体

**优先级规则**: 如果 `fDeviceFeatures2` 非空,则忽略 `fDeviceFeatures`。如果两者都为空,Skia 假设未启用任何可选特性。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 智能指针支持 |
| include/gpu/GpuTypes.h | GPU 通用类型 (Protected 枚举) |
| include/gpu/vk/VulkanMemoryAllocator.h | 内存分配器接口 |
| include/gpu/vk/VulkanTypes.h | Vulkan 基础类型 |
| include/private/gpu/vk/SkiaVulkan.h | Vulkan 头文件包装 |

### 被依赖的模块
- `GrDirectContext` (Ganesh): 使用此结构创建 Vulkan 上下文
- `skgpu::graphite::Context`: Graphite 后端使用相同结构初始化
- Vulkan 后端内部实现: 资源管理、命令提交等

## 公共 API 使用

### 基本使用模式
```cpp
// 1. 创建 Vulkan 资源
VkInstance instance = createVulkanInstance();
VkPhysicalDevice physicalDevice = selectPhysicalDevice(instance);
VkDevice device = createLogicalDevice(physicalDevice);
VkQueue queue = getGraphicsQueue(device, queueFamilyIndex);

// 2. 创建内存分配器
sk_sp<skgpu::VulkanMemoryAllocator> memoryAllocator =
    createVmaAllocator(instance, physicalDevice, device);

// 3. 填充上下文
skgpu::VulkanBackendContext backendContext;
backendContext.fInstance = instance;
backendContext.fPhysicalDevice = physicalDevice;
backendContext.fDevice = device;
backendContext.fQueue = queue;
backendContext.fGraphicsQueueIndex = queueFamilyIndex;
backendContext.fMaxAPIVersion = VK_API_VERSION_1_1;
backendContext.fVkExtensions = &enabledExtensions;
backendContext.fDeviceFeatures2 = &enabledFeatures2;
backendContext.fMemoryAllocator = memoryAllocator;
backendContext.fGetProc = [](const char* name, VkInstance inst, VkDevice dev) {
    if (dev != VK_NULL_HANDLE) return vkGetDeviceProcAddr(dev, name);
    return vkGetInstanceProcAddr(inst, name);
};

// 4. 创建 Skia 上下文
sk_sp<GrDirectContext> grContext = GrDirectContext::MakeVulkan(backendContext);
```

### 启用受保护内存
```cpp
backendContext.fProtectedContext = skgpu::Protected::kYes;
// 需要在 VkDeviceCreateInfo 中启用 protectedMemory 特性
```

### 注册设备丢失回调
```cpp
backendContext.fDeviceLostContext = userData;
backendContext.fDeviceLostProc = [](VulkanDeviceLostContext ctx,
                                     const std::string& desc,
                                     const auto& addrInfos,
                                     const auto& vendorInfos,
                                     const auto& binaryData) {
    LOG_ERROR("Device lost: " << desc);
    // 处理设备丢失
};
// 需要启用 VK_EXT_device_fault 扩展
```

## 设计模式与设计决策

### 聚合模式 (Aggregate)
`VulkanBackendContext` 采用简单聚合设计:
- 所有成员为公共字段,便于直接赋值
- 不持有资源所有权,仅保存引用
- 使用默认初始化值 (VK_NULL_HANDLE, nullptr, 0)

### 生命周期管理
结构体本身不管理资源生命周期:
- **资源创建**: 由客户端代码负责
- **资源销毁**: 客户端需要在 Skia 上下文销毁后清理 Vulkan 对象
- **内存分配器**: 使用智能指针 (`sk_sp`) 自动管理引用计数

### 扩展性设计
通过可选字段支持扩展功能:
- 设备丢失调试: 可选的回调机制
- 受保护内存: 可选的安全特性
- 扩展特性链: 通过 `fDeviceFeatures2` 的 pNext 支持未来扩展

## 性能考量

### 函数指针获取优化
`fGetProc` 设计为回调函数:
- **延迟绑定**: 只在需要时解析函数指针
- **缓存友好**: Skia 内部缓存常用函数指针
- **灵活性**: 支持自定义加载器 (如 Vulkan-Hpp 的 DynamicLoader)

### 内存分配器要求
`fMemoryAllocator` 必须提供:
- **高效的子分配**: 避免为小对象创建独立 VkDeviceMemory
- **内存池化**: 减少分配器开销
- **线程安全**: 支持多线程渲染场景

推荐使用 **Vulkan Memory Allocator (VMA)** 库。

## 平台相关说明

### Android 特定考虑
- 使用 `VK_ANDROID_external_memory_android_hardware_buffer` 扩展需在 `fVkExtensions` 中声明
- 受保护内存用于 DRM 内容播放
- 建议启用 `VK_EXT_queue_family_foreign` 支持外部队列

### 桌面平台 (Windows/Linux/macOS)
- 可能需要启用 Swapchain 扩展 (通过 `fVkExtensions`)
- macOS 上通过 MoltenVK 运行时需注意性能特性支持

### 版本兼容性
**最低要求**: Vulkan 1.1
- 核心特性: 子组操作、多视图渲染
- Promoted 扩展: 外部内存、YCbCr 采样

**推荐版本**: Vulkan 1.2+
- 改进的时间线信号量
- 描述符索引特性

## 错误处理

### 不完整上下文检测
Skia 在创建上下文时会验证:
```cpp
if (!backendContext.fInstance || !backendContext.fDevice ||
    !backendContext.fQueue || !backendContext.fMemoryAllocator) {
    return nullptr;  // 创建失败
}
```

### 版本不匹配问题
```cpp
// 错误示例:
VkApplicationInfo appInfo = { .apiVersion = VK_API_VERSION_1_3 };
backendContext.fMaxAPIVersion = VK_API_VERSION_1_1;  // 不一致!

// 正确做法:
uint32_t apiVersion = VK_API_VERSION_1_1;
appInfo.apiVersion = apiVersion;
backendContext.fMaxAPIVersion = apiVersion;
```

### 扩展不匹配
确保 `fVkExtensions` 中声明的扩展在创建 `VkDevice` 时已启用:
```cpp
std::vector<const char*> deviceExtensions = {
    VK_KHR_SWAPCHAIN_EXTENSION_NAME,
    // ... 其他扩展
};
VkDeviceCreateInfo deviceInfo = {
    .enabledExtensionCount = deviceExtensions.size(),
    .ppEnabledExtensionNames = deviceExtensions.data(),
};
// 同步到 Skia
skgpu::VulkanExtensions vkExtensions;
vkExtensions.init(/* ... 相同的扩展列表 */);
backendContext.fVkExtensions = &vkExtensions;
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/vk/VulkanTypes.h | 定义基础类型 (VulkanGetProc, VulkanDeviceLostProc) |
| include/gpu/vk/VulkanMemoryAllocator.h | 定义必需的内存分配器接口 |
| include/gpu/vk/VulkanExtensions.h | 管理 Vulkan 扩展集合 |
| include/gpu/GrDirectContext.h | Ganesh 使用此结构创建上下文 |
| include/gpu/graphite/vk/VulkanGraphiteContext.h | Graphite 使用此结构创建上下文 |
| src/gpu/vk/VulkanInterface.cpp | 内部实现,使用 fGetProc 加载函数指针 |

## 典型错误与调试

### 问题 1: 上下文创建返回 nullptr
**原因**: 缺少必需的扩展或特性
**解决**: 检查 Vulkan 验证层输出,确认所有依赖已启用

### 问题 2: 渲染结果异常或崩溃
**原因**: 内存分配器实现有误
**解决**: 使用 VMA 库或检查自定义分配器的线程安全性

### 问题 3: 设备丢失未触发回调
**原因**: 未启用 VK_EXT_device_fault 扩展
**解决**: 在 `VkDeviceCreateInfo` 的 pNext 链中添加 `VkPhysicalDeviceFaultFeaturesEXT`

## 最佳实践

1. **使用 Vulkan Memory Allocator (VMA)**: 简化内存管理,提供最佳性能
2. **启用验证层**: 开发阶段启用 VK_LAYER_KHRONOS_validation 捕获错误
3. **检查特性支持**: 在启用特性前通过 `vkGetPhysicalDeviceFeatures2` 确认支持
4. **正确的销毁顺序**: Skia 上下文 → 内存分配器 → Vulkan 设备 → Vulkan 实例
5. **保持对象生命周期**: 确保所有引用的对象在 Skia 上下文使用期间有效
