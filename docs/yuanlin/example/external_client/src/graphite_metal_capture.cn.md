# graphite_metal_capture

> 源文件: example/external_client/src/graphite_metal_capture.cpp

## 概述

graphite_metal_capture 是一个演示 Skia Graphite Metal 后端捕获和序列化 GPU 命令的示例程序。该程序创建两个渲染表面,执行绘制操作,捕获所有 GPU 命令,序列化为二进制数据并写入文件,然后反序列化并检查捕获内容。这展示了 Graphite 的调试和分析能力,可用于离线分析渲染流程或复现 GPU 问题。

该示例使用 Graphite 的新捕获 API (`fEnableCapture`, `startCapture`, `endCapture`),展示了如何录制完整的 GPU 命令序列并进行序列化存储。

## 架构位置

```
skia/
└── example/external_client/src/
    ├── graphite_metal_capture.cpp   # Metal 捕获示例(170行)
    ├── graphite_metal_context_helper.h  # Metal 上下文辅助
    └── graphite_native_metal.cpp    # 基础 Metal 示例
```

## 主要类与结构体

### 使用的核心类型

```cpp
skgpu::graphite::Context         // Graphite 上下文
skgpu::graphite::Recorder        // 命令录制器
skgpu::graphite::Recording       // 录制的命令
SkSurface                        // 渲染表面
SkCapture                        // 捕获对象
```

## 公共 API 函数

### main()

```cpp
int main(int argc, char *argv[]);
```

**参数**:
- `argv[1]`: 输出文件路径(捕获数据写入位置)

**执行流程**:
1. 创建启用捕获的 Graphite 上下文
2. 创建两个渲染表面
3. 开始捕获
4. 在两个表面上绘制
5. 录制并提交 GPU 命令
6. 异步读回像素
7. 结束捕获并序列化
8. 写入文件
9. 反序列化验证

## 内部实现细节

### 启用捕获的上下文创建

```cpp
skgpu::graphite::MtlBackendContext backendContext = GetMetalContext();
skgpu::graphite::ContextOptions options;

options.fEnableCapture = true;  // 关键:启用捕获功能

std::unique_ptr<skgpu::graphite::Context> context =
    skgpu::graphite::ContextFactory::MakeMetal(backendContext, options);
```

**关键配置**: `fEnableCapture = true` 启用捕获基础设施

### 多表面渲染

```cpp
std::unique_ptr<skgpu::graphite::Recorder> recorder = context->makeRecorder();
sk_sp<SkSurface> surface = SkSurfaces::RenderTarget(recorder.get(), imageInfo);
sk_sp<SkSurface> surfaceB = SkSurfaces::RenderTarget(recorder.get(), imageInfo);
```

创建两个独立表面演示多目标渲染捕获。

### 捕获区域

```cpp
context->startCapture();  // 开始捕获所有 GPU 命令
printf("Capture started, now to draw\n");

// Canvas A - 绘制到第一个表面
canvas->clear(SK_ColorCYAN);
SkRRect rrect = SkRRect::MakeRectXY(SkRect::MakeLTRB(10, 20, 50, 70), 10, 10);
SkPaint paint;
paint.setColor(SK_ColorRED);
paint.setAntiAlias(true);
canvas->drawRRect(rrect, paint);

auto contentImg = surface->makeImageSnapshot();  // 触发捕获断点
canvas->drawCircle(50, 50, 30, paint);

// Canvas B - 绘制到第二个表面
canvasB->clear(SK_ColorMAGENTA);
paint.setColor(SK_ColorBLACK);
canvasB->drawImage(contentImg, 0, 0);
canvasB->drawCircle(10, 10, 5, paint);
```

**捕获内容**:
- 表面清空操作
- 圆角矩形绘制
- 图像快照创建(触发断点)
- 圆形绘制
- 跨表面图像使用

### 命令录制与提交

```cpp
std::unique_ptr<skgpu::graphite::Recording> recording = recorder->snap();
if (!recording) {
    printf("Could not create a recording\n");
    return 1;
}

skgpu::graphite::InsertRecordingInfo info;
info.fRecording = recording.get();
if (!context->insertRecording(info)) {
    printf("Context::insertRecording failed\n");
    return 1;
}
```

**步骤**:
1. `snap()`: 完成录制,创建 Recording 对象
2. `insertRecording()`: 将录制插入上下文的命令队列

### 异步像素读取

```cpp
sk_sp<SkImage> img;
auto callback = [](SkImage::ReadPixelsContext ctx,
                   std::unique_ptr<const SkImage::AsyncReadResult> result) {
    if (result->count() != 1) {
        printf("Didn't load exactly one plane\n");
        return;
    }
    auto ii = SkImageInfo::Make(WIDTH, HEIGHT, kRGBA_8888_SkColorType, kPremul_SkAlphaType);
    sk_sp<SkImage>* output = reinterpret_cast<sk_sp<SkImage>*>(ctx);

    SkPixmap pm(ii, result->data(0), result->rowBytes(0));
    *output = SkImages::RasterFromPixmapCopy(pm);
};

context->asyncRescaleAndReadPixels(surface.get(), imageInfo,
                                   SkIRect::MakeSize({WIDTH, HEIGHT}),
                                   SkImage::RescaleGamma::kSrc,
                                   SkImage::RescaleMode::kRepeatedCubic,
                                   callback, &img);
```

**异步读取**:
- 不阻塞主线程
- 在 GPU 完成后调用回调
- 适合高性能应用

### 同步等待 GPU 完成

```cpp
context->submit(skgpu::graphite::SyncToCpu::kYes);
if (context->hasUnfinishedGpuWork()) {
    printf("Sync with GPU completion failed\n");
    return 1;
}
```

**注意**: 此同步方式不适用于所有后端(如 Dawn)

### 捕获序列化

```cpp
auto capture = context->endCapture();
auto serializedCapture = capture->serializeCapture();

output.write(serializedCapture->data(), serializedCapture->size());
output.fsync();
```

**流程**:
1. `endCapture()`: 结束捕获,返回 SkCapture 对象
2. `serializeCapture()`: 序列化为二进制数据
3. 写入文件

### 反序列化验证

```cpp
if (serializedCapture) {
    auto deserializedCapture = SkCapture::MakeFromData(serializedCapture);
} else {
    printf("No capture to inspect.");
    return 1;
}
```

验证序列化数据可以成功反序列化。

## 依赖关系

### Skia Graphite 头文件
```cpp
#include "include/gpu/graphite/Context.h"
#include "include/gpu/graphite/Recorder.h"
#include "include/gpu/graphite/Recording.h"
#include "include/gpu/graphite/Surface.h"
#include "include/gpu/graphite/mtl/MtlBackendContext.h"
#include "include/gpu/graphite/mtl/MtlGraphiteUtils.h"
```

### 捕获 API
```cpp
#include "src/capture/SkCapture.h"  // 注意:这是私有 API
```

### 编码器
```cpp
#include "include/encode/SkJpegEncoder.h"
```

## 设计模式与设计决策

### 1. 构建器模式

Graphite 使用录制器(Recorder)模式:
```cpp
Recorder -> Recording -> Context::insertRecording()
```

### 2. 异步模式

像素读取使用异步回调避免阻塞:
```cpp
asyncRescaleAndReadPixels(..., callback, context)
```

### 3. 设计决策

#### (1) 为何需要 fEnableCapture?

- **性能**: 捕获有开销,默认禁用
- **选择性**: 只在需要时启用
- **调试友好**: 开发时启用,生产时禁用

#### (2) 为何捕获两个表面?

- **全面性**: 展示多目标渲染的捕获
- **跨表面引用**: 测试图像快照在表面间共享

#### (3) makeImageSnapshot 作为断点

```cpp
auto contentImg = surface->makeImageSnapshot();  // 触发断点
```

- **调试工具**: 在捕获工具中标记关键点
- **状态检查**: 可以检查此时的 GPU 状态

## 性能考量

### 1. 捕获开销

启用捕获会增加运行时开销:
- **内存**: 需要存储所有命令
- **CPU**: 序列化和跟踪开销
- **建议**: 仅在调试时使用

### 2. 异步读取优势

```cpp
asyncRescaleAndReadPixels(...)  // 不阻塞
vs
readPixels(...)  // 阻塞等待
```

- **并发性**: CPU 可以继续其他工作
- **吞吐量**: 提高整体渲染吞吐量

### 3. SyncToCpu 影响

```cpp
context->submit(skgpu::graphite::SyncToCpu::kYes);
```

- **性能损失**: 完全同步会等待 GPU 空闲
- **必要性**: 某些操作(如读取像素)需要
- **优化**: 尽量减少同步点

## 相关文件

### 相关示例
- **graphite_native_metal.cpp**: 基础 Graphite Metal 示例
- **ganesh_metal.cpp**: Ganesh Metal 对比

### 捕获工具
- **tools/graphite/**: Graphite 内部工具
- **src/capture/SkCapture.h**: 捕获 API 实现

### 分析工具
- **Xcode Metal Debugger**: 可视化分析捕获的 Metal 命令
- **RenderDoc**: 跨平台图形调试器(如果支持)

该示例展示了 Graphite 的高级调试能力,对于理解渲染流程和诊断 GPU 问题非常有价值。
