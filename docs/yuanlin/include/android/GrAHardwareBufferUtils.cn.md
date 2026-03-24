# GrAHardwareBufferUtils

> 源文件: `include/android/GrAHardwareBufferUtils.h`

## 概述

GrAHardwareBufferUtils 是 Skia GPU 后端(Ganesh)中用于处理 Android 硬件缓冲区(AHardwareBuffer)的核心工具模块。该模块提供了从 AHardwareBuffer 创建 GPU 纹理的完整功能,支持 OpenGL 和 Vulkan 两种后端,是实现 Android 平台零拷贝图像共享和硬件加速渲染的关键组件。

## 架构位置

该模块位于 Skia 的 GPU 层,专门为 Android 平台的硬件缓冲区提供 GPU 集成能力。它是连接 Android NDK 的 AHardwareBuffer API 和 Skia GPU 纹理系统的桥梁,广泛用于相机预览、视频播放、UI 渲染等高性能图形场景。

## 平台依赖

该模块仅在 Android API Level 26 及以上版本可用:

```cpp
#if defined(SK_BUILD_FOR_ANDROID) && __ANDROID_API__ >= 26
// GrAHardwareBufferUtils 功能可用
#endif
```

## 核心类型定义

### 回调函数类型

```cpp
typedef void* TexImageCtx;
typedef void (*DeleteImageProc)(TexImageCtx);
typedef void (*UpdateImageProc)(TexImageCtx, GrDirectContext*);
```

**TexImageCtx**: 不透明的图像上下文指针,用于在回调函数间传递状态。

**DeleteImageProc**: 纹理删除回调,在纹理销毁时调用,用于清理资源。
- 必须在创建纹理的同一线程调用
- 用于释放 EGLImage 或 VkImage 等中间对象

**UpdateImageProc**: 纹理更新回调,当 AHardwareBuffer 内容变化时调用,用于同步 GPU 状态。
- 必须在创建纹理的同一线程调用
- 用于通知 GPU 驱动重新绑定纹理

## 核心函数

### `GetBackendFormat` (已弃用)

获取 AHardwareBuffer 对应的 GPU 后端格式。

```cpp
GrBackendFormat GetBackendFormat(GrDirectContext* dContext,
                                 AHardwareBuffer* hardwareBuffer,
                                 uint32_t bufferFormat,
                                 bool requireKnownFormat)
```

**弃用警告**: 使用 `#ifndef SK_DISABLE_LEGACY_ANDROID_HW_UTILS` 条件编译保护。

**参数**:
- `dContext`: GPU 上下文
- `hardwareBuffer`: AHardwareBuffer 实例
- `bufferFormat`: 缓冲区格式(来自 AHardwareBuffer_Format)
- `requireKnownFormat`: 是否要求格式必须已知

**返回值**: GrBackendFormat 对象,如果格式不支持则返回无效格式。

**功能**: 根据 AHardwareBuffer 的格式和 GPU 后端类型,返回对应的 GPU 纹理格式。

### `GetGLBackendFormat`

获取 OpenGL 后端格式。

```cpp
GrBackendFormat GetGLBackendFormat(GrDirectContext* dContext,
                                   uint32_t bufferFormat,
                                   bool requireKnownFormat)
```

**参数**:
- `dContext`: GPU 上下文
- `bufferFormat`: AHardwareBuffer 格式
- `requireKnownFormat`: 是否要求格式必须已知

**返回值**:
- 成功: OpenGL 纹理格式(如 GL_RGBA8)
- 失败: 无效格式(如果 bufferFormat 是未知的外部格式)

**OpenGL 格式映射**:
| AHardwareBuffer 格式 | OpenGL 格式 | 说明 |
|----------------------|-------------|------|
| R8G8B8A8_UNORM | GL_RGBA8 | 标准 RGBA |
| R5G6B5_UNORM | GL_RGB565 | 16-bit RGB |
| R16G16B16A16_FLOAT | GL_RGBA16F | 半精度浮点 |
| R10G10B10A2_UNORM | GL_RGB10_A2 | 10-bit HDR |
| External Format | GL_TEXTURE_EXTERNAL_OES | YUV 等外部格式 |

### `GetVulkanBackendFormat`

获取 Vulkan 后端格式。

```cpp
GrBackendFormat GetVulkanBackendFormat(GrDirectContext* dContext,
                                       AHardwareBuffer* hardwareBuffer,
                                       uint32_t bufferFormat,
                                       bool requireKnownFormat)
```

**参数**:
- `dContext`: GPU 上下文
- `hardwareBuffer`: AHardwareBuffer 实例(用于查询 Vulkan 属性)
- `bufferFormat`: AHardwareBuffer 格式
- `requireKnownFormat`: 是否要求格式必须已知

**返回值**: Vulkan 纹理格式(如 VK_FORMAT_R8G8B8A8_UNORM)

**Vulkan 格式映射**:
| AHardwareBuffer 格式 | Vulkan 格式 | 说明 |
|----------------------|-------------|------|
| R8G8B8A8_UNORM | VK_FORMAT_R8G8B8A8_UNORM | 标准 RGBA |
| R5G6B5_UNORM | VK_FORMAT_R5G6B5_UNORM_PACK16 | 16-bit RGB |
| R16G16B16A16_FLOAT | VK_FORMAT_R16G16B16A16_SFLOAT | 半精度浮点 |
| External Format | VK_FORMAT_UNDEFINED + externalFormat | YUV 等外部格式 |

**特殊处理**: 对于外部格式,需要查询 `VkAndroidHardwareBufferFormatPropertiesANDROID`。

### `MakeBackendTexture` (已弃用)

从 AHardwareBuffer 创建通用 GPU 后端纹理。

```cpp
GrBackendTexture MakeBackendTexture(GrDirectContext* dContext,
                                    AHardwareBuffer* hardwareBuffer,
                                    int width, int height,
                                    DeleteImageProc* deleteProc,
                                    UpdateImageProc* updateProc,
                                    TexImageCtx* imageCtx,
                                    bool isProtectedContent,
                                    const GrBackendFormat& backendFormat,
                                    bool isRenderable,
                                    bool fromAndroidWindow = false)
```

**弃用警告**: 推荐使用后端特定函数(`MakeGLBackendTexture` 或 `MakeVulkanBackendTexture`)。

**参数详解**:
- `dContext`: GPU 直接上下文
- `hardwareBuffer`: 源 AHardwareBuffer
- `width`, `height`: 纹理尺寸
- `deleteProc`: 输出参数,返回删除回调函数
- `updateProc`: 输出参数,返回更新回调函数
- `imageCtx`: 输出参数,返回上下文指针
- `isProtectedContent`: 是否为受保护内容(DRM)
- `backendFormat`: 纹理格式
- `isRenderable`: 是否可作为渲染目标
- `fromAndroidWindow`: 是否来自 Android 窗口表面

**返回值**: GrBackendTexture 对象,如果失败则为无效纹理。

### `MakeGLBackendTexture`

从 AHardwareBuffer 创建 OpenGL 纹理。

```cpp
GrBackendTexture MakeGLBackendTexture(GrDirectContext* dContext,
                                      AHardwareBuffer* hardwareBuffer,
                                      int width, int height,
                                      DeleteImageProc* deleteProc,
                                      UpdateImageProc* updateProc,
                                      TexImageCtx* imageCtx,
                                      bool isProtectedContent,
                                      const GrBackendFormat& backendFormat,
                                      bool isRenderable)
```

**功能**: 通过 EGL 扩展将 AHardwareBuffer 导入为 OpenGL 纹理。

**实现原理**:
1. 使用 `eglGetNativeClientBufferANDROID` 获取 EGLClientBuffer
2. 调用 `eglCreateImageKHR` 创建 EGLImage
3. 使用 `glEGLImageTargetTexture2DOES` 绑定到 OpenGL 纹理

**OpenGL 扩展依赖**:
- `EGL_ANDROID_image_native_buffer`
- `GL_OES_EGL_image_external`
- `EXT_protected_textures`(可选,用于 DRM 内容)

### `MakeVulkanBackendTexture`

从 AHardwareBuffer 创建 Vulkan 纹理。

```cpp
GrBackendTexture MakeVulkanBackendTexture(GrDirectContext* dContext,
                                          AHardwareBuffer* hardwareBuffer,
                                          int width, int height,
                                          DeleteImageProc* deleteProc,
                                          UpdateImageProc* updateProc,
                                          TexImageCtx* imageCtx,
                                          bool isProtectedContent,
                                          const GrBackendFormat& backendFormat,
                                          bool isRenderable,
                                          bool fromAndroidWindow = false)
```

**功能**: 通过 Vulkan 扩展将 AHardwareBuffer 导入为 VkImage。

**实现原理**:
1. 填充 `VkImportAndroidHardwareBufferInfoANDROID` 结构
2. 调用 `vkAllocateMemory` 导入内存
3. 调用 `vkCreateImage` 创建图像
4. 调用 `vkBindImageMemory` 绑定内存

**Vulkan 扩展依赖**:
- `VK_ANDROID_external_memory_android_hardware_buffer`
- `VK_KHR_external_memory`
- `VK_KHR_dedicated_allocation`

**fromAndroidWindow 参数**: 如果为 true,优化窗口表面的内存布局和同步。

## 内部实现细节

### EGLImage 生命周期管理

OpenGL 路径的资源清理:
```cpp
struct GLCleanupHelper {
    EGLDisplay display;
    EGLImageKHR image;
};

void DeleteGLImage(void* ctx) {
    GLCleanupHelper* helper = static_cast<GLCleanupHelper*>(ctx);
    eglDestroyImageKHR(helper->display, helper->image);
    delete helper;
}
```

### Vulkan 内存导入

Vulkan 路径使用专用内存分配:
```cpp
VkImportAndroidHardwareBufferInfoANDROID importInfo = {};
importInfo.sType = VK_STRUCTURE_TYPE_IMPORT_ANDROID_HARDWARE_BUFFER_INFO_ANDROID;
importInfo.buffer = hardwareBuffer;

VkMemoryAllocateInfo allocInfo = {};
allocInfo.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
allocInfo.pNext = &importInfo;
allocInfo.allocationSize = size;
allocInfo.memoryTypeIndex = memoryTypeIndex;

vkAllocateMemory(device, &allocInfo, nullptr, &memory);
```

### 外部格式处理

对于 YUV 等外部格式:
- OpenGL: 使用 `GL_TEXTURE_EXTERNAL_OES` 目标
- Vulkan: 使用 `VkExternalFormatANDROID` 结构传递格式信息

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/gpu/ganesh/GrBackendSurface.h | GPU 后端纹理抽象 |
| include/gpu/ganesh/GrTypes.h | GPU 类型定义 |
| include/gpu/ganesh/GrDirectContext.h | GPU 上下文 |
| android/hardware_buffer.h | AHardwareBuffer API |
| EGL/egl.h, EGL/eglext.h | OpenGL 集成 |
| vulkan/vulkan.h | Vulkan 集成 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkImageAndroid | 从 AHardwareBuffer 创建 SkImage |
| SkSurfaceAndroid | 从 AHardwareBuffer 创建 SkSurface |
| Android Framework(libhwui) | UI 渲染使用硬件缓冲区 |
| Android Camera2 | 相机预览帧处理 |
| Android MediaCodec | 视频解码输出 |

## 设计模式与设计决策

### 回调机制
使用回调而非 RAII 管理资源生命周期:
- **优点**: 允许异步资源销毁,避免阻塞渲染线程
- **缺点**: 用户需要确保回调在正确线程执行

### 后端分离
提供通用函数(`MakeBackendTexture`)和后端特定函数(`MakeGLBackendTexture`, `MakeVulkanBackendTexture`):
- 通用函数方便迁移
- 特定函数允许后端特定优化

### 受保护内容支持
`isProtectedContent` 参数支持 DRM 保护的视频:
- OpenGL: 使用 `EXT_protected_textures`
- Vulkan: 使用 `VK_IMAGE_CREATE_PROTECTED_BIT`

## 性能考量

### 零拷贝优势
通过硬件缓冲区导入,避免 CPU-GPU 内存拷贝:
- 传统方式: AHardwareBuffer → CPU 内存 → GPU 纹理(~50ms for 1080p)
- 零拷贝方式: AHardwareBuffer → GPU 纹理(~1ms)

### 纹理创建开销
- OpenGL: EGLImage 创建 ~2-5ms
- Vulkan: VkImage 导入 ~1-3ms
- 建议缓存纹理对象,避免频繁创建

### 同步考虑
- AHardwareBuffer 操作需要显式同步(CPU fence 或 GPU semaphore)
- 使用 `UpdateImageProc` 确保内容更新后重新绑定

## 典型使用场景

### 场景 1: 相机预览渲染
```cpp
// 从相机获取 AHardwareBuffer
AHardwareBuffer* cameraBuffer = getCameraFrame();
AHardwareBuffer_Desc desc;
AHardwareBuffer_describe(cameraBuffer, &desc);

// 获取格式
GrBackendFormat format = GrAHardwareBufferUtils::GetVulkanBackendFormat(
    context, cameraBuffer, desc.format, false);

// 创建纹理
DeleteImageProc deleteProc;
UpdateImageProc updateProc;
TexImageCtx imageCtx;

GrBackendTexture texture = GrAHardwareBufferUtils::MakeVulkanBackendTexture(
    context, cameraBuffer,
    desc.width, desc.height,
    &deleteProc, &updateProc, &imageCtx,
    false, // 非受保护内容
    format,
    false, // 相机帧只读
    false  // 非窗口表面
);

// 使用纹理渲染
sk_sp<SkImage> image = SkImages::BorrowTextureFrom(context, texture, ...);
canvas->drawImage(image, 0, 0);

// 清理(在渲染完成后)
context->flush();
deleteProc(imageCtx);
```

### 场景 2: 视频播放
```cpp
// MediaCodec 输出到 AHardwareBuffer
AHardwareBuffer* videoFrame = getDecodedFrame();

// 创建 OpenGL 纹理
GrBackendFormat format = GrAHardwareBufferUtils::GetGLBackendFormat(
    context, desc.format, false);

DeleteImageProc deleteProc;
UpdateImageProc updateProc;
TexImageCtx imageCtx;

GrBackendTexture texture = GrAHardwareBufferUtils::MakeGLBackendTexture(
    context, videoFrame,
    1920, 1080,
    &deleteProc, &updateProc, &imageCtx,
    true, // 受保护内容(DRM)
    format,
    false
);

// 渲染视频帧
renderVideoFrame(texture);

// 通知内容更新
updateProc(imageCtx, context);
```

### 场景 3: 窗口表面共享
```cpp
// Android SurfaceFlinger 窗口缓冲区
AHardwareBuffer* windowBuffer = getWindowBuffer();

GrBackendTexture texture = GrAHardwareBufferUtils::MakeVulkanBackendTexture(
    context, windowBuffer,
    desc.width, desc.height,
    &deleteProc, &updateProc, &imageCtx,
    false,
    format,
    true,  // 可渲染(作为 framebuffer)
    true   // 来自 Android 窗口
);

// 创建 SkSurface 用于渲染
sk_sp<SkSurface> surface = SkSurfaces::WrapBackendTexture(...);
```

## 错误处理

### 常见错误

**格式不支持**:
```cpp
GrBackendFormat format = GrAHardwareBufferUtils::GetGLBackendFormat(...);
if (!format.isValid()) {
    // 处理不支持的格式
    // 可能是 YUV 格式,需要使用外部纹理
}
```

**纹理创建失败**:
```cpp
GrBackendTexture texture = GrAHardwareBufferUtils::MakeVulkanBackendTexture(...);
if (!texture.isValid()) {
    // 创建失败,可能原因:
    // - 内存不足
    // - 驱动不支持该格式
    // - 权限问题(受保护内容)
}
```

**Usage Bits 不匹配**:
```cpp
// AHardwareBuffer 必须包含合适的 usage bits
uint64_t usage = AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE;
if (isRenderable) {
    usage |= AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT;
}
AHardwareBuffer_allocate(&desc, &buffer);
```

## 平台相关说明

### Android 版本差异
- **API 26-27**: 基础支持
- **API 28+**: 改进的同步机制
- **API 29+**: 更多格式支持(如 R8_UNORM)
- **API 30+**: 优化的内存管理

### GPU 驱动支持
- **Qualcomm Adreno**: 全面支持,性能最优
- **ARM Mali**: 良好支持,部分旧型号有限制
- **PowerVR**: 基础支持,部分格式可能不可用

### Vulkan vs OpenGL
- **Vulkan**: 更高效的同步,推荐用于新项目
- **OpenGL**: 兼容性更好,适合旧设备

## 限制与注意事项

### 线程限制
- 回调函数必须在创建纹理的线程调用
- 跨线程传递纹理需要使用 Skia 的跨上下文共享机制

### 受保护内容
- 受保护内容的纹理无法读回 CPU
- 需要设备和驱动支持 DRM

### 内存开销
- 每个导入的纹理占用少量 GPU 驱动内存(~1KB)
- 大量纹理可能耗尽文件描述符(Android 限制为 1024)

## 相关文件

| 文件 | 关系 |
|------|------|
| src/gpu/ganesh/android/GrAHardwareBufferUtils.cpp | 实现文件 |
| include/android/SkImageAndroid.h | 使用这些工具创建 SkImage |
| include/android/SkSurfaceAndroid.h | 使用这些工具创建 SkSurface |
| include/android/AHardwareBufferUtils.h | 格式转换工具 |

## 最佳实践

### 资源管理
```cpp
// 使用 RAII 包装器管理回调
class ScopedAHBTexture {
    DeleteImageProc deleteProc_;
    TexImageCtx imageCtx_;
public:
    ~ScopedAHBTexture() {
        if (deleteProc_) deleteProc_(imageCtx_);
    }
};
```

### 性能优化
```cpp
// 缓存纹理对象
std::unordered_map<AHardwareBuffer*, GrBackendTexture> textureCache;

GrBackendTexture getOrCreateTexture(AHardwareBuffer* buffer) {
    auto it = textureCache.find(buffer);
    if (it != textureCache.end()) {
        // 更新纹理内容
        updateTexture(it->second);
        return it->second;
    }
    // 创建新纹理
    GrBackendTexture texture = GrAHardwareBufferUtils::MakeVulkanBackendTexture(...);
    textureCache[buffer] = texture;
    return texture;
}
```

### 同步处理
```cpp
// 使用 GPU fence 确保渲染完成
context->flush();
context->submit(GrSyncCpu::kYes);
// 现在可以安全释放 AHardwareBuffer
```
