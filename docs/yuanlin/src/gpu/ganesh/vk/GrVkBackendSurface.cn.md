# GrVkBackendSurface

> 源文件
> - include/gpu/ganesh/vk/GrVkBackendSurface.h
> - src/gpu/ganesh/vk/GrVkBackendSurface.cpp

## 概述

`GrVkBackendSurface` 模块为 Ganesh 渲染引擎提供 Vulkan 后端表面（Surface）对象的创建和操作接口。该模块实现了 Vulkan 后端的格式（Format）、纹理（Texture）和渲染目标（RenderTarget）的完整封装，支持 Vulkan 图像布局管理、YCbCr 转换、DRM 格式修饰符等高级特性。

该模块是 Skia 与 Vulkan 图形 API 交互的核心桥梁，提供了三个命名空间的工厂函数和查询函数：`GrBackendFormats`、`GrBackendTextures` 和 `GrBackendRenderTargets`。

## 架构位置

该模块位于 Ganesh 后端表面抽象层的 Vulkan 实现：

```
Skia Graphics Library
└── GPU (Ganesh)
    ├── Backend Surface Abstraction
    │   ├── GrBackendFormat         ← 抽象接口
    │   ├── GrBackendTexture        ← 抽象接口
    │   └── GrBackendRenderTarget  ← 抽象接口
    └── Backend Implementations
        └── Vulkan Backend
            ├── GrVkBackendSurface   ← 当前模块（Vulkan 实现）
            ├── GrVkGpu              ← GPU 实现
            └── GrVkImage            ← 图像管理
```

## 主要类与结构体

### GrVkBackendFormatData

Vulkan 后端格式数据类，封装 Vulkan 格式和 YCbCr 转换信息。

**继承关系**: `GrVkBackendFormatData` → `GrBackendFormatData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFormat` | `VkFormat` | Vulkan 像素格式枚举值 |
| `fYcbcrConversionInfo` | `skgpu::VulkanYcbcrConversionInfo` | YCbCr 颜色空间转换信息 |

**核心方法**

| 方法 | 功能描述 |
|------|---------|
| `asVkFormat()` | 返回 Vulkan 格式枚举值 |
| `getYcbcrConversionInfo()` | 获取 YCbCr 转换信息 |
| `compressionType()` | 返回压缩类型（如 ETC2、BC1） |
| `bytesPerBlock()` | 计算每块字节数 |
| `stencilBits()` | 返回模板位数 |
| `channelMask()` | 返回颜色通道掩码 |
| `makeTexture2D()` | 将 YCbCr 格式转换为常规 RGBA 格式 |

### GrVkBackendTextureData

Vulkan 后端纹理数据类，存储 Vulkan 图像信息和可变状态。

**继承关系**: `GrVkBackendTextureData` → `GrBackendTextureData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVkInfo` | `GrVkImageInfo` | Vulkan 图像信息（格式、布局、队列等） |
| `fMutableState` | `sk_sp<skgpu::MutableTextureState>` | 可变纹理状态（布局、队列家族） |

**核心方法**

| 方法 | 功能描述 |
|------|---------|
| `info()` | 获取 Vulkan 图像信息 |
| `getMutableState()` | 获取可变状态的智能指针 |
| `setMutableState()` | 设置可变状态 |
| `isProtected()` | 检查是否为受保护内存 |
| `isSameTexture()` | 比较是否为同一图像（通过 `VkImage` 句柄） |
| `getBackendFormat()` | 获取后端格式对象 |

### GrVkBackendRenderTargetData

Vulkan 后端渲染目标数据类，存储渲染目标的 Vulkan 图像信息。

**继承关系**: `GrVkBackendRenderTargetData` → `GrBackendRenderTargetData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVkInfo` | `GrVkImageInfo` | Vulkan 图像信息 |
| `fMutableState` | `sk_sp<skgpu::MutableTextureState>` | 可变纹理状态 |

**核心方法**

与 `GrVkBackendTextureData` 类似，提供图像信息访问、状态管理和格式查询功能。

## 公共 API 函数

### GrBackendFormats 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendFormat MakeVk(VkFormat format, bool willUseDRMFormatModifiers = false)` | 创建指定 Vulkan 格式的 `GrBackendFormat` 对象 |
| `GrBackendFormat MakeVk(const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo, bool willUseDRMFormatModifiers = false)` | 创建支持 YCbCr 转换的 `GrBackendFormat` 对象 |
| `bool AsVkFormat(const GrBackendFormat&, VkFormat*)` | 从格式对象提取 Vulkan 格式枚举 |
| `const skgpu::VulkanYcbcrConversionInfo* GetVkYcbcrConversionInfo(const GrBackendFormat&)` | 获取 YCbCr 转换信息指针 |

### GrBackendTextures 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendTexture MakeVk(int width, int height, const GrVkImageInfo&, std::string_view label = {})` | 创建 Vulkan 纹理对象 |
| `bool GetVkImageInfo(const GrBackendTexture&, GrVkImageInfo*)` | 从纹理对象提取 Vulkan 图像信息 |
| `void SetVkImageLayout(GrBackendTexture*, VkImageLayout)` | 更新纹理的 Vulkan 图像布局 |

### GrBackendRenderTargets 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendRenderTarget MakeVk(int width, int height, const GrVkImageInfo&)` | 创建 Vulkan 渲染目标对象 |
| `bool GetVkImageInfo(const GrBackendRenderTarget&, GrVkImageInfo*)` | 从渲染目标提取 Vulkan 图像信息 |
| `void SetVkImageLayout(GrBackendRenderTarget*, VkImageLayout)` | 更新渲染目标的 Vulkan 图像布局 |

## 内部实现细节

### 压缩格式识别

`compressionType()` 方法映射 Vulkan 格式到 Skia 压缩类型：

```cpp
SkTextureCompressionType compressionType() const override {
    switch (fFormat) {
        case VK_FORMAT_ETC2_R8G8B8_UNORM_BLOCK:
            return SkTextureCompressionType::kETC2_RGB8_UNORM;
        case VK_FORMAT_BC1_RGB_UNORM_BLOCK:
            return SkTextureCompressionType::kBC1_RGB8_UNORM;
        case VK_FORMAT_BC1_RGBA_UNORM_BLOCK:
            return SkTextureCompressionType::kBC1_RGBA8_UNORM;
        default:
            return SkTextureCompressionType::kNone;
    }
}
```

### 纹理类型推断

根据 YCbCr 信息和 DRM 修饰符推断纹理类型：

```cpp
static GrTextureType vk_image_info_to_texture_type(const GrVkImageInfo& info) {
    if ((info.fYcbcrConversionInfo.isValid() &&
         info.fYcbcrConversionInfo.hasExternalFormat()) ||
        info.fImageTiling == VK_IMAGE_TILING_DRM_FORMAT_MODIFIER_EXT) {
        return GrTextureType::kExternal;  // 外部纹理
    }
    return GrTextureType::k2D;  // 常规 2D 纹理
}
```

### 默认使用标志应用

为确保图像可用，自动添加默认使用标志：

```cpp
static const VkImageUsageFlags kDefaultUsageFlags =
    VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;

static const VkImageUsageFlags kDefaultTexRTUsageFlags =
    kDefaultUsageFlags |
    VK_IMAGE_USAGE_SAMPLED_BIT |
    VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;

static GrVkImageInfo apply_default_usage_flags(const GrVkImageInfo& info,
                                               VkImageUsageFlags defaultFlags) {
    if (info.fImageUsageFlags == 0) {
        GrVkImageInfo newInfo = info;
        newInfo.fImageUsageFlags = defaultFlags;
        return newInfo;
    }
    return info;
}
```

### 可变状态管理

纹理和渲染目标使用 `MutableTextureState` 跟踪动态状态：

```cpp
if (mutableState) {
    fMutableState = std::move(mutableState);
} else {
    fMutableState = sk_make_sp<skgpu::MutableTextureState>(
        skgpu::MutableTextureStates::MakeVulkan(
            info.fImageLayout,
            info.fCurrentQueueFamily));
}
```

### 图像布局更新

`SetVkImageLayout()` 函数更新可变状态：

```cpp
void SetVkImageLayout(GrBackendTexture* tex, VkImageLayout layout) {
    if (tex && tex->isValid() && tex->backend() == GrBackendApi::kVulkan) {
        GrVkBackendTextureData* data = get_and_cast_data(tex);
        SkASSERT(data);
        skgpu::MutableTextureStates::SetVkImageLayout(data->mutableState(), layout);
    }
}
```

### YCbCr 格式转换

`makeTexture2D()` 方法移除 YCbCr 转换信息，转换为常规 RGBA 格式：

```cpp
void makeTexture2D() override {
    if (fYcbcrConversionInfo.isValid()) {
        fYcbcrConversionInfo = skgpu::VulkanYcbcrConversionInfo();
        fFormat = VK_FORMAT_R8G8B8A8_UNORM;
    }
}
```

### 相等性判断

纹理相等性需要比较图像信息和可变状态：

```cpp
bool equal(const GrBackendTextureData* that) const override {
    if (auto otherVk = static_cast<const GrVkBackendTextureData*>(that)) {
        if (fMutableState != otherVk->fMutableState) {
            return false;  // 必须使用相同的可变状态对象
        }
        return GrVkImageInfoWithMutableState(fVkInfo, fMutableState.get()) ==
               GrVkImageInfoWithMutableState(otherVk->fVkInfo, fMutableState.get());
    }
    return false;
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrVkTypes` | 提供 `GrVkImageInfo` 等 Vulkan 类型 |
| `VulkanMutableTextureState` | 管理 Vulkan 图像的可变状态 |
| `GrBackendSurfacePriv` | 访问后端表面的私有构造函数 |
| `GrVkUtil` | Vulkan 工具函数（格式转换、验证等） |
| `VulkanUtilsPriv` | Vulkan 私有工具函数 |
| `GrVkTypesPriv` | Vulkan 类型的私有辅助功能 |
| `VulkanYcbcrConversionInfo` | YCbCr 颜色空间转换信息 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrVkGpu` | 创建和管理 Vulkan 表面资源 |
| `GrContext` | 创建 Vulkan 上下文时使用 |
| `GrSurface` | 封装 Vulkan 表面 |
| 互操作代码 | 与外部 Vulkan 资源交互 |
| `SkSurface` | 创建 Vulkan 支持的 Skia 表面 |

## 设计模式与设计决策

### 1. 适配器模式

将 Vulkan 的 `VkImage`、`VkFormat` 等概念适配为 Skia 的 `GrBackendTexture`、`GrBackendFormat` 接口。

### 2. 状态模式

使用 `MutableTextureState` 管理图像的动态状态（布局、队列家族），支持状态变化通知。

### 3. 工厂模式

通过命名空间函数提供清晰的创建接口，支持不同的初始化参数组合。

### 4. 策略模式

通过继承 `GrBackendFormatData` 等基类，实现 Vulkan 特定的格式和纹理管理策略。

### 5. 智能指针管理

使用 `sk_sp<skgpu::MutableTextureState>` 共享可变状态，支持多个表面对象引用同一状态。

### 6. 默认参数注入

自动为图像添加合理的默认使用标志，简化客户端代码。

### 7. 类型安全转换

使用 `get_and_cast_data()` 辅助函数确保类型安全，避免错误的向下转型。

### 8. 外部格式支持

通过 YCbCr 转换信息支持 Android 硬件缓冲区等外部格式，扩展互操作性。

## 性能考量

### 1. 状态共享

多个 `GrBackendTexture` 可以共享同一个 `MutableTextureState` 对象，减少状态管理开销。

### 2. 延迟状态同步

图像布局更新不立即提交到 GPU，而是记录在可变状态中，由后续操作批量处理。

### 3. 固定大小结构

`GrVkImageInfo` 使用固定大小的结构体，便于缓存对齐和快速复制。

### 4. 默认标志缓存

默认使用标志在编译期定义为常量，避免运行时计算。

### 5. 智能指针优化

使用 `sk_sp` 的原子引用计数，支持多线程安全的状态共享。

### 6. 条件调试代码

使用 `#if defined(SK_DEBUG)` 限制类型检查代码，确保发布版本无额外开销。

### 7. 内联函数

访问器函数（如 `asVkFormat()`、`info()`）可以被编译器内联。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/vk/GrVkTypes.h` | Vulkan 类型定义 |
| `include/gpu/vk/VulkanTypes.h` | 通用 Vulkan 类型 |
| `include/gpu/vk/VulkanMutableTextureState.h` | Vulkan 可变纹理状态 |
| `src/gpu/vk/VulkanMutableTextureStatePriv.h` | 可变状态私有辅助功能 |
| `src/gpu/ganesh/vk/GrVkUtil.h` | Vulkan 工具函数 |
| `src/gpu/vk/VulkanUtilsPriv.h` | Vulkan 私有工具函数 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面抽象接口 |
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 后端表面私有构造函数 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | Vulkan GPU 实现 |
| `include/gpu/MutableTextureState.h` | 可变纹理状态抽象接口 |
