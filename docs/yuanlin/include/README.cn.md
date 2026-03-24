# include/ - Skia 公共 API 头文件目录总览

## 概述

`include/` 是 Skia 图形库的公共 API 头文件目录。该目录下的头文件定义了 Skia
对外暴露的所有公共接口，是集成 Skia 的开发者最主要的参考目录。与 `src/` 中的
内部实现不同，`include/` 中的 API 遵循稳定性承诺，版本间的变更会在发布说明中
记录。

## 目录结构与子目录说明

```
include/
├── BUILD.bazel          # Bazel 构建配置
├── OWNERS               # 代码审查负责人
├── android/             # Android 平台特定 API
│   └── graphite/        # Android Graphite GPU 后端接口
├── codec/               # 图像编解码 API
├── config/              # 编译配置与平台检测
├── core/                # 核心 API（最重要的子目录）
├── docs/                # 文档生成相关 API
├── effects/             # 视觉效果 API
├── encode/              # 图像编码 API
├── gpu/                 # GPU 渲染 API
│   ├── ganesh/          # Ganesh GPU 后端 API
│   │   ├── d3d/         # Direct3D 接口
│   │   ├── gl/          # OpenGL 接口
│   │   │   ├── egl/     # EGL 平台
│   │   │   ├── epoxy/   # libepoxy 平台
│   │   │   ├── glx/     # GLX 平台
│   │   │   ├── ios/     # iOS 平台
│   │   │   ├── mac/     # macOS 平台
│   │   │   └── win/     # Windows 平台
│   │   ├── mock/        # Mock 测试后端
│   │   ├── mtl/         # Metal 接口
│   │   └── vk/          # Vulkan 接口
│   ├── mtl/             # Metal 共享类型
│   └── vk/              # Vulkan 共享类型
├── pathops/             # 路径布尔运算 API
├── ports/               # 平台移植接口
├── private/             # 内部/半公开 API
│   ├── base/            # 基础内部类型
│   ├── chromium/        # Chromium 专用接口
│   └── gpu/             # GPU 内部接口
│       ├── ganesh/      # Ganesh 内部接口
│       └── vk/          # Vulkan 内部接口
├── sksl/                # SkSL 着色器语言 API
├── svg/                 # SVG 渲染 API
├── third_party/         # 第三方 API 封装
│   └── vulkan/          # Vulkan 头文件
└── utils/               # 工具 API
    └── mac/             # macOS 工具 API
```

## 核心子目录详解

### core/ (核心 API)
Skia 最重要的公共 API 目录，定义了所有基础类型和绑图接口：
- **SkCanvas.h** - 绘图画布，所有绘制操作的入口
- **SkPaint.h** - 绘制样式（颜色、描边、效果）
- **SkPath.h** - 矢量路径（线段、曲线、形状）
- **SkBitmap.h** - 位图像素存储
- **SkImage.h** - 不可变图像
- **SkSurface.h** - 绘图目标表面
- **SkMatrix.h** - 3x3 变换矩阵
- **SkFont.h** - 字体配置
- **SkColor.h** / **SkColorSpace.h** - 颜色和色彩空间
- **SkStream.h** - 数据流 I/O
- **SkShader.h** - 着色器基类
- **SkRefCnt.h** - 引用计数智能指针（sk_sp）

### codec/ (编解码 API)
图像解码器接口，支持 PNG、JPEG、WebP、GIF、BMP、AVIF 等格式。

### effects/ (效果 API)
各种视觉效果的创建接口：
- 渐变着色器（线性、径向、锥形、扫描）
- 图像滤镜（模糊、色彩矩阵、位移映射）
- 颜色滤镜
- 路径效果（虚线、角点等）

### gpu/ (GPU API)
GPU 渲染后端的公共接口，包括：
- **GrDirectContext** - Ganesh GPU 上下文
- **GrBackendTexture** - GPU 纹理封装
- 各平台 GL 上下文创建接口
- Vulkan、Metal、Direct3D 后端特定接口

### private/ (内部 API)
半公开的内部 API，主要供 Chromium 等紧密耦合的客户端使用。
这些接口可能在版本间发生变化，不建议外部项目直接依赖。

## API 稳定性

- `include/core/` - 最稳定，遵循严格的向后兼容性
- `include/effects/`、`include/codec/` 等 - 较稳定
- `include/gpu/` - 随 GPU 后端演进可能有变化
- `include/private/` - 不保证向后兼容

## 依赖关系

- 被 `src/` 中的实现代码引用
- 被 `modules/` 中的高级模块引用
- 被外部客户端代码直接包含使用

## 相关文档与参考

- 源码实现: `src/`
- API 示例: `docs/examples/`
- Skia API 参考: https://skia.org/docs/dev/
- 发布说明: `relnotes/` 和 `RELEASE_NOTES.md`
