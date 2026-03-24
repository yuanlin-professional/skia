# GrVkImageView

> 源文件
> - src/gpu/ganesh/vk/GrVkImageView.h
> - src/gpu/ganesh/vk/GrVkImageView.cpp

## 概述

`GrVkImageView` 是 Skia 图形库中对 Vulkan `VkImageView` 对象的轻量级封装类。它继承自 `GrVkManagedResource`,负责创建和管理 Vulkan 图像视图对象,并处理与 YCbCr 颜色转换相关的配置。图像视图是 Vulkan 中访问图像数据的接口,定义了如何解释图像的格式、子资源范围和颜色通道映射。

`GrVkImageView` 提供了工厂方法用于创建颜色附件和模板附件的视图,支持 mipmap 级别配置和 YCbCr 采样器转换。该类作为图像和着色器/帧缓冲区之间的桥梁,是 Vulkan 资源管理中的基础组件。

## 架构位置

```
Skia 渲染架构
├── GrVkManagedResource (Vulkan 托管资源基类)
│   └── GrVkImageView ← 当前类
│       ├── VkImageView (Vulkan 原生句柄)
│       └── GrVkSamplerYcbcrConversion (可选的 YCbCr 转换)
```

`GrVkImageView` 在 Skia 架构中处于资源封装层,被以下模块使用:
- `GrVkImage`: 图像对象包含 framebuffer view 和 texture view
- `GrVkFramebuffer`: 帧缓冲区引用图像视图作为附件
- `GrVkTexture`: 纹理对象使用图像视图进行采样

## 主要类与结构体

### 继承关系
```
GrManagedResource (资源管理基类)
  ↑
GrVkManagedResource (Vulkan 托管资源)
  ↑
GrVkImageView (图像视图)
```

### Type 枚举

```cpp
enum Type {
    kColor_Type,    // 颜色附件/纹理视图
    kStencil_Type   // 模板附件视图
};
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fImageView` | `VkImageView` | Vulkan 图像视图句柄 |
| `fYcbcrConversion` | `GrVkSamplerYcbcrConversion*` | YCbCr 颜色转换对象(可选) |
| `fGpu` | `const GrVkGpu*` | 继承自基类,GPU 对象指针 |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `static sk_sp<const GrVkImageView> Make(GrVkGpu*, VkImage, VkFormat, Type, uint32_t miplevels, const VulkanYcbcrConversionInfo&)` | 静态工厂方法,创建图像视图 |
| `VkImageView imageView() const` | 获取 Vulkan 图像视图句柄 |
| `void dumpInfo() const override` (仅调试) | 输出调试信息 |

## 内部实现细节

### 图像视图创建流程

```cpp
sk_sp<const GrVkImageView> GrVkImageView::Make(
    GrVkGpu* gpu,
    VkImage image,
    VkFormat format,
    Type viewType,
    uint32_t miplevels,
    const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo) {

    // 1. 处理 YCbCr 颜色转换(如果需要)
    void* pNext = nullptr;
    VkSamplerYcbcrConversionInfo conversionInfo;
    GrVkSamplerYcbcrConversion* ycbcrConversion = nullptr;

    if (ycbcrInfo.isValid()) {
        SkASSERT(gpu->vkCaps().supportsYcbcrConversion());
        SkASSERT(format == ycbcrInfo.format());

        // 查找或创建 YCbCr 转换对象
        ycbcrConversion =
            gpu->resourceProvider()
               .findOrCreateCompatibleSamplerYcbcrConversion(ycbcrInfo);
        if (!ycbcrConversion) {
            return nullptr;
        }

        // 设置 pNext 链
        conversionInfo.sType = VK_STRUCTURE_TYPE_SAMPLER_YCBCR_CONVERSION_INFO;
        conversionInfo.pNext = nullptr;
        conversionInfo.conversion = ycbcrConversion->ycbcrConversion();
        pNext = &conversionInfo;
    }

    // 2. 创建 VkImageView
    VkImageView imageView;
    VkImageViewCreateInfo viewInfo = {
        .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .pNext = pNext,  // YCbCr 转换信息(如果有)
        .flags = 0,
        .image = image,
        .viewType = VK_IMAGE_VIEW_TYPE_2D,
        .format = format,
        .components = {  // 颜色通道映射(默认为 identity)
            VK_COMPONENT_SWIZZLE_IDENTITY,
            VK_COMPONENT_SWIZZLE_IDENTITY,
            VK_COMPONENT_SWIZZLE_IDENTITY,
            VK_COMPONENT_SWIZZLE_IDENTITY
        },
        .subresourceRange = {
            .aspectMask = VK_IMAGE_ASPECT_COLOR_BIT,  // 默认颜色
            .baseMipLevel = 0,
            .levelCount = miplevels,  // mipmap 级别数
            .baseArrayLayer = 0,
            .layerCount = 1
        }
    };

    // 3. 处理模板附件特殊情况
    if (viewType == kStencil_Type) {
        viewInfo.subresourceRange.aspectMask = VK_IMAGE_ASPECT_STENCIL_BIT;
    }

    // 4. 调用 Vulkan API 创建图像视图
    VkResult err;
    GR_VK_CALL_RESULT(gpu, err,
        CreateImageView(gpu->device(), &viewInfo, nullptr, &imageView));
    if (err) {
        return nullptr;
    }

    // 5. 返回封装对象
    return sk_sp<const GrVkImageView>(
        new GrVkImageView(gpu, imageView, ycbcrConversion));
}
```

### 资源释放

```cpp
void GrVkImageView::freeGPUData() const {
    // 1. 销毁 VkImageView
    GR_VK_CALL(fGpu->vkInterface(),
               DestroyImageView(fGpu->device(), fImageView, nullptr));

    // 2. 释放 YCbCr 转换对象引用
    if (fYcbcrConversion) {
        fYcbcrConversion->unref();
    }
}
```

### 调试信息输出

```cpp
#ifdef SK_TRACE_MANAGED_RESOURCES
void GrVkImageView::dumpInfo() const {
    SkDebugf("GrVkImageView: %" PRIdPTR " (%d refs)\n",
             (intptr_t)fImageView, this->getRefCnt());
}
#endif
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrVkManagedResource` | 基类,提供资源生命周期管理 |
| `GrVkGpu` | GPU 对象,提供设备句柄和 Vulkan 接口 |
| `GrVkSamplerYcbcrConversion` | YCbCr 颜色转换对象 |
| `GrVkResourceProvider` | 资源提供者,查找或创建 YCbCr 转换 |
| `GrVkCaps` | 能力查询,检查 YCbCr 支持 |
| `VulkanYcbcrConversionInfo` | YCbCr 转换配置信息 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrVkImage` | 图像对象持有 framebuffer view 和 texture view |
| `GrVkFramebuffer` | 帧缓冲区引用图像视图作为附件 |
| `GrVkTexture` | 纹理对象使用图像视图进行采样 |
| `GrVkDescriptorSet` | 描述符集引用图像视图 |

## 设计模式与设计决策

### 1. 工厂模式 (Factory Pattern)

使用静态工厂方法 `Make()` 创建对象:

```cpp
static sk_sp<const GrVkImageView> Make(...);
```

**优势**:
- 构造函数私有,控制对象创建
- 失败时可返回 nullptr
- 支持复杂的初始化逻辑

### 2. RAII 资源管理

通过智能指针 `sk_sp` 和继承 `GrVkManagedResource` 自动管理生命周期:

```cpp
sk_sp<const GrVkImageView> view = GrVkImageView::Make(...);
// 离开作用域时自动调用 freeGPUData()
```

### 3. 组合模式 (Composition)

将 YCbCr 转换作为可选组件:

```cpp
GrVkSamplerYcbcrConversion* fYcbcrConversion;
// 如果不需要 YCbCr 转换,该指针为 nullptr
```

**优势**:
- 解耦 YCbCr 转换功能
- 节省不使用该功能时的内存

### 4. 不可变性 (Immutability)

返回 `const GrVkImageView`:

```cpp
sk_sp<const GrVkImageView> view = ...;
```

**优势**:
- 图像视图创建后不可修改,线程安全
- 防止意外修改共享资源

### 5. 延迟验证

在 `Make()` 方法中进行能力检查:

```cpp
if (ycbcrInfo.isValid()) {
    SkASSERT(gpu->vkCaps().supportsYcbcrConversion());
    SkASSERT(format == ycbcrInfo.format());
}
```

确保只在支持的设备上创建 YCbCr 图像视图。

## 性能考量

### 1. 轻量级封装

`GrVkImageView` 仅包含两个成员变量:
- `VkImageView` 句柄(8 字节)
- `GrVkSamplerYcbcrConversion*` 指针(8 字节)

总计 16 字节(加上基类指针),内存开销极小。

### 2. 缓存复用

图像视图通常被缓存:
- `GrVkImage::fFramebufferView`: 用于附件的视图
- `GrVkImage::fTextureView`: 用于采样的视图

避免重复创建 `VkImageView` 对象。

### 3. YCbCr 转换复用

```cpp
ycbcrConversion = gpu->resourceProvider()
    .findOrCreateCompatibleSamplerYcbcrConversion(ycbcrInfo);
```

`GrVkResourceProvider` 缓存 YCbCr 转换对象,相同参数复用。

### 4. 引用计数管理

使用 `sk_sp` 智能指针:
- 多个对象可共享同一个图像视图
- 自动管理引用计数,无需手动释放

### 5. 懒销毁

`VkImageView` 在对象析构时才销毁:
- 延迟销毁减少 API 调用频率
- 批量销毁更高效

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/vk/GrVkManagedResource.h` | 基类定义 |
| `src/gpu/ganesh/GrManagedResource.h` | 资源管理基类 |
| `src/gpu/ganesh/vk/GrVkImage.h/cpp` | 使用 GrVkImageView 作为附件和纹理视图 |
| `src/gpu/ganesh/vk/GrVkGpu.h/cpp` | GPU 对象,提供设备句柄 |
| `src/gpu/ganesh/vk/GrVkSamplerYcbcrConversion.h/cpp` | YCbCr 颜色转换 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp` | 资源提供者,管理 YCbCr 转换 |
| `src/gpu/ganesh/vk/GrVkFramebuffer.h/cpp` | 帧缓冲区使用图像视图 |
| `src/gpu/ganesh/vk/GrVkTexture.h/cpp` | 纹理使用图像视图 |
| `include/gpu/vk/VulkanTypes.h` | VulkanYcbcrConversionInfo 定义 |
