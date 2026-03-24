# Skia Fiddle 工具

## 概述

`tools/fiddle` 是 Skia 的在线代码沙盒工具的本地实现。它为 [fiddle.skia.org](https://fiddle.skia.org) 网站提供后端支持，允许用户在浏览器中编写和运行 Skia 绘图代码片段，并即时查看渲染结果。Fiddle 支持多种输出后端（光栅、GPU、PDF、SKP），是学习和演示 Skia API 的核心工具。

## 目录结构

```
tools/fiddle/
├── fiddle_main.cpp          # Fiddle 主程序入口，负责初始化渲染环境和输出结果
├── fiddle_main.h            # 主头文件，定义 DrawOptions 结构体和全局变量
├── draw.cpp                 # draw() 函数的示例实现模板
├── examples.cpp             # 示例代码的加载和管理
├── examples.h               # 示例注册宏 REGISTER_FIDDLE 的定义
├── all_examples.cpp         # 自动生成的所有示例合集
├── make_all_examples_cpp.py # 生成 all_examples.cpp 的 Python 脚本
├── egl_context.cpp          # EGL GPU 上下文创建实现
├── null_context.cpp         # 空 GPU 上下文（回退方案）
├── animate.sh               # 动画渲染辅助脚本
├── parse-fiddle-output      # 解析 fiddle 输出结果的脚本
└── .gitignore               # Git 忽略规则
```

## 核心架构

### DrawOptions 结构体

`fiddle_main.h` 中定义的 `DrawOptions` 是 Fiddle 的核心配置结构，包含以下选项：

- **size**: 输出画布的尺寸（宽度和高度）
- **raster**: 是否启用光栅后端输出
- **gpu**: 是否启用 GPU 后端输出
- **pdf**: 是否启用 PDF 后端输出
- **skp**: 是否启用 SKP 录制输出
- **srgb/f16**: 色彩空间配置
- **textOnly**: 是否仅输出文本（SkDebugf 输出）
- **source**: 源图片路径
- **fMipMapping**: GPU 纹理的 Mipmap 设置
- **fOffScreen***: 离屏渲染目标参数

### 全局变量

Fiddle 有意在全局命名空间中暴露以下变量，供用户代码直接使用：

| 变量 | 类型 | 说明 |
|------|------|------|
| `image` | `sk_sp<SkImage>` | 从 source 路径加载的源图片 |
| `duration` | `double` | 动画总时长（秒） |
| `frame` | `double` | 动画进度 [0, 1] |
| `fontMgr` | `sk_sp<SkFontMgr>` | 可加载系统字体的字体管理器 |
| `backEndTexture` | `GrBackendTexture` | GPU 后端纹理 |
| `backEndRenderTarget` | `GrBackendRenderTarget` | GPU 渲染目标 |

### 用户接口

每个 Fiddle 程序需要实现两个函数：

1. **`GetDrawOptions()`** - 返回 `DrawOptions` 配置，指定输出格式和画布大小
2. **`draw(SkCanvas*)`** - 实际的绘图逻辑，接收画布指针

### 示例注册机制

通过 `examples.h` 中的 `REGISTER_FIDDLE` 宏，可以将多个示例注册到全局注册表中。`make_all_examples_cpp.py` 脚本会扫描所有注册的示例，生成 `all_examples.cpp` 汇总文件。

## GPU 上下文

Fiddle 支持多种 GPU 上下文实现：

- **egl_context.cpp**: 使用 EGL 创建 OpenGL 上下文（Linux 服务器常用）
- **null_context.cpp**: 空上下文回退，当 GPU 不可用时使用

所有实现都通过 `create_direct_context()` 函数提供统一接口。

## 构建与运行

```bash
# 构建 fiddle 可执行文件
ninja -C out/Release fiddle

# 运行 fiddle
out/Release/fiddle --duration 1.0 --frame 0.5
```

## 工作流程

1. 用户在 fiddle.skia.org 网站编写代码
2. 服务器将用户代码与 `fiddle_main.cpp` 组合编译
3. 运行编译后的程序，捕获各后端的输出（PNG、PDF、SKP）
4. 将渲染结果返回给用户浏览器展示

## 与其他模块的关系

- **tools/flags/**: 命令行参数解析
- **tools/ganesh/**: GPU 测试上下文
- **tools/gpu/**: GPU 后端纹理管理（ManagedBackendTexture）
- **modules/canvaskit/**: CanvasKit 的 Web 版本提供类似的在线编辑体验
