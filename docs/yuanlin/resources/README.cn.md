# resources/ - 测试资源文件

## 概述

`resources/` 包含 Skia 测试和开发过程中使用的各种资源文件，包括图像、字体、
SVG 文件、Skottie 动画、SkSL 着色器、ICC 配置文件等。这些资源被单元测试、
GM（Gold Master）测试、性能基准测试和演示工具使用。

## 目录结构

```
resources/
├── BUILD.bazel              # Bazel 构建配置
├── README                   # 原始说明
├── android_fonts/           # Android 字体配置文件
├── diff_canvas_traces/      # Canvas 操作跟踪差异文件
├── empty_images/            # 空图像测试文件
├── fonts/                   # 测试字体文件集合
├── icc_profiles/            # ICC 色彩配置文件
├── images/                  # 测试图像文件
│   ├── *.png                # PNG 测试图像
│   ├── *.jpg                # JPEG 测试图像
│   ├── *.webp               # WebP 测试图像
│   ├── *.gif                # GIF 测试图像
│   └── *.bmp                # BMP 测试图像
├── invalid_images/          # 故意损坏的图像（用于健壮性测试）
├── skottie/                 # Skottie/Lottie 动画 JSON 文件
├── sksl/                    # SkSL 着色器测试文件
├── text/                    # 文本排版测试数据
├── Cowboy.svg               # SVG 测试文件
├── crbug769134.fil          # 回归测试文件
├── nov-talk-sequence.txt    # 演示序列数据
└── pdf_command_stream.txt   # PDF 命令流测试数据
```

## 关键目录说明

### images/
包含各种格式（PNG、JPEG、WebP、GIF、BMP、AVIF、JPEG XL 等）的测试图像，
覆盖不同色彩空间、位深度、压缩方式等变体。

### fonts/
测试字体集合，包含 TrueType、OpenType 等格式，用于文本渲染和字体处理的测试。

### invalid_images/
故意构造的损坏或畸形图像文件，用于测试编解码器的错误处理和安全性。

### skottie/
Lottie 格式的动画 JSON 文件，用于测试 Skottie 动画渲染引擎。

### sksl/
SkSL（Skia Shading Language）着色器源文件，用于测试着色器编译和渲染。

## 使用方式

在测试代码中通过 `GetResourcePath()` 函数获取资源路径：
```cpp
SkString path = GetResourcePath("images/test.png");
```

## 相关文档与参考

- Skia 测试框架: `tests/`
- GM 测试: `gm/`
- 性能基准: `bench/`
