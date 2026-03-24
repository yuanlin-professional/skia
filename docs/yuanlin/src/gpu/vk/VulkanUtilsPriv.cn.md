# VulkanUtilsPriv - Vulkan 内部工具函数集

> 源文件: `src/gpu/vk/VulkanUtilsPriv.h`, `src/gpu/vk/VulkanUtilsPriv.cpp`

## 概述

`VulkanUtilsPriv` 是 Skia Vulkan 后端的私有工具函数和类型集合，提供了多种在 Ganesh 和 Graphite 之间共享的 Vulkan 实用功能。主要包括：GPU 厂商 ID 枚举、驱动版本解析、Vulkan 格式查询工具函数、SPIR-V 编译入口、Vulkan pNext 链操作、YCbCr 采样器转换信息处理、Android 硬件缓冲区（AHardwareBuffer）集成、设备丢失回调处理，以及 `VulkanInterface` 的工厂函数。

## 架构位置

该文件是 Skia GPU 后端 Vulkan 公共层中的核心工具模块，位于 Ganesh/Graphite 之下、Vulkan 驱动之上：

- 被 Ganesh (`src/gpu/ganesh/vk/`) 和 Graphite (`src/gpu/graphite/vk/`) 的 Vulkan 实现广泛使用。
- 被 `VulkanAMDMemoryAllocator` 的 `VulkanMemoryAllocators::Make()` 使用来创建接口。
- 包含 SkSL 到 SPIR-V 的编译桥接函数。

## 主要类与结构体

### `VkVendor` 枚举

```cpp
enum VkVendor {
    kAMD_VkVendor       = 0x1002,
    kARM_VkVendor       = 0x13B5,
    kNvidia_VkVendor    = 0x10DE,
    kQualcomm_VkVendor  = 0x5143,
    kIntel_VkVendor     = 0x8086,
    // ... 等共 12 个厂商
};
```

定义了 Skia 需要识别的 GPU 厂商 PCI ID，用于驱动级别的 Bug 规避。

### `DriverVersion` 结构体

```cpp
struct DriverVersion {
    uint32_t fMajor = 0;
    uint32_t fMinor = 0;
};
```

表示解析后的驱动版本号。提供了 `==`、`!=`、`<`、`>=` 四个比较运算符（全部 `constexpr`），并有编译期 `static_assert` 测试确保正确性。

## 公共 API 函数

### 驱动版本解析

```cpp
DriverVersion ParseVulkanDriverVersion(VkDriverId driverId, uint32_t driverVersion);
```

根据不同驱动的版本编码规则解析版本号：
- **Intel (Windows)**: Major (18 bits) | Minor (14 bits)
- **Nvidia**: Major (10 bits) | Minor (8 bits) | SubMinor (8 bits) | Patch (6 bits)
- **Qualcomm**: 新格式带 0x80000000 标志位；旧格式为未知编码
- **MoltenVK**: Major * 10000 + Minor * 100 + Patch
- **默认**: `VK_MAKE_API_VERSION` 标准格式

### SkSL 到 SPIR-V 编译

```cpp
inline bool SkSLToSPIRV(const SkSL::ShaderCaps* caps, const std::string& sksl,
                         SkSL::ProgramKind programKind, const SkSL::ProgramSettings& settings,
                         SkSL::NativeShader* spirv, SkSL::ProgramInterface* outInterface,
                         ShaderErrorHandler* errorHandler);
```

通过 `SkSLToBackend` 调用 `SkSL::ToSPIRV` 将 SkSL 着色器编译为 SPIR-V。

### Vulkan 格式查询函数（constexpr）

| 函数 | 说明 |
|------|------|
| `VkFormatChannels(VkFormat)` | 返回格式的颜色通道标志 (`SkColorChannelFlags`) |
| `VkFormatBytesPerBlock(VkFormat)` | 返回格式每块的字节数 |
| `VkFormatStencilBits(VkFormat)` | 返回格式的模板位数 |
| `VkFormatNeedsYcbcrSampler(VkFormat)` | 判断是否需要 YCbCr 采样器 |
| `SampleCountToVkSampleCount(uint32_t, VkSampleCountFlagBits*)` | 采样数到 Vulkan 采样标志的转换 |
| `VkFormatIsCompressed(VkFormat)` | 判断是否为压缩格式 (ETC2, BC1) |
| `VkFormatToStr(VkFormat)` | 格式到可读字符串的转换 |

### pNext 链操作模板

```cpp
template <typename VulkanStruct1, typename VulkanStruct2>
void AddToPNextChain(VulkanStruct1* chainStart, VulkanStruct2* ptr);

template <typename T>
const T* GetExtensionFeatureStruct(const VkPhysicalDeviceFeatures2& features,
                                   VkStructureType type);
```

- `AddToPNextChain`: 将结构体前置插入 pNext 链，使用 `static_assert` 防止传入指针的指针。
- `GetExtensionFeatureStruct`: 遍历 features2 的 pNext 链查找指定类型的扩展结构体。

### YCbCr/Swizzle 字符串转换（constexpr）

| 函数 | 说明 |
|------|------|
| `VkModelToStr(VkSamplerYcbcrModelConversion)` | YCbCr 模型到字符串 |
| `VkRangeToStr(VkSamplerYcbcrRange)` | YCbCr 范围到字符串 |
| `VkSwizzleToStr(VkComponentSwizzle, char)` | 分量混合到字符 |

### Android AHardwareBuffer 工具函数（`SK_BUILD_FOR_ANDROID`）

```cpp
void GetYcbcrConversionInfoFromFormatProps(...);
bool GetAHardwareBufferProperties(...);
bool AllocateAndBindImageMemory(...);
```

- `GetYcbcrConversionInfoFromFormatProps`: 从 AHB 格式属性提取 YCbCr 转换信息。
- `GetAHardwareBufferProperties`: 查询 AHB 的 Vulkan 格式和内存属性。
- `AllocateAndBindImageMemory`: 为导入的 AHB 图像分配专用内存并绑定。包含设备本地内存优先、任意可用类型回退的两阶段查找策略。

### 设备丢失回调

```cpp
void InvokeDeviceLostCallback(const VulkanInterface* vulkanInterface, VkDevice vkDevice,
                               VulkanDeviceLostContext faultContext,
                               VulkanDeviceLostProc faultProc,
                               bool supportsDeviceFaultInfoExtension);
```

在 `VK_ERROR_DEVICE_LOST` 后调用。若支持 `VK_EXT_device_fault`，先查询故障数量，再获取详细的地址/厂商信息传递给回调。

### `MakeInterface()`

```cpp
sk_sp<VulkanInterface> MakeInterface(const VulkanBackendContext&,
                                     const VulkanExtensions* extOverride,
                                     uint32_t* physDevVersionOut,
                                     uint32_t* instanceVersionOut);
```

`VulkanInterface` 的工厂函数：
1. 查询实例和物理设备版本，限制到 `fMaxAPIVersion`。
2. 要求 Vulkan 1.1 为最低版本。
3. 创建并验证接口，失败返回 `nullptr`。

### `VulkanYcbcrConversionInfo` 构造与转换

CPP 文件中包含 `VulkanYcbcrConversionInfo` 的完整构造函数和 `toVkSamplerYcbcrConversionCreateInfo` 方法，处理色度滤波器兼容性以及分离重建滤波器等复杂逻辑。

## 内部实现细节

### `SHARED_GR_VULKAN_CALL` 宏

```cpp
#define SHARED_GR_VULKAN_CALL(IFACE, X) (IFACE)->fFunctions.f##X
```

统一 Ganesh 和 Graphite 的 Vulkan 调用方式，避免重复代码。

### AHB 内存类型查找

`AllocateAndBindImageMemory` 使用两阶段查找：
1. 优先选择 `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` 的内存类型。
2. 回退到任意兼容类型（通过 `ffs` 找到最低有效位）。

这处理了 AMD 等平台上 AHB CPU 读写缓冲区仅支持非设备本地堆的情况。

### YCbCr 滤波器兼容性处理

当不支持分离重建滤波器且不支持线性采样时，强制色度滤波器为 `VK_FILTER_NEAREST`，确保 min/mag/chroma 三个滤波器保持一致。

## 依赖关系

- **上游依赖**: `VulkanInterface`、`VulkanBackendContext`、`SkSLToBackend`、`SkSL::ToSPIRV`、`VulkanExtensions`。
- **被依赖**: Ganesh/Graphite Vulkan Caps、GPU 实现、`VulkanAMDMemoryAllocator`。

## 设计模式与设计决策

1. **头文件中的 constexpr 函数**: 大量格式查询函数为 `constexpr`，可在编译期求值，零运行时成本。
2. **平台条件编译**: Android 特有的 AHB 功能通过 `SK_BUILD_FOR_ANDROID` 隔离。
3. **类型安全的 pNext 操作**: `AddToPNextChain` 使用 `static_assert` 防止误传指针的指针。
4. **防御性驱动版本解析**: 每种驱动有独立的解析逻辑，应对各厂商不统一的版本编码。

## 性能考量

- 格式查询函数均为 `static constexpr`，编译器可内联并在编译期求值。
- `VkFormatBytesPerBlock` 对 planar 格式（如 NV12）使用过度估计值用于 GPU 尺寸计算，注释说明未来应采用专用的平面格式大小查询。
- `InvokeDeviceLostCallback` 仅在设备丢失后调用，属于异常路径，性能不敏感。
- `MakeInterface` 中的版本查询和接口创建仅在初始化时执行一次。

## 相关文件

- `src/gpu/vk/VulkanInterface.h` - Vulkan 函数指针接口
- `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文
- `include/gpu/vk/VulkanExtensions.h` - 扩展管理
- `include/gpu/vk/VulkanTypes.h` - Vulkan 类型定义
- `src/gpu/SkSLToBackend.h` - SkSL 编译后端接口
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.h` - SPIR-V 代码生成器
- `src/gpu/vk/vulkanmemoryallocator/VulkanAMDMemoryAllocator.cpp` - 使用 `MakeInterface`
