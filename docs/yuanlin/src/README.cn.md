# src/ - Skia 源码实现目录总览

## 概述

`src/` 是 Skia 图形库的核心源码实现目录。所有头文件在 `include/` 中声明的公共 API
都在此目录中实现。`src/` 中的代码属于 Skia 的内部实现细节，不构成公共 API 的一部分，
可能在任何版本中发生变化。

## 目录结构与子目录说明

```
src/
├── BUILD.bazel          # Bazel 顶层构建配置
├── android/             # Android 平台特定实现
├── base/                # 基础工具库（字节序、浮点、容器等）
├── capture/             # 绘制操作捕获与录制
├── codec/               # 图像编解码器（PNG、JPEG、WebP、GIF 等）
├── core/                # 核心渲染引擎（Canvas、Paint、Path、Matrix 等）
├── effects/             # 视觉效果（颜色滤镜、图像滤镜、遮罩滤镜）
│   ├── colorfilters/    # 颜色滤镜实现
│   └── imagefilters/    # 图像滤镜实现
├── encode/              # 图像编码器（PNG、JPEG、WebP 编码输出）
├── gpu/                 # GPU 渲染后端（最大的子目录）
│   ├── ganesh/          # Ganesh GPU 后端（OpenGL、Vulkan、Metal、D3D）
│   │   ├── d3d/         # Direct3D 后端
│   │   ├── gl/          # OpenGL/OpenGL ES 后端
│   │   ├── mtl/         # Metal 后端
│   │   ├── vk/          # Vulkan 后端
│   │   ├── effects/     # GPU 效果
│   │   ├── geometry/    # GPU 几何处理
│   │   ├── ops/         # GPU 渲染操作
│   │   ├── tessellate/  # GPU 细分曲面
│   │   └── text/        # GPU 文本渲染
│   ├── graphite/        # Graphite 新一代 GPU 后端
│   │   ├── dawn/        # Dawn/WebGPU 后端
│   │   ├── mtl/         # Metal 后端
│   │   ├── vk/          # Vulkan 后端
│   │   ├── compute/     # 计算着色器
│   │   ├── geom/        # 几何处理
│   │   └── render/      # 渲染管线
│   ├── tessellate/      # 共享细分曲面代码
│   ├── mtl/             # Metal 共享代码
│   └── vk/              # Vulkan 共享代码
├── image/               # SkImage 实现（光栅、GPU、延迟加载）
├── lazy/                # 延迟加载与缓存
├── opts/                # 平台优化代码（SSE、AVX、NEON SIMD）
├── pathops/             # 路径布尔运算（交集、并集、差集等）
├── pdf/                 # PDF 文档生成
├── ports/               # 平台移植层（字体、文件系统、线程）
│   └── fontations/      # Fontations Rust 字体引擎移植
├── sfnt/                # SFNT/TrueType/OpenType 字体表解析
├── shaders/             # 着色器实现
│   └── gradients/       # 渐变着色器
├── sksl/                # SkSL 着色器语言编译器
│   ├── analysis/        # 语义分析
│   ├── codegen/         # 代码生成（GLSL、HLSL、Metal、SPIR-V）
│   ├── generated/       # 自动生成的代码
│   ├── ir/              # 中间表示
│   ├── lex/             # 词法分析
│   ├── tracing/         # 着色器调试跟踪
│   └── transform/       # IR 变换优化
├── svg/                 # SVG 导出支持
├── text/                # 文本渲染
│   └── gpu/             # GPU 文本渲染
├── utils/               # 工具类（JSON、调试、事件跟踪）
│   ├── mac/             # macOS 工具
│   └── win/             # Windows 工具
├── xml/                 # XML 解析和生成
└── xps/                 # XPS 文档生成（Windows）
```

## 核心子目录详解

### core/ (核心渲染引擎)
Skia 的心脏，包含 SkCanvas、SkPaint、SkPath、SkBitmap、SkMatrix、
SkRasterPipeline 等核心类的实现。CPU 渲染的完整管线从这里驱动。

### gpu/ (GPU 后端)
最大的子目录，包含两代 GPU 渲染后端：
- **Ganesh**: 成熟的 GPU 后端，支持 OpenGL、Vulkan、Metal、Direct3D
- **Graphite**: 新一代 GPU 后端，支持 Metal、Vulkan、Dawn/WebGPU

### codec/ (图像编解码)
支持 PNG、JPEG、WebP、GIF、BMP、AVIF、JPEG XL、WBMP、ICO 等格式的
解码，以及 Rust 实现的 PNG/BMP 解码器。

### sksl/ (着色器编译器)
SkSL（Skia Shading Language）编译器，将 SkSL 着色器编译为各 GPU API
的原生着色器语言。

### pathops/ (路径布尔运算)
实现路径的交集、并集、差集、异或等布尔运算，使用 Bentley-Ottmann 算法
处理线段交叉。

## 依赖关系

- `include/` - 公共 API 声明
- `third_party/` - 外部依赖库
- `modules/` - 高级功能模块

## 相关文档与参考

- 公共 API: `include/`
- CPU 架构文档: `docs/architecture/CPU.md`
- 构建系统: `BUILD.bazel`、`BUILD.gn`
- Skia 官方文档: https://skia.org/docs/dev/
