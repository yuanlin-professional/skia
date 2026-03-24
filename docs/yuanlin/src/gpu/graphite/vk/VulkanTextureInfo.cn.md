# VulkanTextureInfo

> 源文件
> - src/gpu/graphite/vk/VulkanTextureInfo.cpp

## 概述

`VulkanTextureInfo.cpp` 实现了 Vulkan 纹理信息类的方法，包括格式转换、兼容性检查、调试字符串生成等功能。`VulkanTextureInfo` 结构体封装了创建和管理 Vulkan 纹理所需的所有配置信息，是 Graphite Vulkan 后端纹理系统的核心数据类型。

主要功能：
- 生成纹理信息的调试字符串表示
- 确定纹理的视图格式（支持 YCbCr 转换）
- 检查两个纹理信息是否兼容
- 创建和提取 `TextureInfo` 对象

## 架构位置

```
skgpu::graphite (Graphite 渲染引擎)
  └── vk (Vulkan 后端)
      ├── VulkanTextureInfo (纹理信息 - 本文件)
      ├── VulkanTexture (纹理实现)
      └── VulkanGraphiteUtils (工具函数)
```

## 主要方法

### toBackendString

```cpp
SkString VulkanTextureInfo::toBackendString() const
```

**功能：** 生成纹理信息的可读字符串表示，用于调试和日志输出。

**输出格式：**
```
flags=0x00000000,imageTiling=0,imageUsageFlags=0x00000015,sharingMode=0,aspectMask=1
```

**包含字段：**
- `fFlags` - 图像创建标志（如 PROTECTED_BIT）
- `fImageTiling` - 平铺模式（LINEAR 或 OPTIMAL）
- `fImageUsageFlags` - 使用标志（如 SAMPLED_BIT、COLOR_ATTACHMENT_BIT）
- `fSharingMode` - 共享模式（EXCLUSIVE 或 CONCURRENT）
- `fAspectMask` - 图像方面掩码（COLOR、DEPTH、STENCIL）

### viewFormat

```cpp
TextureFormat VulkanTextureInfo::viewFormat() const
```

**功能：** 确定纹理的视图格式，考虑 YCbCr 转换的情况。

**逻辑：**
1. 如果存在有效的 YCbCr 转换信息：
   - 格式为 `VK_FORMAT_UNDEFINED` → 返回 `TextureFormat::kExternal`
   - 否则，使用 YCbCr 转换信息中的格式
2. 如果没有 YCbCr 转换：
   - 直接使用 `fFormat` 字段

**用途：** 着色器采样时需要知道实际的视图格式，而非底层存储格式。

### isCompatible

```cpp
bool VulkanTextureInfo::isCompatible(const TextureInfo& that, bool requireExact) const
```

**功能：** 检查两个纹理信息是否兼容，用于纹理复用和缓存查找。

**参数：**
- `that` - 另一个纹理信息对象
- `requireExact` - 是否要求精确匹配使用标志

**兼容性条件：**
- 创建标志相同 (`fFlags`)
- 格式相同 (`fFormat`)
- 平铺模式相同 (`fImageTiling`)
- 共享模式相同 (`fSharingMode`)
- 方面掩码相同 (`fAspectMask`)
- YCbCr 转换信息相同 (`fYcbcrConversionInfo`)
- 使用标志兼容（根据 `requireExact` 参数）

**使用标志兼容性：**
- 如果 `requireExact=true`：使用标志必须完全相同
- 如果 `requireExact=false`：`that` 的使用标志必须是当前对象的超集

## TextureInfos 命名空间

### MakeVulkan

```cpp
TextureInfo MakeVulkan(const VulkanTextureInfo& vkInfo)
```

**功能：** 从 Vulkan 特定信息创建跨后端的 `TextureInfo` 对象。

**实现：** 调用 `TextureInfoPriv::Make` 封装 Vulkan 信息。

### GetVulkanTextureInfo

```cpp
bool GetVulkanTextureInfo(const TextureInfo& info, VulkanTextureInfo* out)
```

**功能：** 从跨后端的 `TextureInfo` 对象提取 Vulkan 特定信息。

**返回值：** 成功返回 true，失败返回 false

**实现：** 调用 `TextureInfoPriv::Copy` 提取 Vulkan 信息。

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | `VulkanTextureInfo` 定义 |
| `src/gpu/graphite/TextureInfoPriv.h` | 私有纹理信息操作 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | Vulkan 工具函数 |
| `src/gpu/vk/VulkanUtilsPriv.h` | Vulkan 格式转换 |

### 被依赖关系

- **VulkanTexture** - 使用纹理信息创建 VkImage
- **VulkanResourceProvider** - 纹理缓存和兼容性检查
- **TextureProxy** - 跨后端纹理代理
- **调试工具** - 纹理信息输出

## 设计决策

### 分离的视图格式

`viewFormat()` 方法将底层存储格式与着色器视图格式分离，支持 YCbCr 格式的特殊处理。这对于视频纹理和外部格式至关重要。

### 灵活的兼容性检查

`isCompatible` 方法的 `requireExact` 参数允许两种兼容性检查模式：
- 严格模式：用于精确缓存匹配
- 宽松模式：允许使用标志超集，支持纹理复用

### TextureInfos 命名空间

使用命名空间函数而非类成员函数，将跨后端接口与 Vulkan 特定实现分离，保持公共 API 的简洁性。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | 类型定义 | `VulkanTextureInfo` 结构体定义 |
| `src/gpu/graphite/vk/VulkanTexture.h` | 使用者 | 纹理资源实现 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | 工具 | 格式转换函数 |
| `src/gpu/graphite/TextureInfoPriv.h` | 私有接口 | 纹理信息内部操作 |
