# VulkanFramebuffer

> 源文件
> - `src/gpu/graphite/vk/VulkanFramebuffer.h`
> - `src/gpu/graphite/vk/VulkanFramebuffer.cpp`

## 概述

`VulkanFramebuffer` 是 Skia Graphite 的 Vulkan 后端中用于封装 `VkFramebuffer` 对象的资源包装类。它管理帧缓冲对象的生命周期，并维护对关联纹理（MSAA 纹理和深度模板纹理）的引用，确保这些纹理在帧缓冲使用期间保持有效。该类提供兼容性检查功能，用于帧缓冲的缓存和复用，避免重复创建相同配置的帧缓冲对象。

## 架构位置

`VulkanFramebuffer` 位于 Vulkan 渲染管线的资源管理层：

```
skgpu::graphite 渲染架构
    ├── Resource (资源基类)
    │    └── VulkanFramebuffer
    │         ├── 封装 VkFramebuffer 句柄
    │         ├── 持有 VulkanTexture 引用（MSAA、深度模板）
    │         └── 提供兼容性检查
    └── VulkanCommandBuffer 使用 VulkanFramebuffer
         └── 与 VulkanRenderPass 配合进行渲染
```

它在渲染通道开始时被绑定，定义了渲染目标的附件配置。

## 主要类与结构体

### VulkanFramebuffer

```cpp
class VulkanFramebuffer : public Resource
```

**核心成员变量：**
- `VkFramebuffer fFramebuffer` - Vulkan 帧缓冲对象句柄
- `sk_sp<VulkanTexture> fMsaaTexture` - MSAA 纹理（可选）
- `sk_sp<VulkanTexture> fDepthStencilTexture` - 深度模板纹理（可选）
- `const VulkanSharedContext* fSharedContext` - Vulkan 共享上下文
- `bool fLoadMSAAFromResolve` - 是否从解析纹理加载 MSAA 数据

**核心方法：**
- `static sk_sp<VulkanFramebuffer> Make()` - 工厂方法，创建帧缓冲
- `bool compatible()` - 检查帧缓冲是否与给定配置兼容
- `VkFramebuffer framebuffer()` - 获取 Vulkan 帧缓冲句柄
- `void freeGpuData()` - 释放 GPU 资源

## 公共 API 函数

### 帧缓冲创建

```cpp
static sk_sp<VulkanFramebuffer> Make(
    const VulkanSharedContext* context,
    const VkFramebufferCreateInfo& framebufferInfo,
    const RenderPassDesc& renderPassDesc,
    sk_sp<VulkanTexture> msaaTexture,
    sk_sp<VulkanTexture> depthStencilTexture
)
```

创建 Vulkan 帧缓冲对象。

**参数：**
- `context` - Vulkan 共享上下文
- `framebufferInfo` - Vulkan 帧缓冲创建信息
- `renderPassDesc` - 渲染通道描述（用于提取配置信息）
- `msaaTexture` - MSAA 纹理（可为 nullptr）
- `depthStencilTexture` - 深度模板纹理（可为 nullptr）

**返回值：**
智能指针指向新创建的 `VulkanFramebuffer`，创建失败返回 nullptr。

**实现流程：**
1. 调用 `vkCreateFramebuffer` 创建 Vulkan 帧缓冲对象
2. 检查创建结果，失败返回 nullptr
3. 从 `renderPassDesc` 提取 `loadMSAAFromResolve` 标志
4. 构造 `VulkanFramebuffer` 对象并返回智能指针

### 兼容性检查

```cpp
bool compatible(
    const RenderPassDesc& renderPassDesc,
    const VulkanTexture* msaaTexture,
    const VulkanTexture* depthStencilTexture
)
```

检查帧缓冲是否与给定配置兼容，用于帧缓冲缓存复用。

**参数：**
- `renderPassDesc` - 渲染通道描述
- `msaaTexture` - 待检查的 MSAA 纹理
- `depthStencilTexture` - 待检查的深度模板纹理

**返回值：**
- `true` - 兼容，可复用此帧缓冲
- `false` - 不兼容，需创建新帧缓冲

**兼容性判定条件：**
1. `loadMSAAFromResolve` 标志必须匹配
2. MSAA 纹理必须匹配（通过 `uniqueID()` 比较）
3. 深度模板纹理必须匹配

### 帧缓冲句柄访问

```cpp
VkFramebuffer framebuffer()
```

返回底层的 `VkFramebuffer` 句柄，用于绑定到渲染通道。

### GPU 资源释放

```cpp
void freeGpuData() override
```

释放 Vulkan 帧缓冲对象，在资源销毁时自动调用。

## 内部实现细节

### 构造函数

```cpp
VulkanFramebuffer::VulkanFramebuffer(
    const VulkanSharedContext* context,
    VkFramebuffer framebuffer,
    sk_sp<VulkanTexture> msaaTexture,
    sk_sp<VulkanTexture> depthStencilTexture,
    bool loadMSAAFromResolve
)
    : Resource(context, Ownership::kOwned, /*gpuMemorySize=*/0)
    , fSharedContext(context)
    , fFramebuffer(framebuffer)
    , fMsaaTexture(std::move(msaaTexture))
    , fDepthStencilTexture(std::move(depthStencilTexture))
    , fLoadMSAAFromResolve(loadMSAAFromResolve)
```

**关键设计：**
- **GPU 内存大小设为 0**：帧缓冲对象本身不占用 GPU 内存（仅是附件的引用容器）
- **所有权标记为 kOwned**：表示此类负责释放 `VkFramebuffer`
- **纹理智能指针**：通过 `sk_sp` 持有纹理引用，确保纹理在帧缓冲使用期间不被释放

### 纹理兼容性判定

```cpp
auto compatibleTextures = [](const VulkanTexture* tex1, const VulkanTexture* tex2) {
    if (tex1 && tex2) {
        return tex1->uniqueID() == tex2->uniqueID();
    } else if (!tex1 && !tex2) {
        return true;
    }
    return false;
};
```

**逻辑：**
- 两个纹理都存在：比较唯一 ID
- 两个纹理都不存在：视为兼容
- 一个存在一个不存在：不兼容

这种设计支持以下场景：
- 无 MSAA 渲染（两者 MSAA 纹理都为 nullptr）
- 无深度模板渲染（两者深度模板纹理都为 nullptr）

### LoadMSAAFromResolve 标志

```cpp
bool loadMSAAFromResolve = RenderPassDescWillLoadMSAAFromResolve(renderPassDesc);
```

该标志指示是否从解析纹理（单采样）加载数据到 MSAA 纹理。这影响渲染通道的加载操作配置，因此必须在兼容性检查中考虑。

### 资源释放

```cpp
void VulkanFramebuffer::freeGpuData() {
    VULKAN_CALL(fSharedContext->interface(),
                DestroyFramebuffer(fSharedContext->device(), fFramebuffer, nullptr));
}
```

仅释放 `VkFramebuffer` 对象，纹理资源由智能指针自动管理（引用计数减一）。

## 依赖关系

**直接依赖：**
- `Resource` - 资源基类，提供生命周期管理
- `VulkanSharedContext` - Vulkan 共享上下文，提供设备和接口
- `VulkanTexture` - Vulkan 纹理类，作为附件
- `RenderPassDesc` - 渲染通道描述
- `VkFramebuffer` / `VkFramebufferCreateInfo` - Vulkan 帧缓冲类型

**被依赖者：**
- `VulkanCommandBuffer` - 使用帧缓冲进行渲染
- `VulkanRenderPass` - 与帧缓冲配合定义渲染通道
- `VulkanResourceProvider` - 创建和缓存帧缓冲

## 设计模式与设计决策

### RAII 资源管理
通过 `Resource` 基类和智能指针管理 Vulkan 对象生命周期，确保资源正确释放。

### 工厂模式
`Make()` 静态方法封装 Vulkan API 调用和对象构造，提供统一的创建接口。

### 引用持有而非克隆
持有纹理的智能指针引用，而非克隆纹理，避免不必要的资源复制。

### 缓存友好设计
`compatible()` 方法支持帧缓冲缓存和复用，减少 `vkCreateFramebuffer` 调用次数。

### 轻量级对象
帧缓冲对象本身不占用 GPU 内存（`gpuMemorySize=0`），仅是附件配置的逻辑封装。

### 部分兼容性检查
仅检查 MSAA 和深度模板纹理，假设调用者已确保颜色附件匹配。这种设计简化了检查逻辑，将职责分离到调用者。

## 性能考量

1. **帧缓冲复用**
   通过 `compatible()` 检查支持帧缓冲缓存，避免重复创建相同配置的帧缓冲对象，减少 Vulkan 驱动开销。

2. **智能指针开销**
   使用 `sk_sp` 引用纹理，引入原子引用计数开销，但换取了自动生命周期管理和线程安全。

3. **唯一 ID 比较**
   纹理兼容性通过 `uniqueID()` 比较（整数比较），比指针比较更可靠且不依赖内存地址。

4. **无内存分配**
   帧缓冲对象不分配 GPU 内存，创建和销毁成本低。

5. **移动语义**
   构造函数使用 `std::move` 转移纹理智能指针，避免不必要的引用计数操作。

6. **延迟释放**
   `freeGpuData()` 在资源真正需要释放时才调用，支持延迟删除策略。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Resource.h` | 资源基类 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 共享上下文 |
| `src/gpu/graphite/vk/VulkanTexture.h` | Vulkan 纹理类 |
| `src/gpu/graphite/RenderPassDesc.h` | 渲染通道描述 |
| `src/gpu/graphite/vk/VulkanCommandBuffer.h` | Vulkan 命令缓冲区 |
| `src/gpu/graphite/vk/VulkanRenderPass.h` | Vulkan 渲染通道 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | Vulkan 工具函数 |
| `include/gpu/vk/VulkanTypes.h` | Vulkan 类型定义 |
