# draw - Fiddle 示例绘制实现

> 源文件: `tools/fiddle/draw.cpp`

## 概述

draw.cpp 是 Fiddle 工具的示例翻译单元，演示了如何实现 `GetDrawOptions()` 和 `draw()` 函数。它展示了图像着色器、动画旋转、GPU 纹理操作等 Skia 功能。此文件也是 Fiddle 在线服务中用户代码的模板。

## 架构位置

位于 `tools/fiddle/` 目录，作为 Fiddle 框架的示例实现。用户在 fiddle.skia.org 上编写的代码会替换此文件中的函数实现。

## 主要类与结构体

无类定义。

## 公共 API 函数

### `GetDrawOptions()`
返回 `DrawOptions` 结构体，配置画布大小(256x256)、启用 GPU/纹理/动画等选项、资源图像路径。

### `draw(SkCanvas* canvas)`
核心绘制函数，演示纹理平铺着色器、动画旋转、GPU 后端纹理和渲染目标操作。

## 内部实现细节

- 使用 `image->makeShader` 创建重复平铺着色器
- 通过 `frame * 30.0f * duration` 实现依赖帧号和持续时间的旋转动画
- 演示 `SkImages::BorrowTextureFrom` 从后端纹理创建图像
- 演示 `SkSurfaces::WrapBackendTexture` 和 `WrapBackendRenderTarget`

## 依赖关系

- `skia.h` - Skia 统一头文件
- `tools/fiddle/fiddle_main.h` - 提供全局变量 image, duration, frame 等

## 设计模式与设计决策

- **模板模式**: 文件结构定义了 Fiddle 用户代码必须实现的接口
- `fiddle_main.h` 故意放在最后包含，因为它使用了通用名称污染全局命名空间

## 性能考量

作为示例代码，不涉及性能优化。

## 相关文件

- `tools/fiddle/fiddle_main.h` - Fiddle 全局变量和 DrawOptions 定义
- `tools/fiddle/egl_context.cpp` - GPU 上下文创建
