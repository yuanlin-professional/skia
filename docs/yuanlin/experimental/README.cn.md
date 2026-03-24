# experimental/ - Skia 实验性项目目录

## 概述

`experimental/` 目录包含 Skia 的实验性代码和原型项目。这些项目处于开发或探索阶段，
可能尚未达到生产就绪状态。该目录涵盖了文本渲染、Rust 语言集成、视频编解码、WebGPU
支持、iOS Metal 渲染等多个前沿技术领域的探索。

## 目录结构

```
experimental/
├── BUILD.bazel              # Bazel 顶层构建配置
├── sktext/                  # 实验性文本渲染引擎
├── rust_bmp/                # Rust 实现的 BMP 图像解码器
│   ├── decoder/             # C++ 集成层
│   └── ffi/                 # Rust FFI 核心实现
├── ffmpeg/                  # FFmpeg 视频编解码集成
├── documentation/           # 开发文档（如 Gerrit 使用指南）
├── tools/                   # 辅助开发工具脚本集合
├── filterfuzz/              # 滤镜模糊测试工具
├── lowp-basic/              # 低精度（低功耗）图形实验
├── rust_cxx/                # Rust-C++ CXX 桥接实验
├── tskit/                   # TypeScript 版 CanvasKit 绑定
│   ├── bindings/            # C++/embind 绑定代码
│   ├── build/               # 构建产物目录
│   ├── go/                  # Go 类型生成工具
│   ├── interface/           # TypeScript 接口定义
│   └── npm_build/           # npm 发布构建
├── minimal_ios_mtl_skia_app/  # iOS Metal 最小示例应用
└── webgpu-bazel/            # WebGPU + Bazel 构建实验
    ├── example/             # 示例页面
    └── src/                 # WebGPU 绑定源码
```

## 关键项目说明

### sktext
实验性的高级文本渲染引擎，依赖 SkShaper、SkUnicode 等模块，提供文本塑形、选择、
换行等功能。包含编辑器原型实现。

### rust_bmp
用 Rust 编写的完整 BMP 解码器，支持 1-32 位色深、RLE 压缩、ICC 配置文件等。
通过 CXX 桥接与 Skia C++ 代码集成，提供内存安全保障。

### ffmpeg
基于 FFmpeg 库的视频编解码封装，提供 `SkVideoEncoder` 和 `SkVideoDecoder`，
支持将 Skia 绘制内容录制为视频。

### tskit
TypeScript 版本的 CanvasKit 绑定实验，尝试用 TypeScript 替代 JavaScript
绑定代码，提供更好的类型安全性。

### webgpu-bazel
使用 Bazel 构建系统的 WebGPU 渲染实验，将 Skia 编译为 WebAssembly 并通过
WebGPU API 进行 GPU 加速渲染。

## 依赖关系

- **sktext**: 依赖 `skia` 核心库、`modules/skshaper`、`modules/skunicode`
- **rust_bmp**: 依赖 Rust 工具链、CXX crate、moxcms、zune-jpeg、png crate
- **ffmpeg**: 依赖 FFmpeg 外部库（libavcodec、libavformat 等）
- **tskit**: 依赖 TypeScript、eslint 等 Node.js 开发工具
- **webgpu-bazel**: 依赖 Bazel 构建系统、Dawn WebGPU 后端

## 相关文档与参考

- Skia 核心库文档: `src/` 和 `include/` 目录
- Rust 集成文档: `rust/` 目录
- CanvasKit 模块: `modules/canvaskit/`
- Skia 构建指南: https://skia.org/docs/dev/
