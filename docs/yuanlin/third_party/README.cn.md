# third_party/ - 第三方依赖库

## 概述

`third_party/` 目录包含构建 Skia 各组件和工具所需的外部依赖库。部分依赖直接
存放在 Skia 仓库中，其余的在构建时通过 DEPS 文件从外部仓库拉取到
`third_party/externals/` 目录。所有第三方产品遵循各自的许可证条款。

Skia 团队为没有自带 Bazel 构建规则的第三方库编写了构建规则，维护在
`//bazel/external` 目录中。

## 目录结构

```
third_party/
├── BUILD.gn                 # GN 构建入口
├── third_party.gni          # GN 导入配置
├── go.mod                   # Go 模块配置
├── README                   # 原始说明文档
├── angle2/                  # ANGLE OpenGL ES 实现
├── brotli/                  # Brotli 压缩库
├── cpu-features/            # CPU 特性检测
├── d3d12allocator/          # Direct3D 12 内存分配器
├── dawn/                    # Dawn WebGPU 实现
├── delaunator/              # Delaunay 三角剖分
├── dng_sdk/                 # Adobe DNG SDK
├── etc1/                    # ETC1 纹理压缩
├── expat/                   # XML 解析库
├── freetype2/               # FreeType 字体引擎
├── harfbuzz/                # HarfBuzz 文本塑形
├── highway/                 # Google Highway SIMD 库
├── icu/                     # ICU 国际化组件
├── icu4x/                   # ICU4X Rust 国际化
├── icu_bidi/                # ICU 双向文本支持
├── imgui/                   # Dear ImGui 调试界面
├── libavif/                 # AVIF 图像编解码
├── libgav1/                 # AV1 解码器
├── libgrapheme/             # Unicode 字位分割
├── libjpeg-turbo/           # JPEG 编解码（SIMD 优化）
├── libjxl/                  # JPEG XL 编解码
├── libpng/                  # PNG 编解码
├── libwebp/                 # WebP 图像编解码
├── libyuv/                  # YUV 格式转换
├── lua/                     # Lua 脚本引擎
├── native_app_glue/         # Android Native Activity 粘合层
├── oboe/                    # Android 音频库
├── perfetto/                # Perfetto 性能跟踪
├── piex/                    # 预览图像提取器
├── spirv-cross/             # SPIR-V 着色器转译
├── vello/                   # Vello GPU 渲染器
├── wuffs/                   # Wuffs 安全编解码
└── zlib/                    # zlib 数据压缩
```

## 依赖分类

### 图像编解码
libpng、libjpeg-turbo、libwebp、libavif、libjxl、libgav1、wuffs、piex、dng_sdk、etc1

### 文本与字体
freetype2、harfbuzz、icu、icu4x、icu_bidi、libgrapheme

### GPU 与着色器
dawn、angle2、spirv-cross、vello、d3d12allocator

### 压缩与数据
zlib、brotli、expat

### 工具与平台
imgui、lua、perfetto、highway、cpu-features、oboe、native_app_glue、libyuv、delaunator

## 相关文档与参考

- DEPS 文件: Skia 根目录的 `DEPS`（定义外部依赖版本）
- Bazel 外部构建规则: `bazel/external/`
- Skia 构建文档: https://skia.org/docs/dev/build/
