# SkSurfaceAndroid

> 源文件: `include/android/SkSurfaceAndroid.h`

## 概述

SkSurfaceAndroid 为 Android 平台提供了从硬件缓冲区(AHardwareBuffer)创建 Skia 绘制表面的能力。该模块是 Android Framework 与 Skia 渲染引擎集成的关键接口,允许系统将硬件缓冲区直接包装为可绘制的 SkSurface,实现零拷贝的高效渲染,广泛用于窗口合成、UI 渲染和视频播放等场景。

## 架构位置

该模块位于 Skia 的 Android 平台适配层,是 SkSurfaces 命名空间中的平台特定扩展。它依赖 GrAHardwareBufferUtils 处理 GPU 后端细节,为 Android Framework(特别是 libhwui)提供统一的表面创建接口,是 Android 图形栈中的重要组成部分。

## 命名空间

该模块位于 `SkSurfaces` 命名空间,与其他表面创建函数保持一致:

```cpp
namespace SkSurfaces {
    // Android 特定的表面创建函数
    SK_API sk_sp<SkSurface> WrapAndroidHardwareBuffer(...);
}
```

## 核心函数

### `WrapAndroidHardwareBuffer`

从 Android 硬件缓冲区创建 SkSurface。

```cpp
SK_API sk_sp<SkSurface> WrapAndroidHardwareBuffer(
    GrDirectContext* context,
    AHardwareBuffer* hardwareBuffer,
    GrSurfaceOrigin origin,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* surfaceProps,
    bool fromWindow = false
)
```

**功能**: 将 AHardwareBuffer 包装为 Skia 可绘制的表面,无需拷贝像素数据。

**参数详解**:

**context** (GrDirectContext*):
- GPU 直接上下文,管理 GPU 资源和命令提交
- 必须是已初始化的有效上下文
- 决定使用 OpenGL 还是 Vulkan 后端

**hardwareBuffer** (AHardwareBuffer*):
- 源硬件缓冲区,必须包含合适的 usage bits:
  - `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT`(可作为渲染目标)
  - `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE`(可作为纹理)
- SkSurface 持有该缓冲区的引用,确保其在表面销毁前不被释放

**origin** (GrSurfaceOrigin):
- 纹理坐标原点位置
- `kTopLeft_GrSurfaceOrigin`: 左上角为原点(常见于 OpenGL)
- `kBottomLeft_GrSurfaceOrigin`: 左下角为原点(Vulkan 默认)

**colorSpace** (sk_sp<SkColorSpace>):
- 色彩空间,可为 nullptr(默认 sRGB)
- 支持宽色域(Display P3、Adobe RGB)
- 支持 HDR(线性色彩空间)

**surfaceProps** (const SkSurfaceProps*):
- 表面属性,可为 nullptr
- 控制 LCD 子像素抗锯齿方向
- 设备独立字体渲染选项

**fromWindow** (bool):
- 是否来自 Android 窗口系统
- `true`: 优化窗口表面的内存布局和同步(仅 Vulkan)
- `false`: 通用硬件缓冲区

**返回值**:
- 成功: 返回 SkSurface 智能指针
- 失败: 返回 nullptr,可能原因:
  - 硬件缓冲区格式不支持
  - Usage bits 不正确
  - GPU 内存不足
  - 驱动不支持该操作

## 内部实现细节

### 表面创建流程

1. **格式检测**:
   ```cpp
   AHardwareBuffer_Desc desc;
   AHardwareBuffer_describe(hardwareBuffer, &desc);
   GrBackendFormat format = GrAHardwareBufferUtils::GetBackendFormat(context, desc.format);
   ```

2. **纹理导入**:
   ```cpp
   GrBackendTexture backendTexture = GrAHardwareBufferUtils::MakeBackendTexture(
       context, hardwareBuffer, desc.width, desc.height, ...);
   ```

3. **表面包装**:
   ```cpp
   sk_sp<SkSurface> surface = SkSurfaces::WrapBackendRenderTarget(
       context, backendRenderTarget, origin, colorType, colorSpace, surfaceProps);
   ```

### 生命周期管理

- SkSurface 持有 AHardwareBuffer 的引用计数
- 当 Surface 销毁时:
  1. 调用 `DeleteImageProc` 清理 GPU 资源
  2. 释放 AHardwareBuffer 引用
  3. 如果无其他引用,系统回收硬件缓冲区

### 同步机制

- GPU 渲染命令异步执行
- 使用 `context->flush()` 提交命令
- 使用 `context->submit(GrSyncCpu::kYes)` 等待完成

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkSurface.h | SkSurface 基类定义 |
| include/core/SkRefCnt.h | 智能指针 sk_sp |
| include/gpu/ganesh/GrTypes.h | GPU 类型(GrSurfaceOrigin) |
| include/gpu/ganesh/GrDirectContext.h | GPU 上下文 |
| android/hardware_buffer.h | AHardwareBuffer API |
| GrAHardwareBufferUtils | GPU 后端集成 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Android Framework(libhwui) | 使用该函数创建窗口渲染表面 |
| Android SurfaceFlinger | 窗口合成系统 |
| Android ViewRootImpl | 视图层次结构渲染 |
| 第三方渲染引擎 | 与 Android 窗口系统集成 |

## 设计模式与设计决策

### 命名空间设计
使用 `SkSurfaces` 而非类成员函数:
- 与其他表面创建函数(`MakeRasterDirect`、`MakeRenderTarget`)风格一致
- 避免 SkSurface 类膨胀
- 平台特定代码隔离

### 私有 API 声明
文档明确标注"Private; only to be used by Android Framework":
- 不保证 API 稳定性
- 可能在未来版本中修改
- 一般应用开发者应使用 Android SDK 的高层 API

### 零拷贝设计
直接包装硬件缓冲区,无像素拷贝:
- 性能优势明显(省去数十毫秒的拷贝时间)
- 内存占用更小
- 支持跨进程共享(SurfaceFlinger 场景)

## 性能考量

### 表面创建开销
- 首次创建: ~5-10ms(导入纹理、设置 GPU 状态)
- 缓存复用: ~1ms(仅更新引用)
- 建议复用 Surface 对象

### 渲染性能
- 与普通 GPU Surface 性能相当
- 避免 CPU-GPU 内存拷贝,节省带宽
- 窗口表面(`fromWindow=true`)可能享受额外优化

### 内存占用
- Surface 对象: ~100 字节
- GPU 驱动元数据: ~1KB
- 实际像素内存: 由 AHardwareBuffer 管理(共享)

## 典型使用场景

### 场景 1: Android 窗口渲染(libhwui)
```cpp
// Android Framework 中的伪代码
AHardwareBuffer* windowBuffer = getNativeWindow()->dequeueBuffer();

sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(
    grContext,
    windowBuffer,
    kTopLeft_GrSurfaceOrigin,
    SkColorSpace::MakeSRGB(),
    nullptr,  // 默认 surface props
    true      // 来自窗口
);

// 渲染 View 层次结构
SkCanvas* canvas = surface->getCanvas();
drawViewHierarchy(canvas);

// 提交渲染结果
grContext->flush();
grContext->submit(GrSyncCpu::kNo);

// 将缓冲区送回窗口
getNativeWindow()->queueBuffer(windowBuffer);
```

### 场景 2: 离屏渲染
```cpp
// 创建离屏硬件缓冲区
AHardwareBuffer_Desc desc = {
    .width = 1920,
    .height = 1080,
    .format = AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM,
    .usage = AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT |
             AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE,
};
AHardwareBuffer* offscreenBuffer;
AHardwareBuffer_allocate(&desc, &offscreenBuffer);

// 创建 SkSurface
sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(
    context,
    offscreenBuffer,
    kTopLeft_GrSurfaceOrigin,
    nullptr,  // sRGB
    nullptr,
    false     // 非窗口表面
);

// 离屏渲染
SkCanvas* canvas = surface->getCanvas();
canvas->clear(SK_ColorWHITE);
canvas->drawText(...);

// 将结果用作纹理
sk_sp<SkImage> snapshot = surface->makeImageSnapshot();
```

### 场景 3: HDR 渲染
```cpp
// HDR 硬件缓冲区
AHardwareBuffer_Desc desc = {
    .width = 3840,
    .height = 2160,
    .format = AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT,
    .usage = AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT,
};
AHardwareBuffer* hdrBuffer;
AHardwareBuffer_allocate(&desc, &hdrBuffer);

// 使用线性色彩空间
sk_sp<SkColorSpace> linearRec2020 = SkColorSpace::MakeRGB(
    SkNamedTransferFn::kLinear,
    SkNamedGamut::kRec2020
);

sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(
    context,
    hdrBuffer,
    kTopLeft_GrSurfaceOrigin,
    linearRec2020,
    nullptr,
    false
);

// HDR 渲染(颜色值可超过 1.0)
SkCanvas* canvas = surface->getCanvas();
SkPaint paint;
paint.setColor4f({2.0f, 1.5f, 1.0f, 1.0f}); // HDR 白色
canvas->drawRect(rect, paint);
```

## 错误处理

### Usage Bits 检查
```cpp
// 错误:缺少必要的 usage bits
AHardwareBuffer_Desc desc = {
    .usage = AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE,  // 仅可读
};
// 创建会失败!

// 正确:同时包含读写 usage
desc.usage = AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT |  // 可写
             AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE;  // 可读
```

### 空指针检查
```cpp
sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(...);
if (!surface) {
    // 创建失败,可能原因:
    // 1. 格式不支持(如 YUV)
    // 2. Usage bits 不正确
    // 3. GPU 内存不足
    // 4. 驱动不支持

    // 回退方案:创建普通 GPU Surface
    SkImageInfo info = SkImageInfo::Make(width, height, ...);
    surface = SkSurfaces::RenderTarget(context, skgpu::Budgeted::kYes, info);
}
```

### 同步问题
```cpp
// 错误:未等待渲染完成就释放缓冲区
{
    sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(...);
    surface->getCanvas()->drawRect(...);
    // surface 析构,但 GPU 渲染可能未完成
}
AHardwareBuffer_release(buffer); // 可能导致渲染错误或崩溃

// 正确:显式同步
{
    sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(...);
    surface->getCanvas()->drawRect(...);
    context->flush();
    context->submit(GrSyncCpu::kYes); // 等待 GPU 完成
}
AHardwareBuffer_release(buffer); // 安全
```

## 平台相关说明

### Android 版本要求
- **最低**: Android 8.0(API 26),引入 AHardwareBuffer
- **推荐**: Android 10+(API 29),更好的同步和格式支持
- **最新**: Android 12+(API 31),优化的窗口合成

### GPU 后端差异
- **OpenGL**: 通过 EGLImage 实现,兼容性最好
- **Vulkan**: 通过外部内存扩展,性能更优,同步更精确

### 设备兼容性
- 所有 Android 8.0+ 设备必须支持基础功能
- 某些高级特性(如 HDR)仅限高端设备
- 旧设备可能有驱动 Bug,需要兼容性测试

## 限制与注意事项

### 格式限制
- 仅支持 RGB/RGBA 格式
- YUV 格式需要先转换或使用外部纹理机制
- 深度/模板格式不支持

### Usage Bits 要求
必须同时包含:
- `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT`(渲染目标)
- `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE`(纹理采样)

### 线程安全
- SkSurface 不是线程安全的
- 必须在 GrDirectContext 关联的线程中使用
- 跨线程需要使用 Skia 的跨上下文共享机制

### 受保护内容
- DRM 保护的缓冲区可能无法渲染到屏幕
- 需要使用受保护的 GPU 上下文

## 相关文件

| 文件 | 关系 |
|------|------|
| src/image/SkSurface_AndroidFactories.cpp | 实现文件 |
| include/android/GrAHardwareBufferUtils.h | GPU 后端集成工具 |
| include/core/SkSurface.h | SkSurface 基类 |
| include/gpu/ganesh/SkSurfaceGanesh.h | GPU Surface 创建函数 |
| frameworks/base/libs/hwui | Android Framework 使用示例 |

## 最佳实践

### 资源复用
```cpp
// 复用 Surface 对象,避免重复创建
class SurfaceCache {
    sk_sp<SkSurface> cachedSurface_;
    AHardwareBuffer* cachedBuffer_ = nullptr;

public:
    sk_sp<SkSurface> getSurface(AHardwareBuffer* buffer) {
        if (buffer != cachedBuffer_) {
            cachedSurface_ = SkSurfaces::WrapAndroidHardwareBuffer(...);
            cachedBuffer_ = buffer;
        }
        return cachedSurface_;
    }
};
```

### 错误处理
```cpp
sk_sp<SkSurface> createSurface(GrDirectContext* context,
                               AHardwareBuffer* buffer) {
    // 尝试包装硬件缓冲区
    sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(
        context, buffer, ...);

    if (!surface) {
        // 回退到 CPU 栅格化
        AHardwareBuffer_Desc desc;
        AHardwareBuffer_describe(buffer, &desc);
        SkImageInfo info = SkImageInfo::Make(desc.width, desc.height, ...);
        surface = SkSurfaces::Raster(info);
    }

    return surface;
}
```

### 性能优化
```cpp
// 批量渲染,减少 flush 次数
void renderMultipleViews(SkSurface* surface) {
    SkCanvas* canvas = surface->getCanvas();

    // 绘制多个对象
    drawView1(canvas);
    drawView2(canvas);
    drawView3(canvas);

    // 统一提交
    surface->flushAndSubmit();
}
```

### 同步最佳实践
```cpp
// 使用 GPU Semaphore 实现高效同步
GrBackendSemaphore semaphore;
surface->flush(SkSurface::BackendSurfaceAccess::kPresent,
               GrFlushInfo{.fNumSemaphores = 1, .fSignalSemaphores = &semaphore});

// 将 semaphore 传递给显示系统
queueBufferWithSemaphore(buffer, semaphore);
```

## 未来展望

### Graphite 后端
Skia 新的 Graphite GPU 后端将提供类似功能:
```cpp
namespace SkSurfaces {
    sk_sp<SkSurface> WrapAndroidHardwareBuffer(
        skgpu::graphite::Recorder* recorder,
        AHardwareBuffer* buffer,
        ...
    );
}
```

### API 演进
- 可能增加异步创建支持
- 更细粒度的同步控制
- 与 Android 13+ AIDL HardwareBuffer API 集成
