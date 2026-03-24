# SkImageChromium

> 源文件: `include/private/chromium/SkImageChromium.h`

## 概述
SkImageChromium 提供了仅供 Chromium 外部使用的 SkImage 扩展功能。核心功能是 Promise 纹理机制,允许在工作线程创建 GPU 图像而无需立即提供纹理,纹理在实际绘制时通过回调函数按需获取。此外还提供了获取 SkImage 关联的 GPU 上下文的辅助函数,用于过渡期 API 迁移。

## 架构位置
该文件位于 Skia 的 Chromium 私有接口层,属于 SkImages 命名空间,是图像创建和管理子系统的扩展。它位于公共 SkImage API 之上,为 Chromium 特定的多线程和跨进程图像处理场景提供支持,特别是用于 GPU 加速的图像显示管线。

## 核心概念

### Promise Texture 机制
Promise 纹理允许延迟纹理创建:
1. **创建阶段**: 在任意线程创建 SkImage,不需要 GPU 上下文
2. **描述阶段**: 提供纹理格式、尺寸、mipmap 状态等描述
3. **绘制阶段**: 真正绘制时调用 fulfill 回调获取纹理
4. **释放阶段**: 纹理可以删除时调用 release 回调

### 与 BorrowTextureFrom 的区别
- **BorrowTextureFrom**: 需要预先创建纹理,在主线程创建图像
- **PromiseTextureFrom**: 延迟纹理创建,可在工作线程创建图像

## 类型定义

### 回调函数类型

```cpp
using PromiseImageTextureContext = void*;
using PromiseImageTextureFulfillProc = sk_sp<GrPromiseImageTexture> (*)(PromiseImageTextureContext);
using PromiseImageTextureReleaseProc = void (*)(PromiseImageTextureContext);
```

- **Context**: 用户自定义的上下文指针,传递给回调函数
- **FulfillProc**: 获取纹理的回调,返回 GrPromiseImageTexture
- **ReleaseProc**: 释放纹理的回调,通知纹理可以删除

## 公共 API 函数

### 单平面 Promise 纹理

#### `SK_API sk_sp<SkImage> PromiseTextureFrom(...)`
```cpp
SK_API sk_sp<SkImage> PromiseTextureFrom(
    sk_sp<GrContextThreadSafeProxy> gpuContextProxy,
    const GrBackendFormat& backendFormat,
    SkISize dimensions,
    skgpu::Mipmapped mipmapped,
    GrSurfaceOrigin origin,
    SkColorType colorType,
    SkAlphaType alphaType,
    sk_sp<SkColorSpace> colorSpace,
    PromiseImageTextureFulfillProc textureFulfillProc,
    PromiseImageTextureReleaseProc textureReleaseProc,
    PromiseImageTextureContext textureContext)
```

- **功能**: 创建单平面的 Promise 纹理 GPU 图像
- **参数**:
  - `gpuContextProxy`: 线程安全的 GPU 上下文代理,必需
  - `backendFormat`: 承诺的 GPU 纹理格式
  - `dimensions`: 纹理的宽度和高度
  - `mipmapped`: 是否有 mipmap
  - `origin`: 表面原点(kTopLeft 或 kBottomLeft)
  - `colorType`: 颜色类型
  - `alphaType`: Alpha 类型(不透明/预乘/非预乘)
  - `colorSpace`: 颜色空间,可为 nullptr
  - `textureFulfillProc`: 获取纹理的回调函数
  - `textureReleaseProc`: 释放纹理的回调函数
  - `textureContext`: 传递给回调的用户上下文
- **返回值**: 成功返回 SkImage,失败返回 nullptr
- **调用保证**:
  - fulfill 和 release 最多各调用一次
  - 即使图像创建失败或从未绘制,release 也会被调用
  - fulfill 的纹理属性必须与创建时的描述匹配

### YUV 平面 Promise 纹理

#### `SK_API sk_sp<SkImage> PromiseTextureFromYUVA(...)`
```cpp
SK_API sk_sp<SkImage> PromiseTextureFromYUVA(
    sk_sp<GrContextThreadSafeProxy> gpuContextProxy,
    const GrYUVABackendTextureInfo& backendTextureInfo,
    sk_sp<SkColorSpace> imageColorSpace,
    PromiseImageTextureFulfillProc textureFulfillProc,
    PromiseImageTextureReleaseProc textureReleaseProc,
    PromiseImageTextureContext textureContexts[])
```

- **功能**: 创建 YUV[A] 平面的 Promise 纹理图像
- **参数**:
  - `gpuContextProxy`: 线程安全的 GPU 上下文代理,必需
  - `backendTextureInfo`: YUV 平面排列、格式、转换和原点信息
  - `imageColorSpace`: 图像颜色空间,可为 nullptr
  - `textureFulfillProc`: 获取纹理的回调
  - `textureReleaseProc`: 释放纹理的回调
  - `textureContexts`: 上下文数组,每个平面一个(最多 4 个)
- **返回值**: 成功返回 SkImage,失败返回 nullptr
- **平面支持**: 支持 Y、U、V、A 分别在不同纹理中
- **调用保证**: 每个平面独立调用 fulfill 和 release
- **Mipmap 注意**: 当前忽略 mipmap 属性,未来将要求 fulfill 返回 mipmap 纹理

### 上下文获取

#### `SK_API GrDirectContext* GetContext(const SkImage* src)`
- **功能**: 获取与图像关联的 GPU 上下文(仅 Ganesh 后端)
- **参数**: `src` - 源图像指针
- **返回值**: 如果是 Ganesh 后端图像返回上下文指针,否则返回 nullptr
- **用途**: 帮助过渡某些 API 调用,不打算长期保留

#### `inline GrDirectContext* GetContext(const sk_sp<const SkImage>& src)`
- **功能**: 智能指针版本的上下文获取
- **参数**: `src` - 源图像智能指针
- **返回值**: 同上

## 内部实现细节

### Promise 纹理生命周期
```
创建 Promise Image(工作线程)
       ↓
  添加到绘制命令
       ↓
GrDeferredDisplayListRecorder 录制
       ↓
   DDL 回放(GPU 线程)
       ↓
 textureFulfillProc 调用
       ↓
   获取后端纹理
       ↓
    GPU 绘制
       ↓
   绘制完成
       ↓
 textureReleaseProc 调用
```

### 纹理属性验证
fulfill 回调返回的 GrBackendTexture 必须:
- 格式匹配 backendFormat
- 尺寸匹配 dimensions
- Mipmap 状态匹配(如果 mipmapped=kYes)
- 引用有效的 GPU 纹理
- 纹理已填充像素数据

### 多平面处理
YUV 图像可能有多种平面配置:
- **单平面**: YUV 打包在一个纹理(如 NV12)
- **双平面**: Y 单独,UV 交错(常见)
- **三平面**: Y、U、V 各自独立
- **四平面**: Y、U、V、A 各自独立

每个平面有独立的 fulfill/release 回调和上下文。

### 线程安全保证
- 图像创建可以在任意线程
- 使用 GrContextThreadSafeProxy 而非 GrDirectContext
- 回调在 GPU 线程调用
- 用户需要确保上下文的线程安全

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkRefCnt | 智能指针 |
| SkAPI | API 导出宏 |
| GrContextThreadSafeProxy | 线程安全的上下文代理 |
| GrBackendFormat | 后端纹理格式 |
| GrPromiseImageTexture | Promise 纹理包装 |
| GrDirectContext | 直接上下文(用于 GetContext) |
| GrYUVABackendTextureInfo | YUV 纹理信息 |
| SkColorSpace | 颜色空间 |
| SkImage | 图像基类 |
| skgpu::Mipmapped | Mipmap 枚举 |

### 被依赖的模块
- Chromium 的 GPU 图像显示管线
- Chromium cc/paint 层
- Blink WebGL 纹理共享
- Chromium 视频解码器输出
- GrDeferredDisplayList 实现
- Ganesh GPU 后端

## 设计模式与设计决策

### Promise 模式
核心是 Promise/Future 模式的变体:
- 承诺将来提供纹理
- 实际值在需要时获取
- 解耦创建和使用时机

### 回调机制
使用 C 风格函数指针回调:
- 简单、高效
- 跨语言边界友好
- 避免 std::function 开销

### 上下文传递
每个 Promise 有独立的 void* 上下文:
- 灵活性高,可以传递任意数据
- 类型不安全,需要用户保证正确性
- 用户负责上下文生命周期管理

### 释放保证
无论成功失败,release 总会被调用:
- 防止资源泄漏
- 简化用户的资源管理
- 类似 RAII 的思想

### 过渡性 API
GetContext() 明确标注为过渡性:
- 不打算长期保留
- 帮助迁移现有代码
- 鼓励使用更好的 API

## 性能考量

### 延迟纹理创建
Promise 纹理的主要优势:
- 避免阻塞主线程等待纹理
- 纹理在 GPU 线程创建
- 减少线程同步开销

### 工作线程创建
允许在工作线程创建图像:
- 不需要 GPU 上下文访问
- 可以并行处理多个图像
- 提高整体吞吐量

### 零拷贝纹理共享
Promise 机制支持零拷贝:
- 直接使用解码器输出的纹理
- 避免 CPU/GPU 数据传输
- 支持硬件解码器集成

### 回调开销
fulfill/release 回调有小额开销:
- 函数指针间接调用
- 通常不是瓶颈
- GPU 操作开销远大于回调

### YUV 平面优化
YUV 格式减少带宽:
- YUV 比 RGB 数据量小
- 硬件原生支持 YUV→RGB 转换
- 减少内存占用

## 使用场景

### Chromium 视频渲染
视频帧作为 Promise 纹理:
```cpp
auto image = SkImages::PromiseTextureFrom(
    proxy, format, size, mipmapped, origin,
    colorType, alphaType, colorSpace,
    [](void* ctx) -> sk_sp<GrPromiseImageTexture> {
        VideoFrame* frame = static_cast<VideoFrame*>(ctx);
        return frame->GetGpuTexture();
    },
    [](void* ctx) {
        VideoFrame* frame = static_cast<VideoFrame*>(ctx);
        frame->Release();
    },
    videoFrame);
```

### WebGL 纹理共享
在 Blink 中使用 WebGL 纹理:
```cpp
// 在渲染线程创建 Promise Image
auto image = SkImages::PromiseTextureFrom(
    proxy, format, size, ...,
    fulfillWebGLTexture,
    releaseWebGLTexture,
    webglTextureID);

// 在 GPU 线程绘制
canvas->drawImage(image, x, y);
```

### YUV 视频帧
多平面视频解码:
```cpp
GrYUVABackendTextureInfo yuvaInfo = ...;
PromiseImageTextureContext contexts[3] = {
    yPlaneContext, uPlaneContext, vPlaneContext
};
auto image = SkImages::PromiseTextureFromYUVA(
    proxy, yuvaInfo, colorSpace,
    fulfillProc, releaseProc, contexts);
```

## 安全考量

### 纹理生命周期
用户必须确保:
- fulfill 返回的纹理在 release 前有效
- release 后不再访问纹理
- 上下文指针在回调期间有效

### 线程安全
回调在 GPU 线程执行:
- 用户需要处理线程同步
- 避免在回调中访问主线程数据
- 使用线程安全的引用计数

### 资源泄漏预防
release 总会被调用:
- 即使图像创建失败
- 即使图像从未绘制
- 确保资源得到释放

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkImage.h | SkImage 基类 |
| include/gpu/GrContextThreadSafeProxy.h | 线程安全代理 |
| include/gpu/GrBackendSurface.h | 后端格式定义 |
| src/gpu/ganesh/GrPromiseImageTexture.h | Promise 纹理包装 |
| include/gpu/GrDirectContext.h | 直接上下文 |
| src/image/SkImage_GaneshYUVA.h | YUV 图像实现 |
| src/gpu/ganesh/GrDeferredDisplayList.h | DDL 实现 |
| chromium/cc/paint/paint_image.h | Chromium 使用者 |
