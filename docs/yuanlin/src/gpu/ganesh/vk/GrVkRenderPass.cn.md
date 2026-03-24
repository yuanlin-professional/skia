# GrVkRenderPass

> 源文件
> - src/gpu/ganesh/vk/GrVkRenderPass.h
> - src/gpu/ganesh/vk/GrVkRenderPass.cpp

## 概述

`GrVkRenderPass` 是 Skia Ganesh Vulkan 后端中封装 Vulkan 渲染通道（Render Pass）的核心类。它继承自 `GrVkManagedResource`，负责管理渲染通道对象的创建、兼容性检查和生命周期管理。渲染通道定义了渲染操作如何与帧缓冲附件交互，包括加载/存储操作、图像布局转换和子通道依赖关系。

主要职责包括：
- 封装 `VkRenderPass` 对象及其配置信息
- 支持颜色、resolve 和模板附件的配置
- 处理附件的加载和存储操作（load/store ops）
- 支持自依赖关系（输入附件、非相干高级混合）
- 支持从 resolve 附件加载到 MSAA 附件（discardable MSAA 优化）
- 提供兼容性检查和缓存键生成功能

该类是 Vulkan 渲染管线的基础组件，所有绘制操作都必须在渲染通道内执行。

## 架构位置

`GrVkRenderPass` 在 Vulkan 渲染系统中的位置：

```
Skia Ganesh 渲染系统
  └─ Vulkan 后端
      ├─ GrVkGpu (设备管理)
      ├─ GrVkRenderTarget (渲染目标)
      │   └─ 提供附件描述符
      ├─ GrVkFramebuffer (帧缓冲)
      │   └─ 需要兼容的渲染通道
      ├─ GrVkPipeline (管线对象)
      │   └─ 创建时需要兼容的渲染通道
      ├─ GrVkRenderPass (渲染通道定义) ← 当前类
      └─ GrVkOpsRenderPass (渲染通道执行)
          └─ 使用 GrVkRenderPass 开始渲染
```

渲染通道是 Vulkan 架构的核心概念，定义了渲染操作的结构和依赖关系。

## 主要类与结构体

### 核心类

| 类名 | 父类 | 说明 |
|------|------|------|
| `GrVkRenderPass` | `GrVkManagedResource` | Vulkan 渲染通道封装 |

### 内嵌结构体

**LoadStoreOps**
```cpp
struct LoadStoreOps {
    VkAttachmentLoadOp  fLoadOp;    // 加载操作
    VkAttachmentStoreOp fStoreOp;   // 存储操作
};
```
定义附件的加载和存储行为（load、clear、don't care / store、don't care）。

**AttachmentDesc**
```cpp
struct AttachmentDesc {
    VkFormat fFormat;                // 附件格式
    int fSamples;                    // 采样数
    LoadStoreOps fLoadStoreOps;      // 加载存储操作

    bool isCompatible(const AttachmentDesc& desc) const;
};
```
描述单个附件的属性，用于兼容性检查。

**AttachmentsDescriptor**
```cpp
struct AttachmentsDescriptor {
    AttachmentDesc fColor;           // 颜色附件
    AttachmentDesc fResolve;         // Resolve 附件
    AttachmentDesc fStencil;         // 模板附件
    uint32_t fAttachmentCount;       // 附件总数
};
```
聚合所有附件描述符。

### 枚举类型

**AttachmentFlags**（位标志）
- `kColor_AttachmentFlag = 0x1`：包含颜色附件
- `kStencil_AttachmentFlag = 0x2`：包含模板附件
- `kResolve_AttachmentFlag = 0x4`：包含 resolve 附件
- `kExternal_AttachmentFlag = 0x8`：外部导入的渲染通道

**SelfDependencyFlags**（类枚举，位标志）
- `kNone`：无自依赖
- `kForInputAttachment`：用于输入附件（subpass 读取自身）
- `kForNonCoherentAdvBlend`：用于非相干高级混合

**LoadFromResolve**
- `kNo`：不从 resolve 附件加载
- `kLoad`：从 resolve 附件加载到 MSAA 附件（discardable MSAA）

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fRenderPass` | `VkRenderPass` | Vulkan 渲染通道句柄 |
| `fAttachmentFlags` | `AttachmentFlags` | 附件标志位组合 |
| `fAttachmentsDescriptor` | `AttachmentsDescriptor` | 附件描述符 |
| `fSelfDepFlags` | `SelfDependencyFlags` | 自依赖标志 |
| `fLoadFromResolve` | `LoadFromResolve` | 是否从 resolve 加载 |
| `fGranularity` | `VkExtent2D` | 渲染区域粒度 |
| `fClearValueCount` | `uint32_t` | 需要清除的附件数量 |
| `fColorAttachmentIndex` | `uint32_t` | 颜色附件索引 |

## 公共 API 函数

### 静态工厂方法

```cpp
static GrVkRenderPass* CreateSimple(
    GrVkGpu* gpu,
    AttachmentsDescriptor* descriptor,
    AttachmentFlags flags,
    SelfDependencyFlags selfDepFlags,
    LoadFromResolve loadFromResolve);
```
创建简单渲染通道，使用基本的 LOAD/STORE 操作。

```cpp
static GrVkRenderPass* Create(
    GrVkGpu* gpu,
    const GrVkRenderPass& compatibleRenderPass,
    const LoadStoreOps& colorOp,
    const LoadStoreOps& resolveOp,
    const LoadStoreOps& stencilOp);
```
基于兼容的渲染通道创建新实例，仅改变 load/store 操作。

### 外部渲染通道构造

```cpp
explicit GrVkRenderPass(
    const GrVkGpu* gpu,
    VkRenderPass renderPass,
    uint32_t colorAttachmentIndex);
```
用于导入外部创建的渲染通道（如 Android AHardwareBuffer 集成）。

### 附件查询

```cpp
bool colorAttachmentIndex(uint32_t* index) const;
bool stencilAttachmentIndex(uint32_t* index) const;
bool hasStencilAttachment() const;
bool hasResolveAttachment() const;
```
查询附件索引和存在性。

### 兼容性检查

```cpp
bool isCompatible(GrVkRenderTarget* target,
                  SelfDependencyFlags selfDepFlags,
                  LoadFromResolve loadFromResolve) const;
```
检查渲染目标是否与此渲染通道兼容。

```cpp
bool isCompatible(const GrVkRenderPass& renderPass) const;
bool isCompatible(const AttachmentsDescriptor& desc,
                  const AttachmentFlags& flags,
                  SelfDependencyFlags selfDepFlags,
                  LoadFromResolve loadFromResolve) const;
bool isCompatibleExternalRP(VkRenderPass renderPass) const;
```
多种兼容性检查方法，用于管线和帧缓冲创建。

### Load/Store 操作比较

```cpp
bool equalLoadStoreOps(const LoadStoreOps& colorOps,
                       const LoadStoreOps& resolveOps,
                       const LoadStoreOps& stencilOps) const;
```
检查 load/store 操作是否匹配，用于渲染通道缓存。

### 访问器

```cpp
VkRenderPass vkRenderPass() const;
const VkExtent2D& granularity() const;
uint32_t clearValueCount() const;
SelfDependencyFlags selfDependencyFlags() const;
LoadFromResolve loadFromResolve() const;
```
访问渲染通道属性。

### 缓存键生成

```cpp
void genKey(skgpu::KeyBuilder* b) const;
static void GenKey(skgpu::KeyBuilder* b, ...);
```
生成用于缓存和查找的唯一键。

## 内部实现细节

### 渲染通道创建流程

`Create` 方法实现了完整的 Vulkan 渲染通道创建：

1. **验证配置**：检查自依赖和 load/store 操作的合法性
2. **设置附件描述**：配置颜色、resolve 和模板附件
3. **配置子通道**：设置主子通道（可能还有加载子通道）
4. **设置子通道依赖**：配置自依赖和子通道间依赖
5. **创建 VkRenderPass**：调用 Vulkan API
6. **查询粒度**：获取渲染区域粒度提示
7. **创建对象**：封装为 `GrVkRenderPass` 对象

### 附件配置

**颜色附件**：
```cpp
if (attachmentFlags & kColor_AttachmentFlag) {
    bool needsGeneralLayout =
        SkToBool(selfDepFlags & SelfDependencyFlags::kForInputAttachment);
    VkImageLayout layout = needsGeneralLayout
        ? VK_IMAGE_LAYOUT_GENERAL
        : VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    setup_vk_attachment_description(&attachments[currentAttachment],
                                    attachmentsDescriptor->fColor,
                                    layout, layout);
}
```
当用作输入附件时需要 `GENERAL` 布局，否则使用 `COLOR_ATTACHMENT_OPTIMAL`。

**Resolve 附件**：
```cpp
VkImageLayout layout = loadFromResolve == LoadFromResolve::kLoad
    ? VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
    : VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
```
从 resolve 加载时初始布局为 `SHADER_READ_ONLY_OPTIMAL`。

**模板附件**：
使用 `DEPTH_STENCIL_ATTACHMENT_OPTIMAL` 布局，load/store 操作应用于模板分量。

### 自依赖处理

**输入附件自依赖**：
```cpp
if (selfDepFlags & SelfDependencyFlags::kForInputAttachment) {
    subpassDescMain.inputAttachmentCount = 1;
    subpassDescMain.pInputAttachments = &colorRef;

    dependency.dstStageMask |= VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT;
    dependency.dstAccessMask |= VK_ACCESS_INPUT_ATTACHMENT_READ_BIT;
}
```
配置子通道读取自己的颜色附件作为输入。

**非相干高级混合自依赖**：
```cpp
if (selfDepFlags & SelfDependencyFlags::kForNonCoherentAdvBlend) {
    dependency.dstStageMask |= VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.dstAccessMask |= VK_ACCESS_COLOR_ATTACHMENT_READ_NONCOHERENT_BIT_EXT;
}
```
支持 `VK_EXT_blend_operation_advanced` 的非相干模式。

### Discardable MSAA 支持

当 `loadFromResolve == LoadFromResolve::kLoad` 时，创建两个子通道：

**子通道 0（加载子通道）**：
- 输入附件：resolve 附件（`SHADER_READ_ONLY_OPTIMAL`）
- 颜色附件：MSAA 附件（写入）
- 用途：将 resolve 内容加载到 MSAA 附件

**子通道 1（主子通道）**：
- 颜色附件：MSAA 附件（读写）
- Resolve 附件：resolve 附件（写入）
- 用途：正常渲染并 resolve

子通道依赖关系：
```cpp
VkSubpassDependency& dependency = dependencies[currentDependency++];
dependency.srcSubpass = 0;
dependency.dstSubpass = mainSubpass;
dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
dependency.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_READ_BIT |
                          VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
```

这种方式避免了显式的 blit 操作，利用 Vulkan 的子通道机制高效实现。

### 兼容性规则

Vulkan 渲染通道兼容性基于以下规则：
1. **附件数量和类型**：必须相同
2. **附件格式**：必须相同
3. **采样数**：必须相同
4. **自依赖标志**：必须匹配
5. **LoadFromResolve 模式**：必须匹配

注意：**Load/Store 操作不影响兼容性**，这允许多个具有不同 load/store 操作的渲染通道共享管线和帧缓冲。

### 缓存键生成

键包含所有影响兼容性的信息：
```cpp
void GenKey(skgpu::KeyBuilder* b, ...) {
    b->add32(attachmentFlags);

    if (attachmentFlags & kColor_AttachmentFlag) {
        b->add32(fColor.fFormat);
        b->add32(fColor.fSamples);
    }
    // ... resolve, stencil ...

    uint32_t extraFlags = (uint32_t)selfDepFlags;
    extraFlags |= ((uint32_t)loadFromResolve << 30);
    b->add32(extraFlags);

    // 外部渲染通道使用句柄值
    if (attachmentFlags & kExternal_AttachmentFlag) {
        b->add32((uint32_t)(externalRenderPass & 0xFFFFFFFF));
        b->add32((uint32_t)(externalRenderPass >> 32));
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrVkManagedResource` | 基类，提供资源管理功能 |
| `GrVkGpu` | Vulkan 设备和接口 |
| `GrVkRenderTarget` | 提供附件描述符 |
| `GrVkCaps` | 能力查询（输入附件、高级混合等） |
| `VulkanUtilsPriv` | Vulkan 工具函数 |
| `skgpu::KeyBuilder` | 缓存键构建 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkFramebuffer` | 创建时需要兼容的渲染通道 |
| `GrVkPipeline` | 创建时需要兼容的渲染通道 |
| `GrVkOpsRenderPass` | 开始渲染通道 |
| `GrVkResourceProvider` | 缓存和管理渲染通道 |

## 设计模式与设计决策

### 工厂模式
使用静态工厂方法创建渲染通道，隐藏复杂的 Vulkan API 调用，提供简洁的接口。

### 兼容性分离
将兼容性相关属性（格式、采样数）与运行时属性（load/store 操作）分离，允许渲染通道的重用和缓存。

### 外部渲染通道支持
通过特殊的构造函数和 `kExternal_AttachmentFlag` 标志支持外部创建的渲染通道，这对于与其他框架集成（如 Android）很重要。

### 位标志优化
使用位标志表示附件类型和自依赖，允许高效的组合和检查。

### 缓存友好设计
提供 `genKey` 方法生成唯一键，支持渲染通道的缓存和快速查找，避免重复创建。

### 延迟求值
渲染区域粒度在创建后查询，确保获取驱动提供的最优值。

## 性能考量

### 渲染通道兼容性
Vulkan 要求使用兼容的渲染通道创建管线和帧缓冲。通过明确的兼容性规则，Skia 可以最大化渲染通道的重用，减少对象创建开销。

### 子通道优化
使用子通道和自依赖而非显式同步和布局转换，利用 tile-based 渲染器的优化，减少内存带宽。

### Discardable MSAA
通过从 resolve 加载到 MSAA 的子通道设计，避免了完整的 MSAA 附件加载，在某些硬件上可显著节省内存带宽。

### 输入附件
使用输入附件自依赖支持 shader 读取前一 fragment 的输出，比创建临时纹理更高效（特别是在 tile-based GPU 上）。

### Load/Store 操作优化
仔细选择 load/store 操作可以显著影响性能：
- `DONT_CARE` 允许驱动跳过不必要的操作
- `CLEAR` 比先 load 再 clear 更高效
- `STORE` 确保结果写回内存

### 粒度提示
查询并使用渲染区域粒度可以让驱动更好地优化 tile 边界对齐。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/vk/GrVkManagedResource.h` | 父类 | 资源管理基类 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 依赖 | Vulkan GPU 设备 |
| `src/gpu/ganesh/vk/GrVkRenderTarget.h` | 协作 | 提供附件描述符 |
| `src/gpu/ganesh/vk/GrVkFramebuffer.h` | 使用者 | 需要兼容的渲染通道 |
| `src/gpu/ganesh/vk/GrVkPipeline.h` | 使用者 | 创建时需要兼容的渲染通道 |
| `src/gpu/ganesh/vk/GrVkOpsRenderPass.h` | 使用者 | 执行渲染通道 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h` | 使用者 | 缓存渲染通道 |
| `src/gpu/ganesh/vk/GrVkCaps.h` | 依赖 | 能力查询 |
| `src/gpu/vk/VulkanUtilsPriv.h` | 依赖 | Vulkan 工具函数 |
