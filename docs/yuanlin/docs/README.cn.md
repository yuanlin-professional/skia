# docs/ - Skia 技术文档

## 概述

`docs/` 目录包含 Skia 项目的技术文档，包括架构设计文档、API 使用示例和
中文翻译文档。该目录下的文档面向 Skia 开发者和集成者，帮助理解 Skia 的
内部架构和使用方法。

## 目录结构

```
docs/
├── architecture/            # 架构设计文档
│   ├── CPU.md               # CPU 后端架构详解
│   └── CPU.dot              # CPU 后端架构图（Graphviz）
├── examples/                # API 使用示例代码
│   ├── *.cpp                # 数百个 C++ 示例文件
│   └── ...                  # 覆盖 Bitmap、Canvas、Paint、Path 等
└── yuanlin/                 # 中文翻译文档
    ├── README.md            # 中文文档索引
    ├── src/                 # src/ 目录中文文档
    ├── include/             # include/ 目录中文文档
    ├── modules/             # modules/ 目录中文文档
    ├── tools/               # tools/ 目录中文文档
    └── ...                  # 其他目录的中文文档
```

## 关键文件

### architecture/CPU.md
Skia CPU 后端架构的详细技术文档，涵盖：
- 背景与术语定义（位图、混合模式、光栅化等）
- 完整的数据流程详解（从 API 调用到像素写入）
- 各组件说明：SkCanvas -> SkBitmapDevice -> SkDraw -> SkScan ->
  SkRasterPipelineBlitter -> SkRasterPipeline
- 文本渲染流程
- Paint 配置与效果管线

### examples/
数百个独立的 C++ 代码示例，每个文件演示 Skia API 的特定功能：
- Bitmap 操作（创建、像素操作、色彩空间）
- Canvas 绘图（路径、图像、文本）
- Paint 效果（着色器、滤镜、混合模式）
- Path 操作（构建、变换、布尔运算）

## 相关文档与参考

- Skia 官网文档: https://skia.org/docs/
- 站点源码: `site/`
- API 参考: `include/` 目录中的头文件
