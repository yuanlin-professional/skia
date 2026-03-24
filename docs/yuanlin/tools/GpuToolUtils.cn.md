# GpuToolUtils.h - GPU 工具实用函数

> 源文件: [tools/GpuToolUtils.h](../../tools/GpuToolUtils.h)

## 概述

此头文件提供了一个工具函数 `MakeTextureImage`，用于将 `SkImage` 转换为 GPU 纹理支持的图像。该函数根据当前 Canvas 使用的 GPU 后端（Ganesh 或 Graphite）自动选择正确的纹理上传路径。它主要在 Skia 的测试和基准测试工具（如 dm、nanobench）中使用，确保测试图像以 GPU 纹理形式存在。

## 架构位置

该头文件属于 Skia 工具层（`tools/`），是连接 Skia 核心图像 API 和 GPU 后端的桥接工具。它同时支持 Ganesh（旧 GPU 后端）和 Graphite（新 GPU 后端），通过条件编译（`SK_GANESH`、`SK_GRAPHITE`）适配不同的构建配置。

## 主要类与结构体

本文件在 `ToolUtils` 命名空间中定义了一个内联函数。所依赖的关键类型：

- **`SkCanvas`**：Skia 画布，通过它获取 GPU 上下文
- **`SkImage`**：Skia 图像基类
- **`GrDirectContext`**：Ganesh 直接上下文
- **`GrCaps`**：Ganesh GPU 能力描述
- **`skgpu::graphite::Recorder`**：Graphite 录制器

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `ToolUtils::MakeTextureImage(canvas, orig)` | `canvas`: SkCanvas 指针; `orig`: 源图像 | `sk_sp<SkImage>`: GPU 纹理图像或原始图像 | 将图像上传为 GPU 纹理 |

## 内部实现细节

1. **空值检查**：如果输入图像为空，直接返回 `nullptr`。
2. **Ganesh 路径**（`SK_GANESH`）：
   - 通过 `canvas->recordingContext()->asDirectContext()` 获取 `GrDirectContext`
   - 检查图像尺寸是否超过 GPU 最大纹理大小（`caps->maxTextureSize()`）
   - 如果超过限制，返回原始位图图像（让 Ganesh 的分块绘制功能处理大图）
   - 否则调用 `SkImages::TextureFromImage(dContext, orig)` 上传纹理
3. **Graphite 路径**（`SK_GRAPHITE`）：
   - 通过 `canvas->recorder()` 获取 `Recorder`
   - 调用 `SkImages::TextureFromImage(recorder, orig, {false})` 上传（不生成 mipmap）
4. **CPU 回退**：如果既无 Ganesh 也无 Graphite 上下文，返回原始图像。

## 依赖关系

- **Skia 核心**：`SkCanvas`、`SkImage`、`SkRefCnt`
- **Ganesh**（条件）：`GrDirectContext`、`GrRecordingContext`、`SkImageGanesh`、`GrCaps`、`GrDirectContextPriv`
- **Graphite**（条件）：`graphite::Image`、`graphite::Recorder`

## 设计模式与设计决策

- **头文件内联实现**：函数定义在头文件中（`inline`），注释解释这是因为工具库可能被编译为 "核心" 库，此时客户端（如 dm）的条件编译宏不可见。内联确保宏在调用点可见。
- **后端自动检测**：通过查询 Canvas 的录制上下文自动判断使用哪个 GPU 后端，简化了调用者的使用。
- **大纹理保护**：对超过 GPU 最大纹理尺寸的图像不强制上传，而是保留为位图，让 Ganesh 的分块绘制功能来处理。这确保了工具不会阻止对 Ganesh 分块功能的测试。
- **条件编译**：使用 `#if defined(SK_GANESH)` 和 `#if defined(SK_GRAPHITE)` 保护各后端特定代码，允许仅启用其中一个或两个后端。

## 性能考量

- 纹理上传（`TextureFromImage`）涉及 CPU 到 GPU 的数据传输，是潜在的性能瓶颈。
- 对大图像跳过上传避免了可能的内存不足或性能问题。
- Graphite 路径明确禁用 mipmap 生成（`fMipmapped=false`），减少了 GPU 内存使用。
- 内联实现避免了函数调用开销，但增加了编译时间。

## 相关文件

- `include/core/SkImage.h`：图像基类
- `include/gpu/ganesh/SkImageGanesh.h`：Ganesh 图像创建 API
- `include/gpu/graphite/Image.h`：Graphite 图像创建 API
- `tools/` 下使用此函数的各种测试工具

### 补充说明

- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
