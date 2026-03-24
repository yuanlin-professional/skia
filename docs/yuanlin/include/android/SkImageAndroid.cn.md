# SkImageAndroid

> 源文件: `include/android/SkImageAndroid.h`

## 概述

SkImageAndroid 提供了 Android 平台特定的图像创建和管理功能,包括从硬件缓冲区(AHardwareBuffer)创建图像、位图到图像的特殊转换,以及 GPU 纹理锁定机制。该模块是 Android 系统高性能图像处理的核心,支持零拷贝图像共享、相机预览、视频播放等场景,同时提供了独特的纹理锁定功能优化动态内容的渲染性能。

## 架构位置

该模块位于 Skia 的 Android 平台适配层,是 `SkImages` 和 `skgpu::ganesh` 命名空间的扩展。它连接了 Android NDK 的硬件缓冲区 API 和 Skia 的图像系统,为 Android Framework(libhwui)和应用开发者提供高效的图像处理能力。

## SkImages 命名空间

### `DeferredFromAHardwareBuffer` (简化版本)

从 AHardwareBuffer 延迟创建 SkImage。

```cpp
SK_API sk_sp<SkImage> DeferredFromAHardwareBuffer(
    AHardwareBuffer* hardwareBuffer,
    SkAlphaType alphaType = kPremul_SkAlphaType
)
```

**参数**:
- `hardwareBuffer`: 源硬件缓冲区
- `alphaType`: Alpha 类型,默认预乘

**返回值**: SkImage 智能指针,如果失败则返回 nullptr

**功能说明**:
- 延迟创建:图像对象立即返回,GPU 纹理在首次使用时创建
- 适用于简单场景,使用默认参数(sRGB 色彩空间,TopLeft 原点)

### `DeferredFromAHardwareBuffer` (完整版本)

从 AHardwareBuffer 延迟创建 SkImage,支持自定义参数。

```cpp
SK_API sk_sp<SkImage> DeferredFromAHardwareBuffer(
    AHardwareBuffer* hardwareBuffer,
    SkAlphaType alphaType,
    sk_sp<SkColorSpace> colorSpace,
    GrSurfaceOrigin surfaceOrigin = kTopLeft_GrSurfaceOrigin
)
```

**参数详解**:

**hardwareBuffer** (AHardwareBuffer*):
- 源硬件缓冲区,可来自相机、视频解码器、窗口系统等
- SkImage 持有缓冲区的引用,确保其生命周期

**alphaType** (SkAlphaType):
- `kPremul_SkAlphaType`: 预乘 Alpha(默认,性能最优)
- `kUnpremul_SkAlphaType`: 非预乘 Alpha
- `kOpaque_SkAlphaType`: 不透明(无 Alpha 通道)

**colorSpace** (sk_sp<SkColorSpace>):
- 色彩空间,可为 nullptr(默认 sRGB)
- 支持宽色域:Display P3、Adobe RGB、BT.2020
- 支持 HDR:线性色彩空间

**surfaceOrigin** (GrSurfaceOrigin):
- `kTopLeft_GrSurfaceOrigin`: 左上角为原点(常见)
- `kBottomLeft_GrSurfaceOrigin`: 左下角为原点(OpenGL 默认)

**返回值**: SkImage 智能指针

**典型用途**:
```cpp
// 相机预览(通常是 YUV 格式,使用外部纹理)
sk_sp<SkImage> cameraFrame = SkImages::DeferredFromAHardwareBuffer(
    cameraBuffer,
    kOpaque_SkAlphaType,  // 相机帧通常不透明
    nullptr,              // sRGB
    kTopLeft_GrSurfaceOrigin
);

// HDR 视频帧
sk_sp<SkImage> hdrFrame = SkImages::DeferredFromAHardwareBuffer(
    videoBuffer,
    kPremul_SkAlphaType,
    SkColorSpace::MakeRGB(SkNamedTransferFn::kHLG, SkNamedGamut::kRec2020),
    kTopLeft_GrSurfaceOrigin
);
```

### `TextureFromAHardwareBufferWithData`

从 AHardwareBuffer 创建 SkImage 并上传像素数据。

```cpp
SK_API sk_sp<SkImage> TextureFromAHardwareBufferWithData(
    GrDirectContext* context,
    const SkPixmap& pixmap,
    AHardwareBuffer* hardwareBuffer,
    GrSurfaceOrigin surfaceOrigin = kTopLeft_GrSurfaceOrigin
)
```

**功能**: 将 SkPixmap 中的像素数据上传到 AHardwareBuffer,并创建对应的 SkImage。

**参数**:
- `context`: GPU 上下文,用于执行数据上传
- `pixmap`: 源像素数据(CPU 内存)
- `hardwareBuffer`: 目标硬件缓冲区
- `surfaceOrigin`: 纹理原点

**返回值**: SkImage 智能指针

**使用场景**:
- 预生成的纹理数据(如从文件解码的图像)需要上传到硬件缓冲区
- 跨进程共享图像(通过 AHardwareBuffer 传递)
- 与其他 API(Camera、MediaCodec)共享纹理

**示例**:
```cpp
// 从 PNG 解码到内存
SkBitmap bitmap;
decodeImageFromFile("texture.png", &bitmap);

// 创建硬件缓冲区
AHardwareBuffer* buffer = allocateHardwareBuffer(bitmap.width(), bitmap.height());

// 上传数据并创建图像
sk_sp<SkImage> image = SkImages::TextureFromAHardwareBufferWithData(
    grContext,
    bitmap.pixmap(),
    buffer,
    kTopLeft_GrSurfaceOrigin
);

// 图像可用于渲染,数据已在 GPU
canvas->drawImage(image, 0, 0);
```

### `PinnableRasterFromBitmap`

从 SkBitmap 创建可锁定的栅格图像。

```cpp
SK_API sk_sp<SkImage> PinnableRasterFromBitmap(const SkBitmap& bitmap)
```

**功能**: 创建一个特殊的 SkImage,可通过 `skgpu::ganesh::PinAsTexture` 锁定为 GPU 纹理。

**关键特性**:
- 初始为 CPU 栅格图像
- 可按需上传到 GPU 并锁定
- 锁定后行为类似 GPU 纹理图像
- Skia 不会自动拷贝位图像素(零拷贝)

**使用场景**:
- 动态生成的内容(如动画帧)
- 频繁更新的纹理(如视频帧)
- 需要在 CPU 和 GPU 间灵活切换的图像

**注意事项**:
- 位图像素必须在图像生命周期内保持有效
- 锁定后,源位图不应再修改(否则行为未定义)

### `RasterFromBitmapNoCopy`

从 SkBitmap 创建零拷贝的栅格图像。

```cpp
SK_API sk_sp<SkImage> RasterFromBitmapNoCopy(const SkBitmap& bitmap)
```

**功能**: 类似 `SkImage::MakeFromBitmap`,但不拷贝像素数据。

**区别对比**:
| 函数 | 拷贝行为 | 线程安全 | 修改源数据影响 |
|------|----------|----------|----------------|
| SkImages::RasterFromBitmapNoCopy | 不拷贝 | 否 | 图像内容会改变 |
| SkImage::MakeFromBitmap | 拷贝 | 是 | 无影响 |
| SkImages::PinnableRasterFromBitmap | 不拷贝,可锁定 GPU | 否 | 锁定前会改变 |

**使用场景**:
- 临时图像(立即使用,无需长期保存)
- 确保源位图不会被修改
- 性能关键路径,避免内存拷贝开销

**示例**:
```cpp
SkBitmap tempBitmap;
generateBitmapContent(&tempBitmap);

// 零拷贝创建图像
sk_sp<SkImage> image = SkImages::RasterFromBitmapNoCopy(tempBitmap);

// 立即渲染
canvas->drawImage(image, 0, 0);

// 注意:之后不应修改 tempBitmap
```

## skgpu::ganesh 命名空间

### `PinAsTexture`

将图像锁定为 GPU 纹理。

```cpp
bool PinAsTexture(GrRecordingContext* context, SkImage* image)
```

**功能**: 上传图像到 GPU 并锁定,后续绘制将使用 GPU 纹理,即使源数据被修改。

**参数**:
- `context`: GPU 录制上下文
- `image`: 目标图像(必须是 `PinnableRasterFromBitmap` 创建的)

**返回值**:
- `true`: 成功锁定为纹理
- `false`: 失败(图像类型不兼容或 GPU 内存不足)

**重要特性**:
- 多次调用累计引用计数(必须匹配 `UnpinTexture` 次数)
- 锁定后,图像绑定到特定 GrContext,有线程限制
- 提高动态内容的渲染性能(避免重复上传)

**典型流程**:
```cpp
// 1. 创建可锁定图像
SkBitmap dynamicBitmap;
sk_sp<SkImage> image = SkImages::PinnableRasterFromBitmap(dynamicBitmap);

// 2. 首次绘制时锁定
if (skgpu::ganesh::PinAsTexture(grContext, image.get())) {
    // 现在是 GPU 纹理
}

// 3. 多次绘制(无需重复上传)
for (int i = 0; i < 100; ++i) {
    canvas->drawImage(image, x, y);
}

// 4. 不再需要时解锁
skgpu::ganesh::UnpinTexture(grContext, image.get());

// 5. 如果源数据改变,重新锁定
modifyBitmapPixels(dynamicBitmap);
// 需要重新 Pin 以上传新数据
```

### `UnpinTexture`

解锁 GPU 纹理。

```cpp
void UnpinTexture(GrRecordingContext* context, SkImage* image)
```

**功能**: 减少纹理锁定引用计数,当计数归零时释放 GPU 资源。

**参数**:
- `context`: 必须与 `PinAsTexture` 使用的同一上下文
- `image`: 要解锁的图像

**行为**:
- 平衡的 Pin/Unpin 调用后,纹理可被 GPU 回收
- 如果源数据的 uniqueID/generationID 改变,下次 Pin 将重新上传

**错误处理**:
```cpp
// 错误:不匹配的 Pin/Unpin
skgpu::ganesh::PinAsTexture(context, image);
skgpu::ganesh::UnpinTexture(context, image);
skgpu::ganesh::UnpinTexture(context, image); // 错误!未配对

// 正确:平衡调用
for (int i = 0; i < 3; ++i) {
    skgpu::ganesh::PinAsTexture(context, image);
}
for (int i = 0; i < 3; ++i) {
    skgpu::ganesh::UnpinTexture(context, image);
}
```

## 内部实现细节

### 延迟图像创建
`DeferredFromAHardwareBuffer` 创建的图像是延迟的:
- 图像对象立即返回(轻量级包装器)
- GPU 纹理在首次 `SkCanvas::drawImage` 时创建
- 减少启动时间和内存占用

### 纹理锁定机制
`PinAsTexture` 的内部状态:
```cpp
struct PinnedTextureState {
    GrBackendTexture texture;
    uint32_t generationID;  // 源数据的版本
    int pinCount;           // 引用计数
};
```

当源数据修改时(generationID 变化):
- 下次 Pin 时检测到版本不匹配
- 重新上传像素数据
- 更新 generationID

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkImage.h | SkImage 基类定义 |
| include/core/SkRefCnt.h | 智能指针 sk_sp |
| include/gpu/ganesh/GrTypes.h | GPU 类型定义 |
| include/gpu/ganesh/GrDirectContext.h | GPU 上下文 |
| android/hardware_buffer.h | AHardwareBuffer API |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Android Framework(libhwui) | 使用硬件缓冲区图像 |
| Android Camera2 API | 相机预览帧显示 |
| Android MediaCodec | 视频解码输出 |
| 第三方图像库 | 与 Android 硬件加速集成 |

## 设计模式与设计决策

### 延迟加载模式
`DeferredFromAHardwareBuffer` 采用延迟加载:
- 优点:减少初始化开销,避免不必要的 GPU 资源创建
- 缺点:首次绘制时可能有轻微延迟

### 引用计数管理
`PinAsTexture` 使用引用计数而非布尔标志:
- 支持嵌套锁定(如递归绘制)
- 避免过早释放纹理

### 零拷贝优化
多个函数提供零拷贝选项:
- 性能优先,但需要用户保证数据生命周期
- 明确的命名(如 `NoCopy`)提示使用风险

## 性能考量

### 延迟图像的开销
- 创建图像对象: <1ms
- 首次绘制(创建纹理): 5-20ms(取决于尺寸和格式)
- 后续绘制: ~1ms

### 纹理锁定的收益
以 1920x1080 动态图像为例:
- 未锁定:每帧上传 ~8MB,耗时 ~10-20ms
- 锁定后:无上传开销,耗时 <1ms
- 性能提升: 10-20 倍

### 内存占用
- `DeferredFromAHardwareBuffer` 图像: ~200 字节(+ AHardwareBuffer 引用)
- 锁定的纹理:额外占用 GPU 内存(width * height * bytes_per_pixel)

## 典型使用场景

### 场景 1: 相机预览
```cpp
// 相机回调中
void onCameraFrame(AHardwareBuffer* frameBuffer) {
    // 创建延迟图像
    sk_sp<SkImage> frame = SkImages::DeferredFromAHardwareBuffer(
        frameBuffer,
        kOpaque_SkAlphaType
    );

    // 绘制预览
    canvas->drawImage(frame, 0, 0);
}
```

### 场景 2: 动画纹理优化
```cpp
class AnimatedTexture {
    SkBitmap bitmap_;
    sk_sp<SkImage> image_;
    bool pinned_ = false;

public:
    void updateFrame(int frameIndex) {
        // 更新位图像素
        drawFrameInto(frameIndex, &bitmap_);

        if (!pinned_) {
            // 首次使用时创建可锁定图像
            image_ = SkImages::PinnableRasterFromBitmap(bitmap_);
            pinned_ = true;
        }
    }

    void draw(SkCanvas* canvas, GrRecordingContext* context) {
        // 锁定为纹理(首次调用时上传)
        static bool locked = false;
        if (!locked) {
            locked = skgpu::ganesh::PinAsTexture(context, image_.get());
        }

        canvas->drawImage(image_, 0, 0);
    }

    ~AnimatedTexture() {
        if (pinned_) {
            skgpu::ganesh::UnpinTexture(context_, image_.get());
        }
    }
};
```

### 场景 3: 视频播放
```cpp
// MediaCodec 输出
void renderVideoFrame(AHardwareBuffer* videoBuffer) {
    // 创建图像(支持 YUV 外部格式)
    sk_sp<SkImage> frame = SkImages::DeferredFromAHardwareBuffer(
        videoBuffer,
        kPremul_SkAlphaType,
        nullptr, // sRGB
        kTopLeft_GrSurfaceOrigin
    );

    // 渲染到屏幕
    canvas->drawImageRect(frame, videoRect, SkSamplingOptions());
}
```

## 错误处理

### 不兼容的图像类型
```cpp
// 错误:对普通图像调用 PinAsTexture
sk_sp<SkImage> normalImage = SkImage::MakeFromBitmap(bitmap);
bool success = skgpu::ganesh::PinAsTexture(context, normalImage.get());
// success == false

// 正确:使用 PinnableRasterFromBitmap
sk_sp<SkImage> pinnableImage = SkImages::PinnableRasterFromBitmap(bitmap);
bool success = skgpu::ganesh::PinAsTexture(context, pinnableImage.get());
// success == true
```

### 生命周期管理
```cpp
// 错误:源位图过早销毁
{
    SkBitmap tempBitmap;
    generatePixels(&tempBitmap);
    sk_sp<SkImage> image = SkImages::RasterFromBitmapNoCopy(tempBitmap);
    // tempBitmap 销毁
}
// image 现在指向无效内存!

// 正确:确保位图生命周期
class TextureHolder {
    SkBitmap bitmap_;
    sk_sp<SkImage> image_;
public:
    void create() {
        generatePixels(&bitmap_);
        image_ = SkImages::RasterFromBitmapNoCopy(bitmap_);
        // bitmap_ 与 image_ 生命周期绑定
    }
};
```

## 平台相关说明

### Android 版本支持
- **AHardwareBuffer 功能**: Android 8.0+(API 26)
- **完整 GPU 支持**: Android 9.0+(API 28)
- **HDR 支持**: Android 10+(API 29)

### GPU 后端
- OpenGL: 通过 EGLImage 实现
- Vulkan: 通过外部内存扩展实现
- 性能差异不大,Vulkan 同步更精确

## 相关文件

| 文件 | 关系 |
|------|------|
| src/image/SkImage_AndroidFactories.cpp | 实现文件 |
| include/android/GrAHardwareBufferUtils.h | GPU 后端集成 |
| include/core/SkImage.h | SkImage 基类 |
| src/image/SkImage_Raster.cpp | 栅格图像实现 |
| src/image/SkImage_GpuBase.cpp | GPU 图像实现 |

## 最佳实践

### 选择合适的函数
```cpp
// 场景 1:外部硬件缓冲区(相机、视频)
sk_sp<SkImage> image = SkImages::DeferredFromAHardwareBuffer(buffer, ...);

// 场景 2:动态内容(需要频繁绘制)
sk_sp<SkImage> image = SkImages::PinnableRasterFromBitmap(bitmap);
skgpu::ganesh::PinAsTexture(context, image.get());

// 场景 3:静态内容(长期保存)
sk_sp<SkImage> image = SkImage::MakeFromBitmap(bitmap); // 拷贝

// 场景 4:临时内容(立即使用)
sk_sp<SkImage> image = SkImages::RasterFromBitmapNoCopy(bitmap);
```

### 纹理锁定管理
```cpp
// 使用 RAII 管理锁定
class ScopedPinnedTexture {
    GrRecordingContext* context_;
    SkImage* image_;
public:
    ScopedPinnedTexture(GrRecordingContext* ctx, SkImage* img)
        : context_(ctx), image_(img) {
        skgpu::ganesh::PinAsTexture(context_, image_);
    }
    ~ScopedPinnedTexture() {
        skgpu::ganesh::UnpinTexture(context_, image_);
    }
};
```

### 性能监控
```cpp
// 监控纹理上传
class TextureUploadTracker {
    int uploadCount_ = 0;
public:
    sk_sp<SkImage> createPinnableImage(const SkBitmap& bitmap) {
        auto image = SkImages::PinnableRasterFromBitmap(bitmap);

        // 自定义回调跟踪上传
        if (skgpu::ganesh::PinAsTexture(context, image.get())) {
            uploadCount_++;
            LOG("Texture upload #%d", uploadCount_);
        }

        return image;
    }
};
```
