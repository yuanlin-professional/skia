# VulkanBackendTexture

> 源文件
> - `src/gpu/graphite/vk/VulkanBackendTexture.cpp`

## 概述

`VulkanBackendTexture` 提供了 Vulkan 纹理在 Skia Graphite 跨平台纹理接口中的具体实现。该文件定义了 `VulkanBackendTextureData` 类用于封装 Vulkan 特定的纹理数据（`VkImage` 句柄、内存分配信息、可变状态），并通过 `BackendTextures` 命名空间提供创建和访问 Vulkan 纹理的工厂函数及访问器。这些接口使得上层代码能够以统一的方式处理不同后端的纹理资源，同时支持与外部 Vulkan 纹理的互操作。

## 架构位置

`VulkanBackendTexture` 位于 Graphite 的纹理抽象层：

```
skgpu::graphite 纹理系统
    ├── BackendTexture (跨平台纹理接口)
    │    ├── BackendTextureData (数据基类)
    │    │    └── VulkanBackendTextureData (Vulkan 实现)
    │    └── BackendTexturePriv (内部访问辅助)
    └── BackendTextures 命名空间
         ├── MakeVulkan() - 创建 Vulkan 纹理
         ├── GetVkImage() - 提取 VkImage 句柄
         ├── GetVkImageLayout() - 获取图像布局
         ├── GetVkQueueFamilyIndex() - 获取队列家族索引
         ├── GetMemoryAlloc() - 获取内存分配信息
         └── SetMutableState() - 更新纹理状态
```

它为 Graphite 与外部 Vulkan 应用的纹理共享、导入导出提供桥梁。

## 主要类与结构体

### VulkanBackendTextureData

```cpp
class VulkanBackendTextureData final : public BackendTextureData
```

封装 Vulkan 纹理的后端数据。

**核心成员变量：**
- `VkImage fVkImage` - Vulkan 图像句柄
- `VulkanAlloc fMemoryAlloc` - 内存分配信息（来自 VMA 或自定义分配器）
- `sk_sp<skgpu::MutableTextureState> fMutableState` - 可变纹理状态（布局、队列家族）

**核心方法：**
- `VulkanBackendTextureData(...)` - 构造函数
- `VkImage image() const` - 获取图像句柄
- `VulkanAlloc memoryAllocator() const` - 获取内存分配信息
- `sk_sp<skgpu::MutableTextureState> mutableState() const` - 获取可变状态
- `void copyTo(...)` - 拷贝数据到目标
- `bool equal(...)` - 比较两个纹理数据是否相等

## 公共 API 函数

### 创建 Vulkan 纹理

```cpp
BackendTexture BackendTextures::MakeVulkan(
    SkISize dimensions,
    const VulkanTextureInfo& info,
    VkImageLayout layout,
    uint32_t queueFamilyIndex,
    VkImage image,
    VulkanAlloc vulkanMemoryAllocation
)
```

从 Vulkan 资源创建跨平台的 `BackendTexture` 对象。

**参数：**
- `dimensions` - 纹理尺寸
- `info` - Vulkan 纹理信息（格式、用途标志等）
- `layout` - 初始图像布局
- `queueFamilyIndex` - 队列家族索引
- `image` - Vulkan 图像句柄
- `vulkanMemoryAllocation` - 内存分配信息

**返回值：**
包装了 Vulkan 纹理的 `BackendTexture` 对象。

**实现：**
```cpp
return BackendTexturePriv::Make(
    dimensions,
    TextureInfos::MakeVulkan(info),
    VulkanBackendTextureData(
        vulkanMemoryAllocation,
        sk_make_sp<skgpu::MutableTextureState>(
            skgpu::MutableTextureStates::MakeVulkan(layout, queueFamilyIndex)),
        image)
);
```

### 提取 Vulkan 图像句柄

```cpp
VkImage BackendTextures::GetVkImage(const BackendTexture& tex)
```

从 `BackendTexture` 中提取底层的 `VkImage` 句柄。

**返回值：**
- 有效的 `VkImage` 句柄（如果是 Vulkan 后端且有效）
- `VK_NULL_HANDLE`（如果无效或非 Vulkan 后端）

### 获取图像布局

```cpp
VkImageLayout BackendTextures::GetVkImageLayout(const BackendTexture& tex)
```

获取纹理当前的 Vulkan 图像布局。

**返回值：**
- 当前的 `VkImageLayout`（如 `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL`）
- `VK_IMAGE_LAYOUT_UNDEFINED`（如果无效或非 Vulkan 后端）

### 获取队列家族索引

```cpp
uint32_t BackendTextures::GetVkQueueFamilyIndex(const BackendTexture& tex)
```

获取纹理当前所属的队列家族索引。

**返回值：**
- 队列家族索引（如果有效）
- 0（如果无效或非 Vulkan 后端）

### 获取内存分配信息

```cpp
VulkanAlloc BackendTextures::GetMemoryAlloc(const BackendTexture& tex)
```

获取纹理的内存分配信息（用于资源释放或共享）。

**返回值：**
- `VulkanAlloc` 结构体（包含内存句柄、偏移、大小等）
- 空 `VulkanAlloc{}`（如果无效或非 Vulkan 后端）

### 获取可变状态

```cpp
sk_sp<skgpu::MutableTextureState> BackendTextures::GetMutableState(const BackendTexture& tex)
```

获取纹理的可变状态对象（布局和队列家族）。

**返回值：**
- 智能指针指向 `MutableTextureState`（如果有效）
- 空智能指针（如果无效或非 Vulkan 后端）

### 设置可变状态

```cpp
void BackendTextures::SetMutableState(
    BackendTexture* tex,
    const skgpu::MutableTextureState& newState
)
```

更新纹理的可变状态（通常在跨队列或跨上下文使用时更新布局和队列家族）。

**参数：**
- `tex` - 要更新的纹理（非 const）
- `newState` - 新的纹理状态

## 内部实现细节

### 数据封装

`VulkanBackendTextureData` 存储三个关键组件：
1. **VkImage** - Vulkan 图像对象的句柄
2. **VulkanAlloc** - 内存分配元数据（用于释放或与外部系统交互）
3. **MutableTextureState** - 可变状态（布局和队列家族索引）

### 可变状态管理

```cpp
sk_sp<skgpu::MutableTextureState> fMutableState
```

使用智能指针管理状态对象，支持共享和自动生命周期管理。状态可通过 `SetMutableState()` 更新，用于同步纹理在不同 Vulkan 队列或上下文间的使用。

### 相等性比较

```cpp
bool equal(const BackendTextureData* that) const override {
    if (auto otherVk = static_cast<const VulkanBackendTextureData*>(that)) {
        // 仅比较 VkImage 句柄
        return fVkImage == otherVk->fVkImage;
    }
    return false;
}
```

纹理相等性仅基于 `VkImage` 句柄判定，忽略内存分配和状态信息。这意味着相同图像的不同包装被视为相等。

### 拷贝语义

```cpp
void copyTo(AnyBackendTextureData& dstData) const override {
    dstData.emplace<VulkanBackendTextureData>(fMemoryAlloc, fMutableState, fVkImage);
}
```

拷贝操作执行浅拷贝：
- `VkImage` 句柄被拷贝（不克隆图像）
- `VulkanAlloc` 结构体被拷贝（不分配新内存）
- `MutableTextureState` 智能指针被共享（引用计数增加）

### 辅助函数

```cpp
static const VulkanBackendTextureData* get_and_cast_data(const BackendTexture& tex)
static VulkanBackendTextureData* get_and_cast_data(BackendTexture* tex)
```

提供 const 和非 const 版本的数据提取函数，包含类型断言以确保安全性。

### 类型安全检查

所有访问器函数都首先验证：
1. 纹理是否有效（`tex.isValid()`）
2. 后端类型是否为 Vulkan（`tex.backend() == BackendApi::kVulkan`）

不满足条件时返回默认值（`VK_NULL_HANDLE`、`VK_IMAGE_LAYOUT_UNDEFINED` 等），避免崩溃。

## 依赖关系

**直接依赖：**
- `BackendTexture` - 跨平台纹理接口
- `BackendTextureData` - 纹理数据基类
- `BackendTexturePriv` - 内部访问辅助类
- `MutableTextureState` - 可变纹理状态
- `VulkanTextureInfo` - Vulkan 纹理信息结构
- `VulkanAlloc` - Vulkan 内存分配信息
- `VkImage` / `VkImageLayout` - Vulkan 图像类型

**被依赖者：**
- `VulkanTexture` - Graphite 内部纹理实现
- `VulkanResourceProvider` - 创建和管理纹理
- 外部应用 - 导入导出 Vulkan 纹理
- 纹理包装 API - 包装外部创建的 Vulkan 纹理

## 设计模式与设计决策

### 桥接模式（Bridge Pattern）
分离跨平台接口（`BackendTexture`）和 Vulkan 特定实现（`VulkanBackendTextureData`），允许上层代码统一处理不同后端。

### 工厂模式
`MakeVulkan()` 提供统一的创建接口，隐藏内部的 `BackendTexturePriv` 构造细节。

### 可变状态模式
将频繁变化的状态（布局、队列家族）与不变的纹理属性（尺寸、格式）分离，减少数据冗余和更新成本。

### 句柄传递
不管理 `VkImage` 的生命周期，仅存储和传递句柄。调用者负责图像的创建和销毁。

### 防御性编程
所有访问器在操作前进行多重检查，返回安全的默认值而非崩溃。

### 浅拷贝语义
拷贝操作不克隆底层 Vulkan 资源，仅复制句柄和共享状态对象，符合纹理共享的预期语义。

## 性能考量

1. **轻量级封装**
   `VulkanBackendTextureData` 仅存储三个字段（句柄、分配信息、状态指针），内存开销小。

2. **状态共享**
   `MutableTextureState` 使用智能指针共享，多个 `BackendTexture` 可以引用同一状态对象，节省内存。

3. **避免虚函数调用**
   访问器函数为非虚成员函数，编译器可内联优化。

4. **条件检查优化**
   多重检查（有效性、后端类型）在发布版本中可能被优化为单次分支。

5. **调试开销隔离**
   `type()` 方法仅在调试版本中存在，发布版本无类型检查开销。

6. **状态更新效率**
   `SetMutableState()` 通过引用计数的智能指针更新状态，避免对象重新分配。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `include/gpu/graphite/BackendTexture.h` | 跨平台纹理接口 |
| `src/gpu/graphite/BackendTexturePriv.h` | 纹理内部访问辅助 |
| `include/gpu/MutableTextureState.h` | 可变纹理状态 |
| `include/gpu/vk/VulkanMutableTextureState.h` | Vulkan 纹理状态工具 |
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | Vulkan 类型定义 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | Vulkan 工具函数 |
| `src/gpu/graphite/vk/VulkanTexture.h` | Vulkan 纹理实现 |
| `src/gpu/graphite/vk/VulkanResourceProvider.h` | Vulkan 资源提供者 |
