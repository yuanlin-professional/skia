# ProtectedSlide

> 源文件: `tools/viewer/ProtectedSlide.cpp`

## 概述

ProtectedSlide 是一个针对 Android 平台的演示幻灯片，用于测试和展示受保护内容（Protected Content）在 GPU 渲染管线中的行为。它验证了通过 AHardwareBuffer 创建的受保护纹理在 Ganesh 和 Graphite 后端中的正确渲染，特别是用于复现 bug b/242266174。

## 架构位置

属于 `tools/viewer` 模块，仅在 Android API 26+ 平台上编译（`__ANDROID_API__ >= 26`）。同时支持 Ganesh（`SK_GANESH`）和 Graphite（`SK_GRAPHITE`）GPU 后端。

## 主要类与结构体

### ProtectedSlide
- 继承自 `Slide`
- 常量 `kSize = 128`: 渲染目标尺寸
- 显示尺寸为 128x256（上下两张图像）

### 辅助函数（匿名命名空间）
- `release_buffer`: 释放 AHardwareBuffer
- `wrap_buffer`: 将 AHB 包装为 SkSurface（支持 Ganesh/Graphite）
- `create_protected_render_target`: 创建受保护的 GPU 渲染目标
- `create_protected_buffer`: 分配受保护的 AHardwareBuffer
- `create_protected_AHB_image`: 在受保护 AHB 上绘制棋盘格图像
- `create_protected_skia_image`: 在受保护 Skia Surface 上绘制棋盘格

## 公共 API 函数

- `getDimensions()`: 返回 {128, 256}
- `draw(SkCanvas*)`: 创建受保护资源并渲染

## 内部实现细节

### 绘制流程
1. 检测后端是否支持受保护内容（不支持时显示绿色/蓝色/红色背景）
2. 分配受保护的 AHardwareBuffer（128x128，RGBA8888）
3. 创建两种受保护图像：AHB 支持的红色棋盘格和 Skia 渲染目标支持的蓝色棋盘格
4. 在另一个受保护渲染目标上间接绘制（复现 bug：AHB 图像可能"毒害"之前的绘制操作）
5. 直接和间接图像分上下两行绘制

### AHB 标志配置
```
AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE |
AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT |
AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT
```
禁止 CPU 读写，标记为受保护内容。

### Bug 复现机制
通过在中间渲染目标上先绘制纯色和圆形，再绘制受保护 AHB 图像，检验此操作是否会影响之前的绘制结果。

## 依赖关系

- `<android/hardware_buffer.h>`: Android 硬件缓冲区 API
- `include/android/SkImageAndroid.h` / `include/android/SkSurfaceAndroid.h`: AHB 集成
- `include/gpu/ganesh/GrDirectContext.h`: Ganesh GPU 上下文
- `include/gpu/graphite/Context.h`: Graphite GPU 上下文
- `tools/ToolUtils.h`: 棋盘格绘制工具

## 设计模式与设计决策

- **平台条件编译**: 使用多层 `#if defined()` 宏同时支持 Ganesh 和 Graphite
- **错误诊断颜色**: 不支持受保护内容时显示不同颜色（绿色=Ganesh不支持，蓝色=Graphite不支持，红色=无GPU上下文）
- **资源清理**: 手动管理 AHB 生命周期，确保 draw 结束后释放

## 性能考量

- 每帧重新分配和释放 AHB，仅用于诊断目的
- 受保护内容不可 CPU 回读，所有操作必须在 GPU 端完成

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
- `include/android/SkSurfaceAndroid.h`: Android AHB 表面包装
- `tools/ganesh/ProtectedUtils_Ganesh.cpp`: Ganesh 受保护内容工具
