# VulkanInterface - Vulkan 函数指针接口

> 源文件: `src/gpu/vk/VulkanInterface.h`, `src/gpu/vk/VulkanInterface.cpp`

## 概述

`VulkanInterface` 是 Skia 对 Vulkan API 函数指针的封装层。它将所有 Skia 所需的 Vulkan 函数收集到一个统一的结构体中，为 Ganesh 和 Graphite 两套渲染后端提供一致的 Vulkan 调用接口。在创建 GPU 上下文时，外部通过 `VulkanGetProc` 回调函数提供函数指针的解析能力，`VulkanInterface` 负责根据 Vulkan 版本和已启用的扩展来获取并验证所有必要的函数指针。

## 架构位置

`VulkanInterface` 位于 Skia GPU 后端的 Vulkan 公共层（`src/gpu/vk/`），处于 Ganesh/Graphite 与底层 Vulkan 驱动之间的适配层。它被以下组件依赖：

- **Ganesh Vulkan 后端** (`src/gpu/ganesh/vk/`): `GrVkGpu`、`GrVkCommandBuffer` 等通过此接口调用 Vulkan。
- **Graphite Vulkan 后端** (`src/gpu/graphite/vk/`): 同样使用此接口。
- **VulkanMemory / VulkanAMDMemoryAllocator**: 内存分配器从此接口拷贝函数指针。
- **VulkanUtilsPriv**: 通过 `MakeInterface()` 工厂函数创建此接口的实例。

## 主要类与结构体

### `VulkanInterface`

继承自 `SkRefCnt`，使用引用计数进行生命周期管理。

| 成员 | 说明 |
|------|------|
| `Functions fFunctions` | 包含所有 Vulkan 函数指针的嵌套结构体 |

### `VulkanInterface::VkPtr<FNPTR_TYPE>`

私有模板包装类，用于将函数指针初始化为 `nullptr`，避免未初始化的风险。支持赋值运算符和到原始函数指针类型的隐式转换。

### `VulkanInterface::Functions`

包含所有 Vulkan 函数指针的结构体，按逻辑分组：

- **Vulkan 1.0 核心函数**: 约 135 个，覆盖实例管理、设备管理、内存、缓冲区、图像、管线、描述符集、渲染通道、命令缓冲区和绘制命令等全部核心 API。
- **Vulkan 1.1 提升函数**: `GetPhysicalDeviceFeatures2`、`GetImageMemoryRequirements2`、`BindBufferMemory2`、`TrimCommandPool`、`GetDescriptorSetLayoutSupport`、`CreateSamplerYcbcrConversion` 等。
- **Vulkan 1.2 函数**: `CreateRenderPass2`（来自 `VK_KHR_create_renderpass2`）。
- **Vulkan 1.3 函数**: 扩展动态状态（`VK_EXT_extended_dynamic_state` / `VK_EXT_extended_dynamic_state2`）相关的 15 个函数。
- **扩展函数**: `VK_EXT_vertex_input_dynamic_state`、`VK_EXT_device_fault`、`VK_EXT_host_image_copy`、`VK_ANDROID_external_memory_android_hardware_buffer`（Android 平台）。

## 公共 API 函数

### 构造函数

```cpp
VulkanInterface(VulkanGetProc getProc,
                VkInstance instance,
                VkDevice device,
                uint32_t instanceVersion,
                uint32_t physicalDeviceVersion,
                const VulkanExtensions*);
```

通过 `getProc` 回调解析所有函数指针。函数按三个层级获取：
1. **全局/加载器函数**: `instance` 和 `device` 均为 `VK_NULL_HANDLE`。
2. **实例级函数**: 传入 `instance`，`device` 为 `VK_NULL_HANDLE`。
3. **设备级函数**: `instance` 为 `VK_NULL_HANDLE`，传入 `device`。

对于在较高 Vulkan 版本中被提升（promoted）的扩展函数，会优先尝试核心版本名称，回退到带 KHR/EXT 后缀的扩展版本。

### `validate()`

```cpp
bool validate(uint32_t instanceVersion,
              uint32_t physicalDeviceVersion,
              const VulkanExtensions*) const;
```

验证所有必需的函数指针是否已成功解析。验证逻辑分为：
- Vulkan 1.0 + 1.1 核心函数（始终必需）。
- 条件检查：根据版本号或扩展是否启用来验证对应函数。
- 在 `SK_DEBUG` 模式下，验证失败会输出文件名和行号信息。

## 内部实现细节

### 宏驱动的函数获取

实现使用两个宏简化重复代码：

```cpp
#define ACQUIRE_PROC(name, instance, device)
#define ACQUIRE_PROC_SUFFIX(name, suffix, instance, device)
```

`ACQUIRE_PROC` 用于获取标准名称的函数，`ACQUIRE_PROC_SUFFIX` 用于获取带扩展后缀（如 KHR、EXT）的函数。二者内部都通过 `reinterpret_cast` 将 `getProc` 返回的通用指针转换为具体的 Vulkan 函数指针类型。

### 版本回退策略

对于从扩展提升到核心的函数，采用版本优先策略：
```cpp
if (physicalDeviceVersion >= VK_API_VERSION_1_3) {
    ACQUIRE_PROC(CmdSetCullMode, ...);           // 核心名称
} else if (extensions->hasExtension(...)) {
    ACQUIRE_PROC_SUFFIX(CmdSetCullMode, EXT, ...); // 扩展名称
}
```

### 验证的防御性设计

`RETURN_FALSE_INTERFACE` 宏在 Debug 模式下打印失败的文件和行号，在 Release 模式下静默返回 `false`。

## 依赖关系

- **上游依赖**: `SkRefCnt`（引用计数基类）、`VulkanTypes.h`（Vulkan 类型定义）、`SkiaVulkan.h`（Vulkan 头文件包装）、`VulkanExtensions`（扩展查询）。
- **被依赖**: Ganesh/Graphite Vulkan 后端的几乎所有组件、VMA 内存分配器、`VulkanUtilsPriv`。

## 设计模式与设计决策

1. **函数表模式（Dispatch Table）**: 将所有 Vulkan 函数指针集中在一个结构体中，而非分散在各调用点。这使得函数指针可以被编译器自动生成赋值运算符来整体拷贝。
2. **VkPtr 包装类**: 通过模板类保证指针默认初始化为 `nullptr`，避免使用未初始化指针导致的崩溃。
3. **版本与扩展感知**: 构造时根据实际可用的 Vulkan 版本和扩展来选择性地获取函数，实现了对不同 Vulkan 驱动的良好适配。
4. **验证与构造分离**: 构造函数不做验证，由独立的 `validate()` 方法完成。这允许调用者在验证失败时做出不同的处理决策。
5. **引用计数共享**: 继承 `SkRefCnt` 使得接口可以在多个组件间安全共享。

## 性能考量

- 函数指针查找仅在构造时执行一次，运行时调用与直接函数调用等价（间接函数调用，无额外开销）。
- `VkPtr` 的隐式类型转换为 `operator FNPTR_TYPE()` 是零成本抽象。
- `validate()` 仅在初始化阶段调用，不影响渲染路径性能。
- `Functions` 结构体使用编译器生成的赋值运算符，避免了手动拷贝大量指针的代码。

## 相关文件

- `include/gpu/vk/VulkanTypes.h` - Vulkan 类型定义（`VulkanGetProc` 等）
- `include/gpu/vk/VulkanExtensions.h` - 扩展查询类
- `include/private/gpu/vk/SkiaVulkan.h` - Vulkan 头文件包装
- `src/gpu/vk/VulkanUtilsPriv.h` - `MakeInterface()` 工厂函数
- `src/gpu/vk/vulkanmemoryallocator/VulkanAMDMemoryAllocator.cpp` - 从接口拷贝函数指针
- `src/gpu/ganesh/vk/GrVkGpu.h` - Ganesh Vulkan GPU 实现
