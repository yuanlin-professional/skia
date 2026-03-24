# graphite_native_metal.cpp - Graphite Metal 原生渲染示例

> 源文件: `example/external_client/src/graphite_native_metal.cpp`

## 概述

`graphite_native_metal.cpp` 是一个完整的示例程序，演示了如何使用 Skia 的 Graphite 渲染后端通过 Apple Metal API 进行 GPU 加速渲染。该示例创建一个 Metal 上下文，使用 Graphite 的 Recorder 和 Recording 机制录制绘图命令，将结果渲染为图像，并最终编码为 JPEG 文件输出。

此示例是外部客户端集成 Skia Graphite Metal 后端的参考实现，展示了完整的 GPU 渲染生命周期：上下文创建、Surface 分配、绘图命令录制、GPU 提交、像素回读和图像编码。

## 架构位置

```
Skia 示例程序
├── example/external_client/
│   ├── BUILD.bazel                          <-- 构建定义
│   └── src/
│       ├── graphite_native_metal.cpp        <-- 本文件：Metal 渲染示例
│       ├── graphite_native_vulkan.cpp       <-- Vulkan 渲染示例
│       ├── graphite_metal_context_helper.h  <-- Metal 上下文辅助
│       └── ...
```

## 主要类与结构体

本文件不定义新类，使用 Skia 现有的 Graphite API。

### 使用的核心类型
- `skgpu::graphite::Context` - Graphite 上下文，管理 GPU 资源和命令提交
- `skgpu::graphite::Recorder` - 命令录制器，录制绘图操作
- `skgpu::graphite::Recording` - 录制结果，包含待提交的 GPU 命令
- `skgpu::graphite::MtlBackendContext` - Metal 后端上下文配置
- `SkSurface` / `SkCanvas` - Skia 绘图 Surface 和 Canvas

## 公共 API 函数

### `main(int argc, char* argv[])`
程序入口。用法：`graphite_native_metal <name.jpeg>`

完整执行流程：
1. 创建 Metal 后端上下文
2. 创建 Graphite Context
3. 创建 Recorder 和 RenderTarget Surface
4. 在 Canvas 上绘制图形（青色背景 + 黄色圆角矩形）
5. 快照录制器生成 Recording
6. 将 Recording 插入 Context 并提交到 GPU
7. 异步读取像素
8. 等待 GPU 完成
9. 编码为 JPEG 并写入文件

## 内部实现细节

### Metal 上下文创建

```cpp
skgpu::graphite::MtlBackendContext backendContext = GetMetalContext();
std::unique_ptr<skgpu::graphite::Context> context =
    skgpu::graphite::ContextFactory::MakeMetal(backendContext, options);
```

Metal 上下文的实际创建委托给 `graphite_metal_context_helper.h` 中的 `GetMetalContext()` 辅助函数。

### 录制-提交模式

Graphite 使用显式的录制-提交模式，不同于 Ganesh 的隐式刷新：

```cpp
// 1. 创建 Recorder 和 Surface
std::unique_ptr<skgpu::graphite::Recorder> recorder = context->makeRecorder();
sk_sp<SkSurface> surface = SkSurfaces::RenderTarget(recorder.get(), imageInfo);

// 2. 在 Surface 上绘制
SkCanvas* canvas = surface->getCanvas();
canvas->clear(SK_ColorCYAN);
canvas->drawRRect(rrect, paint);

// 3. 快照 Recording
std::unique_ptr<skgpu::graphite::Recording> recording = recorder->snap();

// 4. 提交到 GPU
skgpu::graphite::InsertRecordingInfo info;
info.fRecording = recording.get();
context->insertRecording(info);
```

### 异步像素回读

```cpp
auto callback = [](SkImage::ReadPixelsContext ctx,
                   std::unique_ptr<const SkImage::AsyncReadResult> result) {
    auto ii = SkImageInfo::Make(WIDTH, HEIGHT, kRGBA_8888_SkColorType, kPremul_SkAlphaType);
    sk_sp<SkImage>* output = reinterpret_cast<sk_sp<SkImage>*>(ctx);
    SkPixmap pm(ii, result->data(0), result->rowBytes(0));
    *output = SkImages::RasterFromPixmapCopy(pm);
};
context->asyncRescaleAndReadPixels(surface.get(), imageInfo,
    SkIRect::MakeSize({WIDTH, HEIGHT}),
    SkImage::RescaleGamma::kSrc, SkImage::RescaleMode::kRepeatedCubic,
    callback, &img);
```

使用异步回调模式读取像素，回调中从 GPU 数据创建光栅图像。

### GPU 同步

```cpp
context->submit(skgpu::graphite::SyncToCpu::kYes);
if (context->hasUnfinishedGpuWork()) {
    printf("Sync with GPU completion failed\n");
    return 1;
}
```

注意：`SyncToCpu::kYes` 并非所有后端都支持（如 Dawn），这里仅适用于 Metal。

## 依赖关系

- **Skia 核心**：`SkBitmap`, `SkCanvas`, `SkImage`, `SkRRect`, `SkSurface`, `SkStream`
- **Skia Graphite**：`Context`, `Recorder`, `Recording`, `Surface`, `ContextOptions`
- **Skia Graphite Metal**：`MtlBackendContext`, `MtlGraphiteUtils`
- **编码器**：`SkJpegEncoder`
- **本地辅助**：`graphite_metal_context_helper.h`

## 设计模式与设计决策

1. **完整生命周期演示**：示例展示了从上下文创建到最终输出的每一步，包括错误处理，作为集成参考非常完整。

2. **显式命令提交**：Graphite 的录制-提交模式使 GPU 工作负载可预测，不像 Ganesh 的隐式刷新那样可能在意想不到的地方触发 GPU 操作。

3. **异步回读**：使用异步 API 读取 GPU 像素，这是 Graphite 推荐的方式，避免了同步等待的性能瓶颈。

4. **详细的错误检查**：每个可能失败的步骤都有错误检查和诊断输出，方便调试集成问题。

5. **辅助函数分离**：Metal 上下文创建被分离到独立的辅助头文件中，使主程序专注于 Skia API 的使用。

## 性能考量

- **SyncToCpu::kYes**：强制 CPU 等待 GPU 完成所有工作，是简单但低效的同步方式。生产代码应使用回调或围栏（fence）机制。
- **asyncRescaleAndReadPixels**：虽然使用了异步 API，但 `SyncToCpu::kYes` 使得整个操作实际上是同步的。在真实应用中应使用事件循环处理回调。
- **RasterFromPixmapCopy**：回调中进行了像素数据复制，因为 `AsyncReadResult` 的生命周期有限。
- **JPEG 编码**：使用 CPU 进行 JPEG 编码，这在编码大图像时可能成为瓶颈。
- **Surface 尺寸**：示例使用 200x400 的较小 Surface，在实际应用中应根据显示需求调整。

## 相关文件

- `example/external_client/src/graphite_native_vulkan.cpp` - Vulkan 版本的类似示例
- `example/external_client/src/graphite_metal_context_helper.h` - Metal 上下文创建辅助
- `include/gpu/graphite/Context.h` - Graphite Context API
- `include/gpu/graphite/Recorder.h` - Graphite Recorder API
- `include/gpu/graphite/mtl/MtlGraphiteUtils.h` - Metal Graphite 工具
