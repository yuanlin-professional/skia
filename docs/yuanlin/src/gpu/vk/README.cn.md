# vk - Skia GPU 通用 Vulkan 工具层

## 概述

`src/gpu/vk` 目录包含 Skia 图形库中 Vulkan 图形 API 的通用工具代码。这些代码是 Ganesh(旧版 GPU 后端)和 Graphite(新一代 GPU 后端)共享的 Vulkan 基础设施,提供了 Vulkan 函数接口封装、内存管理、扩展处理、着色器编译、格式工具和设备特性查询等核心功能。

Vulkan 是一个跨平台的低级别 GPU 图形和计算 API,以其显式控制和高性能著称。与 Metal 和 OpenGL 不同,Vulkan 需要应用程序显式管理几乎所有资源,包括内存分配、同步、命令缓冲区和管线状态。Skia 通过该目录中的共享代码层封装了这些复杂性,为上层的 Ganesh 和 Graphite 后端提供统一的 Vulkan 操作接口。

`VulkanInterface` 是该目录的核心结构体,它聚合了所有 Skia 需要的 Vulkan 函数指针。Skia 不直接链接 Vulkan 库,而是通过 `VulkanGetProc` 回调在运行时动态获取函数指针。这种设计使 Skia 能够在不同 Vulkan 实现之间透明切换,并支持 Vulkan 1.0 到 1.4 及各种扩展。

内存管理通过 `VulkanMemory` 命名空间中的工具函数实现,它们封装了 `VulkanMemoryAllocator` 接口的调用,处理缓冲区和图像的内存分配、映射、刷新和无效化。该模块还包含了 `VulkanExtensions` 扩展管理、`VulkanMutableTextureState` 纹理状态追踪和 `VulkanPreferredFeatures` 设备特性协商等重要功能。

对于 Android 平台,该目录还通过 `VulkanUtilsPriv.h` 中的条件编译代码支持 `AHardwareBuffer` 的 Vulkan 互操作,包括 YCbCr 色彩转换信息提取和硬件缓冲区的内存绑定。

## 架构图

```
+----------------------------------------------------------+
|                     Skia 应用层                           |
+----------------------------------------------------------+
        |                    |
+-------v--------+  +-------v--------+
|  Ganesh/Vulkan |  | Graphite/Vulkan|
|  GPU 后端      |  |  GPU 后端      |
+-------+--------+  +-------+--------+
        |                    |
        +--------+-----------+
                 |
     +-----------v-------------------------------------------+
     |                src/gpu/vk (共享层)                     |
     |                                                       |
     |  +--------------------+  +-------------------------+  |
     |  | VulkanInterface    |  | VulkanMemory            |  |
     |  | (函数指针集合)      |  | (内存管理工具函数)       |  |
     |  | - 200+ VK函数      |  | - AllocBufferMemory()   |  |
     |  | - validate()       |  | - AllocImageMemory()    |  |
     |  +--------------------+  | - MapAlloc/UnmapAlloc() |  |
     |                          | - FlushMappedAlloc()    |  |
     |  +--------------------+  +-------------------------+  |
     |  | VulkanExtensions   |                               |
     |  | (扩展管理)         |  +-------------------------+  |
     |  | - init()           |  | VulkanUtilsPriv          |  |
     |  | - hasExtension()   |  | - SkSLToSPIRV()         |  |
     |  +--------------------+  | - VkFormat* 工具函数     |  |
     |                          | - 设备厂商枚举          |  |
     |  +--------------------+  | - DriverVersion         |  |
     |  | VulkanMutableTex   |  | - AHardwareBuffer集成   |  |
     |  | tureState          |  +-------------------------+  |
     |  | (纹理状态管理)     |                               |
     |  +--------------------+  +-------------------------+  |
     |                          | VulkanPreferredFeatures  |  |
     |                          | (设备特性协商)           |  |
     |                          +-------------------------+  |
     +----------------------------+--------------------------+
                                  |
              +-------------------v-------------------+
              |          Vulkan API / 驱动层          |
              | VkInstance, VkDevice, VkBuffer,       |
              | VkImage, VkCommandBuffer, ...         |
              +---------------------------------------+
```

## 目录结构

```
src/gpu/vk/
|-- BUILD.bazel                          # Bazel 构建配置
|-- VulkanExtensions.cpp                 # Vulkan 扩展管理实现
|-- VulkanInterface.h                    # Vulkan 函数指针接口 (头文件)
|-- VulkanInterface.cpp                  # Vulkan 函数指针初始化 (~700行)
|-- VulkanMemory.h                       # Vulkan 内存工具函数 (头文件)
|-- VulkanMemory.cpp                     # Vulkan 内存工具函数实现
|-- VulkanMutableTextureState.cpp        # Vulkan 可变纹理状态实现
|-- VulkanMutableTextureStatePriv.h      # 纹理状态私有接口
|-- VulkanPreferredFeatures.cpp          # Vulkan 推荐设备特性 (~97KB)
|-- VulkanUtilsPriv.h                    # Vulkan 私有工具函数 (格式/驱动/着色器)
|-- VulkanUtilsPriv.cpp                  # Vulkan 私有工具函数实现 (~19KB)
|-- vulkanmemoryallocator/              # VMA 子目录 (见专属文档)
```

## 关键类与函数

### `VulkanInterface` (VulkanInterface.h)

Skia 与 Vulkan 交互的函数指针集合,继承自 `SkRefCnt` 以支持引用计数共享:

```cpp
struct VulkanInterface : public SkRefCnt {
    VulkanInterface(VulkanGetProc getProc,
                    VkInstance instance,
                    VkDevice device,
                    uint32_t instanceVersion,
                    uint32_t physicalDeviceVersion,
                    const VulkanExtensions*);

    bool validate(uint32_t instanceVersion,
                  uint32_t physicalDeviceVersion,
                  const VulkanExtensions*) const;

    struct Functions {
        // Vulkan 1.0 核心函数 (~130个)
        VkPtr<PFN_vkCreateInstance> fCreateInstance;
        VkPtr<PFN_vkAllocateMemory> fAllocateMemory;
        VkPtr<PFN_vkCreateImage> fCreateImage;
        VkPtr<PFN_vkCmdDraw> fCmdDraw;
        // ... 更多核心函数

        // Vulkan 1.1 函数
        VkPtr<PFN_vkGetPhysicalDeviceFeatures2> fGetPhysicalDeviceFeatures2;
        VkPtr<PFN_vkGetImageMemoryRequirements2> fGetImageMemoryRequirements2;
        VkPtr<PFN_vkBindBufferMemory2> fBindBufferMemory2;

        // Vulkan 1.2 函数
        VkPtr<PFN_vkCreateRenderPass2> fCreateRenderPass2;

        // Vulkan 1.3 扩展动态状态
        VkPtr<PFN_vkCmdSetCullMode> fCmdSetCullMode;
        VkPtr<PFN_vkCmdSetDepthTestEnable> fCmdSetDepthTestEnable;

        // Vulkan 1.4 / VK_EXT_host_image_copy
        VkPtr<PFN_vkTransitionImageLayout> fTransitionImageLayout;
        VkPtr<PFN_vkCopyMemoryToImage> fCopyMemoryToImage;

        // Android 专用
        VkPtr<PFN_vkGetAndroidHardwareBufferPropertiesANDROID>
            fGetAndroidHardwareBufferProperties;
    } fFunctions;
};
```

内部使用 `VkPtr<FNPTR_TYPE>` 模板包装器,确保所有函数指针初始化为 `nullptr`。

### `VulkanMemory` 命名空间 (VulkanMemory.h)

封装 `VulkanMemoryAllocator` 接口的高层工具函数:

| 函数 | 功能 |
|------|------|
| `AllocBufferMemory()` | 分配缓冲区内存(支持保护内存、持久映射) |
| `AllocImageMemory()` | 分配图像内存(支持专用分配、延迟分配、保护内存) |
| `FreeBufferMemory()` / `FreeImageMemory()` | 释放内存 |
| `MapAlloc()` / `UnmapAlloc()` | 映射/取消映射分配的内存 |
| `FlushMappedAlloc()` | 刷新非一致性映射内存 |
| `InvalidateMappedAlloc()` | 无效化非一致性映射内存 |
| `GetNonCoherentMappedMemoryRange()` | 计算对齐的映射内存范围 |

### `VulkanExtensions` (VulkanExtensions.cpp)

Vulkan 扩展管理器,支持初始化、排序和版本查询:

```cpp
void init(VulkanGetProc getProc,
          VkInstance instance, VkPhysicalDevice physDev,
          uint32_t instanceExtensionCount, const char* const* instanceExtensions,
          uint32_t deviceExtensionCount, const char* const* deviceExtensions);

bool hasExtension(const char ext[], uint32_t minVersion) const;
```

内部使用排序数组加二分查找(`SkTSearch`)实现高效的扩展名查询。

### `VulkanMutableTextureState` (VulkanMutableTextureState.cpp)

追踪 Vulkan 纹理的可变状态:
- `VkImageLayout` - 图像布局(如 `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL`)
- `uint32_t queueFamilyIndex` - 队列族索引(用于所有权转移)

提供 `GetVkImageLayout()` / `SetVkImageLayout()` / `GetVkQueueFamilyIndex()` / `SetVkQueueFamilyIndex()` 等访问器。

### 格式工具函数 (VulkanUtilsPriv.h)

一系列 `constexpr` 的 `VkFormat` 查询函数:

| 函数 | 功能 |
|------|------|
| `VkFormatChannels(VkFormat)` | 返回颜色通道标志 |
| `VkFormatBytesPerBlock(VkFormat)` | 每块字节数 |
| `VkFormatStencilBits(VkFormat)` | 模板位深度 |
| `VkFormatNeedsYcbcrSampler(VkFormat)` | 是否需要 YCbCr 采样器 |
| `VkFormatIsCompressed(VkFormat)` | 是否为压缩格式 |
| `SampleCountToVkSampleCount()` | 采样数转换 |
| `VkFormatToStr(VkFormat)` | 格式名称字符串化 |

### GPU 厂商枚举与驱动版本 (VulkanUtilsPriv.h)

```cpp
enum VkVendor {
    kAMD_VkVendor       = 0x1002,
    kARM_VkVendor       = 0x13B5,
    kBroadcom_VkVendor  = 0x14E4,
    kGoogle_VkVendor    = 0x1AE0,
    kIntel_VkVendor     = 0x8086,
    kNvidia_VkVendor    = 0x10DE,
    kQualcomm_VkVendor  = 0x5143,
    kSamsung_VkVendor   = 0x144D,
    // ... 更多厂商
};

struct DriverVersion {
    uint32_t fMajor = 0;
    uint32_t fMinor = 0;
};
```

`ParseVulkanDriverVersion()` 函数根据 `VkDriverId` 解析不同厂商的版本编码格式。

### `SkSLToSPIRV()` (VulkanUtilsPriv.h)

SkSL 到 SPIR-V 的着色器翻译,是 `SkSLToBackend()` 框架的 Vulkan 特化:

```cpp
inline bool SkSLToSPIRV(const SkSL::ShaderCaps* caps,
                         const std::string& sksl,
                         SkSL::ProgramKind programKind,
                         const SkSL::ProgramSettings& settings,
                         SkSL::NativeShader* spirv,
                         SkSL::ProgramInterface* outInterface,
                         ShaderErrorHandler* errorHandler);
```

### pNext 链操作工具

```cpp
template <typename VulkanStruct1, typename VulkanStruct2>
void AddToPNextChain(VulkanStruct1* chainStart, VulkanStruct2* ptr);

template <typename T>
const T* GetExtensionFeatureStruct(const VkPhysicalDeviceFeatures2& features,
                                   VkStructureType type);
```

这些模板函数用于安全地操作 Vulkan 结构体的 `pNext` 扩展链。

## 依赖关系

```
src/gpu/vk/ 依赖:
  +-- include/gpu/vk/VulkanTypes.h (Vulkan 类型定义)
  +-- include/gpu/vk/VulkanMemoryAllocator.h (内存分配器接口)
  +-- include/gpu/vk/VulkanExtensions.h (扩展管理公共接口)
  +-- include/private/gpu/vk/SkiaVulkan.h (Vulkan 头文件引入)
  +-- include/third_party/vulkan/ (Vulkan 头文件)
  +-- src/base/SkTSearch.h, SkTSort.h (搜索和排序工具)
  +-- src/gpu/SkSLToBackend.h (SkSL 通用转换框架)
  +-- src/sksl/codegen/SkSLSPIRVCodeGenerator.h (SPIR-V 代码生成)
  +-- src/gpu/MutableTextureStatePriv.h (可变纹理状态私有接口)

被以下模块使用:
  +-- src/gpu/ganesh/vk/ (Ganesh Vulkan 后端)
  +-- src/gpu/graphite/vk/ (Graphite Vulkan 后端)
  +-- src/gpu/vk/vulkanmemoryallocator/ (VMA 集成)
```

## 设计模式分析

### 1. 外观模式 (Facade Pattern)

`VulkanInterface` 为 200+ 个 Vulkan 函数指针提供统一的初始化和验证入口。上层代码通过 `interface->fFunctions.fCreateImage(...)` 调用 Vulkan,而无需关心函数指针的获取方式和版本兼容性。

### 2. 策略模式 (Strategy Pattern)

`VulkanMemoryAllocator` 接口定义了内存分配策略的抽象。`VulkanMemory` 命名空间中的工具函数使用该接口,不关心具体实现是 VMA、自定义分配器还是 Android 特化分配器。

### 3. 空对象模式 (Null Object)

`VkPtr<FNPTR_TYPE>` 模板默认将函数指针初始化为 `nullptr`,确保未初始化的函数不会被意外调用。`validate()` 方法检查所有必需函数是否已正确加载。

### 4. 类型擦除 (Type Erasure)

`VulkanMutableTextureState` 使用 `MutableTextureStateData` 基类和 `AnyStateData` 存储,将 Vulkan 特定状态隐藏在后端无关的 `MutableTextureState` 接口后面。通过 `BackendApi::kVulkan` 标记在运行时恢复类型信息。

### 5. 编译期常量优化

大量格式查询函数使用 `constexpr`,在编译期完成计算。例如 `VkFormatChannels()`、`VkFormatBytesPerBlock()` 等函数可以在常量表达式上下文中使用,避免了运行时开销。

## 数据流

```
1. 初始化流:
   应用提供 VulkanGetProc + VkInstance + VkDevice
        |
   VulkanInterface 构造函数:
        |-- 通过 getProc 加载所有函数指针
        |-- validate() 验证版本所需函数已加载
        |
   VulkanExtensions::init():
        |-- 收集并排序所有实例/设备扩展
        |-- 查询各扩展的规范版本号

2. 内存分配流:
   Ganesh/Graphite 需要创建 VkBuffer/VkImage
        |
   VulkanMemory::AllocBufferMemory() / AllocImageMemory()
        |-- 设置属性标志 (保护/专用/延迟/持久映射)
        |-- 调用 VulkanMemoryAllocator->allocateBufferMemory()
        |-- allocator->getAllocInfo() 获取分配信息
        |
   VulkanMemory::MapAlloc() 映射内存
        |-- allocator->mapMemory()
        |-- 返回数据指针
        |
   VulkanMemory::FlushMappedAlloc() 刷新非一致性内存
        |-- 对齐到 nonCoherentAtomSize
        |-- allocator->flushMemory()

3. 着色器编译流:
   SkSL 源码 --> SkSLToSPIRV() --> SkSL::ToSPIRV 代码生成 --> SPIR-V 字节码
                                                                    |
                                                     VkDevice 创建
                                                     VkShaderModule

4. 纹理状态追踪:
   VulkanMutableTextureState 存储:
        |-- VkImageLayout (当前图像布局)
        |-- QueueFamilyIndex (当前所有权队列族)
        |
   布局转换时更新:
        |-- SetVkImageLayout(state, newLayout)
        |-- SetVkQueueFamilyIndex(state, newFamily)
```

## 相关文档与参考

- **Vulkan 规范**: https://www.khronos.org/registry/vulkan/specs/
- **Vulkan 1.1 (Skia 最低要求)**: Skia 要求 Vulkan 1.1 作为最低版本
- **VK_EXT_extended_dynamic_state**: 支持动态设置光栅化状态,减少管线对象数量
- **VK_EXT_host_image_copy (Vulkan 1.4)**: 允许 CPU 端直接拷贝纹理数据
- **VK_ANDROID_external_memory_android_hardware_buffer**: Android AHardwareBuffer 互操作
- **VK_EXT_device_fault**: 设备丢失时获取详细故障信息
- **SPIR-V**: Vulkan 标准着色器中间表示
- **Ganesh Vulkan 后端**: `src/gpu/ganesh/vk/`
- **Graphite Vulkan 后端**: `src/gpu/graphite/vk/`
- **VMA 子目录**: `src/gpu/vk/vulkanmemoryallocator/` - AMD Vulkan Memory Allocator 集成
