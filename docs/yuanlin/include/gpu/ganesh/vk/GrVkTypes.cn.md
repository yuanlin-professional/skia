# GrVkTypes - Vulkan 类型定义

> 源文件: `include/gpu/ganesh/vk/GrVkTypes.h`

## 概述

GrVkTypes.h 定义了 Skia Ganesh GPU 后端中与 Vulkan API 交互所需的核心数据结构。该文件提供了三个主要结构体，用于封装 Vulkan 图像信息、可绘制对象信息和表面信息，是 Skia 与外部 Vulkan 资源交互的桥梁。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端
- **层级**: 公共 API 接口层
- **作用域**: Vulkan 后端专用类型定义

该文件位于 Ganesh GPU 后端的 Vulkan 实现模块中，为上层提供与 Vulkan 资源交互的标准化接口。

## 主要类与结构体

### GrVkImageInfo

封装 Vulkan 图像对象的完整信息，用于包装 GrBackendTexture 或 GrBackendRenderTarget。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fImage | VkImage | Vulkan 图像句柄 |
| fAlloc | skgpu::VulkanAlloc | 图像的内存分配信息 |
| fImageTiling | VkImageTiling | 图像平铺模式（最优或线性） |
| fImageLayout | VkImageLayout | 当前图像布局状态 |
| fFormat | VkFormat | 图像像素格式 |
| fImageUsageFlags | VkImageUsageFlags | 图像用途标志位 |
| fSampleCount | uint32_t | 多重采样数量（默认为1） |
| fLevelCount | uint32_t | Mipmap 层级数量 |
| fCurrentQueueFamily | uint32_t | 当前所属队列族索引 |
| fProtected | skgpu::Protected | 是否为受保护内存 |
| fYcbcrConversionInfo | skgpu::VulkanYcbcrConversionInfo | YCbCr 颜色空间转换信息 |
| fSharingMode | VkSharingMode | 队列共享模式 |
| fPartOfSwapchainOrAndroidWindow | bool | Android 专用标志 |

**队列族处理规则**:
- 包装外部纹理时，`fCurrentQueueFamily` 应设置为：
  - `VK_QUEUE_FAMILY_IGNORED`（默认）
  - `VK_QUEUE_FAMILY_EXTERNAL`
  - `VK_QUEUE_FAMILY_FOREIGN_EXT`
  - 如果 `fSharingMode` 为 `VK_SHARING_MODE_EXCLUSIVE`，也可以是传入 Skia 的图形队列索引

**相等性比较**:
实现了 `operator==`，比较所有成员变量（包括平台特定字段）以判断两个图像信息是否相同。

### GrVkDrawableInfo

用于 SkDrawable 的 `drawBackendGpu()` 调用，允许将自定义 Vulkan 命令注入到 Skia 的渲染流程中。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSecondaryCommandBuffer | VkCommandBuffer | 次级命令缓冲区（供 drawable 记录命令） |
| fColorAttachmentIndex | uint32_t | 颜色附件索引 |
| fCompatibleRenderPass | VkRenderPass | 兼容的渲染通道对象 |
| fFormat | VkFormat | 颜色附件格式 |
| fDrawBounds | VkRect2D* | 绘制边界（可选填写） |
| fFromSwapchainOrAndroidWindow | bool | Android 专用标志 |

**使用约束**:
1. **命令缓冲区**: drawable 在提供的次级命令缓冲区中记录绘制命令，GPU 后端在渲染通道内执行
2. **状态不变性**: 不得修改 VkRenderPass 或子通道的状态
3. **边界管理**: 如果填写 `fDrawBounds`，将用于 `vkCmdBeginRenderPass` 的边界设置；否则假设整个附件都可能被写入
4. **独立提交**: drawable 可以创建独立命令缓冲区提交到队列以渲染离屏纹理，但需自行处理采样图像的内存屏障

### GrVkSurfaceInfo

描述 Vulkan 表面创建所需的配置参数，用于创建新的 Vulkan 表面资源。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fSampleCount | uint32_t | 多重采样数量（默认为1） |
| fLevelCount | uint32_t | Mipmap 层级数量 |
| fProtected | skgpu::Protected | 是否使用受保护内存 |
| fImageTiling | VkImageTiling | 图像平铺模式 |
| fFormat | VkFormat | 像素格式 |
| fImageUsageFlags | VkImageUsageFlags | 图像用途标志 |
| fYcbcrConversionInfo | skgpu::VulkanYcbcrConversionInfo | YCbCr 转换信息 |
| fSharingMode | VkSharingMode | 队列共享模式 |

## 公共 API 函数

### `GrVkImageInfo::operator==`
```cpp
bool operator==(const GrVkImageInfo& that) const
```
- **功能**: 比较两个图像信息对象是否完全相同
- **参数**: `that` - 待比较的图像信息对象
- **返回值**: 如果所有字段均相等则返回 true
- **特殊处理**: 在 Android 平台会额外比较 `fPartOfSwapchainOrAndroidWindow` 字段

## 内部实现细节

### 队列族管理策略
在跨队列族共享资源时，Skia 需要明确知道资源的当前所有者。通过 `fCurrentQueueFamily` 和 `fSharingMode` 的组合，可以正确处理：
- **独占模式**: 资源在队列族间转移时需要显式所有权转移
- **并发模式**: 多个队列族可同时访问，但可能需要额外的同步

### Android 平台特殊处理
通过 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 宏，在 Android 平台编译时会启用额外的标志位：
- `fPartOfSwapchainOrAndroidWindow`: 标识资源是否来自交换链或原生窗口
- `fFromSwapchainOrAndroidWindow`: 在 drawable 信息中同样标识来源

这些标志用于优化 Android 平台的窗口合成和显示流程。

### YCbCr 颜色空间支持
Vulkan 支持外部格式的 YCbCr 图像（常用于视频解码），通过 `fYcbcrConversionInfo` 封装转换器信息，使 Skia 能够正确采样和渲染这类图像。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/gpu/GpuTypes.h | GPU 通用类型定义（如 Protected 枚举） |
| include/gpu/vk/VulkanTypes.h | 底层 Vulkan 类型（VkImage, VkFormat 等） |

### 被依赖的模块

- **GrBackendTexture/GrBackendRenderTarget**: 使用 GrVkImageInfo 包装外部 Vulkan 纹理
- **GrBackendDrawableInfo**: 使用 GrVkDrawableInfo 封装 drawable 接口
- **GrVkGpu**: Vulkan GPU 实现类使用这些结构体与 Vulkan API 交互
- **GrVkTexture/GrVkRenderTarget**: 内部使用这些信息创建和管理资源

## 设计模式与设计决策

### 1. 信息封装模式
三个结构体采用纯数据容器设计，封装 Vulkan 资源的必要信息，避免直接暴露 Vulkan 句柄操作：
- **优点**: 简化跨模块接口，便于序列化和传递
- **应用**: 通过值语义传递资源元数据，而非管理资源生命周期

### 2. 平台抽象策略
通过条件编译宏隔离平台特定字段：
- Android 平台添加交换链标志
- 其他平台编译时不包含这些字段
- 保持核心 API 跨平台一致性

### 3. 外部资源桥接
GrVkImageInfo 允许 Skia 使用非 Skia 创建的 Vulkan 资源：
- 支持与其他图形库（如游戏引擎、视频解码器）共享纹理
- 通过明确的队列族和布局信息确保同步正确性

## 性能考量

### 1. 结构体内存布局
所有结构体成员按自然对齐排列，避免额外填充：
- 整型字段（如 fSampleCount）在前
- 大对象（如 fAlloc）分布合理
- 相等性比较按字段顺序逐一检查

### 2. 队列族优化
正确设置 `fCurrentQueueFamily` 可以避免不必要的所有权转移：
- 独占模式下明确所有权可减少屏障开销
- 并发模式适用于频繁跨队列共享的场景

### 3. Drawable 独立命令缓冲区
允许 drawable 提交独立命令缓冲区的设计：
- 支持异步计算/传输操作
- 需要开发者自行管理同步，避免 Skia 引入额外开销

## 平台相关说明

### Android 平台
- 启用 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 时，额外跟踪资源是否来自系统交换链
- 用于优化 SurfaceFlinger 合成流程
- 影响资源生命周期管理（如延迟释放）

### Apple 平台
通过包含 Vulkan 类型头文件，支持 macOS 上的 MoltenVK（Metal 到 Vulkan 转换层）。

### WebGPU/跨平台
虽然此文件专用于 Vulkan，但 Skia 的后端抽象设计使得类似结构（如 GrGLTextureInfo）在其他 API 中也有对应实现。

## 相关文件

| 文件 | 关系 |
|------|------|
| include/gpu/vk/VulkanTypes.h | 提供基础 Vulkan 类型定义 |
| include/gpu/ganesh/vk/GrBackendDrawableInfo.h | 使用 GrVkDrawableInfo 的封装类 |
| src/gpu/ganesh/vk/GrVkGpu.h | 主要使用这些类型与 Vulkan 交互 |
| src/gpu/ganesh/vk/GrVkTexture.h | 使用 GrVkImageInfo 管理纹理 |
| src/gpu/ganesh/GrBackendSurface.h | 后端无关的表面抽象，内部存储 GrVkImageInfo |
| include/gpu/GpuTypes.h | 定义跨 API 通用类型（如 Protected） |
