# VulkanGraphiteTypes

> 源文件: `include/gpu/graphite/vk/VulkanGraphiteTypes.h`

## 概述
VulkanGraphiteTypes 定义了 Skia Graphite 渲染系统中 Vulkan 后端的核心类型和工厂函数。该文件提供了纹理信息封装、后端纹理创建、信号量管理等关键功能,是 Graphite Vulkan 后端与上层 API 之间的类型桥梁。

## 架构位置
该文件位于 Skia Graphite GPU 后端的 Vulkan 平台层,属于 `skgpu::graphite` 命名空间。它扩展了通用的 `TextureInfo` 和 `BackendTexture` 类型,为 Vulkan 提供特定的实现,位于平台抽象层和具体 Vulkan 实现之间。

## 主要类与结构体

### VulkanTextureInfo
封装 Vulkan 纹理创建和使用所需的完整信息,继承自 `TextureInfo::Data`。

**继承关系**: `TextureInfo::Data` → `VulkanTextureInfo`

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFlags | VkImageCreateFlags | 图像创建标志 |
| fFormat | VkFormat | Vulkan 像素格式 (如 VK_FORMAT_R8G8B8A8_UNORM) |
| fImageTiling | VkImageTiling | 平铺模式 (OPTIMAL/LINEAR) |
| fImageUsageFlags | VkImageUsageFlags | 用途标志 (采样、渲染目标、传输等) |
| fSharingMode | VkSharingMode | 共享模式 (EXCLUSIVE/CONCURRENT) |
| fAspectMask | VkImageAspectFlags | 图像方面掩码 (颜色、深度、模板、平面) |
| fYcbcrConversionInfo | VulkanYcbcrConversionInfo | YCbCr 颜色转换信息 |

**支持的图像创建标志**:
- `VK_IMAGE_CREATE_PROTECTED_BIT`: 受保护内存
- `VK_IMAGE_CREATE_MULTISAMPLED_RENDER_TO_SINGLE_SAMPLED_BIT_EXT`: 多采样渲染到单采样 (需扩展)

**设计特点**:
- 使用默认初始化为安全值 (如 `VK_FORMAT_UNDEFINED`)
- 支持 YCbCr 平面采样 (通过 `fAspectMask` 指定特定平面)
- 继承采样数和 mipmap 级别信息

## 公共 API 函数

### 构造函数
#### 默认构造函数
```cpp
VulkanTextureInfo() = default;
```
- **功能**: 创建未初始化的纹理信息
- **默认值**: 格式为 UNDEFINED,平铺为 OPTIMAL,方面为 COLOR_BIT

#### 完整构造函数
```cpp
VulkanTextureInfo(VkSampleCountFlagBits sampleCount,
                  Mipmapped mipmapped,
                  VkImageCreateFlags flags,
                  VkFormat format,
                  VkImageTiling imageTiling,
                  VkImageUsageFlags imageUsageFlags,
                  VkSharingMode sharingMode,
                  VkImageAspectFlags aspectMask,
                  VulkanYcbcrConversionInfo ycbcrConversionInfo)
```
- **功能**: 创建包含所有配置的纹理信息
- **参数**:
  - `sampleCount`: MSAA 采样数 (1/2/4/8/16/32/64)
  - `mipmapped`: 是否生成 mipmap 链
  - `flags`: 图像创建标志
  - `format`: Vulkan 像素格式
  - `imageTiling`: 平铺模式 (OPTIMAL 性能更好)
  - `imageUsageFlags`: 用途标志位掩码
  - `sharingMode`: 队列共享模式
  - `aspectMask`: 方面掩码 (通常为 COLOR_BIT)
  - `ycbcrConversionInfo`: YCbCr 转换配置 (可选)

### `isProtected()`
```cpp
Protected isProtected() const;
```
- **功能**: 检查是否使用受保护内存
- **返回值**: `Protected::kYes` 或 `Protected::kNo`
- **实现**: 检查 `fFlags & VK_IMAGE_CREATE_PROTECTED_BIT`

### `viewFormat()`
```cpp
TextureFormat viewFormat() const;
```
- **功能**: 获取视图格式 (用于着色器采样)
- **返回值**: Skia 通用的 `TextureFormat` 枚举
- **用途**: 将 Vulkan 特定格式转换为平台无关格式

### `toBackendString()`
```cpp
SkString toBackendString() const override;
```
- **功能**: 生成可读的后端描述字符串
- **返回值**: 包含格式、用途、标志等信息的字符串
- **用途**: 调试和日志输出

### `isCompatible()`
```cpp
bool isCompatible(const TextureInfo& that, bool requireExact) const override;
```
- **功能**: 检查两个纹理信息是否兼容
- **参数**:
  - `that`: 待比较的纹理信息
  - `requireExact`: 是否要求完全匹配
- **返回值**: 兼容返回 true
- **用途**: 纹理复用、格式转换判断

## 工厂函数命名空间

### TextureInfos 命名空间

#### `MakeVulkan`
```cpp
SK_API TextureInfo MakeVulkan(const VulkanTextureInfo& vkInfo);
```
- **功能**: 从 Vulkan 特定信息创建通用 `TextureInfo`
- **参数**: `vkInfo` - Vulkan 纹理信息
- **返回值**: 平台无关的 `TextureInfo` 对象
- **用途**: 封装后端细节,提供统一接口

#### `GetVulkanTextureInfo`
```cpp
SK_API bool GetVulkanTextureInfo(const TextureInfo& info,
                                  VulkanTextureInfo* vkInfo);
```
- **功能**: 从通用 `TextureInfo` 提取 Vulkan 特定信息
- **参数**:
  - `info`: 通用纹理信息
  - `vkInfo`: 输出参数,填充 Vulkan 信息
- **返回值**: 成功返回 true,类型不匹配返回 false
- **用途**: 向下转型,获取后端细节

### BackendTextures 命名空间

#### `MakeVulkan`
```cpp
SK_API BackendTexture MakeVulkan(SkISize dimensions,
                                 const VulkanTextureInfo& info,
                                 VkImageLayout layout,
                                 uint32_t queueFamilyIndex,
                                 VkImage image,
                                 VulkanAlloc alloc);
```
- **功能**: 包装外部 Vulkan 图像为 Skia 后端纹理
- **参数**:
  - `dimensions`: 纹理尺寸 (宽度和高度)
  - `info`: Vulkan 纹理信息
  - `layout`: 当前图像布局 (如 `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL`)
  - `queueFamilyIndex`: 拥有队列族索引
  - `image`: 外部 VkImage 句柄
  - `alloc`: 内存分配信息
- **返回值**: Skia 可使用的 `BackendTexture` 对象
- **用途**: 与外部 Vulkan 代码互操作,共享纹理

### BackendSemaphores 命名空间

#### `MakeVulkan`
```cpp
SK_API BackendSemaphore MakeVulkan(VkSemaphore semaphore);
```
- **功能**: 包装 Vulkan 信号量为 Skia 后端信号量
- **参数**: `semaphore` - VkSemaphore 句柄
- **返回值**: 平台无关的 `BackendSemaphore` 对象
- **用途**: GPU 命令同步,跨队列依赖

#### `GetVkSemaphore`
```cpp
SK_API VkSemaphore GetVkSemaphore(const BackendSemaphore& semaphore);
```
- **功能**: 从后端信号量提取 Vulkan 信号量句柄
- **参数**: `semaphore` - Skia 后端信号量
- **返回值**: VkSemaphore 句柄,类型不匹配返回 VK_NULL_HANDLE
- **用途**: 将 Skia 信号量传递给外部 Vulkan 代码

## 内部实现细节

### 类型擦除机制
`VulkanTextureInfo` 通过 `TextureInfo::Data` 基类实现类型擦除:
1. **存储**: `TextureInfo` 内部使用 `std::variant` 存储不同后端的数据
2. **访问**: 通过虚函数 `copyTo()` 和模板方法 `isCompatible()` 访问
3. **静态标识**: `kBackend` 常量用于编译时类型检查

### YCbCr 平面采样
支持直接采样 YCbCr 纹理的特定平面:
```cpp
// 采样 Y 平面
VulkanTextureInfo yPlaneInfo;
yPlaneInfo.fFormat = VK_FORMAT_R8_UNORM;  // Y 平面兼容格式
yPlaneInfo.fAspectMask = VK_IMAGE_ASPECT_PLANE_0_BIT;  // 第一个平面
```

### 用途标志组合
常见用途标志组合:
- **采样纹理**: `VK_IMAGE_USAGE_SAMPLED_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT`
- **渲染目标**: `VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_SAMPLED_BIT`
- **存储纹理**: `VK_IMAGE_USAGE_STORAGE_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT`

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/gpu/graphite/BackendTexture.h | 后端纹理抽象 |
| include/gpu/graphite/GraphiteTypes.h | 通用类型 (Protected, Mipmapped) |
| include/gpu/graphite/TextureInfo.h | 纹理信息基类 |
| include/gpu/vk/VulkanTypes.h | Vulkan 基础类型 (VulkanAlloc, YcbcrConversionInfo) |

### 被依赖的模块
- Graphite Vulkan 上下文: 使用这些类型创建纹理
- 纹理创建工厂: 调用 `MakeVulkan` 工厂函数
- 外部互操作代码: 使用 `BackendTexture` 共享纹理

## 设计模式与设计决策

### 类型安全的后端多态
通过模板 API 而非继承实现多态:
```cpp
// 编译时检查
static constexpr skgpu::BackendApi kBackend = skgpu::BackendApi::kVulkan;
```

### 工厂方法模式 (Factory Method)
使用命名空间级别的工厂函数:
- 避免构造函数污染
- 提供描述性的创建方法
- 支持未来扩展新的创建方式

### 桥接模式 (Bridge Pattern)
`TextureInfo` 作为抽象,`VulkanTextureInfo` 作为实现:
- **抽象层**: 平台无关的 `TextureInfo` 接口
- **实现层**: `VulkanTextureInfo` 包含 Vulkan 特定细节
- **解耦**: 上层代码不依赖 Vulkan 具体类型

## 性能考量

### 平铺模式选择
- **OPTIMAL**: GPU 优化的内存布局,性能最佳,CPU 不可直接访问
- **LINEAR**: 线性内存布局,CPU 可访问,性能较差
- **建议**: 渲染纹理使用 OPTIMAL,Staging 缓冲区使用 LINEAR

### 图像布局转换
频繁的布局转换影响性能:
- 创建时使用 `UNDEFINED` 初始布局
- 明确目标布局 (如 `SHADER_READ_ONLY_OPTIMAL`)
- 批量转换多个图像避免管线气泡

### 队列共享模式
- **EXCLUSIVE**: 单队列独占,性能更好,需要队列所有权转移
- **CONCURRENT**: 多队列并发访问,灵活但可能有性能开销
- **建议**: 除非必要,优先使用 EXCLUSIVE

### 内存分配策略
通过 `VulkanAlloc` 控制:
- 小纹理使用子分配减少内存碎片
- 大纹理使用独立 `VkDeviceMemory`
- 瞬态纹理考虑惰性分配

## 平台相关说明

### Android 特定功能
- **外部内存**: 支持 `AHardwareBuffer` 导入
- **YCbCr 格式**: 用于相机和视频解码输出
- **受保护内存**: DRM 内容播放
- **扩展依赖**: `VK_ANDROID_external_memory_android_hardware_buffer`

### 桌面平台 (Windows/Linux/macOS)
- **标准格式**: RGBA8、BGRA8 等常规格式
- **Swapchain 集成**: 需要 `VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT`
- **MoltenVK (macOS)**: 某些格式和特性受限

### 移动平台优化
- **压缩格式**: ASTC、ETC2 减少带宽
- **Transient 附件**: 使用 `VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT`

## 使用示例

### 创建采样纹理
```cpp
using namespace skgpu::graphite;

VulkanTextureInfo vkInfo(
    VK_SAMPLE_COUNT_1_BIT,                       // 无 MSAA
    Mipmapped::kYes,                             // 生成 mipmap
    0,                                            // 无特殊标志
    VK_FORMAT_R8G8B8A8_UNORM,                   // RGBA8 格式
    VK_IMAGE_TILING_OPTIMAL,                    // 优化平铺
    VK_IMAGE_USAGE_SAMPLED_BIT |                // 用于采样
        VK_IMAGE_USAGE_TRANSFER_DST_BIT,        // 可作为传输目标
    VK_SHARING_MODE_EXCLUSIVE,                  // 独占访问
    VK_IMAGE_ASPECT_COLOR_BIT,                  // 颜色方面
    VulkanYcbcrConversionInfo()                 // 无 YCbCr 转换
);

TextureInfo textureInfo = TextureInfos::MakeVulkan(vkInfo);
```

### 包装外部纹理
```cpp
// 外部代码创建的 Vulkan 图像
VkImage externalImage = /* ... */;
VulkanAlloc externalAlloc = /* ... */;

BackendTexture backendTex = BackendTextures::MakeVulkan(
    {1920, 1080},                                // 尺寸
    vkInfo,                                      // 纹理信息
    VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,   // 当前布局
    0,                                           // 队列族索引
    externalImage,                               // VkImage 句柄
    externalAlloc                                // 内存分配
);

// 在 Graphite 中使用
sk_sp<SkImage> image = SkImages::AdoptTextureFrom(context, backendTex, ...);
```

### 创建渲染目标
```cpp
VulkanTextureInfo rtInfo(
    VK_SAMPLE_COUNT_4_BIT,                       // 4x MSAA
    Mipmapped::kNo,                              // 渲染目标无需 mipmap
    0,
    VK_FORMAT_B8G8R8A8_UNORM,                   // BGRA8 (Swapchain 常用)
    VK_IMAGE_TILING_OPTIMAL,
    VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |       // 颜色附件
        VK_IMAGE_USAGE_SAMPLED_BIT,             // 可后续采样
    VK_SHARING_MODE_EXCLUSIVE,
    VK_IMAGE_ASPECT_COLOR_BIT,
    VulkanYcbcrConversionInfo()
);
```

### YCbCr 平面采样
```cpp
// 获取 AHardwareBuffer 的 YCbCr 信息
VulkanYcbcrConversionInfo ycbcrInfo = getYcbcrInfoFromAHB(ahb);

VulkanTextureInfo ycbcrTexInfo(
    VK_SAMPLE_COUNT_1_BIT,
    Mipmapped::kNo,
    0,
    VK_FORMAT_UNDEFINED,                         // 外部格式
    VK_IMAGE_TILING_OPTIMAL,
    VK_IMAGE_USAGE_SAMPLED_BIT,
    VK_SHARING_MODE_EXCLUSIVE,
    VK_IMAGE_ASPECT_COLOR_BIT,
    ycbcrInfo                                    // YCbCr 转换配置
);
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/graphite/TextureInfo.h | 基类定义 |
| include/gpu/graphite/BackendTexture.h | 后端纹理抽象 |
| include/gpu/vk/VulkanTypes.h | Vulkan 基础类型 |
| include/gpu/graphite/vk/VulkanGraphiteContext.h | Vulkan 上下文创建 |
| src/gpu/graphite/vk/VulkanTexture.cpp | 纹理对象实现 |

## 常见问题与解决方案

### 问题 1: 格式不支持
**症状**: 纹理创建失败或验证层报错
**原因**: 设备不支持指定格式或用途组合
**解决**: 使用 `vkGetPhysicalDeviceFormatProperties` 查询支持的特性

### 问题 2: 布局转换错误
**症状**: 同步验证错误或渲染结果不正确
**原因**: `BackendTexture` 的 `layout` 参数与实际布局不匹配
**解决**: 确保传入的布局与 Vulkan 图像的当前布局一致

### 问题 3: 内存泄漏
**症状**: 内存使用持续增长
**原因**: `BackendTexture` 销毁后外部 VkImage 未释放
**解决**: 使用 `BackendTexture::isValid()` 检查所有权,正确管理外部资源生命周期

### 问题 4: YCbCr 采样失败
**症状**: 纹理显示错误或崩溃
**原因**: YCbCr 转换信息不匹配或未启用扩展
**解决**: 确保 `VkSamplerYcbcrConversion` 与纹理创建时使用的一致

## 最佳实践

1. **使用工厂函数**: 优先使用 `TextureInfos::MakeVulkan` 而非直接构造
2. **检查兼容性**: 在复用纹理前使用 `isCompatible` 验证
3. **明确用途标志**: 只添加实际需要的用途位,避免不必要的限制
4. **布局管理**: 使用 Skia 的自动布局转换,避免手动管理
5. **外部互操作**: 使用 `BackendTexture` 时明确所有权,避免双重释放
6. **调试输出**: 利用 `toBackendString()` 生成可读日志

## 扩展建议

虽然当前接口完善,未来可能的扩展方向:
- 支持 Vulkan 1.3 的动态渲染特性
- 添加图像视图类型 (1D/2D/3D/Cube/Array)
- 支持稀疏纹理绑定
- 扩展同步原语支持 (时间线信号量)
