# VulkanTexture

> 源文件
> - src/gpu/graphite/vk/VulkanTexture.h
> - src/gpu/graphite/vk/VulkanTexture.cpp

## 概述

`VulkanTexture` 是 Skia Graphite Vulkan 后端的纹理资源类，封装了 Vulkan 图像对象（`VkImage`）及其相关的 GPU 内存管理、布局转换、视图管理等功能。它是 Graphite 渲染引擎中所有纹理操作的核心组件。

主要功能包括：
- 创建和管理 Vulkan 图像及其内存分配
- 支持包装外部图像（wrapped images）
- 管理图像布局转换和队列族转移
- 创建和缓存图像视图（ImageView）
- 缓存描述符集和帧缓冲对象
- 支持 Mipmap 和 MSAA
- 支持 YCbCr 色彩空间转换
- 支持受保护内存（protected memory）
- 支持延迟内存分配（lazy allocation）
- 支持主机端直接上传数据（host-image-copy）

该类是 Vulkan 渲染管线中最基础的纹理抽象，被广泛用于渲染目标、着色器采样纹理、深度/模板缓冲等场景。

## 架构位置

`VulkanTexture` 位于 Skia Graphite 渲染引擎的 Vulkan 后端纹理层：

```
skgpu::graphite (Graphite 渲染引擎)
  ├── Texture (纹理基类)
  └── vk (Vulkan 后端)
      ├── VulkanSharedContext (Vulkan 共享上下文)
      ├── VulkanTexture (纹理实现 - 本类)
      ├── VulkanImageView (图像视图)
      ├── VulkanYcbcrConversion (YCbCr 转换)
      ├── VulkanDescriptorSet (描述符集)
      └── VulkanFramebuffer (帧缓冲)
```

在渲染管线中的位置：
```
纹理创建请求
  ↓
VulkanTexture::Make() (创建 VkImage 和内存)
  ↓
VulkanTexture (纹理对象)
  ├→ VulkanImageView (创建视图)
  ├→ VulkanDescriptorSet (绑定到描述符)
  └→ VulkanFramebuffer (作为渲染目标)
```

## 主要类与结构体

### VulkanTexture

继承自 `Texture` 基类，表示一个 Vulkan 纹理资源。

**关键成员：**
- `VkImage fImage` - Vulkan 图像对象句柄
- `VulkanAlloc fMemoryAlloc` - 内存分配信息
- `sk_sp<VulkanYcbcrConversion> fYcbcrConversion` - YCbCr 转换对象（可选）
- `STArray<2, std::unique_ptr<const VulkanImageView>> fImageViews` - 缓存的图像视图
- `STArray<3, CachedTextureDescSet> fCachedSingleTextureDescSets` - 缓存的描述符集
- `STArray<3, sk_sp<VulkanFramebuffer>> fCachedFramebuffers` - 缓存的帧缓冲对象

**主要方法：**
- `static bool MakeVkImage(...)` - 创建 Vulkan 图像和内存
- `static sk_sp<Texture> Make(...)` - 创建新纹理
- `static sk_sp<Texture> MakeWrapped(...)` - 包装外部图像
- `void setImageLayout(...)` - 设置图像布局
- `VkImageLayout currentLayout()` - 获取当前布局
- `const VulkanImageView* getImageView(...)` - 获取或创建图像视图
- `bool uploadDataOnHost(...)` - 主机端数据上传

### CreatedImageInfo

嵌套结构体，用于返回创建的图像信息。

**成员：**
- `VkImage fImage` - 图像句柄
- `VulkanAlloc fMemoryAlloc` - 内存分配信息
- `sk_sp<MutableTextureState> fMutableState` - 可变纹理状态（布局和队列族）

## 公共 API 函数

### MakeVkImage

```cpp
static bool MakeVkImage(const VulkanSharedContext* context,
                        SkISize dimensions,
                        const TextureInfo& info,
                        CreatedImageInfo* outInfo)
```

**功能：** 创建 Vulkan 图像对象和分配 GPU 内存。

**参数：**
- `context` - Vulkan 共享上下文
- `dimensions` - 纹理尺寸
- `info` - 纹理配置信息
- `outInfo` - 输出参数，返回创建的图像信息

**返回值：** 成功返回 true，失败返回 false

**实现细节：**
1. **验证参数**
   - 检查尺寸是否为空
   - 检查尺寸是否超过设备限制
   - 检查受保护内存支持

2. **配置图像创建信息**
   - 确定初始布局（线性平铺为 PREINITIALIZED，否则为 UNDEFINED）
   - 计算 Mipmap 级别数
   - 设置采样数、使用标志、共享模式等

3. **调用 Vulkan API 创建图像**
   ```cpp
   vkCreateImage(device, &imageCreateInfo, nullptr, &image);
   ```

4. **分配和绑定内存**
   - 使用 `VulkanMemory::AllocImageMemory` 分配内存
   - 支持强制专用内存（dedicated memory）
   - 支持延迟分配（lazy allocation）用于瞬时附件
   - 失败时尝试降级到常规分配
   - 绑定内存到图像：`vkBindImageMemory`

5. **创建可变状态对象**
   - 初始化布局和队列族索引

### Make

```cpp
static sk_sp<Texture> Make(const VulkanSharedContext* sharedContext,
                           SkISize dimensions,
                           const TextureInfo& info,
                           sk_sp<VulkanYcbcrConversion> ycbcrConversion,
                           std::string_view label)
```

**功能：** 创建新的 VulkanTexture 对象的工厂方法。

**参数：**
- `sharedContext` - Vulkan 共享上下文
- `dimensions` - 纹理尺寸
- `info` - 纹理配置信息
- `ycbcrConversion` - YCbCr 转换对象（可选，用于 YUV 格式）
- `label` - 调试标签

**返回值：** 智能指针包装的 Texture 对象，失败返回 nullptr

**实现：** 调用 `MakeVkImage` 创建图像，然后构造 VulkanTexture 对象。

### MakeWrapped

```cpp
static sk_sp<Texture> MakeWrapped(const VulkanSharedContext* sharedContext,
                                  SkISize dimensions,
                                  const TextureInfo& info,
                                  sk_sp<MutableTextureState> mutableState,
                                  VkImage image,
                                  const VulkanAlloc& alloc,
                                  sk_sp<VulkanYcbcrConversion> ycbcrConversion,
                                  std::string_view label)
```

**功能：** 包装外部 Vulkan 图像为 VulkanTexture 对象。

**用途：** 用于包装以下来源的图像：
- 交换链（swapchain）图像
- 外部导入的图像（如 Android 硬件缓冲区）
- 其他 Vulkan 库创建的图像

**特点：** 所有权设置为 `Ownership::kWrapped`，析构时不释放图像和内存。

### setImageLayout / setImageLayoutAndQueueIndex

```cpp
void setImageLayout(VulkanCommandBuffer* buffer,
                    VkImageLayout newLayout,
                    VkAccessFlags dstAccessMask,
                    VkPipelineStageFlags dstStageMask) const

void setImageLayoutAndQueueIndex(VulkanCommandBuffer* cmdBuffer,
                                 VkImageLayout newLayout,
                                 VkAccessFlags dstAccessMask,
                                 VkPipelineStageFlags dstStageMask,
                                 uint32_t newQueueFamilyIndex) const
```

**功能：** 在命令缓冲中插入图像布局转换屏障。

**参数：**
- `buffer/cmdBuffer` - 命令缓冲对象
- `newLayout` - 目标布局
- `dstAccessMask` - 目标访问掩码
- `dstStageMask` - 目标管线阶段掩码
- `newQueueFamilyIndex` - 目标队列族索引（仅 `setImageLayoutAndQueueIndex`）

**实现细节：**
1. **优化：跳过不必要的转换**
   - 如果新旧布局相同且为只读布局，且队列族未改变，则跳过

2. **处理共享模式差异**
   - 独占模式（EXCLUSIVE）：需要处理队列族转移
   - 并发模式（CONCURRENT）：不需要队列族转移

3. **创建图像内存屏障**
   ```cpp
   VkImageMemoryBarrier barrier = {
       .srcAccessMask = LayoutToSrcAccessMask(currentLayout),
       .dstAccessMask = dstAccessMask,
       .oldLayout = currentLayout,
       .newLayout = newLayout,
       .srcQueueFamilyIndex = currentQueueIndex,
       .dstQueueFamilyIndex = newQueueFamilyIndex,
       .image = fImage,
       ...
   };
   ```

4. **添加到命令缓冲**
   - 调用 `cmdBuffer->addImageMemoryBarrier(...)`

5. **更新可变状态**
   - 更新内部跟踪的布局和队列族索引

### getImageView

```cpp
const VulkanImageView* getImageView(VulkanImageView::Usage usage) const
```

**功能：** 获取或创建指定用途的图像视图。

**参数：** `usage` - 图像视图用途（如 Attachment、Sampling 等）

**返回值：** 图像视图指针

**实现：**
- 首先在缓存中查找匹配的视图
- 如果不存在，创建新视图并缓存
- 视图自动配置 YCbCr 转换（如果有）

### uploadDataOnHost

```cpp
bool uploadDataOnHost(const UploadSource& source, const SkIRect& dstRect) override
```

**功能：** 使用主机端直接拷贝（Host Image Copy）上传纹理数据。

**特点：**
- 不需要经过 GPU 缓冲区和传输队列
- 要求图像必须有 `VK_IMAGE_USAGE_HOST_TRANSFER_BIT` 标志
- 要求图像未被 GPU 使用
- 仅支持从 UNDEFINED 布局开始

**实现步骤：**
1. **布局转换（使用 Host API）**
   ```cpp
   vkTransitionImageLayout(device, 1, &transition);
   ```
   从 UNDEFINED 转换到 SHADER_READ_ONLY_OPTIMAL

2. **拷贝数据**
   - 为每个 Mipmap 级别构建 `VkMemoryToImageCopy` 结构
   - 调用 `vkCopyMemoryToImage` 直接从主机内存拷贝到图像

3. **更新状态**
   - 更新图像布局为 SHADER_READ_ONLY_OPTIMAL

### 辅助函数

**LayoutToPipelineSrcStageFlags**
```cpp
static VkPipelineStageFlags LayoutToPipelineSrcStageFlags(const VkImageLayout layout)
```
根据图像布局确定源管线阶段标志。

**LayoutToSrcAccessMask**
```cpp
static VkAccessFlags LayoutToSrcAccessMask(const VkImageLayout layout)
```
根据图像布局确定源访问掩码，用于正确设置内存屏障。

## 内部实现细节

### 构造函数

```cpp
VulkanTexture::VulkanTexture(const VulkanSharedContext* sharedContext,
                             SkISize dimensions,
                             const TextureInfo& info,
                             sk_sp<MutableTextureState> mutableState,
                             VkImage image,
                             const VulkanAlloc& alloc,
                             Ownership ownership,
                             sk_sp<VulkanYcbcrConversion> ycbcrConversion,
                             std::string_view label)
```

**特点：**
- 私有构造函数，仅通过工厂方法调用
- 根据是否使用延迟内存分配，传递标志给基类
- 断言：延迟内存仅用于瞬时附件
- 同步调试标签到 Vulkan 对象

### freeGpuData

```cpp
void freeGpuData() override
```

**清理顺序：**
1. 清空图像视图缓存（必须在销毁图像之前）
2. 如果所有权为 kOwned，销毁图像和释放内存
3. 对于 kWrapped 所有权，不执行任何操作

### 缓存机制

#### 图像视图缓存
- 使用 `STArray<2, ...>` 存储，预分配 2 个元素
- 按用途类型区分（Attachment、Sampling 等）
- 延迟创建，首次使用时才创建

#### 描述符集缓存
```cpp
using CachedTextureDescSet = std::pair<sk_sp<const Sampler>, sk_sp<VulkanDescriptorSet>>;
mutable STArray<3, CachedTextureDescSet> fCachedSingleTextureDescSets;
```
- 缓存与特定 Sampler 配对的描述符集
- 通过 Sampler 的唯一 ID 查找
- 避免重复创建相同配置的描述符集

#### 帧缓冲缓存
- 缓存与特定渲染通道配置配对的帧缓冲对象
- 通过 `compatible()` 方法检查配置是否匹配
- 包括 MSAA 纹理和深度/模板纹理的组合

### 延迟内存分配

```cpp
bool uses_lazy_memory(const VulkanAlloc& alloc) {
    return alloc.fFlags & VulkanAlloc::Flag::kLazilyAllocated_Flag;
}
```

**用途：** 瞬时附件（Transient Attachments）
- 仅在渲染过程中存在，不需要持久化
- 例如：MSAA 解析的中间目标、延迟渲染的 G-Buffer

**特点：**
- GPU 内存仅在实际使用时才分配物理页面
- 大幅降低内存占用
- 通过 `onUpdateGpuMemorySize()` 动态查询实际占用

**实现：**
```cpp
size_t VulkanTexture::onUpdateGpuMemorySize() {
    if (uses_lazy_memory(fMemoryAlloc)) {
        VkDeviceSize committedMemory;
        vkGetDeviceMemoryCommitment(device, fMemoryAlloc.fMemory, &committedMemory);
        return committedMemory;
    }
    return this->gpuMemorySize();
}
```

### 共享模式与队列族转移

**独占模式（VK_SHARING_MODE_EXCLUSIVE）：**
- 图像一次只能被一个队列族访问
- 需要显式的队列族所有权转移屏障
- 更高的性能（无需同步开销）

**并发模式（VK_SHARING_MODE_CONCURRENT）：**
- 图像可被多个队列族同时访问
- 不需要所有权转移屏障
- 性能略低，但使用更简单

**特殊队列族索引：**
- `VK_QUEUE_FAMILY_IGNORED` - 忽略队列族（并发模式或无需转移）
- `VK_QUEUE_FAMILY_EXTERNAL` - 外部队列（如 Android 硬件缓冲区）
- `VK_QUEUE_FAMILY_FOREIGN_EXT` - 外部队列（扩展）

### 主机上传的条件检查

`canUploadOnHost()` 检查以下条件：
1. 图像必须有 `VK_IMAGE_USAGE_HOST_TRANSFER_BIT` 标志
2. 图像不能在 GPU 上忙碌（`isTextureBusyOnGPU()`）
3. 不是 RGB888 格式（需要转换为 RGBA8888）
4. 图像从未被使用过（布局为 UNDEFINED）

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `src/gpu/graphite/Texture.h` | 基类定义 |
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | Vulkan Graphite 公共类型 |
| `src/gpu/graphite/vk/VulkanImageView.h` | 图像视图类 |
| `src/gpu/graphite/vk/VulkanYcbcrConversion.h` | YCbCr 转换 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | 共享上下文 |
| `src/gpu/graphite/vk/VulkanCommandBuffer.h` | 命令缓冲 |
| `src/gpu/vk/VulkanMemory.h` | 内存分配工具 |
| `src/core/SkMipmap.h` | Mipmap 级别计算 |

### 被依赖关系

该类被以下组件使用：
- **VulkanResourceProvider** - 创建和管理纹理资源
- **VulkanDescriptorSet** - 绑定纹理到描述符集
- **VulkanFramebuffer** - 作为渲染目标附件
- **VulkanCommandBuffer** - 记录纹理相关的渲染命令
- **UploadTask** - 执行纹理数据上传

## 设计模式与设计决策

### 工厂模式

- 使用静态 `Make` 和 `MakeWrapped` 方法而非公共构造函数
- 可以在创建失败时返回 nullptr
- 隐藏复杂的 Vulkan 对象创建细节

### 资源管理模式

- 继承自 `Resource` 基类，自动集成资源追踪系统
- 使用 `Ownership` 枚举区分自有和包装的资源
- 智能指针管理生命周期，防止内存泄漏

### 延迟创建模式

- 图像视图按需创建和缓存
- 描述符集和帧缓冲按需创建和缓存
- 避免创建未使用的对象，节省内存

### 缓存模式

- 使用 `STArray` 存储缓存对象，小数组栈分配
- 线性搜索，适合缓存项数量少的场景（通常 1-3 个）
- 缓存键包括用途、采样器、渲染通道配置等

### 可变状态模式

- 使用 `MutableTextureState` 跟踪图像布局和队列族
- 允许在运行时修改状态，同时保持纹理对象不可变
- 支持在不同上下文间共享纹理状态

### 分离接口设计

- `MakeVkImage` 仅创建 Vulkan 对象，不创建 C++ 包装类
- 允许在不同场景下复用图像创建逻辑
- 例如：测试、预创建图像池等

## 性能考量

### 内存管理优化

1. **延迟内存分配**
   - 瞬时附件使用延迟分配，大幅降低内存峰值
   - 例如：4K MSAA 渲染目标从 128MB 降至实际使用量（可能为 0）

2. **内存分配策略**
   - 支持专用内存分配（减少碎片，提高性能）
   - 降级机制：延迟分配失败时自动降级到常规分配

3. **缓存重用**
   - 图像视图、描述符集、帧缓冲按需创建并缓存
   - 避免重复创建相同配置的 Vulkan 对象

### 布局转换优化

1. **跳过冗余转换**
   - 相同布局且为只读状态时，跳过屏障插入
   - 减少命令缓冲开销和 GPU 同步点

2. **精确的访问掩码和阶段标志**
   - 根据布局精确计算源访问掩码和管线阶段
   - 最小化不必要的同步范围，提高并行性

3. **批量布局转换**
   - 多个 Mipmap 级别在单个屏障中处理
   - 减少屏障数量

### 主机上传优化

1. **Host Image Copy (HIC)**
   - 绕过 GPU 缓冲区和传输队列
   - 直接从 CPU 内存拷贝到 GPU 图像
   - 适用于初始化和低频更新场景

2. **条件检查**
   - 仅在图像空闲且从未使用时使用 HIC
   - 避免复杂的布局转换和同步

### 缓存效率

1. **STArray 栈分配**
   - 小数组（2-3 个元素）直接在栈上分配
   - 避免堆分配的开销

2. **线性搜索**
   - 缓存项数量少（通常 1-3 个）
   - 线性搜索比哈希表更快（无哈希和碰撞处理开销）

### 最佳实践

1. **复用纹理对象**
   - 避免频繁创建和销毁纹理
   - 使用资源池管理纹理生命周期

2. **预先设置正确的初始布局**
   - 创建时选择合适的初始布局（LINEAR 用 PREINITIALIZED，其他用 UNDEFINED）
   - 减少后续布局转换

3. **合理使用瞬时附件标志**
   - 仅对确实瞬时的附件使用延迟分配
   - 避免误用导致性能下降

4. **批量上传纹理数据**
   - 使用 UploadTask 批量上传多个纹理
   - 减少命令缓冲提交次数

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/graphite/Texture.h` | 基类 | 纹理基类，定义通用接口 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | 上下文 | 提供设备、接口、分配器访问 |
| `src/gpu/graphite/vk/VulkanImageView.h` | 组件 | 图像视图类，用于访问图像 |
| `src/gpu/graphite/vk/VulkanYcbcrConversion.h` | 组件 | YCbCr 色彩空间转换 |
| `src/gpu/graphite/vk/VulkanCommandBuffer.h` | 使用者 | 记录纹理相关命令 |
| `src/gpu/graphite/vk/VulkanDescriptorSet.h` | 使用者 | 绑定纹理到着色器 |
| `src/gpu/graphite/vk/VulkanFramebuffer.h` | 使用者 | 使用纹理作为渲染目标 |
| `src/gpu/graphite/vk/VulkanResourceProvider.h` | 创建者 | 资源提供者，创建纹理 |
| `src/gpu/vk/VulkanMemory.h` | 内存管理 | GPU 内存分配和释放工具 |
| `src/gpu/graphite/task/UploadTask.h` | 协作类 | 纹理数据上传任务 |
| `include/gpu/MutableTextureState.h` | 状态管理 | 可变纹理状态接口 |
