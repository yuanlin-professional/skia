# ganesh_metal

> 源文件: example/external_client/src/ganesh_metal.cpp

## 概述

ganesh_metal 是一个演示在 macOS/iOS 上使用 Skia Ganesh Metal 后端进行 GPU 渲染的基础示例。程序创建 Metal 上下文,渲染简单图形(青色背景上的洋红色圆角矩形),将结果编码为 JPEG 并保存到文件。展示了 Ganesh Metal 后端的基本使用流程和像素读回机制。

## 主要实现

**Metal 上下文**: 使用 `GetMetalContext()` 辅助函数获取
**渲染表面**: 200x400 RGBA8888
**绘制内容**: 清空(青色) + 圆角矩形(洋红色,抗锯齿)
**输出**: JPEG 编码,写入文件

```cpp
// 核心流程
GrMtlBackendContext backendContext = GetMetalContext();
sk_sp<GrDirectContext> ctx = GrDirectContexts::MakeMetal(backendContext);
sk_sp<SkSurface> surface = SkSurfaces::RenderTarget(ctx.get(), skgpu::Budgeted::kYes, imageInfo);
surface->getCanvas()->clear(SK_ColorCYAN);
surface->getCanvas()->drawRRect(rrect, paint);
ctx->flush();
sk_sp<SkImage> img = surface->makeImageSnapshot();
sk_sp<SkData> jpeg = SkJpegEncoder::Encode(ctx.get(), img.get(), {});
```

## 关键点

- **budgeted 表面**: 允许 GPU 资源缓存重用
- **抗锯齿**: `paint.setAntiAlias(true)` 启用平滑边缘
- **flush**: 确保绘制命令提交到 Metal
- **GPU 编码**: JPEG 编码在 GPU 上执行(如果支持)

## 相关文件
- ganesh_metal_context_helper.h/mm: Metal 上下文创建
- ganesh_gl.cpp: OpenGL 对比示例
- VulkanBasic.cpp: Vulkan 对比示例
