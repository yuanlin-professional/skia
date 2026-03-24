# GrVkTypesPriv

> 源文件
> - src/gpu/ganesh/vk/GrVkTypesPriv.h
> - src/gpu/ganesh/vk/GrVkTypesPriv.cpp

## 概述

`GrVkTypesPriv` 是 Skia Ganesh Vulkan 后端中定义私有类型和工具函数的模块。它提供了 Vulkan 图像规格（`GrVkImageSpec`）的定义，以及用于类型转换和信息构建的辅助函数。该模块是 Ganesh 内部使用的，为 Vulkan 图像和表面信息的处理提供便利。

主要内容包括：
- `GrVkImageSpec` 结构体：紧凑的图像规格表示
- `GrVkImageInfoWithMutableState` 函数：更新可变纹理状态
- `GrVkImageSpecToSurfaceInfo` 函数：从图像规格生成完整的表面信息

这是一个轻量级的工具模块，为 Vulkan 类型操作提供简洁的接口。

## 架构位置

`GrVkTypesPriv` 在 Vulkan 类型系统中的位置：

```
Skia GPU 类型层次
  ├─ 公共类型 (include/gpu/ganesh/vk/GrVkTypes.h)
  │   ├─ GrVkImageInfo (公共图像信息)
  │   └─ GrVkSurfaceInfo (公共表面信息)
  └─ 私有类型 (src/gpu/ganesh/vk/GrVkTypesPriv.h) ← 当前模块
      ├─ GrVkImageSpec (内部图像规格)
      └─ 工具函数
```

该模块作为私有实现，连接公共 API 和内部实现。

## 主要类与结构体

### GrVkImageSpec

```cpp
struct GrVkImageSpec {
    VkImageTiling fImageTiling;                        // 图像平铺模式
    VkFormat fFormat;                                  // 图像格式
    VkImageUsageFlags fImageUsageFlags;                // 使用标志
    skgpu::VulkanYcbcrConversionInfo fYcbcrConversionInfo;  // YCbCr 转换信息
    VkSharingMode fSharingMode;                        // 共享模式

    GrVkImageSpec();                                   // 默认构造
    GrVkImageSpec(const GrVkSurfaceInfo& info);        // 从表面信息构造
};
```

### 成员说明

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fImageTiling` | `VkImageTiling` | 图像平铺模式（`OPTIMAL` 或 `LINEAR`） |
| `fFormat` | `VkFormat` | Vulkan 图像格式（如 `VK_FORMAT_R8G8B8A8_UNORM`） |
| `fImageUsageFlags` | `VkImageUsageFlags` | 使用标志（如 `COLOR_ATTACHMENT`、`SAMPLED` 等） |
| `fYcbcrConversionInfo` | `VulkanYcbcrConversionInfo` | YCbCr 颜色空间转换信息 |
| `fSharingMode` | `VkSharingMode` | 队列族共享模式（`EXCLUSIVE` 或 `CONCURRENT`） |

## 公共 API 函数

### 可变状态更新

```cpp
GrVkImageInfo GrVkImageInfoWithMutableState(
    const GrVkImageInfo& info,
    const skgpu::MutableTextureState* mutableState);
```

根据可变纹理状态更新图像信息。该函数创建新的 `GrVkImageInfo` 对象，包含更新后的图像布局和队列族索引。

**参数**：
- `info`：原始图像信息
- `mutableState`：新的可变状态（布局和队列族）

**返回**：更新后的图像信息

**用途**：在纹理状态转换时更新图像元数据，例如在队列间传输或布局转换后。

### 图像规格转换

```cpp
GrVkSurfaceInfo GrVkImageSpecToSurfaceInfo(
    const GrVkImageSpec& vkSpec,
    uint32_t sampleCount,
    uint32_t levelCount,
    skgpu::Protected isProtected);
```

从紧凑的图像规格生成完整的表面信息。

**参数**：
- `vkSpec`：图像规格
- `sampleCount`：采样数（MSAA）
- `levelCount`：mipmap 级别数
- `isProtected`：是否为受保护内存

**返回**：完整的表面信息对象

**用途**：在创建纹理或渲染目标时，从规格构建完整的表面配置。

## 内部实现细节

### GrVkImageSpec 构造

**默认构造**：
```cpp
GrVkImageSpec()
    : fImageTiling(VK_IMAGE_TILING_OPTIMAL)
    , fFormat(VK_FORMAT_UNDEFINED)
    , fImageUsageFlags(0)
    , fSharingMode(VK_SHARING_MODE_EXCLUSIVE) {}
```
初始化为安全的默认值：
- `OPTIMAL` 平铺（大多数情况下性能最佳）
- `UNDEFINED` 格式（需要后续设置）
- 无使用标志（需要后续设置）
- `EXCLUSIVE` 共享模式（单队列族访问）

**从 GrVkSurfaceInfo 构造**：
```cpp
GrVkImageSpec(const GrVkSurfaceInfo& info)
    : fImageTiling(info.fImageTiling)
    , fFormat(info.fFormat)
    , fImageUsageFlags(info.fImageUsageFlags)
    , fYcbcrConversionInfo(info.fYcbcrConversionInfo)
    , fSharingMode(info.fSharingMode) {}
```
提取表面信息中的关键字段，忽略采样数和级别数（这些是运行时属性）。

### 可变状态更新实现

```cpp
GrVkImageInfo GrVkImageInfoWithMutableState(
    const GrVkImageInfo& info,
    const skgpu::MutableTextureState* mutableState) {
    SkASSERT(mutableState);
    GrVkImageInfo newInfo = info;
    newInfo.fImageLayout = skgpu::MutableTextureStates::GetVkImageLayout(mutableState);
    newInfo.fCurrentQueueFamily = skgpu::MutableTextureStates::GetVkQueueFamilyIndex(mutableState);
    return newInfo;
}
```

**实现步骤**：
1. 断言可变状态非空
2. 复制原始图像信息
3. 从可变状态提取新的图像布局
4. 从可变状态提取新的队列族索引
5. 返回更新后的信息

这种按值返回的设计确保原始信息不被修改，适合函数式编程风格。

### 表面信息构建实现

```cpp
GrVkSurfaceInfo GrVkImageSpecToSurfaceInfo(
    const GrVkImageSpec& vkSpec,
    uint32_t sampleCount,
    uint32_t levelCount,
    skgpu::Protected isProtected) {
    GrVkSurfaceInfo info;
    // 共享信息
    info.fSampleCount = sampleCount;
    info.fLevelCount = levelCount;
    info.fProtected = isProtected;

    // Vulkan 信息
    info.fImageTiling = vkSpec.fImageTiling;
    info.fFormat = vkSpec.fFormat;
    info.fImageUsageFlags = vkSpec.fImageUsageFlags;
    info.fYcbcrConversionInfo = vkSpec.fYcbcrConversionInfo;
    info.fSharingMode = vkSpec.fSharingMode;

    return info;
}
```

**实现步骤**：
1. 创建空的表面信息对象
2. 填充运行时参数（采样数、级别数、保护标志）
3. 从图像规格复制 Vulkan 特定字段
4. 返回完整的表面信息

这种设计将静态规格与动态参数分离，提高了代码的模块化。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/gpu/ganesh/vk/GrVkTypes.h` | 公共 Vulkan 类型定义 |
| `include/gpu/vk/VulkanTypes.h` | 跨 GPU 的 Vulkan 类型 |
| `include/gpu/vk/VulkanMutableTextureState.h` | 可变纹理状态 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan API 包含 |
| `skgpu::MutableTextureState` | 可变状态抽象 |
| `skgpu::Protected` | 保护内存标志 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkImage` | 使用 `GrVkImageSpec` 描述图像配置 |
| `GrVkTexture` | 使用工具函数构建图像信息 |
| `GrVkRenderTarget` | 使用工具函数构建表面信息 |
| 纹理创建函数 | 使用 `GrVkImageSpecToSurfaceInfo` |

## 设计模式与设计决策

### 值语义
所有函数使用值语义（按值返回），避免指针和生命周期管理的复杂性。现代编译器的返回值优化（RVO）确保了高效性。

### 类型分离
将紧凑的内部规格（`GrVkImageSpec`）与完整的公共信息（`GrVkSurfaceInfo`）分离，适合不同的使用场景：
- **规格**：用于模板和配置传递，不包含运行时数据
- **信息**：用于实际对象创建，包含完整参数

### 不可变性
工具函数不修改输入参数，而是创建新对象，遵循不可变性原则，减少副作用。

### 断言驱动
使用断言验证前提条件（如 `SkASSERT(mutableState)`），在调试模式下捕获错误，发布版本无开销。

### 轻量级模块
整个模块只有约 50 行代码，专注于简单的类型转换，避免过度设计。

## 性能考量

### 结构体大小
`GrVkImageSpec` 是紧凑的 POD 类型，大小通常为 32-48 字节，适合栈分配和高效拷贝。

### 按值返回优化
现代编译器的 RVO 和移动语义确保按值返回不会有额外的拷贝开销：
```cpp
GrVkSurfaceInfo info = GrVkImageSpecToSurfaceInfo(...);  // 无拷贝
```

### 内联潜力
所有函数都是简单的字段赋值，编译器很可能内联，消除函数调用开销。

### 无动态分配
所有操作都在栈上完成，无堆分配，无内存碎片。

### 缓存友好
紧凑的数据结构提高缓存局部性，减少缓存未命中。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/gpu/ganesh/vk/GrVkTypes.h` | 依赖 | 公共 Vulkan 类型 |
| `include/gpu/vk/VulkanTypes.h` | 依赖 | 跨 GPU Vulkan 类型 |
| `include/gpu/vk/VulkanMutableTextureState.h` | 依赖 | 可变状态 |
| `src/gpu/ganesh/vk/GrVkImage.h` | 使用者 | 图像封装 |
| `src/gpu/ganesh/vk/GrVkTexture.h` | 使用者 | 纹理实现 |
| `src/gpu/ganesh/vk/GrVkRenderTarget.h` | 使用者 | 渲染目标实现 |
